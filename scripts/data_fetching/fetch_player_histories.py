# sctipts/fetch_player_histories.py

import pandas as pd

from fantasy_optimizer.api_client import fetch_bootstrap_static, fetch_player_history
from fantasy_optimizer.models.gameweek import PlayerGameweekStat

data = fetch_bootstrap_static()
player_ids = [p["id"] for p in data["elements"]]

all_stats = []

for pid in player_ids:
    history_json = fetch_player_history(pid)
    for raw_gw in history_json["history"]:
        try:
            stat = PlayerGameweekStat(**raw_gw)
            all_stats.append(stat.model_dump())
        except Exception as e:
            print(f"Failed to parse GW stat for player {pid}: {e}")

df = pd.DataFrame(all_stats)
df.to_parquet("data/player_gameweek_stats.parquet")

print(df.head())
print(f"\n✅ Loaded {len(df)} player gameweek stats into DataFrame")
