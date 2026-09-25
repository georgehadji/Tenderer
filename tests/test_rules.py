"""Checklist and deadlines. Golden cases: the «Έγγραφα» boundaries of the v0 workbook check."""

import datetime as dt
from datetime import date

import pytest
from hypothesis import given
from hypothesis import strategies as st

from tenderer.core.catalog.tender import Anchor, Unit
from tenderer.core.rules.checklist import DocumentFact, Status, evaluate, open_items
from tenderer.core.rules.dates import Calendar, add_months, days360_us, weekdays_back
from tenderer.core.rules.deadlines import DeadlineRule, deadline, offer_validity_end

INVITATION, OFFER_DEADLINE, AWARD_DOCS = date(2026, 8, 7), date(2026, 8, 19), date(2026, 10, 20)
CONTRACT_END = date(2029, 6, 30)
AT_AWARD = {Anchor.SUBMISSION: AWARD_DOCS, Anchor.INVITATION_SENT: INVITATION, Anchor.CONTRACT_END: CONTRACT_END}
AT_OFFER = {Anchor.SUBMISSION: OFFER_DEADLINE, Anchor.INVITATION_SENT: INVITATION}


def status(tender, rid, fact_kwargs, key_dates):
    req = tender.requirement(rid)
    [item] = evaluate([req], [DocumentFact(req.doc_type, **fact_kwargs)], key_dates)
    return item.status


WD29 = weekdays_back(AWARD_DOCS, 29)
CASES = [
    ("R12 exactly 3 months", "R12", {"issued_on": date(2026, 7, 20)}, AT_AWARD, Status.NOT_SATISFIED),
    ("R12 3 months minus a day", "R12", {"issued_on": date(2026, 7, 21)}, AT_AWARD, Status.SATISFIED),
    ("R12 after submission", "R12", {"issued_on": date(2026, 10, 21)}, AT_AWARD, Status.NOT_SATISFIED),
    ("R18 29 working days", "R18", {"issued_on": WD29}, AT_AWARD, Status.SATISFIED),
    ("R18 one day earlier", "R18", {"issued_on": WD29 - dt.timedelta(days=1)}, AT_AWARD, Status.NOT_SATISFIED),
    ("R13 expires on the day", "R13", {"valid_until": AWARD_DOCS}, AT_AWARD, Status.SATISFIED),
    ("R13 expired the day before", "R13", {"valid_until": date(2026, 10, 19)}, AT_AWARD, Status.NOT_SATISFIED),
    ("R9 signed on invitation day", "R9", {"issued_on": INVITATION}, AT_OFFER, Status.NOT_SATISFIED),
    ("R9 signed after deadline", "R9", {"issued_on": date(2026, 8, 20)}, AT_OFFER, Status.NOT_SATISFIED),
    ("R9 signed on deadline", "R9", {"issued_on": OFFER_DEADLINE}, AT_OFFER, Status.SATISFIED),
    ("R22 two months after end", "R22", {"valid_until": date(2029, 8, 30)}, AT_AWARD, Status.SATISFIED),
    ("R22 a day short", "R22", {"valid_until": date(2029, 8, 29)}, AT_AWARD, Status.NOT_SATISFIED),
    ("R1 in force at deadline", "R1", {"valid_until": OFFER_DEADLINE}, AT_OFFER, Status.SATISFIED),
    ("R12 award date blank", "R12", {"issued_on": date(2026, 9, 1)}, {}, Status.UNKNOWN),
    ("manual blank", "R4", {}, AT_AWARD, Status.UNKNOWN),
    ("manual set", "R4", {"manual_status": Status.SATISFIED}, AT_AWARD, Status.SATISFIED),
    ("manual status ignored on a dated rule", "R12", {"manual_status": Status.SATISFIED}, AT_AWARD, Status.UNKNOWN),
    ("not applicable", "R10", {"applicable": False}, AT_OFFER, Status.NOT_APPLICABLE),
]


