"""Export D&D works from a local MariaDB/MySQL copy of the ISFDB database.

Usage: python -m dnd_novels.export_isfdb [output.csv]

Needs the ISFDB dump imported into a local database named ``isfdb`` and a
read-only account (see README). Only the ``mysql`` command-line client is
used, so there is no Python package to install. Environment overrides:
MYSQL_EXE (path to the client), ISFDB_USER (default ``isfdb_ro``).

Writes one row per work (ISFDB title), with the date, publisher and ISBN of
its earliest edition. ISFDB data is CC BY; see the README for attribution.
"""

import csv
import os
import shutil
import subprocess
import sys
from pathlib import Path

from . import isbn as isbnlib

DEFAULT_MYSQL = r"C:\Program Files\MariaDB 11.8\bin\mysql.exe"
DEFAULT_OUT = Path("data/isfdb_dnd.csv")
COLUMNS = ["isfdb_title_id", "title", "authors", "first_pub_date", "setting", "series",
           "series_number", "isbn13", "isbn10", "publisher", "format", "notes"]

# ISFDB root series that hold D&D fiction -> setting name. Roots mapped to None
# are generic D&D roots whose setting comes from the child series (see
# DND_CHILD_SETTINGS) or stays blank.
ROOTS = {
    24168: None,            # Dungeons & Dragons
    68177: "",              # Advanced Dungeons & Dragons
    1402: "Forgotten Realms",
    2169: "Dragonlance",
    1391: "Dark Sun",
    12217: "Greyhawk",
    24937: "Planescape",
    27375: "Spelljammer",
    12343: "Mystara",
    25266: "Birthright",
}
DND_CHILD_SETTINGS = {
    "Eberron": "Eberron",
    "Ravenloft": "Ravenloft",
    "Spelljammer (Dungeons & Dragons)": "Spelljammer",
}
TITLE_TYPES = ("NOVEL", "ANTHOLOGY", "COLLECTION")  # omnibuses are left out on purpose
FORMATS = {"NOVEL": "novel", "ANTHOLOGY": "anthology", "COLLECTION": "anthology"}
SKIP_PUB_TYPES = {"OMNIBUS", "MAGAZINE", "FANZINE", "NONFICTION"}

_SELECTED = f"""
WITH RECURSIVE tree AS (
  SELECT series_id FROM series WHERE series_id IN ({",".join(map(str, ROOTS))})
  UNION
  SELECT s.series_id FROM series s JOIN tree ON s.series_parent = tree.series_id
),
sel AS (
  SELECT t.* FROM titles t JOIN tree ON t.series_id = tree.series_id
  WHERE t.title_parent = 0
    AND t.title_ttype IN ({",".join(repr(t) for t in TITLE_TYPES)})
)
"""

QUERIES = {
    "series": "SELECT series_id, series_title, IFNULL(series_parent, 0) FROM series",
    "titles": _SELECTED + """SELECT title_id, title_title, title_copyright, title_ttype,
        title_graphic, series_id, IFNULL(title_seriesnum, ''), IFNULL(title_seriesnum_2, '')
        FROM sel""",
    "pubs": _SELECTED + """SELECT pc.title_id, p.pub_id, p.pub_year, IFNULL(p.pub_isbn, ''),
        IFNULL(pub.publisher_name, ''), IFNULL(p.pub_ctype, '')
        FROM sel JOIN pub_content pc ON pc.title_id = sel.title_id
        JOIN pubs p ON p.pub_id = pc.pub_id
        LEFT JOIN publishers pub ON pub.publisher_id = p.publisher_id""",
    "authors": _SELECTED + """SELECT ca.title_id, a.author_canonical
        FROM sel JOIN canonical_author ca ON ca.title_id = sel.title_id
        JOIN authors a ON a.author_id = ca.author_id ORDER BY ca.title_id, ca.ca_id""",
}


def run_query(sql: str) -> list[list[str]]:
    mysql = os.environ.get("MYSQL_EXE") or shutil.which("mysql") or DEFAULT_MYSQL
    user = os.environ.get("ISFDB_USER", "isfdb_ro")
    result = subprocess.run(
        [mysql, "-u", user, "isfdb", "--batch", "--skip-column-names",
         "--default-character-set=utf8mb4", "-e", sql],
        capture_output=True, check=True)
    return parse_batch_output(result.stdout.decode("utf-8"))


