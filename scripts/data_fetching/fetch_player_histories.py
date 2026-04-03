from time import sleep

from loguru import logger

from fantasy_optimizer.api_client import fetch_bootstrap_static, fetch_player_history
from fantasy_optimizer.db.upsert import upsert_gameweek_stats
from fantasy_optimizer.models.gameweek import PlayerGameweekStat

BATCH_SIZE = 50


def main(force_refresh: bool = False):
    data = fetch_bootstrap_static(force_refresh=force_refresh)
    player_ids = [p["id"] for p in data["elements"]]
    print(
        f"Fetching gameweek histories for {len(player_ids)} players (force_refresh={force_refresh})"
    )

    batch = []
    total_saved = 0

    for i, pid in enumerate(player_ids):
        history_json = fetch_player_history(pid, force_refresh=force_refresh)
        for raw_gw in history_json["history"]:
            try:
                stat = PlayerGameweekStat(**raw_gw)
                batch.append(stat.model_dump())
            except Exception as e:
                logger.warning("Failed to parse GW stat for player %s: %s", pid, e)
        sleep(0.05)

        if len(batch) >= BATCH_SIZE:
            upsert_gameweek_stats(batch)
            total_saved += len(batch)
            batch = []
            print(f"  {total_saved} stats saved ({i + 1}/{len(player_ids)} players)...")

    if batch:
        upsert_gameweek_stats(batch)
        total_saved += len(batch)

    print(f"Upserted {total_saved} player gameweek stats to DB")


if __name__ == "__main__":
    main()