@pytest.mark.parametrize(("label", "rid", "fact", "key_dates", "want"), CASES, ids=[c[0] for c in CASES])
def test_workbook_document_boundaries(tender, label, rid, fact, key_dates, want):
    assert status(tender, rid, fact, key_dates) is want


def test_r18_boundary_date_is_a_weekday():
    assert WD29 == date(2026, 9, 9)  # a Wednesday


def test_offer_dates_match_workbook(tender):
    end = offer_validity_end(tender.offer, OFFER_DEADLINE)
    assert end == date(2027, 8, 20)
    assert end + dt.timedelta(days=tender.offer.participation_guarantee_extra_days) == date(2027, 9, 19)
    assert add_months(CONTRACT_END, tender.offer.performance_guarantee_extra_months) == date(2029, 8, 30)


def test_no_record_is_unknown_and_open(tender):
    items = evaluate([tender.requirement("R13")], [], AT_AWARD)
    assert [(i.status, i.reason) for i in items] == [(Status.UNKNOWN, "no_record")]
    assert open_items(items) == items


def test_one_item_per_driver(tender):
    req = tender.requirement("R20")
    items = evaluate([req], [DocumentFact(req.doc_type, "driver 1", valid_until=date(2027, 1, 1)),
                             DocumentFact(req.doc_type, "driver 2", valid_until=date(2026, 1, 1))], AT_AWARD)
    assert [(i.subject, i.status) for i in items] == [
        ("driver 1", Status.SATISFIED), ("driver 2", Status.NOT_SATISFIED)]


optional_date = st.none() | st.dates(date(2020, 1, 1), date(2032, 12, 31))


@given(rid=st.sampled_from([f"R{n}" for n in range(1, 27)]), issued=optional_date, valid=optional_date,
       submission=optional_date, invitation=optional_date, end=optional_date)
def test_h3_a_missing_fact_never_yields_satisfied(tender, rid, issued, valid, submission, invitation, end):
    """H3: SATISFIED requires every date the rule reads."""
    req = tender.requirement(rid)
    keys = {k: v for k, v in ((Anchor.SUBMISSION, submission), (Anchor.INVITATION_SENT, invitation),
                              (Anchor.CONTRACT_END, end)) if v is not None}
    [item] = evaluate([req], [DocumentFact(req.doc_type, issued_on=issued, valid_until=valid)], keys)
    if item.status is Status.SATISFIED:
        v = req.validity
        assert v.kind.value in ("none",) or v.anchor in keys
        if v.kind.value in ("issued_within", "signed_after"):
            assert issued is not None
        if v.kind.value in ("in_force", "valid_until"):
            assert valid is not None
        assert v.kind.value != "manual"


# ---------------- deadlines ----------------
REVIEWED_2026 = Calendar(frozenset({date(2026, 10, 28), date(2026, 12, 25), date(2026, 12, 26)}), frozenset({2026}))


def test_five_working_days_skip_weekend_and_holiday():
    # ΕΕΕΣ renewal request on Fri 23 Oct 2026; 28 Oct is a holiday (X1, §3.1)
    d = deadline(date(2026, 10, 23), DeadlineRule(5, Unit.WORKING_DAYS, "3.1"), REVIEWED_2026)
    assert d.legal_latest == date(2026, 11, 2)
    assert d.remind_by == date(2026, 10, 30)  # earliest convention: the holiday counted as a working day
    assert not d.ambiguous


def test_calendar_days_roll_forward_but_remind_by_earliest():
    d = deadline(date(2026, 10, 14), DeadlineRule(10, Unit.DAYS, "5.3.1"), REVIEWED_2026)  # ends Sat 24 Oct
    assert d.legal_latest == date(2026, 10, 26)
    assert d.remind_by == date(2026, 10, 23)


def test_missing_calendar_year_is_ambiguous():
    d = deadline(date(2027, 3, 1), DeadlineRule(5, Unit.WORKING_DAYS, "3.1"), REVIEWED_2026)
    assert d.ambiguous and "2027" in d.note


