"""Reproduce the five hand-checked books from saved ISFDB responses (no network)."""

import unittest
from pathlib import Path

from dnd_novels import build_csv, isbn

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "tests" / "fixtures"

# Written from the books themselves, not from the code's output.
EXPECTED = {
    "9781560761198": dict(
        title="Canticle", authors="R. A. Salvatore", first_pub_date="1991",
        setting="Forgotten Realms", series="The Cleric Quintet", series_number="1",
        isbn10="1560761199", publisher="TSR", format="novel"),
    "9781560760672": dict(
        title="The Parched Sea", authors="Troy Denning", first_pub_date="1991",
        setting="Forgotten Realms", series="The Harpers", series_number="1",
        isbn10="1560760672", publisher="TSR", format="novel"),
    "9781560761532": dict(
        title="Beyond the Moons", authors="David Cook", first_pub_date="1991",
        setting="Spelljammer", series="The Cloakmaster Cycle", series_number="1",
        isbn10="1560761539", publisher="TSR", format="novel"),
    # First printing Oct 1998 (hardcover); seeded ISBN is the later paperback.
    "9780786913886": dict(
        title="The Silent Blade", authors="R. A. Salvatore", first_pub_date="1998-10",
        setting="Forgotten Realms", series="Paths of Darkness", series_number="1",
        isbn10="0786913886", publisher="TSR/Wizards of the Coast", format="novel"),
    "9798887240077": dict(
        title="Dungeons & Dragons - Library Collection",
        authors="R. A. Salvatore; Geno Salvatore", first_pub_date="2023-11",
        setting="Forgotten Realms", series="Dungeons & Dragons - Library Collection",
        series_number="1", isbn10="", publisher="IDW", format="graphic novel"),
}


class SeedBooksTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        rows = build_csv.build_rows(ROOT / "data" / "seeds.csv", FIXTURES)
        cls.rows = {r["isbn13"]: r for r in rows}

    def test_all_five_books_present(self):
        self.assertEqual(set(self.rows), set(EXPECTED))

    def test_fields(self):
        for isbn13, expected in EXPECTED.items():
            for field, value in expected.items():
                with self.subTest(isbn13=isbn13, field=field):
                    actual = self.rows[isbn13][field]
                    if field == "first_pub_date" and len(value) == 4:
                        actual = actual[:4]  # only the year is hand-verified
                    self.assertEqual(actual, value)

    def test_silent_blade_notes_date_conflict(self):
        notes = self.rows["9780786913886"]["notes"]
        self.assertIn("1998-10", notes)
        self.assertIn("1999-06", notes)

    def test_isbns_valid(self):
        for isbn13, row in self.rows.items():
            with self.subTest(isbn13=isbn13):
                self.assertTrue(isbn.is_valid(row["isbn13"]))


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
