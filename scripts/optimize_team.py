import argparse
import json
from pathlib import Path

import cvxpy as cp
import pandas as pd
from sqlalchemy import text

from fantasy_optimizer.api_client import fetch_bootstrap_static
from fantasy_optimizer.db.database import engine

DATA_DIR = Path(__file__).resolve().parents[1] / "data"

# ----------------------------
# Configuration
# ----------------------------
USE_MARKET_ACTIVITY = True
USE_DISCIPLINE_CONSTRAINT = True
USE_PLAYING_CHANCE_WEIGHTS = False
USE_UPSIDE_SCORE = True

USE_BAYESIAN_FORECAST = False
USE_SIMULATION_FORECAST = True
assert not (
    USE_BAYESIAN_FORECAST and USE_SIMULATION_FORECAST
), "Only one forecast method can be used at a time."
TRANSFER_PENALTY_WEIGHT = 0
LIMIT_TRANSFERS = True
MAX_TRANSFERS = 2  # Set to 1 for one allowed transfer


# ----------------------------
# Helper Functions
# ----------------------------
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
    if USE_SIMULATION_FORECAST or USE_BAYESIAN_FORECAST:
        with engine.connect() as conn:
            forecast_df = pd.read_sql(
                text("SELECT player_id, expected_points FROM forecasts"), conn
            )
        forecast_df = forecast_df.rename(columns={"player_id": "id"})
        players = players.merge(forecast_df, on="id", how="inner")
    else:
        players["expected_points"] = players["form"].astype(float).fillna(0.0)
    return players


def enhance_features(players):
    if USE_MARKET_ACTIVITY:
        players["market_score"] = (
            players["transfers_in_event"] - players["transfers_out_event"]
        ) / 1000.0
    else:
        players["market_score"] = 0.0

    if USE_DISCIPLINE_CONSTRAINT:
        players["discipline_penalty"] = (
            players["yellow_cards"] + 2 * players["red_cards"]
        ).fillna(0.0)
    else:
        players["discipline_penalty"] = 0.0

    if USE_UPSIDE_SCORE:
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

    if USE_PLAYING_CHANCE_WEIGHTS:
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
    name_to_id = dict(zip(players["full_name"], players["player_id"]))

    if file_path:
        with open(file_path, "r") as f:
            team_data = json.load(f)
        current_team_ids = team_data["player_ids"]
        current_balance = float(team_data["balance"])
        return current_team_ids, current_balance

    # Fallback: interactive mode
    import questionary
    from InquirerPy.prompts.fuzzy import FuzzyPrompt

    sorted_names = players.sort_values("second_name")["full_name"].tolist()

    selected_names = FuzzyPrompt(
        message="Select your current team (15 players):",
        choices=sorted_names,
        multiselect=True,
        validate=lambda result: len(result) == 15,
        invalid_message="You must select exactly 15 players.",
    ).execute()

    current_team_ids = [name_to_id[name] for name in selected_names]
    current_balance = float(questionary.text("Enter your current balance:").ask())
    return current_team_ids, current_balance


def build_optimizer(player_pool, current_team_ids, current_balance):
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

    # Max 3 per team
    for team_id in player_pool["team"].unique():
        mask = (player_pool["team"] == team_id).astype(float).values
        constraints.append(mask @ x <= 3)

    # Transfer penalty
    change_vector = (
        (~player_pool["player_id"].isin(current_team_ids)).astype(float).values
    )

    if LIMIT_TRANSFERS:
        constraints.append(change_vector @ x <= MAX_TRANSFERS)

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
        + 0.08 * market @ x
        + 0.06 * upside @ x
        - 0.05 * discipline @ x
        - TRANSFER_PENALTY_WEIGHT * (change_vector @ x)
    )

    return cp.Problem(objective, constraints), x


def save_team_to_file(player_ids, balance, path: Path | str = "my_team.json"):
    with open(path, "w") as f:
        json.dump({"player_ids": player_ids, "balance": balance}, f, indent=2)


# ----------------------------
# Main Execution
# ----------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--team-file", type=str, help="Path to JSON file with current team"
    )
    parser.add_argument(
        "--save-team", action="store_true", help="Save the optimized team to a file"
    )
    args = parser.parse_args()

    players, team_name_to_id = load_player_data()

    players = apply_forecast(players)
    players = enhance_features(players)

    players = players.rename(columns={"id": "player_id"})
    excluded_team_ids = [
        team_name_to_id.get(name) for name in ["AIK", "Hammarby", "Malmö FF"]
    ]
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

    current_team_ids, current_balance = select_current_team(
        player_pool, file_path=args.team_file
    )
    if args.save_team:
        (Path(DATA_DIR) / "curr_team").mkdir(parents=True, exist_ok=True)
        save_team_to_file(
            current_team_ids,
            current_balance,
            path=DATA_DIR / "curr_team" / "myteam.json",
        )

    problem, x = build_optimizer(player_pool, current_team_ids, current_balance)
    result = problem.solve(solver=cp.ECOS_BB)

    if problem.status != cp.OPTIMAL:
        print(f"⚠️ Optimization failed: {problem.status}")
        exit(1)
    else:
        print(f"✅ Optimization successful! Objective value: {result:.2f}")

    assert x.value is not None
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
