"""Look up publications on ISFDB (https://www.isfdb.org, data is CC BY) by ISBN.

Only the REST endpoint is used. It returns one record per *publication*
(edition/printing), not per work, and has no series information.
"""

import re
import time
import urllib.request
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

from . import isbn as isbnlib

REST_URL = "https://www.isfdb.org/cgi-bin/rest/getpub.cgi?{isbn}"
USER_AGENT = "dnd-novels-spreadsheet (https://github.com/beebus/dnd-novels-spreadsheet)"
FORMATS = {"NOVEL": "novel", "ANTHOLOGY": "anthology"}
MONTHS = {m: i for i, m in enumerate(
    ["january", "february", "march", "april", "may", "june", "july",
     "august", "september", "october", "november", "december"], start=1)}

_last_request = 0.0


def fetch_xml(isbn: str, cache_dir: Path) -> bytes:
    """Return the raw API response, using cache_dir so each ISBN is fetched once."""
    global _last_request
    cache_file = Path(cache_dir) / f"{isbnlib.to_isbn10(isbn) or isbn}.xml"
    if cache_file.exists():
        return cache_file.read_bytes()
    wait = 1.0 - (time.monotonic() - _last_request)
    if wait > 0:
        time.sleep(wait)
    request = urllib.request.Request(
        REST_URL.format(isbn=isbn), headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=30) as response:
        data = response.read()
    _last_request = time.monotonic()
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    cache_file.write_bytes(data)
    return data


def parse_publications(xml_bytes: bytes) -> list[dict]:
    # Cloudflare appends a <script> after the closing tag; drop anything past it.
    end = xml_bytes.rfind(b"</ISFDB>")
    if end != -1:
        xml_bytes = xml_bytes[:end + len(b"</ISFDB>")]
    root = ET.fromstring(xml_bytes)
    pubs = []
    for p in root.iter("Publication"):
        pubs.append({
            "record": p.findtext("Record", ""),
            "title": (p.findtext("Title") or "").strip(),
            "authors": [a.text.strip() for a in p.iter("Author") if a.text],
            "year": normalise_date(p.findtext("Year", "")),
            "isbn": isbnlib.clean(p.findtext("Isbn", "")),
            "publisher": (p.findtext("Publisher") or "").strip(),
            "binding": p.findtext("Binding", ""),
            "type": p.findtext("Type", ""),
            "note": p.findtext("Note", "") or "",
        })
    return pubs


def normalise_date(value: str) -> str:
    """'1991-11-00' -> '1991-11', '1994-00-00' -> '1994', 'date unknown' -> ''."""
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})$", value.strip())
    if not m:
        return ""
    year, month, _ = m.groups()
    return year if month == "00" else f"{year}-{month}"


def first_printing_from_note(note: str) -> str:
    """Find 'First Printing: October 1998' style statements in a record's note."""
    m = re.search(r"First Printing:\s*([A-Za-z]+)\s+(\d{4})", note, re.IGNORECASE)
    if not m or m.group(1).lower() not in MONTHS:
        return ""
    return f"{m.group(2)}-{MONTHS[m.group(1).lower()]:02d}"


def work_from_publications(pubs: list[dict], isbn: str) -> dict:
    """Collapse the publication records for one ISBN into a single work row.

    Records for other titles that share the ISBN (ISFDB data errors) are dropped.
    first_pub_date is the earliest of the record dates and any
    'First Printing' statements in notes.
    """
    wanted = isbnlib.to_isbn13(isbn)
    pubs = [p for p in pubs if p["isbn"] and isbnlib.to_isbn13(p["isbn"]) == wanted]
    if not pubs:
        return {}
    title = Counter(p["title"] for p in pubs).most_common(1)[0][0]
    pubs = [p for p in pubs if p["title"] == title]

    candidates = set()
    for p in pubs:
        if p["year"]:
            candidates.add(p["year"])
        stated = first_printing_from_note(p["note"])
        if stated:
            candidates.add(stated)
    ordered = sorted(candidates)
    dated = [p for p in pubs if p["year"]]
    earliest = min(dated, key=lambda p: p["year"]) if dated else pubs[0]

    notes = []
    if len(ordered) > 1:
        notes.append("ISFDB date candidates: " + ", ".join(ordered))
    return {
        "title": title,
        "authors": "; ".join(earliest["authors"]),
        "first_pub_date": ordered[0] if ordered else "",
        "publisher": earliest["publisher"],
        "format": FORMATS.get(earliest["type"], earliest["type"].lower()),
        "notes": "; ".join(notes),
    }
