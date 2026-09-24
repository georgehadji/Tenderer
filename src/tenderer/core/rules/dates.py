"""Calendar arithmetic shared by the rules and pricing modules. Pure; no clock."""

import calendar
import csv
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path


def add_months(d: date, months: int) -> date:
    """Same day `months` later, clamped to the month's last day (spreadsheet EDATE)."""
    y, m = divmod(d.month - 1 + months, 12)
    year, month = d.year + y, m + 1
    return date(year, month, min(d.day, calendar.monthrange(year, month)[1]))


def is_weekend(d: date) -> bool:
    return d.weekday() >= 5


def weekdays_back(d: date, n: int) -> date:
    """The n-th weekday before d. Holidays count as working days, which gives the latest start."""
    while n:
        d -= timedelta(days=1)
        if not is_weekend(d):
            n -= 1
    return d


def days360_us(start: date, end: date) -> int:
    """30/360 US (NASD) day count, as spreadsheet YEARFRAC basis 0."""
    def last_of_feb(d: date) -> bool:
        return d.month == 2 and d.day == calendar.monthrange(d.year, 2)[1]

    d1, d2 = start.day, end.day
    if last_of_feb(start) and last_of_feb(end):
        d2 = 30
    if last_of_feb(start):
        d1 = 30
    if d2 == 31 and d1 >= 30:
        d2 = 30
    if d1 == 31:
        d1 = 30
    return (end.year - start.year) * 360 + (end.month - start.month) * 30 + (d2 - d1)


@dataclass(frozen=True)
class Calendar:
    """Public holidays from reviewed files. A year missing from `reviewed_years` makes deadlines ambiguous."""
    holidays: frozenset[date]
    reviewed_years: frozenset[int]

    def is_working_day(self, d: date) -> bool:
        return not is_weekend(d) and d not in self.holidays


def load_calendar(paths: Iterable[Path]) -> Calendar:
    """Read `holidays-<year>.csv` files (columns date,name,reviewed). A year counts as reviewed only if
    every row of its file says `yes`."""
    holidays: set[date] = set()
    reviewed: set[int] = set()
    for path in paths:
        rows = list(csv.DictReader(path.read_text(encoding="utf-8").splitlines()))
        days = [date.fromisoformat(r["date"]) for r in rows]
        years = {d.year for d in days}
        if len(years) != 1:
            raise ValueError(f"{path}: rows must belong to one year, found {sorted(years)}")
        holidays.update(days)
        if all(r["reviewed"] == "yes" for r in rows):
            reviewed |= years
    return Calendar(frozenset(holidays), frozenset(reviewed))
