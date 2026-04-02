# fantasy_optimizer/api_client.py
import json
import time
from pathlib import Path

import requests

DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)

HISTORY_DIR = DATA_DIR / "player_histories"
HISTORY_DIR.mkdir(exist_ok=True)


def fetch_bootstrap_static(force_refresh: bool = False) -> dict:
    file_path = DATA_DIR / "bootstrap-static.json"

    if file_path.exists() and not force_refresh:
        with open(file_path, "r") as f:
            return json.load(f)

    url = "https://fantasy.allsvenskan.se/api/bootstrap-static/"
    last_exc: Exception = RuntimeError("No attempts made")
    for attempt in range(3):
        try:
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
            with open(file_path, "w") as f:
                json.dump(data, f, indent=2)
            return data
        except requests.exceptions.HTTPError as e:
            last_exc = e
            if attempt < 2:
                time.sleep(2)
    raise last_exc


def fetch_player_history(player_id: int, force_refresh: bool = False) -> dict:
    """Fetch and cache per-player gameweek history from the API."""
    file_path = HISTORY_DIR / f"{player_id}.json"

    if file_path.exists() and not force_refresh:
        with open(file_path) as f:
            return json.load(f)

    url = f"https://fantasy.allsvenskan.se/api/element-summary/{player_id}/"
    last_exc: Exception = RuntimeError("No attempts made")
    for attempt in range(4):
        try:
            response = requests.get(url, timeout=15)
            response.raise_for_status()
            data = response.json()
            with open(file_path, "w") as f:
                json.dump(data, f, indent=2)
            time.sleep(0.05)
            return data
        except (requests.exceptions.HTTPError, requests.exceptions.Timeout) as e:
            last_exc = e
            if attempt < 3:
                time.sleep(2**attempt)
    raise last_exc
