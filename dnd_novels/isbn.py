"""ISBN helpers: normalise, validate and convert between ISBN-10 and ISBN-13."""

import re


def clean(isbn: str) -> str:
    return re.sub(r"[^0-9Xx]", "", isbn).upper()


def isbn10_check_digit(first9: str) -> str:
    total = sum((10 - i) * int(d) for i, d in enumerate(first9))
    check = (11 - total % 11) % 11
    return "X" if check == 10 else str(check)


def isbn13_check_digit(first12: str) -> str:
    total = sum(int(d) * (1 if i % 2 == 0 else 3) for i, d in enumerate(first12))
    return str((10 - total % 10) % 10)


def is_valid(isbn: str) -> bool:
    s = clean(isbn)
    if len(s) == 10:
        return s[:9].isdigit() and isbn10_check_digit(s[:9]) == s[9]
    if len(s) == 13:
        return s.isdigit() and isbn13_check_digit(s[:12]) == s[12]
    return False


def to_isbn13(isbn: str) -> str:
    s = clean(isbn)
    if len(s) == 13:
        return s
    if len(s) != 10:
        raise ValueError(f"Not an ISBN: {isbn!r}")
    core = "978" + s[:9]
    return core + isbn13_check_digit(core)


def to_isbn10(isbn: str) -> str:
    """ISBN-10 equivalent, or "" for 979- ISBNs, which have none."""
    s = clean(isbn)
    if len(s) == 10:
        return s
    if len(s) != 13:
        raise ValueError(f"Not an ISBN: {isbn!r}")
    if not s.startswith("978"):
        return ""
    return s[3:12] + isbn10_check_digit(s[3:12])
