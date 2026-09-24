"""GR jurisdiction pack: Easter vectors of docs/architecture.md §6.2, holiday files, number words."""

from datetime import date, timedelta

import pytest

from tenderer.jurisdictions.gr import number_in_words, orthodox_easter, public_holidays
from tenderer.shell.packs import calendar


@pytest.mark.parametrize(("year", "easter", "clean_monday", "good_friday", "whit_monday"), [
    (2026, date(2026, 4, 12), date(2026, 2, 23), date(2026, 4, 10), date(2026, 6, 1)),
    (2027, date(2027, 5, 2), date(2027, 3, 15), date(2027, 4, 30), date(2027, 6, 21)),
    (2028, date(2028, 4, 16), date(2028, 2, 28), date(2028, 4, 14), date(2028, 6, 5)),
])
def test_easter_vectors(year, easter, clean_monday, good_friday, whit_monday):
    assert orthodox_easter(year) == easter
    days = public_holidays(year)
    assert {clean_monday, good_friday, easter + timedelta(days=1), whit_monday} <= set(days)


def test_reference_files_match_the_computation():
    cal = calendar("gr")
    for year in range(2026, 2030):
        assert {d for d in cal.holidays if d.year == year} == set(public_holidays(year))


def test_unreviewed_years_stay_ambiguous():
    assert calendar("gr").reviewed_years == frozenset()  # every file still says reviewed=no


@pytest.mark.parametrize(("n", "words"), [
    (0, "μηδέν"), (1, "ένα"), (10, "δέκα"), (11, "έντεκα"), (12, "δώδεκα"), (13, "δεκατρία"), (14, "δεκατέσσερα"),
    (16, "δεκαέξι"), (19, "δεκαεννέα"), (20, "είκοσι"), (21, "είκοσι ένα"), (74, "εβδομήντα τέσσερα"),
    (99, "ενενήντα εννέα"),
])
def test_number_words_match_workbook(n, words):
    assert number_in_words(n) == words


def test_number_words_reject_out_of_range():
    with pytest.raises(ValueError):
        number_in_words(100)


# ---------------- identifiers (synthetic values only: this repository is public) ----------------
from tenderer.jurisdictions.gr.ids import afm, phone, plate  # noqa: E402


def test_afm_check_digit():
    assert afm(" 123456783 ") == "123456783"  # 1004 mod 11 = 3
    for bad in ("123456784", "12345678", "000000000", "12345678a"):
        with pytest.raises(ValueError):
            afm(bad)


@pytest.mark.parametrize(("raw", "want"), [("ΝΒΚ-1234", "ΝΒΚ-1234"), ("nbk 1234", "ΝΒΚ-1234"), ("ΝΒΚ1234", "ΝΒΚ-1234")])
def test_plate_normalised(raw, want):
    assert plate(raw) == want


@pytest.mark.parametrize("bad", ["ΝΒΓ-1234", "ΝΒ-1234", "ΝΒΚ-12345", "ΝΒΚ-12A4"])
def test_plate_rejected(bad):
    with pytest.raises(ValueError):
        plate(bad)


@pytest.mark.parametrize(("raw", "want"), [("6912345678", "+306912345678"), ("+30 231 012 3456", "+302310123456"),
                                           ("0030 69 1234 5678", "+306912345678")])
def test_phone_e164(raw, want):
    assert phone(raw) == want


@pytest.mark.parametrize("bad", ["5912345678", "691234567", "+44 20 7946 0000"])
def test_phone_rejected(bad):
    with pytest.raises(ValueError):
        phone(bad)