@given(st.dates(date(2026, 1, 1), date(2026, 11, 30)), st.integers(1, 20), st.sampled_from(list(Unit)))
def test_remind_by_is_never_after_legal_latest(event, n, unit):
    d = deadline(event, DeadlineRule(n, unit, "x"), REVIEWED_2026)
    assert d.remind_by <= d.legal_latest
    assert d.remind_by > event - dt.timedelta(days=1)


def test_days360_us_matches_spreadsheet_basis_0():
    assert days360_us(date(2026, 10, 15), date(2029, 6, 30)) == 975
    assert days360_us(date(2026, 1, 31), date(2026, 3, 31)) == 60
    assert days360_us(date(2028, 2, 29), date(2029, 2, 28)) == 360


# ---------------- rule kinds no current tender uses ----------------
def req(kind, amount=None, unit=None, anchor=Anchor.SUBMISSION):
    from tenderer.core.catalog.tender import Requirement, Validity, ValidityKind
    return Requirement("R99", "x", ("Β9",), "x", "x", "1.1", "doc", ("client",),
                       Validity(ValidityKind(kind), amount, unit, anchor), None)


@pytest.mark.parametrize(("issued", "want"), [
    (date(2026, 10, 11), Status.SATISFIED), (date(2026, 10, 10), Status.NOT_SATISFIED)])
def test_issued_within_calendar_days(issued, want):
    [item] = evaluate([req("issued_within", 10, Unit.DAYS)], [DocumentFact("doc", issued_on=issued)], AT_AWARD)
    assert item.status is want


@pytest.mark.parametrize(("valid", "want"), [
    (date(2026, 10, 30), Status.SATISFIED), (date(2026, 10, 29), Status.NOT_SATISFIED)])
def test_valid_until_calendar_days(valid, want):
    [item] = evaluate([req("valid_until", 10, Unit.DAYS)], [DocumentFact("doc", valid_until=valid)], AT_AWARD)
    assert item.status is want


def test_rule_without_anchor_is_unknown():
    [item] = evaluate([req("in_force", anchor=None)], [DocumentFact("doc", valid_until=date(2030, 1, 1))], AT_AWARD)
    assert item.status is Status.UNKNOWN


def test_deadline_needs_a_positive_amount():
    with pytest.raises(ValueError):
        deadline(date(2026, 1, 1), DeadlineRule(0, Unit.DAYS, "x"), REVIEWED_2026)


def test_calendar_file_reviewed_and_mixed_years(tmp_path):
    from tenderer.core.rules.dates import load_calendar
    ok = tmp_path / "holidays-2026.csv"
    ok.write_text("date,name,reviewed\n2026-01-01,a,yes\n", encoding="utf-8")
    assert load_calendar([ok]).reviewed_years == frozenset({2026})
    bad = tmp_path / "holidays-2027.csv"
    bad.write_text("date,name,reviewed\n2027-01-01,a,yes\n2028-01-01,b,yes\n", encoding="utf-8")
    with pytest.raises(ValueError):
        load_calendar([bad])


@pytest.mark.parametrize(("rid", "fact", "key_dates", "reason"), [
    ("R13", {}, AT_AWARD, "missing_date:valid_until"),
    ("R22", {}, AT_AWARD, "missing_date:valid_until"),
    ("R22", {"valid_until": date(2030, 1, 1)}, {}, "missing_date:contract_end"),
    ("R9", {}, AT_OFFER, "missing_date:issued_on"),
    ("R9", {"issued_on": date(2026, 8, 10)}, {Anchor.INVITATION_SENT: INVITATION}, "missing_date:submission"),
    ("R9", {"issued_on": date(2026, 8, 10)}, {}, "missing_date:invitation_sent"),
    ("R2", {}, {}, "recorded"),
])
def test_explicit_reasons(tender, rid, fact, key_dates, reason):
    req = tender.requirement(rid)
    [item] = evaluate([req], [DocumentFact(req.doc_type, **fact)], key_dates)
    assert item.reason == reason
