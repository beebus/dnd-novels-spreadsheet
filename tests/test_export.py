"""Unit tests for the ISFDB export logic, using small synthetic rows (no database)."""

import unittest

from dnd_novels import export_isfdb as ex

# series_id, title, parent
SERIES = [
    ["24168", "Dungeons & Dragons", "0"],
    ["12133", "Eberron", "24168"],
    ["900", "Eberron: Dragonmarked", "12133"],
    ["1402", "Forgotten Realms Universe", "0"],
    ["1414", "Forgotten Realms", "1402"],
    ["11665", "Forgotten Realms: The Cleric Quintet", "1402"],
    ["2169", "Dragonlance", "0"],
    ["78036", "Dungeons & Dragons (R. A. Salvatore)", "24168"],
]


class ParseTest(unittest.TestCase):
    def test_batch_output_unescapes(self):
        self.assertEqual(ex.parse_batch_output("a\\tb\tc\\nd\te\\\\f\n"),
                         [["a\tb", "c\nd", "e\\f"]])

    def test_normalise_date(self):
        self.assertEqual(ex.normalise_date("1991-10-00"), "1991-10")
        self.assertEqual(ex.normalise_date("1994-00-00"), "1994")
        self.assertEqual(ex.normalise_date("8888-00-00"), "")
        self.assertEqual(ex.normalise_date("0000-00-00"), "")
        self.assertEqual(ex.normalise_date(""), "")


class SeriesTest(unittest.TestCase):
    def setUp(self):
        self.series = {int(a): (b, int(c)) for a, b, c in SERIES}

    def test_setting_prefix_is_stripped(self):
        self.assertEqual(ex.resolve_series(11665, self.series),
                         ("Forgotten Realms", "The Cleric Quintet"))

    def test_setting_from_child_of_generic_root(self):
        self.assertEqual(ex.resolve_series(900, self.series),
                         ("Eberron", "Dragonmarked"))

    def test_generic_dnd_series_has_blank_setting(self):
        self.assertEqual(ex.resolve_series(78036, self.series),
                         ("", "Dungeons & Dragons (R. A. Salvatore)"))

    def test_series_directly_under_root(self):
        self.assertEqual(ex.resolve_series(2169, self.series), ("Dragonlance", "Dragonlance"))


class BuildWorksTest(unittest.TestCase):
    def build(self, titles, pubs, authors):
        return ex.build_works(SERIES, titles, pubs, authors)

    def test_first_edition_and_isbn(self):
        works = self.build(
            [["1", "Book", "1998-10-00", "NOVEL", "No", "11665", "1", ""]],
            [["1", "20", "1999-06-00", "0786913886", "TSR", "NOVEL"],
             ["1", "10", "1998-10-00", "", "TSR", "NOVEL"]],
            [["1", "A. Author"]])
        self.assertEqual(len(works), 1)
        w = works[0]
        self.assertEqual((w["first_pub_date"], w["publisher"], w["isbn13"], w["isbn10"]),
                         ("1998-10", "TSR", "9780786913886", "0786913886"))
        self.assertIn("1999-06", w["notes"])  # ISBN taken from a later edition

    def test_omnibus_editions_are_ignored(self):
        w = self.build(
            [["1", "Book", "1990-00-00", "NOVEL", "No", "11665", "2", ""]],
            [["1", "5", "1989-01-00", "1560761199", "Omni Press", "OMNIBUS"],
             ["1", "6", "1990-05-00", "1560760672", "TSR", "NOVEL"]],
            [["1", "A. Author"]])[0]
        self.assertEqual((w["publisher"], w["isbn10"]), ("TSR", "1560760672"))

    def test_invalid_isbn_is_dropped(self):
        w = self.build(
            [["1", "Book", "1990-00-00", "NOVEL", "No", "11665", "", ""]],
            [["1", "6", "1990-05-00", "1560761198", "TSR", "NOVEL"]], [["1", "A"]])[0]
        self.assertEqual(w["isbn13"], "")

    def test_format_mapping_and_authors(self):
        titles = [["1", "Anth", "1990-00-00", "ANTHOLOGY", "No", "1414", "", ""],
                  ["2", "Coll", "1991-00-00", "COLLECTION", "No", "1414", "", ""],
                  ["3", "Graphic", "1992-00-00", "NOVEL", "Yes", "1414", "", ""]]
        works = {w["title"]: w for w in self.build(titles, [], [
            ["1", "A"], ["1", "B"], ["2", "C"], ["3", "D"]])}
        self.assertEqual(works["Anth"]["format"], "anthology")
        self.assertEqual(works["Anth"]["authors"], "A; B")
        self.assertEqual(works["Coll"]["format"], "anthology")
        self.assertEqual(works["Graphic"]["format"], "graphic novel")
        self.assertIn("no dated edition", works["Coll"]["notes"])

    def test_title_date_falls_back_to_first_edition(self):
        w = self.build(
            [["1", "Book", "8888-00-00", "NOVEL", "No", "1414", "", ""]],
            [["1", "6", "1995-03-00", "", "TSR", "NOVEL"]], [["1", "A"]])[0]
        self.assertEqual(w["first_pub_date"], "1995-03")

    def test_letter_series_number_preferred(self):
        w = self.build([["1", "Book", "1990-00-00", "NOVEL", "No", "1414", "3", "3a"]],
                       [], [["1", "A"]])[0]
        self.assertEqual(w["series_number"], "3a")


if __name__ == "__main__":
    unittest.main()
