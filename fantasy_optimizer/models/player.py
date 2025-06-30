# fantasy_optimizer/models/player.py
from typing import Optional

from pydantic import BaseModel


class Player(BaseModel):
    id: int  # Unique player ID
    web_name: str  # Common display name (e.g., "Friedrich")
    first_name: str  # First name of the player
    second_name: str  # Last name of the player
    team: int  # Team ID (used to join with team data)
    element_type: int  # Position: 1=GK, 2=DEF, 3=MID, 4=FWD
    now_cost: int  # Current price in tenths of a million (e.g., 61 = 6.1M)

    status: str  # Player availability: 'a'=available, 'i'=injured, 'd'=doubtful, etc.
    total_points: int  # Cumulative fantasy points this season
    minutes: int  # Total minutes played
    goals_scored: int  # Goals scored
    assists: int  # Assists
    clean_sheets: int  # Clean sheets (GK/DEF only, but available for all)
    goals_conceded: int  # Goals conceded while on the pitch
    own_goals: int  # Own goals
    penalties_saved: int  # Penalty saves (GK only)
    penalties_missed: int  # Penalties missed by player
    yellow_cards: int  # Yellow cards received
    red_cards: int  # Red cards received
    saves: int  # Saves made (GK only)

    bonus: Optional[int] = (
        0  # Bonus points awarded by the BPS system (may be missing for new players)
    )

    form: Optional[str]  # Short-term form (last few games), string like "1.1"
    selected_by_percent: Optional[
        str
    ]  # Percentage of managers owning the player, as string like "7.8"
    points_per_game: Optional[str]  # Avg. points per game, string like "4.6"
    ep_next: Optional[str]  # Expected points next GW (if available)
    ep_this: Optional[str]  # Expected points this GW (if available)
