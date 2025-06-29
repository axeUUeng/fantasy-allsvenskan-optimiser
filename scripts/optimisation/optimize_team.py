import cvxpy as cp
from pathlib import Path
import pandas as pd
import questionary
from InquirerPy import inquirer


from fantasy_optimizer.api_client import fetch_bootstrap_static

DATA_DIR = Path(__file__).resolve().parents[2] / "data"

# ----------------------------
# Configuration
# ----------------------------
USE_MARKET_ACTIVITY = True
USE_DISCIPLINE_CONSTRAINT = True
USE_PLAYING_CHANCE_WEIGHTS = True
USE_UPSIDE_SCORE = True
USE_BAYESIAN_FORECAST = True
TRANSFER_PENALTY_WEIGHT = 0.1
LIMIT_TRANSFERS = True
MAX_TRANSFERS = 1  # Set to 1 for one allowed transfer

# ----------------------------
# Helper Functions
# ----------------------------
def load_player_data():
    bootstrap = fetch_bootstrap_static()
    players = pd.DataFrame(bootstrap["elements"])
    teams = pd.DataFrame(bootstrap["teams"])
    team_name_to_id = {row["name"]: row["id"] for _, row in teams.iterrows()}
    team_id_to_name = {v: k for k, v in team_name_to_id.items()}
    players["team_name"] = players["team"].map(team_id_to_name)
    players["position"] = players["element_type"].map({1: "GK", 2: "DEF", 3: "MID", 4: "FWD"})
    players["cost"] = players["now_cost"] / 10
    players["full_name"] = players["first_name"].str.strip() + " " + players["second_name"].str.strip()
    return players, team_name_to_id


def apply_forecast(players):
    if USE_BAYESIAN_FORECAST:
        forecast_df = pd.read_parquet(DATA_DIR / "player_forecasts.parquet")
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
        players["upside_score"] = (
            4 * players["goals_scored"] + 3 * players["assists"] + players["key_passes"]
        ).fillna(0.0)
    else:
        players["upside_score"] = 0.0

    if USE_PLAYING_CHANCE_WEIGHTS:
        playing_chance = players["chance_of_playing_next_round"].fillna(0.0) / 100.0
        players["expected_points"] *= playing_chance

    # Injury penalty
    injured = players["status"] == "d"
    players.loc[injured, "expected_points"] *= 0.5
    return players


def select_current_team(players):
    
    name_to_id = dict(zip(players["full_name"], players["player_id"]))
    sorted_names = players.sort_values("second_name")["full_name"].tolist()

    selected_names = inquirer.fuzzy(
        message="Select your current team (15 players):",
        choices=sorted_names,
        multiselect=True,
        validate=lambda result: len(result) == 15 or "You must select exactly 15 players.",
    ).execute()

    current_team_ids = [name_to_id[name] for name in selected_names]
    current_balance = float(questionary.text("Enter your current balance:").ask())
    return current_team_ids, current_balance


def build_optimizer(player_pool, current_team_ids, current_balance):
    n = len(player_pool)
    x = cp.Variable(n, boolean=True)
    constraints = []

    # Budget constraint
    team_value = player_pool[player_pool["player_id"].isin(current_team_ids)]["cost"].sum()
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
    change_vector = (~player_pool["player_id"].isin(current_team_ids)).astype(float).values
    if LIMIT_TRANSFERS:
        constraints.append(change_vector @ x <= MAX_TRANSFERS)

    expected = player_pool["expected_points"].values
    market = player_pool["market_score"].values
    upside = player_pool["upside_score"].values
    discipline = player_pool["discipline_penalty"].values

    objective = cp.Maximize(
        expected @ x
        + 0.008 * market @ x
        + 0.006 * upside @ x
        - 0.005 * discipline @ x
        - TRANSFER_PENALTY_WEIGHT * (change_vector @ x)
    )

    return cp.Problem(objective, constraints), x


# ----------------------------
# Main Execution
# ----------------------------
if __name__ == "__main__":
    players, team_name_to_id = load_player_data()
    players = apply_forecast(players)
    players = enhance_features(players)

    # Build final player pool
    players = players.rename(columns={"id": "player_id"})
    
    excluded_team_ids = [team_name_to_id[name] for name in ["AIK", "Hammarby", "Malmö FF"]]
    player_pool = players[
        (~players["team"].isin(excluded_team_ids)) & players["status"].isin(["a", "d"])
    ].copy()

    current_team_ids, current_balance = select_current_team(players)
    problem, x = build_optimizer(player_pool, current_team_ids, current_balance)
    problem.solve(solver=cp.ECOS_BB, verbose=False)

    player_pool["selected"] = x.value > 0.99
    optimal_team = player_pool[player_pool["selected"]].copy().sort_values("position")
    print("\n✅ Optimal team:")
    print(optimal_team[["full_name", "team_name", "position", "cost", "expected_points"]])
