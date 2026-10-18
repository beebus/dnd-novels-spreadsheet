"""Build the novels CSV from data/seeds.csv, filling ISFDB rows from the API.

Usage: python -m dnd_novels.build_csv [seeds.csv] [output.csv] [cache_dir]

Seed rows with source=isfdb get title, authors, date, publisher and format from
ISFDB; setting, series and series_number always come from the seed file
(ISFDB's REST API does not expose them). Rows with source=manual are used as-is.
"""

import csv
import sys
from pathlib import Path

from . import isbn as isbnlib
from . import isfdb

COLUMNS = ["title", "authors", "first_pub_date", "setting", "series", "series_number",
           "isbn13", "isbn10", "publisher", "format", "notes"]
ISFDB_FIELDS = ["title", "authors", "first_pub_date", "publisher", "format"]


def build_rows(seeds_path: Path, cache_dir: Path) -> list[dict]:
    rows = []
    with open(seeds_path, newline="", encoding="utf-8") as f:
        for seed in csv.DictReader(f):
            row = {c: seed.get(c, "") for c in COLUMNS}
            raw = seed["isbn"]
            if not isbnlib.is_valid(raw):
                raise ValueError(f"Invalid ISBN in seeds: {raw}")
            row["isbn13"] = isbnlib.to_isbn13(raw)
            row["isbn10"] = isbnlib.to_isbn10(raw)
            if seed["source"] == "isfdb":
                work = isfdb.work_from_publications(
                    isfdb.parse_publications(isfdb.fetch_xml(raw, cache_dir)), raw)
                if not work:
                    raise LookupError(f"ISFDB has no record for {raw}")
                for field in ISFDB_FIELDS:
                    row[field] = work[field]
                notes = [n for n in (work["notes"], seed.get("notes", "")) if n]
                row["notes"] = "; ".join(notes)
            rows.append(row)
    return rows


def write_csv(rows: list[dict], out_path: Path) -> None:
    with open(out_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    seeds = Path(sys.argv[1] if len(sys.argv) > 1 else "data/seeds.csv")
    out = Path(sys.argv[2] if len(sys.argv) > 2 else "novels.csv")
    cache = Path(sys.argv[3] if len(sys.argv) > 3 else "cache")
    write_csv(build_rows(seeds, cache), out)
    print(f"Wrote {out}")
