"""Shared fixtures for the test suite."""

import pytest


@pytest.fixture()
def raw_stats_block():
    """47-line block representing one valid player as copy-pasted from the site."""
    values = [
        "Erik Svensson",
        "Mittfältare",
        "IFK Göteborg",
        "5.2",
        "14.3",
        "8.0",
        "120.0",
        "3.5",
        "22.5",
        "4",
        "3",
        "1.23",
        "21.0",
        "30.0",
        "6",
        "10",
        "5",
        "8",
        "0",
        "12",
        "14",
        "980",
        "2.10",
        "1.80",
        "1.50",
        "0.35",
        "0.30",
        "0.25",
        "4.50",
        "0.75",
        "0.40",
        "0.30",
        "8",
        "1.20",
        "15",
        "2.50",
        "6.00",
        "0.00",
        "10 %",
        "70.00",
        "85 %",
        "2",
        "0",
        "0.14",
        "0.00",
        "12",
        "0.86",
    ]
    assert len(values) == 47
    return values


@pytest.fixture()
def raw_stats_file(tmp_path, raw_stats_block):
    """Write two player blocks (separated by blank line) to a temp file."""
    block1 = raw_stats_block
    block2 = [
        "Anna Karlsson",
        "Försvarare",
        "Malmö FF",
        "4.8",
        "11.2",
        "7.5",
        "80.0",
        "2.0",
        "15.0",
        "1",
        "2",
        "1.05",
        "17.0",
        "24.0",
        "8",
        "4",
        "12",
        "3",
        "0",
        "10",
        "12",
        "840",
        "0.50",
        "0.80",
        "0.60",
        "0.10",
        "0.16",
        "0.12",
        "1.50",
        "0.30",
        "0.10",
        "0.16",
        "3",
        "0.60",
        "5",
        "1.00",
        "8.00",
        "0.00",
        "0 %",
        "72.00",
        "90 %",
        "1",
        "0",
        "0.08",
        "0.00",
        "6",
        "0.50",
    ]
    content = "\n".join(block1) + "\n\n" + "\n".join(block2) + "\n"
    p = tmp_path / "enhanced_stats.csv"
    p.write_text(content, encoding="utf-8")
    return p


@pytest.fixture()
def sample_players_df():
    """Small synthetic player DataFrame for optimizer tests."""
    import numpy as np
    import pandas as pd

    rng = np.random.default_rng(42)

    positions = ["GK"] * 4 + ["DEF"] * 10 + ["MID"] * 10 + ["FWD"] * 6
    teams = list(range(1, 9)) * 4 + list(range(1, 5))
    n = len(positions)

    df = pd.DataFrame(
        {
            "player_id": range(1, n + 1),
            "position": positions,
            "team": teams[:n],
            "cost": rng.uniform(4.0, 10.0, n).round(1),
            "expected_points": rng.uniform(2.0, 8.0, n).round(2),
            "market_score": rng.uniform(0, 1, n),
            "upside_score": rng.uniform(0, 1, n),
            "discipline_penalty": rng.uniform(0, 1, n),
        }
    )
    return df
