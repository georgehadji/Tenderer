"""Deadlines from a legal rule and the holiday calendar (docs/architecture.md §6.2, AD8).

Every plausible counting convention is computed; the reminder goes out by the earliest one (`remind_by`).
`legal_latest` follows Regulation 1182/71 as secondary sources describe it (UNVERIFIED against the primary
text) and is shown only as information. A year without a reviewed calendar makes the deadline ambiguous.
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, timedelta

from tenderer.core.catalog.tender import OfferTerms, Unit
from tenderer.core.rules.dates import Calendar, add_months, is_weekend


@dataclass(frozen=True)
class DeadlineRule:
    amount: int
    unit: Unit
    source_section: str


@dataclass(frozen=True)
class Deadline:
    remind_by: date
    legal_latest: date
    ambiguous: bool
    note: str


def deadline(event_on: date, rule: DeadlineRule, calendar: Calendar) -> Deadline:
    n = rule.amount
    if n <= 0:
        raise ValueError("a deadline needs a positive amount")
    if rule.unit is Unit.WORKING_DAYS:
        legal = _working_days_after(event_on, n, calendar.is_working_day)
        weekdays_only = _working_days_after(event_on, n, lambda d: not is_weekend(d))
        event_counted = _working_days_after(event_on - timedelta(days=1), n, calendar.is_working_day)
        candidates: tuple[date, ...] = (legal, weekdays_only, event_counted)
    else:
        end = event_on + timedelta(days=n) if rule.unit is Unit.DAYS else add_months(event_on, n)
        legal = _roll_forward(end, calendar)
        candidates = (legal, end - timedelta(days=1))  # second: the day of the event is counted
    remind_by = min(candidates)
    years = range(min(event_on, remind_by).year, legal.year + 1)
    missing = [y for y in years if y not in calendar.reviewed_years]
    note = f"no reviewed holiday calendar for {', '.join(map(str, missing))}" if missing else ""
    return Deadline(remind_by, legal, bool(missing), note)


def offer_validity_end(terms: OfferTerms, offer_deadline: date) -> date:
    """The offer is valid `offer_validity_months` from the day after the deadline (§4.4.1, strict reading)."""
    return add_months(offer_deadline + timedelta(days=1), terms.offer_validity_months)


def _working_days_after(start: date, n: int, is_working: Callable[[date], bool]) -> date:
    d = start
    while n:
        d += timedelta(days=1)
        if is_working(d):
            n -= 1
    return d


def _roll_forward(d: date, calendar: Calendar) -> date:
    while not calendar.is_working_day(d):
        d += timedelta(days=1)
    return d

