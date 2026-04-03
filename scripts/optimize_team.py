import argparse
import json
from pathlib import Path

import cvxpy as cp
import pandas as pd
from sqlalchemy import text

from fantasy_optimizer.api_client import fetch_bootstrap_static
from fantasy_optimizer.config import load_config
from fantasy_optimizer.db.database import engine

DATA_DIR = Path(__file__).resolve().parents[1] / "data"


def load_player_data():
    bootstrap = fetch_bootstrap_static()
    players = pd.DataFrame(bootstrap["elements"])
    teams = pd.DataFrame(bootstrap["teams"])
    team_name_to_id = {row["name"]: row["id"] for _, row in teams.iterrows()}
    team_id_to_name = {v: k for k, v in team_name_to_id.items()}
    # Map team_division onto players so we can filter by division later
    team_id_to_division = (
        teams.set_index("id")["team_division"].to_dict()
        if "team_division" in teams.columns
        else {}
    )
    players["team_name"] = players["team"].map(team_id_to_name)  # type: ignore[arg-type]
    players["team_division"] = players["team"].map(team_id_to_division)  # type: ignore[arg-type]
    players["position"] = players["element_type"].map(
        {1: "GK", 2: "DEF", 3: "MID", 4: "FWD"}  # type: ignore[arg-type]
    )
    players["cost"] = players["now_cost"] / 10
    players["full_name"] = (
        players["first_name"].str.strip() + " " + players["second_name"].str.strip()
    )
    return players, team_name_to_id


def apply_forecast(players):
    with engine.connect() as conn:
        forecast_df = pd.read_sql(
            text("SELECT player_id, expected_points FROM forecasts"), conn
        )
    if forecast_df.empty:
        players["expected_points"] = players["form"].astype(float).fillna(0.0)
    else:
        forecast_df = forecast_df.rename(columns={"player_id": "id"})
        players = players.merge(forecast_df, on="id", how="inner")
    return players


def enhance_features(players, cfg):
    if cfg.use_market_activity:
        players["market_score"] = (
            players["transfers_in_event"] - players["transfers_out_event"]
        ) / 1000.0
    else:
        players["market_score"] = 0.0

    if cfg.use_discipline_constraint:
        players["discipline_penalty"] = (
            players["yellow_cards"] + 2 * players["red_cards"]
        ).fillna(0.0)
    else:
        players["discipline_penalty"] = 0.0

    if cfg.use_upside_score:
        is_def_or_gk = players["position"].isin(["GK", "DEF"])
        is_att = players["position"].isin(["MID", "FWD"])
        players["upside_score"] = (
            4 * players["goals_scored"]
            + 3 * players["assists"]
            + players["key_passes"].fillna(0)
            + players["attacking_bonus"].fillna(0)
            + is_def_or_gk
            * (
                players["defending_bonus"].fillna(0)
                + 0.2 * players["clearances_blocks_interceptions"].fillna(0)
            )
            + is_att * players["winning_goals"].fillna(0)
        )
    else:
        players["upside_score"] = 0.0

    if cfg.use_playing_chance_weights:
        playing_chance = players["chance_of_playing_next_round"].fillna(0.0) / 100.0
        players["expected_points"] *= playing_chance

    # Injury penalty
    status_multipliers = {
        "a": 1.0,  # available
        "d": 0.5,  # doubtful
        "i": 0.6,  # injured
        "u": 0.6,  # unfit
        "n": 0.5,  # not in squad
        "s": 0.6,  # suspended
    }
    players["expected_points"] *= players["status"].map(status_multipliers).fillna(0.6)
    return players


def select_current_team(players, file_path=None):
    import questionary
    from InquirerPy.prompts.fuzzy import FuzzyPrompt

    name_to_id = dict(zip(players["full_name"], players["player_id"]))
    id_to_name = dict(zip(players["player_id"], players["full_name"]))
    sorted_names = players.sort_values("second_name")["full_name"].tolist()

    if file_path:
        team_data = validate_team_file(file_path)
        current_team_ids = team_data["player_ids"]
        current_balance = float(team_data["balance"])
    else:
        current_team_ids = None
        current_balance = None

    max_transfers = None

    while True:
        if current_team_ids is None:
            selected_names = FuzzyPrompt(
                message="Select your current team (15 players):",
                choices=sorted_names,
                multiselect=True,
                validate=lambda result: len(result) == 15,
                invalid_message="You must select exactly 15 players.",
            ).execute()
            current_team_ids = [name_to_id[name] for name in selected_names]

        if current_balance is None:

            def _validate_balance(v):
                try:
                    val = float(v)
                except ValueError:
                    return "Enter a number (e.g. 2.5)."
                if val < 0:
                    return "Balance cannot be negative."
                return True

            current_balance = float(
                questionary.text(
                    "Enter your current balance (e.g. 2.5):",
                    validate=_validate_balance,
                ).ask()
            )

        if max_transfers is None:

            def _validate_transfers(v):
                if not v.isdigit():
                    return "Enter a non-negative integer."
                if int(v) < 0:
                    return "Transfers cannot be negative."
                if int(v) > 15:
                    return "Maximum 15 transfers allowed."
                return True

            max_transfers = int(
                questionary.text(
                    "How many transfers do you want to make?",
                    validate=_validate_transfers,
                ).ask()
            )

        # Confirmation summary
        print("\n--- Confirmation ---")
        print("Current team:")
        for pid in current_team_ids:
            print(f"  {id_to_name.get(pid, str(pid))}")
        print(f"Budget (bank balance): {current_balance:.1f}")
        print(f"Transfers: {max_transfers}")
        print("--------------------\n")

        confirmed = questionary.confirm("Is this correct?").ask()
        if confirmed:
            break

        adjust = questionary.select(
            "What would you like to change?",
            choices=["Team", "Balance", "Transfers"],
        ).ask()

        if adjust == "Team":
            current_team_ids = None
        elif adjust == "Balance":
            current_balance = None
        else:
            max_transfers = None

    return current_team_ids, current_balance, max_transfers


