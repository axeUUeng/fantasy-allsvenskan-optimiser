"""Load the cleaned enhanced stats CSV into the enhanced_stats DB table.

Workflow:
1. Copy-paste the players table from the stats provider
2. Run: uv run python scripts/parse_enhanced_stats.py
3. Run: uv run python scripts/ingest_enhanced_stats.py
"""

import csv
from pathlib import Path

from fantasy_optimizer.db.upsert import upsert_enhanced_stats

CLEAN_CSV = Path(__file__).parent.parent / "data" / "enhanced_stats_clean.csv"

# Columns to store in DB (must match EnhancedStatRow)
DB_COLS = {
    "name",
    "position",
    "team",
    "xFP",
    "xFP_3",
    "xFP_5",
    "xFP_7",
    "pris",
    "mal",
    "assist",
    "xG",
    "xA",
}
FLOAT_COLS = DB_COLS - {"name", "position", "team"}


def _coerce(col: str, val: str) -> float | str | None:
    if val == "" or val is None:
        return None
    if col in FLOAT_COLS:
        try:
            return float(val)
        except ValueError:
            return None
    return val


def load(csv_path: Path = CLEAN_CSV) -> None:
    if not csv_path.exists():
        raise FileNotFoundError(
            f"{csv_path} not found. Run parse_enhanced_stats.py first."
        )

    rows: list[dict] = []
    with csv_path.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for raw in reader:
            row = {col: _coerce(col, val) for col, val in raw.items() if col in DB_COLS}
            rows.append(row)

    if not rows:
        print("No rows found in CSV — nothing to load.")
        return

    # Deduplicate by name — keep last occurrence (most recently copy-pasted)
    seen: dict[str, dict] = {}
    for row in rows:
        seen[row["name"]] = row
    unique_rows = list(seen.values())

    dupes = len(rows) - len(unique_rows)
    if dupes:
        print(f"Removed {dupes} duplicate entries.")

    upsert_enhanced_stats(unique_rows)
    print(f"Loaded {len(unique_rows)} players into enhanced_stats.")


if __name__ == "__main__":
    load()
