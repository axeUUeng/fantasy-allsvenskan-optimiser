# fantasy_optimizer/api_client.py
import json
import time
from pathlib import Path

from fantasy_optimizer.http import fetch_with_retry

DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)

HISTORY_DIR = DATA_DIR / "player_histories"
HISTORY_DIR.mkdir(exist_ok=True)


def fetch_bootstrap_static(force_refresh: bool = False) -> dict:
    file_path = DATA_DIR / "bootstrap-static.json"

    if file_path.exists() and not force_refresh:
        with open(file_path, "r") as f:
            return json.load(f)

    data = fetch_with_retry("https://fantasy.allsvenskan.se/api/bootstrap-static/")
    with open(file_path, "w") as f:
        json.dump(data, f, indent=2)
    return data


def fetch_player_history(player_id: int, force_refresh: bool = False) -> dict:
    """Fetch and cache per-player gameweek history from the API."""
    file_path = HISTORY_DIR / f"{player_id}.json"

    if file_path.exists() and not force_refresh:
        with open(file_path) as f:
            return json.load(f)

    data = fetch_with_retry(
        f"https://fantasy.allsvenskan.se/api/element-summary/{player_id}/"
    )
    with open(file_path, "w") as f:
        json.dump(data, f, indent=2)
    time.sleep(0.05)
    return data
