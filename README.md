# dnd-novels-spreadsheet

A spreadsheet (CSV) of Dungeons & Dragons fiction: TSR and Wizards of the Coast novels, anthologies, graphic novels and 5th Edition tie-ins. Endless Quest gamebooks are out of scope.

It is early work. Right now a small Python script builds the CSV for a short list of seed books, which are used to check the approach before scaling up.

## What the CSV contains

One row per work (the first edition), not one per edition or printing.

| Column | Meaning |
|---|---|
| `title` | Title as published |
| `authors` | Authors, separated by `; ` |
| `first_pub_date` | Earliest known date, `YYYY` or `YYYY-MM` |
| `setting` | Campaign setting, e.g. Forgotten Realms, Spelljammer |
| `series` | Series name |
| `series_number` | Book number within the series |
| `isbn13` | ISBN-13 |
| `isbn10` | ISBN-10, blank for 979- ISBNs, which have none |
| `publisher` | Publisher of the earliest known edition |
| `format` | `novel`, `anthology` or `graphic novel` |
| `notes` | Data conflicts and other remarks |

Missing values stay blank; nothing is invented.

## How it works

`data/seeds.csv` lists the books to include, one ISBN per row.

- Rows with `source=isfdb` are looked up through the [ISFDB](https://www.isfdb.org) REST API. ISFDB returns one record per edition, so the script merges them into one row. It takes the earliest date, including "First Printing: Month YYYY" statements in notes, and records conflicting dates in `notes`.
- Rows with `source=manual` (for example books ISFDB doesn't have) are used as written.
- `setting`, `series` and `series_number` always come from the seed file, because ISFDB's REST API doesn't provide them.

API responses are cached in `cache/` so each ISBN is fetched once, and requests are limited to one per second.

## Requirements

Python 3.14 (the version CI uses). There are no third-party packages, so there is nothing to `pip install`.

## Run the tests

The tests use saved ISFDB responses in `tests/fixtures/`, so they need no network access.

```
python -m unittest discover -s tests -t .
```

They check that the five seed books come out as expected: *Canticle*, *The Parched Sea*, *Beyond the Moons*, *The Silent Blade* and the IDW *Dungeons & Dragons - Library Collection* volume 1. They also check the ISBN conversions.

## Build the CSV

```
python -m dnd_novels.build_csv
```

This reads `data/seeds.csv`, queries ISFDB (the first run needs internet) and writes `novels.csv` in the current folder. The file is UTF-8 with a byte-order mark so Excel shows accented names correctly.

The arguments are optional and positional: `python -m dnd_novels.build_csv [seeds.csv] [output.csv] [cache_dir]`.

To use the saved fixtures instead of the live API:

```
python -m dnd_novels.build_csv data/seeds.csv novels.csv tests/fixtures
```

## Adding a book

Add a row to `data/seeds.csv`. For an ISFDB book, fill in `isbn`, `source=isfdb`, `setting`, `series` and `series_number`, and leave the other columns empty. For anything else, use `source=manual` and fill in every column. Then add its saved ISFDB response to `tests/fixtures/` and an expected entry in `tests/test_seed_books.py` if you want it covered by the tests.

## Sources and attribution

- Bibliographic data from the [Internet Speculative Fiction Database](https://www.isfdb.org), which publishes its data under a Creative Commons Attribution (CC BY) license.
- The *Dungeons & Dragons - Library Collection* row was entered by hand from a retailer listing.

## License

Code is under the MIT [LICENSE](LICENSE).
