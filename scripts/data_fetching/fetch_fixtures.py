import json
import time
from pathlib import Path

import pandas as pd
import requests

DATA_DIR = Path(__file__).resolve().parents[2] / "data"


def fetch_fixtures() -> list[dict]:
    url = "https://fantasy.allsvenskan.se/api/fixtures/"
    response = requests.get(url, timeout=15)
    response.raise_for_status()
    data = response.json()

    with open(DATA_DIR / "fixtures.json", "w") as f:
        json.dump(data, f, indent=2)

    time.sleep(0.3)
    return data


def build_fixture_frame(data: list[dict]) -> pd.DataFrame:
    season = next(int(f["kickoff_time"][:4]) for f in data if f.get("kickoff_time"))

    rows = []
    for fixture in data:
        base = {
            "season": season,
            "round": fixture["event"],
        }
        rows.append(
            {
                **base,
                "team": fixture["team_h"],
                "opponent_team": fixture["team_a"],
                "was_home": True,
                "team_score": fixture["team_h_score"],
                "opponent_score": fixture["team_a_score"],
            }
        )
        rows.append(
            {
                **base,
                "team": fixture["team_a"],
                "opponent_team": fixture["team_h"],
                "was_home": False,
                "team_score": fixture["team_a_score"],
                "opponent_score": fixture["team_h_score"],
            }
        )

    df = pd.DataFrame(rows)
    return df.drop_duplicates(subset=["season", "round", "team", "was_home"])


def main():
    from fantasy_optimizer.db.upsert import upsert_fixtures

    data = fetch_fixtures()
    df = build_fixture_frame(data)
    upsert_fixtures(df.to_dict(orient="records"))
    print(f"Upserted {len(df)} fixture rows to DB")


if __name__ == "__main__":
    main()
