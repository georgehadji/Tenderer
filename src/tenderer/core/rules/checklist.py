"""Checklist evaluator: the status of every requirement for one planned submission (docs/architecture.md §6.2).

Decision table: one small evaluator per validity kind, kept in a dict. Results are three-valued (AD7):
a missing fact is UNKNOWN, never SATISFIED, and UNKNOWN is shown exactly like NOT_SATISFIED.
Freshness is measured against the planned submission date passed in `key_dates`, never against today.
"""

from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from datetime import date, timedelta
from enum import StrEnum

from tenderer.core.catalog.tender import Anchor, Requirement, Unit, Validity, ValidityKind
from tenderer.core.rules.dates import add_months, weekdays_back


class Status(StrEnum):
    SATISFIED = "SATISFIED"
    NOT_SATISFIED = "NOT_SATISFIED"
    UNKNOWN = "UNKNOWN"
    NOT_APPLICABLE = "NOT_APPLICABLE"


@dataclass(frozen=True)
class DocumentFact:
    """Metadata of one document the client holds. Never its content (AD5)."""
    doc_type: str
    subject: str = ""  # which vehicle, driver or escort, as a label; empty for the client
    issued_on: date | None = None  # issue or signature date
    valid_until: date | None = None
    manual_status: Status | None = None  # only for `manual` requirements
    applicable: bool = True


@dataclass(frozen=True)
class Item:
    requirement_id: str
    text: str  # the requirement as the tender states it, so a snapshot reads on its own
    subject: str
    status: Status
    reason: str
    source_section: str


Outcome = tuple[Status, str]
KeyDates = Mapping[Anchor, date]


def evaluate(
    requirements: Iterable[Requirement], facts: Iterable[DocumentFact], key_dates: KeyDates
) -> tuple[Item, ...]:
    facts = tuple(facts)
    items: list[Item] = []
    for req in requirements:
        mine = [f for f in facts if f.doc_type == req.doc_type]
        if not mine:
            items.append(Item(req.id, req.text, "", Status.UNKNOWN, "no_record", req.source_section))
        for fact in mine:
            if not fact.applicable:
                status, reason = Status.NOT_APPLICABLE, "not_applicable"
            else:
                status, reason = _EVALUATORS[req.validity.kind](req.validity, fact, key_dates)
            items.append(Item(req.id, req.text, fact.subject, status, reason, req.source_section))
    return tuple(items)


def open_items(items: Iterable[Item]) -> tuple[Item, ...]:
    return tuple(i for i in items if i.status not in (Status.SATISFIED, Status.NOT_APPLICABLE))


def _date(v: Validity, k: KeyDates) -> date | None:
    return k.get(v.anchor) if v.anchor is not None else None


def _in_force(v: Validity, f: DocumentFact, k: KeyDates) -> Outcome:
    anchor = _date(v, k)
    if anchor is None:
        return Status.UNKNOWN, f"missing_date:{v.anchor}"
    if f.valid_until is None:
        return Status.UNKNOWN, "missing_date:valid_until"
    return (Status.SATISFIED, "in_force") if f.valid_until >= anchor else (Status.NOT_SATISFIED, "expired")


def _issued_within(v: Validity, f: DocumentFact, k: KeyDates) -> Outcome:
    anchor = _date(v, k)
    if anchor is None or v.amount is None:
        return Status.UNKNOWN, f"missing_date:{v.anchor}"
    if f.issued_on is None:
        return Status.UNKNOWN, "missing_date:issued_on"
    if f.issued_on > anchor:
        return Status.NOT_SATISFIED, "issued_after_submission"
    # The window ends on the anchor and has `amount` units; its first day is the earliest allowed issue date.
    # Working days count holidays as working days: the shortest window, so we warn early, never late (AD8).
    if v.unit is Unit.MONTHS:
        ok = f.issued_on > add_months(anchor, -v.amount)
    elif v.unit is Unit.DAYS:
        ok = f.issued_on > anchor - timedelta(days=v.amount)
    else:
        ok = f.issued_on >= weekdays_back(anchor, v.amount - 1)
    return (Status.SATISFIED, "fresh") if ok else (Status.NOT_SATISFIED, "too_old")


def _signed_after(v: Validity, f: DocumentFact, k: KeyDates) -> Outcome:
    anchor, submission = _date(v, k), k.get(Anchor.SUBMISSION)
    if anchor is None:
        return Status.UNKNOWN, f"missing_date:{v.anchor}"
    if submission is None:
        return Status.UNKNOWN, f"missing_date:{Anchor.SUBMISSION}"
    if f.issued_on is None:
        return Status.UNKNOWN, "missing_date:issued_on"
    if f.issued_on <= anchor:
        return Status.NOT_SATISFIED, "signed_too_early"
    if f.issued_on > submission:
        return Status.NOT_SATISFIED, "signed_after_submission"
    return Status.SATISFIED, "signed_in_window"


def _valid_until(v: Validity, f: DocumentFact, k: KeyDates) -> Outcome:
    anchor = _date(v, k)
    if anchor is None or v.amount is None:
        return Status.UNKNOWN, f"missing_date:{v.anchor}"
    if f.valid_until is None:
        return Status.UNKNOWN, "missing_date:valid_until"
    needed = add_months(anchor, v.amount) if v.unit is Unit.MONTHS else anchor + timedelta(days=v.amount)
    return (Status.SATISFIED, "long_enough") if f.valid_until >= needed else (Status.NOT_SATISFIED, "expires_too_early")


def _none(v: Validity, f: DocumentFact, k: KeyDates) -> Outcome:
    return Status.SATISFIED, "recorded"


def _manual(v: Validity, f: DocumentFact, k: KeyDates) -> Outcome:
    if f.manual_status in (Status.SATISFIED, Status.NOT_SATISFIED):
        return f.manual_status, "operator_checked"
    return Status.UNKNOWN, "awaiting_operator"


_EVALUATORS: dict[ValidityKind, Callable[[Validity, DocumentFact, KeyDates], Outcome]] = {
    ValidityKind.IN_FORCE: _in_force,
    ValidityKind.ISSUED_WITHIN: _issued_within,
    ValidityKind.SIGNED_AFTER: _signed_after,
    ValidityKind.VALID_UNTIL: _valid_until,
    ValidityKind.NONE: _none,
    ValidityKind.MANUAL: _manual,
}