def build_optimizer(player_pool, current_team_ids, current_balance, max_transfers, cfg):
    n = len(player_pool)
    x = cp.Variable(n, boolean=True)
    constraints = []

    # Budget constraint
    team_value = player_pool[player_pool["player_id"].isin(current_team_ids)][
        "cost"
    ].sum()
    budget = team_value + current_balance
    constraints.append(player_pool["cost"].values @ x <= budget)

    # Team size
    constraints.append(cp.sum(x) == 15)

    # Position constraints
    for pos, count in [("GK", 2), ("DEF", 5), ("MID", 5), ("FWD", 3)]:
        mask = (player_pool["position"] == pos).astype(float).values
        constraints.append(mask @ x == count)

    # Max players per team
    for team_id in player_pool["team"].unique():
        mask = (player_pool["team"] == team_id).astype(float).values
        constraints.append(mask @ x <= cfg.max_players_per_team)

    # Transfer limit
    change_vector = (
        (~player_pool["player_id"].isin(current_team_ids)).astype(float).values
    )
    if cfg.limit_transfers:
        constraints.append(change_vector @ x <= max_transfers)

    expected = player_pool["expected_points"].values
    expected = expected / expected.max()
    market = player_pool["market_score"].values
    market = market / market.max() if market.max() > 0 else market
    upside = player_pool["upside_score"].values
    upside = upside / upside.max() if upside.max() > 0 else upside
    discipline = player_pool["discipline_penalty"].values
    discipline = discipline / discipline.max() if discipline.max() > 0 else discipline

    objective = cp.Maximize(
        expected @ x
        + cfg.market_weight * market @ x
        + cfg.upside_weight * upside @ x
        - cfg.discipline_weight * discipline @ x
        - cfg.transfer_penalty_weight * (change_vector @ x)
    )

    return cp.Problem(objective, constraints), x


def validate_team_file(path: str) -> dict:
    """Validate --team-file exists, is valid JSON, and contains exactly 15 players."""
    p = Path(path)
    if not p.exists():
        print(f"Error: team file not found: {path}")
        raise SystemExit(1)
    try:
        with open(p) as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error: team file is not valid JSON: {e}")
        raise SystemExit(1)
    if "player_ids" not in data or "balance" not in data:
        print("Error: team file must contain 'player_ids' and 'balance' keys.")
        raise SystemExit(1)
    if len(data["player_ids"]) != 15:
        print(f"Error: team file has {len(data['player_ids'])} players, expected 15.")
        raise SystemExit(1)
    if not isinstance(data["balance"], (int, float)) or data["balance"] < 0:
        print("Error: 'balance' must be a non-negative number.")
        raise SystemExit(1)
    return data


def save_team_to_file(player_ids, balance, path: Path | str = "my_team.json"):
    with open(path, "w") as f:
        json.dump({"player_ids": player_ids, "balance": balance}, f, indent=2)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--team-file", type=str, help="Path to JSON file with current team"
    )
    parser.add_argument(
        "--save-team", action="store_true", help="Save the optimized team to a file"
    )
    args = parser.parse_args()

    cfg = load_config()
    players, team_name_to_id = load_player_data()

    players = apply_forecast(players)
    players = enhance_features(players, cfg)

    players = players.rename(columns={"id": "player_id"})
    excluded_team_ids = [team_name_to_id.get(name) for name in cfg.excluded_teams]
    division_known = bool(players["team_division"].notna().any())
    if division_known:
        # Filter to Allsvenskan only once team_division is populated by the API
        player_pool = players[
            (~players["team"].isin(excluded_team_ids))
            & (players["can_select"])
            & (players["team_division"] == "allsvenskan")
        ].copy()
    else:
        player_pool = players[
            (~players["team"].isin(excluded_team_ids)) & (players["can_select"])
        ].copy()

    current_team_ids, current_balance, max_transfers = select_current_team(
        player_pool, file_path=args.team_file
    )

    save_path = Path(DATA_DIR) / "curr_team" / "myteam.json"
    if args.save_team:
        save_path.parent.mkdir(parents=True, exist_ok=True)
        save_team_to_file(current_team_ids, current_balance, path=save_path)
        print(f"Team saved to: {save_path}")

    problem, x = build_optimizer(
        player_pool, current_team_ids, current_balance, max_transfers, cfg
    )
    result = problem.solve(solver=cp.HIGHS)

    if problem.status != cp.OPTIMAL:
        print(f"Optimization failed: {problem.status}")
        if args.save_team:
            print(f"Input team retained at: {save_path}")
        exit(1)
    else:
        print(f"Optimization successful! Objective value: {result:.2f}")

    assert x.value is not None
    # x is a binary (0/1) decision variable, but solvers return floating-point values.
    # Values should be exactly 0 or 1, but may land at e.g. 0.9999 due to numerical
    # precision. Thresholding at 0.99 robustly converts these to True/False.
    player_pool["selected"] = x.value > 0.99
    optimal_team = (
        player_pool[player_pool["selected"]]
        .copy()
        .sort_values(["position", "expected_points"], ascending=[True, False])  # type: ignore[call-overload]
    )
    print("\n✅ Optimal team:")
    print(
        optimal_team[
            [
                "web_name",
                "full_name",
                "team_name",
                "position",
                "cost",
                "expected_points",
            ]
        ]
    )
