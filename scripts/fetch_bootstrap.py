from fantasy_optimizer.api_client import fetch_bootstrap_static
from fantasy_optimizer.models.player import Player
from fantasy_optimizer.models.team import Team

# 1. Fetch raw data
data = fetch_bootstrap_static()

# 2. Parse players
players = []
for raw in data["elements"]:
    try:
        player = Player(**raw)
        players.append(player)
    except Exception as e:
        print(f"Failed to parse player ID {raw.get('id')}: {e}")

print(f"Parsed {len(players)} players successfully")

# 3. Parse teams
teams = [Team(**team) for team in data["teams"]]
id_to_team = {team.id: team for team in teams}

# 4. Show a few players with team names
for player in players[:5]:
    team_name = id_to_team[player.team].name
    print(f"{player.web_name} ({team_name}): {player.total_points} pts. Status: {player.status}")
