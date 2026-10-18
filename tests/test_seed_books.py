"""The five hand-checked books must come out of the committed data as expected."""

import unittest
from pathlib import Path

from dnd_novels import build_csv, isbn

ROOT = Path(__file__).resolve().parent.parent

# Written from the books themselves, not from the code's output.
EXPECTED = {
    "Canticle": dict(
        authors="R. A. Salvatore", first_pub_date="1991", setting="Forgotten Realms",
        series="The Cleric Quintet", series_number="1", isbn13="9781560761198",
        isbn10="1560761199", publisher="TSR", format="novel"),
    "The Parched Sea": dict(
        authors="Troy Denning", first_pub_date="1991", setting="Forgotten Realms",
        series="The Harpers", series_number="1", isbn13="9781560760672",
        isbn10="1560760672", publisher="TSR", format="novel"),
    "Beyond the Moons": dict(
        authors="David Cook", first_pub_date="1991", setting="Spelljammer",
        series="The Cloakmaster Cycle", series_number="1", isbn13="9781560761532",
        isbn10="1560761539", publisher="TSR", format="novel"),
    # First printing is the Oct 1998 hardcover. The owner's copy (ISBN 0786913886)
    # is a later paperback printing, so the row carries the first edition's ISBN.
    "The Silent Blade": dict(
        authors="R. A. Salvatore", first_pub_date="1998-10", setting="Forgotten Realms",
        series="Paths of Darkness", series_number="1", format="novel"),
    "Dungeons & Dragons - Library Collection": dict(
        authors="R. A. Salvatore; Geno Salvatore", first_pub_date="2023-11",
        setting="Forgotten Realms", series="Dungeons & Dragons - Library Collection",
        series_number="1", isbn13="9798887240077", isbn10="", publisher="IDW",
        format="graphic novel"),
}


def all_rows():
    return build_csv.build_rows(ROOT / "data" / "isfdb_dnd.csv", ROOT / "data" / "manual.csv")


class SeedBooksTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = {}
        for row in all_rows():
            # The Silent Blade also exists as a 2021 title in another series.
            if row["title"] in EXPECTED and row["setting"] == EXPECTED[row["title"]]["setting"]:
                cls.rows[row["title"]] = row

    def test_all_five_books_present(self):
        self.assertEqual(set(self.rows), set(EXPECTED))

    def test_fields(self):
        for title, expected in EXPECTED.items():
            for field, value in expected.items():
                with self.subTest(title=title, field=field):
                    actual = self.rows[title][field]
                    if field == "first_pub_date" and len(value) == 4:
                        actual = actual[:4]  # only the year is hand-verified
                    self.assertEqual(actual, value)

    def test_isbns_valid(self):
        for title, row in self.rows.items():
            with self.subTest(title=title):
                self.assertTrue(isbn.is_valid(row["isbn13"]))

    def test_no_duplicate_isbns(self):
        isbns = [r["isbn13"] for r in all_rows() if r["isbn13"]]
        self.assertEqual({i for i in isbns if isbns.count(i) > 1}, set())


class IsbnTest(unittest.TestCase):
    def test_conversion(self):
        self.assertEqual(isbn.to_isbn13("1-56076-119-9"), "9781560761198")
        self.assertEqual(isbn.to_isbn10("9781560761198"), "1560761199")

    def test_979_has_no_isbn10(self):
        self.assertEqual(isbn.to_isbn10("979-88-87240-07-7"), "")

    def test_invalid(self):
        self.assertFalse(isbn.is_valid("1560761198"))


if __name__ == "__main__":
    unittest.main()
