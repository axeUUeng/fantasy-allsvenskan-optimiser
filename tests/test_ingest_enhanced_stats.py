"""Tests for scripts/ingest_enhanced_stats.py"""

import csv
from pathlib import Path
from unittest.mock import patch

import pytest

from scripts.ingest_enhanced_stats import DB_COLS, _coerce, load

# --- _coerce ---


def test_coerce_float_col():
    assert _coerce("xFP", "7.4") == 7.4


def test_coerce_float_col_empty_returns_none():
    assert _coerce("xFP", "") is None


def test_coerce_float_col_invalid_returns_none():
    assert _coerce("xFP", "n/a") is None


def test_coerce_string_col():
    assert _coerce("name", "Erik Svensson") == "Erik Svensson"


def test_coerce_string_col_empty_returns_none():
    assert _coerce("name", "") is None


# --- load ---


def _write_clean_csv(path: Path, rows: list[dict]):
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _make_row(name: str, xfp: str = "5.0") -> dict:
    """Minimal row with all CSV columns (extras ignored by load)."""
    base = {
        col: ""
        for col in [
            "name",
            "position",
            "team",
            "xFP",
            "xFP_3",
            "pris",
            "poang",
            "form",
            "agarandel",
            "mal",
            "assist",
            "xFP_per_pris",
            "xFP_5",
            "xFP_7",
            "clean_sheets",
            "off_bonus",
            "def_bonus",
            "inslappta_mal",
            "raddningar",
            "starter",
            "matcher",
            "minuter",
            "xG",
            "xA",
            "xT",
            "xG_PM",
            "xA_PM",
            "xT_PM",
            "xAG",
            "xAG_PM",
            "mal_PM",
            "assist_PM",
            "skottassist",
            "skottassist_PM",
            "fasta_sit",
            "fasta_sit_PM",
            "def_aktioner_PM",
            "raddningar_PM",
            "raddnings_pct",
            "snittminuter",
            "anvandning",
            "gula_kort",
            "roda_kort",
            "gula_kort_PM",
            "roda_kort_PM",
            "fouls",
            "fouls_PM",
        ]
    }
    base.update({"name": name, "xFP": xfp, "position": "MID", "team": "IFK"})
    return base


def test_load_calls_upsert_with_correct_count(tmp_path):
    csv_path = tmp_path / "enhanced_stats_clean.csv"
    _write_clean_csv(csv_path, [_make_row("Player A"), _make_row("Player B")])

    captured = []
    with patch(
        "scripts.ingest_enhanced_stats.upsert_enhanced_stats",
        side_effect=captured.append,
    ):
        load(csv_path)

    assert len(captured) == 1
    assert len(captured[0]) == 2


def test_load_deduplicates_by_name(tmp_path):
    csv_path = tmp_path / "enhanced_stats_clean.csv"
    _write_clean_csv(
        csv_path,
        [
            _make_row("Player A", xfp="5.0"),
            _make_row("Player A", xfp="6.0"),  # duplicate — second wins
            _make_row("Player B"),
        ],
    )

    captured = []
    with patch(
        "scripts.ingest_enhanced_stats.upsert_enhanced_stats",
        side_effect=captured.append,
    ):
        load(csv_path)

    rows = captured[0]
    assert len(rows) == 2
    names = {r["name"] for r in rows}
    assert names == {"Player A", "Player B"}
    # Last occurrence of Player A wins
    a = next(r for r in rows if r["name"] == "Player A")
    assert a["xFP"] == 6.0


def test_load_only_stores_db_cols(tmp_path):
    csv_path = tmp_path / "enhanced_stats_clean.csv"
    _write_clean_csv(csv_path, [_make_row("Player A")])

    captured = []
    with patch(
        "scripts.ingest_enhanced_stats.upsert_enhanced_stats",
        side_effect=captured.append,
    ):
        load(csv_path)

    row_keys = set(captured[0][0].keys())
    assert row_keys == DB_COLS


def test_load_raises_if_file_missing(tmp_path):
    with pytest.raises(FileNotFoundError):
        load(tmp_path / "nonexistent.csv")


def test_load_empty_csv_does_nothing(tmp_path, capsys):
    csv_path = tmp_path / "enhanced_stats_clean.csv"
    _write_clean_csv(csv_path, [_make_row("X")])
    # Overwrite with header-only
    csv_path.write_text("name,xFP\n", encoding="utf-8")

    with patch("scripts.ingest_enhanced_stats.upsert_enhanced_stats") as mock_upsert:
        load(csv_path)
        mock_upsert.assert_not_called()
