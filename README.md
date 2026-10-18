# dnd-novels-spreadsheet

A spreadsheet (CSV) of Dungeons & Dragons fiction: TSR and Wizards of the Coast novels, anthologies, graphic novels and 5th Edition tie-ins. Endless Quest gamebooks are out of scope.

It is early work. A Python script exports the D&D works from the ISFDB database and builds the CSV; the output still needs checking against other sources.

## What the CSV contains

One row per work (the first edition), not one per edition or printing.

| Column           | Meaning                                              |
|------------------|------------------------------------------------------|
| `title`          | Title as published                                   |
| `authors`        | Authors, separated by `; `                           |
| `first_pub_date` | Earliest known date, `YYYY` or `YYYY-MM`             |
| `setting`        | Campaign setting, e.g. Forgotten Realms, Spelljammer |
| `series`         | Series name                                          |
| `series_number`  | Book number within the series                        |
| `isbn13`         | ISBN-13                                              |
| `isbn10`         | ISBN-10, blank for 979- ISBNs, which have none       |
| `publisher`      | Publisher of the earliest known edition              |
| `format`         | `novel`, `anthology` or `graphic novel`              |
| `notes`          | Data conflicts and other remarks                     |

Missing values stay blank; nothing is invented.

## How it works

The data flows in two steps.

1. **Export** (`python -m dnd_novels.export_isfdb`) queries a local copy of the [ISFDB](https://www.isfdb.org) database for every novel, anthology and single-author short-story collection in the D&D series trees (Forgotten Realms, Dragonlance, Eberron, Ravenloft, Greyhawk, Dark Sun, Spelljammer, Planescape, Mystara, Birthright and general D&D). Omnibuses are left out, and ISFDB `COLLECTION` titles are listed as `anthology`. Each work gets the date, publisher and ISBN of its earliest edition, plus its series, number and setting. The result is saved as `data/isfdb_dnd.csv`, which is committed so the rest of the project works without the database.
2. **Build** (`python -m dnd_novels.build_csv`) merges that file with `data/manual.csv`, for works ISFDB doesn't have (it has almost no graphic novels), and writes `novels.csv`. A manual row replaces an ISFDB row with the same ISBN-13.

## Requirements

Python 3.14 (the version CI uses). There are no third-party packages, so there is nothing to `pip install`. The export step also needs the local ISFDB database described below; the tests and the build step do not.

## Run the tests

The tests use the committed CSVs and synthetic rows, so they need no database or network access.

```
python -m unittest discover -s tests -t .
```

They check that the five seed books come out as expected (*Canticle*, *The Parched Sea*, *Beyond the Moons*, *The Silent Blade* and the IDW *Dungeons & Dragons - Library Collection* volume 1), plus the export logic and ISBN conversions.

## Build the CSV

```
python -m dnd_novels.build_csv
```

This writes `novels.csv` in the current folder. The file is UTF-8 with a byte-order mark so Excel shows accented names correctly. The arguments are optional and positional: `python -m dnd_novels.build_csv [isfdb_dnd.csv] [manual.csv] [output.csv]`.

## Refreshing the ISFDB data

1. Download the latest full database backup from [ISFDB Downloads](https://isfdb.org/wiki/index.php/ISFDB_Downloads) (a `.zip` of about 350 MB) and unzip it somewhere outside the repo.
2. Install MariaDB or MySQL and import the dump into a database named `isfdb`.
3. Create a read-only account: `CREATE USER 'isfdb_ro'@'localhost' IDENTIFIED BY ''; GRANT SELECT ON isfdb.* TO 'isfdb_ro'@'localhost';`
4. Run `python -m dnd_novels.export_isfdb`.

The export finds the `mysql` client on your PATH, or uses `MYSQL_EXE`, or falls back to `C:\Program Files\MariaDB 11.8\bin\mysql.exe`. Set `ISFDB_USER` to use a different account.

## Adding a book ISFDB doesn't have

Add a row to `data/manual.csv` with the same columns as the output and leave `isfdb_title_id` empty. To cover it with a test, add an entry to `tests/test_seed_books.py`.

## Sources and attribution

- Bibliographic data from the [Internet Speculative Fiction Database](https://www.isfdb.org), which publishes its data under a Creative Commons Attribution (CC BY) license.
- The *Dungeons & Dragons - Library Collection* row was entered by hand from a retailer listing.

## License

Code is under the MIT [LICENSE](LICENSE).
