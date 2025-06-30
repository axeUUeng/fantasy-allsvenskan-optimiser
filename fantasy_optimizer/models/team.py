# fantasy_optimizer/models/team.py
from typing import Optional

from pydantic import BaseModel


class Team(BaseModel):
    id: int  # Team ID (used to link players to teams)
    name: str  # Full team name (e.g., "Djurgården")
    short_name: str  # Abbreviated name (e.g., "DIF")
    strength: Optional[int] = None  # Composite strength rating (optional, 1–5 scale)
