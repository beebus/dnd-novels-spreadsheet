"""Combine the ISFDB export with hand-entered rows into the final CSV.

Usage: python -m dnd_novels.build_csv [isfdb_dnd.csv] [manual.csv] [output.csv]

data/isfdb_dnd.csv is produced by ``python -m dnd_novels.export_isfdb``.
data/manual.csv holds works ISFDB does not have (e.g. graphic novels); a manual
row replaces an ISFDB row with the same ISBN-13.
"""

import csv
import sys
from pathlib import Path

from . import isbn as isbnlib

COLUMNS = ["title", "authors", "first_pub_date", "setting", "series", "series_number",
           "isbn13", "isbn10", "publisher", "format", "notes", "isfdb_title_id"]


def read_rows(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def build_rows(isfdb_path: Path, manual_path: Path) -> list[dict]:
    manual = read_rows(manual_path)
    for row in manual:
        isbn13 = row["isbn13"]
        if isbn13 and not isbnlib.is_valid(isbn13):
            raise ValueError(f"Invalid ISBN in {manual_path}: {isbn13}")
    manual_isbns = {r["isbn13"] for r in manual if r["isbn13"]}
    rows = [r for r in read_rows(isfdb_path) if r["isbn13"] not in manual_isbns]
    rows += manual
    rows.sort(key=lambda r: (r["setting"], r["series"], r["first_pub_date"], r["title"]))
    return [{c: r.get(c, "") for c in COLUMNS} for r in rows]


def write_csv(rows: list[dict], out_path: Path) -> None:
    # utf-8-sig so Excel shows accented names correctly
    with open(out_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    isfdb = Path(sys.argv[1] if len(sys.argv) > 1 else "data/isfdb_dnd.csv")
    manual = Path(sys.argv[2] if len(sys.argv) > 2 else "data/manual.csv")
    out = Path(sys.argv[3] if len(sys.argv) > 3 else "novels.csv")
    rows = build_rows(isfdb, manual)
    write_csv(rows, out)
    print(f"Wrote {len(rows)} rows to {out}")
