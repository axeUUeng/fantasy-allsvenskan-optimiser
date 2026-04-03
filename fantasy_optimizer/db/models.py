from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    Integer,
    String,
    UniqueConstraint,
    func,
)

from fantasy_optimizer.db.database import Base


class TeamRow(Base):
    __tablename__ = "teams"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    short_name = Column(String, nullable=False)
    strength = Column(Integer, nullable=True)
    team_division = Column(String, nullable=True)


class PlayerRow(Base):
    __tablename__ = "players"

    id = Column(Integer, primary_key=True)
    web_name = Column(String, nullable=False)
    first_name = Column(String, nullable=False)
    second_name = Column(String, nullable=False)
    team = Column(Integer, nullable=False)
    element_type = Column(Integer, nullable=False)
    now_cost = Column(Integer, nullable=False)
    status = Column(String, nullable=False)
    total_points = Column(Integer, nullable=False)
    minutes = Column(Integer, nullable=False)
    goals_scored = Column(Integer, nullable=False)
    assists = Column(Integer, nullable=False)
    clean_sheets = Column(Integer, nullable=False)
    goals_conceded = Column(Integer, nullable=False)
    own_goals = Column(Integer, nullable=False)
    penalties_saved = Column(Integer, nullable=False)
    penalties_missed = Column(Integer, nullable=False)
    yellow_cards = Column(Integer, nullable=False)
    red_cards = Column(Integer, nullable=False)
    saves = Column(Integer, nullable=False)
    bonus = Column(Integer, nullable=True)
    attacking_bonus = Column(Integer, nullable=True)
    defending_bonus = Column(Integer, nullable=True)
    winning_goals = Column(Integer, nullable=True)
    clearances_blocks_interceptions = Column(Integer, nullable=True)
    form = Column(String, nullable=True)
    selected_by_percent = Column(String, nullable=True)
    points_per_game = Column(String, nullable=True)
    ep_next = Column(String, nullable=True)
    ep_this = Column(String, nullable=True)


class PlayerGameweekStatRow(Base):
    __tablename__ = "player_gameweek_stats"

    id = Column(Integer, primary_key=True, autoincrement=True)
    element = Column(Integer, nullable=False)
    fixture = Column(Integer, nullable=False)
    opponent_team = Column(Integer, nullable=False)
    total_points = Column(Integer, nullable=False)
    was_home = Column(Boolean, nullable=False)
    kickoff_time = Column(String, nullable=True)
    team_h_score = Column(Integer, nullable=True)
    team_a_score = Column(Integer, nullable=True)
    minutes = Column(Integer, nullable=False)
    goals_scored = Column(Integer, nullable=False)
    assists = Column(Integer, nullable=False)
    clean_sheets = Column(Integer, nullable=False)
    goals_conceded = Column(Integer, nullable=False)
    own_goals = Column(Integer, nullable=False)
    penalties_saved = Column(Integer, nullable=False)
    penalties_missed = Column(Integer, nullable=False)
    yellow_cards = Column(Integer, nullable=False)
    red_cards = Column(Integer, nullable=False)
    saves = Column(Integer, nullable=False)
    bonus = Column(Integer, nullable=True)
    round = Column(Integer, nullable=False)

    __table_args__ = (UniqueConstraint("element", "fixture", name="uq_player_fixture"),)


class FixtureRow(Base):
    __tablename__ = "fixtures"

    id = Column(Integer, primary_key=True, autoincrement=True)
    season = Column(Integer, nullable=False)
    round = Column(Integer, nullable=False)
    team = Column(Integer, nullable=False)
    opponent_team = Column(Integer, nullable=False)
    was_home = Column(Boolean, nullable=False)
    team_score = Column(Integer, nullable=True)
    opponent_score = Column(Integer, nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "season", "round", "team", "was_home", name="uq_fixture_team_round"
        ),
    )


class ForecastRow(Base):
    __tablename__ = "forecasts"

    player_id = Column(Integer, primary_key=True)
    expected_points = Column(Float, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class EnhancedStatRow(Base):
    __tablename__ = "enhanced_stats"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False, unique=True)
    position = Column(String, nullable=True)
    team = Column(String, nullable=True)
    xFP = Column(Float, nullable=True)
    xFP_3 = Column(Float, nullable=True)
    xFP_5 = Column(Float, nullable=True)
    xFP_7 = Column(Float, nullable=True)
    pris = Column(Float, nullable=True)
    mal = Column(Float, nullable=True)
    assist = Column(Float, nullable=True)
    xG = Column(Float, nullable=True)
    xA = Column(Float, nullable=True)
    ingested_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
