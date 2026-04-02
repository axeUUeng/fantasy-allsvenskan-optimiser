from fantasy_optimizer.api_client import fetch_bootstrap_static
from fantasy_optimizer.db.upsert import upsert_players, upsert_teams
from fantasy_optimizer.models.player import Player
from fantasy_optimizer.models.team import Team


def main(force_refresh: bool = True):
    data = fetch_bootstrap_static(force_refresh=force_refresh)

    teams = []
    for raw in data["teams"]:
        try:
            teams.append(Team(**raw).model_dump())
        except Exception as e:
            print(f"Failed to parse team ID {raw.get('id')}: {e}")

    upsert_teams(teams)
    print(f"Upserted {len(teams)} teams to DB")

    players = []
    for raw in data["elements"]:
        try:
            players.append(Player(**raw).model_dump())
        except Exception as e:
            print(f"Failed to parse player ID {raw.get('id')}: {e}")

    upsert_players(players)
    print(f"Upserted {len(players)} players to DB")


if __name__ == "__main__":
    main()