def parse_batch_output(text: str) -> list[list[str]]:
    """Parse `mysql --batch` output: tab separated, with \\t \\n \\\\ escaped."""
    rows = []
    for line in text.splitlines():
        rows.append([_unescape(f) for f in line.split("\t")])
    return rows


def _unescape(field: str) -> str:
    return (field.replace("\\t", "\t").replace("\\n", "\n").replace("\\\\", "\\")
            if "\\" in field else field)


def normalise_date(value: str) -> str:
    """'1991-10-00' -> '1991-10', '1994-00-00' -> '1994'; ISFDB's 8888/0000 = unknown."""
    year, _, rest = value.partition("-")
    if not year.isdigit() or year in ("0000", "8888"):
        return ""
    month = rest.partition("-")[0]
    return year if month in ("", "00") else f"{year}-{month}"


def resolve_series(series_id: int, series: dict[int, tuple[str, int]]) -> tuple[str, str]:
    """Return (setting, series name) for a series by walking up to its root."""
    chain = []
    sid = series_id
    while sid and sid in series and len(chain) < 20:
        chain.append(sid)
        sid = series[sid][1]
    root = chain[-1]
    setting = ROOTS.get(root)
    if setting is None:  # generic D&D root: use the child series if it is a setting
        child = series[chain[-2]][0] if len(chain) > 1 else ""
        setting = DND_CHILD_SETTINGS.get(child, "")
    name = series[series_id][0]
    if setting and name.startswith(setting + ": "):
        name = name[len(setting) + 2:]
    return setting, name


def build_works(series_rows, title_rows, pub_rows, author_rows) -> list[dict]:
    series = {int(r[0]): (r[1], int(r[2])) for r in series_rows}
    authors: dict[str, list[str]] = {}
    for title_id, name in author_rows:
        authors.setdefault(title_id, []).append(name)

    pubs: dict[str, list[dict]] = {}
    for title_id, pub_id, year, raw_isbn, publisher, ctype in pub_rows:
        if ctype in SKIP_PUB_TYPES:
            continue
        s = isbnlib.clean(raw_isbn)
        pubs.setdefault(title_id, []).append({
            "date": normalise_date(year), "isbn": s if isbnlib.is_valid(s) else "",
            "publisher": publisher, "pub_id": int(pub_id)})

    works = []
    for title_id, title, copyright_, ttype, graphic, series_id, num, num2 in title_rows:
        setting, series_name = resolve_series(int(series_id), series)
        editions = sorted((p for p in pubs.get(title_id, []) if p["date"]),
                          key=lambda p: (p["date"], p["pub_id"]))
        first = editions[0] if editions else None
        with_isbn = next((p for p in editions if p["isbn"]), None)
        notes = []
        if first and with_isbn and with_isbn is not first:
            notes.append(f"ISBN is from the {with_isbn['date']} "
                         f"{with_isbn['publisher']} edition; the first edition has none")
        if not first:
            notes.append("no dated edition in ISFDB")
        names = authors.get(title_id, [])
        if ttype == "COLLECTION" and len(names) > 1:
            notes.append("collection with several credited authors")
        works.append({
            "isfdb_title_id": title_id,
            "title": title,
            "authors": "; ".join(names),
            "first_pub_date": normalise_date(copyright_) or (first["date"] if first else ""),
            "setting": setting,
            "series": series_name,
            "series_number": num2 or num,
            "isbn13": isbnlib.to_isbn13(with_isbn["isbn"]) if with_isbn else "",
            "isbn10": isbnlib.to_isbn10(with_isbn["isbn"]) if with_isbn else "",
            "publisher": first["publisher"] if first else "",
            "format": "graphic novel" if graphic == "Yes" else FORMATS[ttype],
            "notes": "; ".join(notes),
        })
    works.sort(key=lambda w: (w["setting"], w["series"], w["first_pub_date"], w["title"]))
    return works


def write_csv(works: list[dict], out_path: Path) -> None:
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(works)


if __name__ == "__main__":
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_OUT
    data = {name: run_query(sql) for name, sql in QUERIES.items()}
    works = build_works(data["series"], data["titles"], data["pubs"], data["authors"])
    write_csv(works, out)
    print(f"Wrote {len(works)} works to {out}")
