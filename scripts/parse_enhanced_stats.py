"""Parse the raw copy-pasted enhanced stats data into a clean CSV."""

import csv
from pathlib import Path

COLUMNS = [
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

FIELDS_PER_PLAYER = len(COLUMNS)  # 47


def clean_value(val: str) -> str:
    return val.strip().rstrip("%").strip()


def parse(input_path: Path, output_path: Path) -> None:
    lines = input_path.read_text(encoding="utf-8").splitlines()

    blocks: list[list[str]] = []
    current: list[str] = []
    for line in lines:
        if line.strip() == "":
            if current:
                blocks.append(current)
                current = []
        else:
            current.append(line.strip())
    if current:
        blocks.append(current)

    rows: list[dict] = []
    skipped = 0
    for block in blocks:
        if len(block) != FIELDS_PER_PLAYER:
            print(
                f"Skipping block starting with '{block[0]}' — expected {FIELDS_PER_PLAYER} fields, got {len(block)}"
            )
            skipped += 1
            continue
        row = {col: clean_value(val) for col, val in zip(COLUMNS, block)}
        rows.append(row)

    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Done: {len(rows)} players written to {output_path}")
    if skipped:
        print(f"Skipped {skipped} malformed block(s)")


if __name__ == "__main__":
    base = Path(__file__).parent.parent / "data"
    parse(base / "enhanced_stats.csv", base / "enhanced_stats_clean.csv")
