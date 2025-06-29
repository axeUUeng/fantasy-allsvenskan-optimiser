# scripts/fetch_fixtures.py
import requests
import pandas as pd
from pathlib import Path
import json
import time

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
FIXTURE_FILE = DATA_DIR / "fixtures.parquet"
FIXTURE_JSON = DATA_DIR / "fixtures.json"

TEAM_MAP_FILE = DATA_DIR / "bootstrap-static.json"


def fetch_fixtures():
    print("📡 Fetching fixture data...")
    url = "https://fantasy.allsvenskan.se/api/fixtures/"
    response = requests.get(url)
    response.raise_for_status()
    data = response.json()

    with open(FIXTURE_JSON, "w") as f:
        json.dump(data, f, indent=2)

    time.sleep(0.3)  # Be polite to the server

    return data


def build_fixture_frame(data):
    rows = []
    for fixture in data:
        event = fixture["event"]
        team_h = fixture["team_h"]
        team_a = fixture["team_a"]

        # Home team rows
        rows.append({
            "round": event,
            "team": team_h,
            "opponent_team": team_a,
            "was_home": True,
            "team_score": fixture["team_h_score"],
            "opponent_score": fixture["team_a_score"]
        })

        # Away team rows
        rows.append({
            "round": event,
            "team": team_a,
            "opponent_team": team_h,
            "was_home": False,
            "team_score": fixture["team_a_score"],
            "opponent_score": fixture["team_h_score"]
        })

    return pd.DataFrame(rows)


def main():
    fixtures = fetch_fixtures()
    df = build_fixture_frame(fixtures)
    df.to_parquet(FIXTURE_FILE, index=False)
    print(f"✅ Saved fixture data to {FIXTURE_FILE} with {len(df)} rows")


if __name__ == "__main__":
    main()
