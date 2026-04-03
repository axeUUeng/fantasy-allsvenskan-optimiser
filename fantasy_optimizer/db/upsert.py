from sqlalchemy.dialects.postgresql import insert

from fantasy_optimizer.db.database import engine
from fantasy_optimizer.db.models import (
    EnhancedStatRow,
    FixtureRow,
    ForecastRow,
    PlayerGameweekStatRow,
    PlayerRow,
    TeamRow,
)


def upsert_teams(teams: list[dict]):
    with engine.begin() as conn:
        stmt = insert(TeamRow).values(teams)
        stmt = stmt.on_conflict_do_update(
            index_elements=["id"],
            set_={c: stmt.excluded[c] for c in teams[0] if c != "id"},
        )
        conn.execute(stmt)


def upsert_players(players: list[dict]):
    with engine.begin() as conn:
        stmt = insert(PlayerRow).values(players)
        stmt = stmt.on_conflict_do_update(
            index_elements=["id"],
            set_={c: stmt.excluded[c] for c in players[0] if c != "id"},
        )
        conn.execute(stmt)


def upsert_gameweek_stats(stats: list[dict]):
    """Upsert on (element, fixture) — one row per player per match."""
    with engine.begin() as conn:
        stmt = insert(PlayerGameweekStatRow).values(stats)
        stmt = stmt.on_conflict_do_update(
            constraint="uq_player_fixture",
            set_={
                c: stmt.excluded[c] for c in stats[0] if c not in ("element", "fixture")
            },
        )
        conn.execute(stmt)


def upsert_forecasts(forecasts: list[dict]):
    """Upsert on player_id — replaces the forecast each run."""
    with engine.begin() as conn:
        stmt = insert(ForecastRow).values(forecasts)
        stmt = stmt.on_conflict_do_update(
            index_elements=["player_id"],
            set_={"expected_points": stmt.excluded.expected_points},
        )
        conn.execute(stmt)


def upsert_enhanced_stats(stats: list[dict]):
    """Upsert on name — replaces all stats each weekly import."""
    with engine.begin() as conn:
        stmt = insert(EnhancedStatRow).values(stats)
        stmt = stmt.on_conflict_do_update(
            index_elements=["name"],
            set_={c: stmt.excluded[c] for c in stats[0] if c != "name"},
        )
        conn.execute(stmt)


def upsert_fixtures(fixtures: list[dict]):
    """Upsert on (season, round, team, was_home)."""
    with engine.begin() as conn:
        stmt = insert(FixtureRow).values(fixtures)
        stmt = stmt.on_conflict_do_update(
            constraint="uq_fixture_team_round",
            set_={
                c: stmt.excluded[c]
                for c in fixtures[0]
                if c not in ("season", "round", "team", "was_home")
            },
        )
        conn.execute(stmt)
