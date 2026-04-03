"""Tests for fantasy_optimizer/config.py"""

from fantasy_optimizer.config import OptimizationConfig, load_config


def test_defaults():
    cfg = OptimizationConfig()
    assert cfg.market_weight == 0.08
    assert cfg.upside_weight == 0.06
    assert cfg.discipline_weight == 0.05
    assert cfg.transfer_penalty_weight == 0.0
    assert cfg.limit_transfers is True
    assert cfg.max_transfers == 15
    assert cfg.max_players_per_team == 3
    assert cfg.excluded_teams == []
    assert cfg.use_market_activity is True
    assert cfg.use_upside_score is True
    assert cfg.use_playing_chance_weights is False


def test_load_config_no_file_returns_defaults(tmp_path):
    cfg = load_config(tmp_path / "nonexistent.toml")
    assert cfg == OptimizationConfig()


def test_load_config_reads_toml(tmp_path):
    toml = tmp_path / "config.toml"
    toml.write_text(
        '[optimization]\nexcluded_teams = ["AIK"]\nmax_transfers = 3\nmarket_weight = 0.10\n',
        encoding="utf-8",
    )
    cfg = load_config(toml)
    assert cfg.excluded_teams == ["AIK"]
    assert cfg.max_transfers == 3
    assert cfg.market_weight == 0.10


def test_load_config_partial_toml_keeps_defaults(tmp_path):
    toml = tmp_path / "config.toml"
    toml.write_text("[optimization]\nmax_transfers = 5\n", encoding="utf-8")
    cfg = load_config(toml)
    assert cfg.max_transfers == 5
    assert cfg.market_weight == 0.08  # default preserved


def test_load_config_empty_toml_returns_defaults(tmp_path):
    toml = tmp_path / "config.toml"
    toml.write_text("", encoding="utf-8")
    cfg = load_config(toml)
    assert cfg == OptimizationConfig()
