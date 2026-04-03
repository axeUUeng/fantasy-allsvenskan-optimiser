"""Optimization configuration — loaded from config.toml in the project root."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path

_CONFIG_PATH = Path(__file__).resolve().parents[1] / "config.toml"


@dataclass
class OptimizationConfig:
    # Feature toggles
    use_market_activity: bool = True
    use_discipline_constraint: bool = True
    use_playing_chance_weights: bool = False
    use_upside_score: bool = True

    # Objective weights
    market_weight: float = 0.08
    upside_weight: float = 0.06
    discipline_weight: float = 0.05
    transfer_penalty_weight: float = 0.0

    # Transfer constraints
    limit_transfers: bool = True
    max_transfers: int = 15

    # Team selection
    excluded_teams: list[str] = field(default_factory=list)
    max_players_per_team: int = 3


def load_config(path: Path = _CONFIG_PATH) -> OptimizationConfig:
    if not path.exists():
        return OptimizationConfig()

    with path.open("rb") as f:
        data = tomllib.load(f)

    cfg = data.get("optimization", {})
    return OptimizationConfig(
        use_market_activity=cfg.get("use_market_activity", True),
        use_discipline_constraint=cfg.get("use_discipline_constraint", True),
        use_playing_chance_weights=cfg.get("use_playing_chance_weights", False),
        use_upside_score=cfg.get("use_upside_score", True),
        market_weight=cfg.get("market_weight", 0.08),
        upside_weight=cfg.get("upside_weight", 0.06),
        discipline_weight=cfg.get("discipline_weight", 0.05),
        transfer_penalty_weight=cfg.get("transfer_penalty_weight", 0.0),
        limit_transfers=cfg.get("limit_transfers", True),
        max_transfers=cfg.get("max_transfers", 15),
        excluded_teams=cfg.get("excluded_teams", []),
        max_players_per_team=cfg.get("max_players_per_team", 3),
    )
