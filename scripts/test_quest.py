import questionary
import pandas as pd
from pathlib import Path
from fantasy_optimizer.api_client import fetch_bootstrap_static

DATA_DIR = Path(__file__).parent.parent / "data"

# Load player pool from the last modeling step (assuming it was saved or passed in)
bootstrap = fetch_bootstrap_static()
players = pd.DataFrame(bootstrap["elements"])
print(players.columns)
sorted_players = players.sort_values('second_name')

# Concatenate 'first_name' and 'web_name' into a list
player_names = [
    f"{row['first_name']} {row['second_name']}" for _, row in sorted_players.iterrows()
]

selected_names = questionary.checkbox(
    "Select your current team (15 players):",
    choices=player_names
).ask()

print("You selected:", selected_names)
