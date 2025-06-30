# fantasy_optimizer/models/gameweek.py
from typing import Optional

from pydantic import BaseModel


class PlayerGameweekStat(BaseModel):
    element: int  # Player ID
    fixture: int  # Fixture ID
    opponent_team: int
    total_points: int
    was_home: bool
    kickoff_time: Optional[str]
    team_h_score: int
    team_a_score: int

    minutes: int
    goals_scored: int
    assists: int
    clean_sheets: int
    goals_conceded: int
    own_goals: int
    penalties_saved: int
    penalties_missed: int
    yellow_cards: int
    red_cards: int
    saves: int
    bonus: Optional[int] = 0

    round: int  # Gameweek number
