import cvxpy as cp
from pathlib import Path
import pandas as pd
import questionary

from fantasy_optimizer.api_client import fetch_bootstrap_static

DATA_DIR = Path(__file__).parent.parent / "data"

# Load player pool from the last modeling step (assuming it was saved or passed in)
bootstrap = fetch_bootstrap_static()
players = pd.DataFrame(bootstrap["elements"])
teams = pd.DataFrame(bootstrap["teams"])
team_id_to_name = {row["id"]: row["name"] for _, row in teams.iterrows()}
team_name_to_id = {v: k for k, v in team_id_to_name.items()}

# Disallowed teams
excluded_team_ids = [team_name_to_id[name] for name in ["AIK", "Hammarby", "Malmö FF"]]

forecast_df = pd.read_parquet(DATA_DIR / "player_forecasts.parquet")
expected_points = forecast_df.rename(columns={"player_id": "element"})

players["position"] = players["element_type"].map({1: "GK", 2: "DEF", 3: "MID", 4: "FWD"})
players["team_name"] = players["team"].map(team_id_to_name)
players = players.merge(expected_points, left_on="id", right_on="element", how="inner")
# Apply penalty to injured players
penalty_factor = 0.5
players.loc[players["status"] == "d", "expected_points"] *= penalty_factor


players["cost"] = players["now_cost"] / 10
players = players.rename(columns={"id": "player_id", "web_name": "name"})
player_pool = players[[
    "player_id", "name", "team", "team_name", "position", "cost", "total_points", "status"
]].rename(columns={
    "total_points": "expected_points"
})

# Filter out excluded teams
player_pool = player_pool[~player_pool["team"].isin(excluded_team_ids)].reset_index(drop=True)
player_pool = player_pool[player_pool["player_id"].isin(
    players[players["status"].isin(["a", "d"])]["player_id"]
)]



# Decision variable: binary for each player
n = len(player_pool)
x = cp.Variable(n, boolean=True)

# Constraints
constraints = []
sorted_players = players.sort_values('second_name')

# Create mapping from full name to player_id
players["full_name"] = players["first_name"].str.strip() + " " + players["second_name"].str.strip()
name_to_id = dict(zip(players["full_name"], players["player_id"]))

# Create display list
player_names = sorted(players["full_name"].tolist())  # alphabetically sorted for easier browsing

# Prompt user to select players
selected_names = questionary.checkbox(
    "Select your current team (15 players):",
    choices=player_names
).ask()

# Error handling
if not selected_names or len(selected_names) != 15:
    raise ValueError("⚠️ You must select exactly 15 players.")

# Map names to IDs
current_team_ids = [name_to_id[name] for name in selected_names]

print("✅ Your team", selected_names)

current_balance = input("Enter your current balance: ")

# Budget: total cost ≤ 100.0
total_team_value = players[players["player_id"].isin(current_team_ids)]["cost"].sum()
budget = total_team_value + current_balance
constraints.append(player_pool["cost"].values @ x <= budget)


# Team size: exactly 15 players
constraints.append(cp.sum(x) == 15)

# Position constraints
for pos, count in [("GK", 2), ("DEF", 5), ("MID", 5), ("FWD", 3)]:
    mask = (player_pool["position"] == pos).astype(float).values
    constraints.append(mask @ x == count)

# Max 3 players per team
for team_id in player_pool["team"].unique():
    mask = (player_pool["team"] == team_id).astype(float).values
    constraints.append(mask @ x <= 3)


# Soft constraint: minimize number of changes 
transfer_penalty = 0.5  # weight of penalty per transfer
change_vector = (~player_pool["player_id"].isin(current_team_ids)).astype(float).values
objective = cp.Maximize(player_pool["expected_points"].values @ x - transfer_penalty * (change_vector @ x))
# # Objective: maximize expected points
# objective = cp.Maximize(player_pool["expected_points"].values @ x)

# Problem definition and solve
problem = cp.Problem(objective, constraints)
problem.solve(solver=cp.ECOS_BB, verbose=False)

# Extract selected team
player_pool["selected"] = x.value > 0.99
optimal_team = player_pool[player_pool["selected"]].copy().sort_values("position")

print(optimal_team)
