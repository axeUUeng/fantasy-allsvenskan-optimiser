#scripts/build_player_pool.py
from fantasy_optimizer.api_client import fetch_bootstrap_static
from fantasy_optimizer.models.player import Player
from fantasy_optimizer.models.team import Team
from pathlib import Path
import pandas as pd
import json

# Load all gameweek stats from cached files
DATA_DIR = Path(__file__).resolve().parents[2] / "data"
HISTORY_DIR = DATA_DIR / "player_histories"
all_stats = []

for file in HISTORY_DIR.glob("*.json"):
    with open(file) as f:
        raw = json.load(f)
        for gw in raw["history"]:
            all_stats.append(gw)

df = pd.DataFrame(all_stats)

# Load bootstrap player/team metadata
bootstrap = fetch_bootstrap_static()
players = [Player(**p) for p in bootstrap["elements"]]
teams = {t["id"]: t["name"] for t in bootstrap["teams"]}

# Compute rolling average points over last 3 GWs
latest_round = df["round"].max()
window = 3
df_recent = df[df["round"] > latest_round - window]

avg_points = (
    df_recent.groupby("element")["total_points"]
    .mean()
    .rename("expected_points")
)

# Merge with player metadata
player_df = pd.DataFrame([p.model_dump() for p in players])
player_pool = player_df.merge(avg_points, left_on="id", right_index=True, how="left")
player_pool["expected_points"] = player_pool["expected_points"].fillna(0)

# Add readable info
player_pool["team_name"] = player_pool["team"].map(teams)

# Map position ID to name
position_map = {1: "GK", 2: "DEF", 3: "MID", 4: "FWD"}
player_pool["position"] = player_pool["element_type"].map(position_map)

# Optional: scale price to millions
player_pool["price"] = player_pool["now_cost"] / 10

# Keep only useful columns
player_pool = player_pool[
    ["id", "web_name", "team_name", "position", "price", "expected_points"]
].sort_values("expected_points", ascending=False).reset_index(drop=True)
print(player_pool.head(10))
print(f"\n✅ Created player pool with {len(player_pool)} players.")
