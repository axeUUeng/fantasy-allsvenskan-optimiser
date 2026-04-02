"""
Single entrypoint for all data ingestion.

Usage:
    uv run python scripts/ingest.py            # use cached player histories
    uv run python scripts/ingest.py --refresh  # force re-fetch everything from API
"""

import argparse

from data_fetching.fetch_bootstrap import main as fetch_bootstrap
from data_fetching.fetch_fixtures import main as fetch_fixtures
from data_fetching.fetch_player_histories import main as fetch_player_histories


def main(force_refresh: bool = False):
    print("=== Step 1/3: Players & Teams ===")
    fetch_bootstrap(force_refresh=force_refresh)

    print("\n=== Step 2/3: Fixtures ===")
    fetch_fixtures()

    print("\n=== Step 3/3: Player Gameweek Histories ===")
    fetch_player_histories(force_refresh=force_refresh)

    print("\nIngestion complete.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Force re-fetch from API instead of using cache",
    )
    args = parser.parse_args()
    main(force_refresh=args.refresh)
