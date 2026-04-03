"""Tests for scripts/parse_enhanced_stats.py"""

import csv

from scripts.parse_enhanced_stats import COLUMNS, FIELDS_PER_PLAYER, clean_value, parse


def test_fields_per_player():
    assert FIELDS_PER_PLAYER == 47
    assert len(COLUMNS) == 47


def test_clean_value_strips_whitespace():
    assert clean_value("  hello  ") == "hello"


def test_clean_value_strips_percent():
    assert clean_value("51.2 %") == "51.2"
    assert clean_value("0 %") == "0"


def test_clean_value_no_percent():
    assert clean_value("7.4") == "7.4"


def test_parse_two_players(raw_stats_file, tmp_path):
    out = tmp_path / "clean.csv"
    parse(raw_stats_file, out)

    rows = list(csv.DictReader(out.open(encoding="utf-8")))
    assert len(rows) == 2
    assert rows[0]["name"] == "Erik Svensson"
    assert rows[0]["position"] == "Mittfältare"
    assert rows[0]["team"] == "IFK Göteborg"
    assert rows[0]["xFP"] == "5.2"
    assert rows[1]["name"] == "Anna Karlsson"


def test_parse_strips_percent_in_output(raw_stats_file, tmp_path):
    out = tmp_path / "clean.csv"
    parse(raw_stats_file, out)
    rows = list(csv.DictReader(out.open(encoding="utf-8")))
    # agarandel column had "22.5" (no % in fixture), raddnings_pct had "10 %"
    assert "%" not in rows[0]["raddnings_pct"]


def test_parse_skips_malformed_block(tmp_path):
    bad = tmp_path / "bad.csv"
    # Only 3 lines — not a valid player block
    bad.write_text("Player Name\nMittfältare\nIFK Göteborg\n", encoding="utf-8")
    out = tmp_path / "out.csv"
    parse(bad, out)
    rows = list(csv.DictReader(out.open(encoding="utf-8")))
    assert len(rows) == 0


def test_parse_empty_file(tmp_path):
    empty = tmp_path / "empty.csv"
    empty.write_text("", encoding="utf-8")
    out = tmp_path / "out.csv"
    parse(empty, out)
    rows = list(csv.DictReader(out.open(encoding="utf-8")))
    assert len(rows) == 0


def test_parse_output_has_all_columns(raw_stats_file, tmp_path):
    out = tmp_path / "clean.csv"
    parse(raw_stats_file, out)
    reader = csv.DictReader(out.open(encoding="utf-8"))
    assert list(reader.fieldnames) == COLUMNS
