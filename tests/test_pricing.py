"""Offer validator and guarantees: the offer-sheet cases of the v0 workbook check (§8 of the Phase B kit)."""

import datetime as dt
from decimal import Decimal as D

import pytest
from hypothesis import given
from hypothesis import strategies as st

from tenderer.core.pricing.money import Money, to_decimal
from tenderer.core.pricing.offer import (
    GuaranteeCheck,
    LineError,
    OfferLine,
    Route,
    check_participation_guarantee,
    guarantee_amount,
    offer_price,
    validate_offer,
)
from tenderer.core.rules.deadlines import offer_validity_end


def eur(s: str) -> Money:
    return Money(D(s))


ROUTES = {
    "G26-0703-Τ2": Route("G26-0703-Τ2", eur("51.18"), eur("26869.50"), 525, client_said_yes=True),
    "26-ΠΠ-Τ1": Route("26-ΠΠ-Τ1", eur("77.55"), eur("40713.75"), 525, client_said_yes=False),
    "TEST-TIE": Route("TEST-TIE", eur("51.25"), eur("26906.25"), 525, client_said_yes=True),
    "S26-ΓΛΚΒ-Τ5": Route("S26-ΓΛΚΒ-Τ5", eur("586.30"), eur("61561.50"), 105, client_said_yes=True),
    "TEST-EDGE": Route("TEST-EDGE", eur("80.00"), eur("42000.00"), 525, client_said_yes=True),
}


def line(code, d, form, template, prio):
    return OfferLine(code, d, None if form is None else eur(form), None if template is None else eur(template), prio)


def test_tie_rounds_half_up():
    assert offer_price(eur("51.25"), 10) == eur("46.13")  # 46.125


def test_guarantee_amounts_round_up_to_the_cent():
    assert guarantee_amount(eur("26869.50"), D("0.002")) == eur("53.74")  # 53.739
    # performance guarantee: 4% of price × days; 49.64 × 525 × 0.04 = 1042.44 exactly
    assert guarantee_amount(Money(offer_price(eur("51.18"), 3).amount * 525), D("0.04")) == eur("1042.44")
    assert guarantee_amount(Money(offer_price(eur("51.25"), 10).amount * 525), D("0.04")) == eur("968.73")


def test_clean_offer():
    p1, p3 = offer_price(eur("51.18"), 3), offer_price(eur("51.25"), 10)
    checks = validate_offer([
        line("G26-0703-Τ2", 3, str(p1.amount), str(p1.amount), 1),
        line("TEST-TIE", 10, str(p3.amount), str(p3.amount), 2),
    ], ROUTES)
    assert [c.error for c in checks] == [None, None]
    assert checks[0].price == eur("49.64")


def test_one_error_per_line_in_workbook_order():
    p1 = offer_price(eur("51.18"), 3)
    p5 = offer_price(eur("586.30"), 15)
    pe = offer_price(eur("80.00"), 20)
    checks = validate_offer([
        line("G26-0703-Τ2", D("7.5"), str(p1.amount), str(p1.amount), 1),  # decimal discount
        line("TEST-TIE", 10, "46.12", "46.12", 2),                            # wrong rounding
        line("S26-ΓΛΚΒ-Τ5", 15, str(p5.amount), "498.35", 3),                # template differs (498.36)
        line("TEST-EDGE", 20, str(pe.amount), str(pe.amount), 3),             # duplicate priority
        line("26-ΠΠ-Τ1", 0, "77.55", "77.55", 5),                             # client said no
        line("NO-SUCH", 0, "1", "1", 6),                                       # unknown route
    ], ROUTES)
    assert [c.error for c in checks] == [
        LineError.DISCOUNT_NOT_INTEGER, LineError.FORM_PRICE_WRONG, LineError.TEMPLATE_MISMATCH,
        LineError.PRIORITY_DUPLICATE, LineError.NO_CLIENT_DECISION, LineError.UNKNOWN_ROUTE,
    ]
    assert p5 == eur("498.36")


def test_group_discount_and_duplicate_route():
    routes = dict(ROUTES)
    routes["TEST-TIE"] = Route("TEST-TIE", eur("51.25"), eur("26906.25"), 525, group="Ο1", client_said_yes=True)
    routes["TEST-EDGE"] = Route("TEST-EDGE", eur("80.00"), eur("42000.00"), 525, group="Ο1", client_said_yes=True)
    p3, pe = offer_price(eur("51.25"), 10), offer_price(eur("80.00"), 12)
    checks = validate_offer([
        line("TEST-TIE", 10, str(p3.amount), str(p3.amount), 1),
        line("TEST-EDGE", 12, str(pe.amount), str(pe.amount), 2),
        line("TEST-TIE", 10, str(p3.amount), str(p3.amount), 3),
    ], routes)
    assert checks[1].error is LineError.GROUP_DISCOUNT_MISMATCH
    assert checks[2].error is LineError.ROUTE_DUPLICATE


@pytest.mark.parametrize(("discount", "ok"), [(0, True), (99, True), (100, False), (-1, False), ("7", True),
                                              (D("7.0"), True), (D("7.5"), False), (7.0, False), (True, False)])
def test_discount_must_be_an_integer_0_to_99_and_never_a_float(discount, ok):
    d = int(to_decimal(discount)) if ok else 0
    price = offer_price(eur("51.18"), d).amount if ok else D("1")
    [check] = validate_offer([line("G26-0703-Τ2", discount, str(price), str(price), 1)], ROUTES)
    assert (check.error is None) is ok


def test_floats_are_rejected_at_the_boundary():
    with pytest.raises(TypeError):
        Money(51.18)  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        to_decimal(0.1)


def test_form_price_with_more_than_two_decimals_is_wrong():
    p = offer_price(eur("51.18"), 3).amount
    [check] = validate_offer([line("G26-0703-Τ2", 3, str(p) + "0001", str(p), 1)], ROUTES)
    assert check.error is LineError.FORM_PRICE_WRONG


def test_participation_guarantee_checks(tender):
    until = offer_validity_end(tender.offer, dt.date(2026, 8, 19)) + dt.timedelta(days=30)
    assert until == dt.date(2027, 9, 19)
    need = guarantee_amount(Money(D("26869.50") + D("26906.25")), D("0.002"))
    assert check_participation_guarantee(need, need, until, False, until) is GuaranteeCheck.OK
    assert check_participation_guarantee(need, eur("1.00"), until, False, until) is GuaranteeCheck.BELOW_MINIMUM
    assert check_participation_guarantee(need, eur("1000.00"), until - dt.timedelta(days=1), False, until) \
        is GuaranteeCheck.EXPIRES_TOO_EARLY
    assert check_participation_guarantee(need, eur("1000.00"), until, True, until) is GuaranteeCheck.OK_PAPER
    assert check_participation_guarantee(need, None, until, True, until) is GuaranteeCheck.MISSING_DATA


@given(st.decimals(min_value=D("0.01"), max_value=D("99999.99"), places=2), st.integers(0, 99))
def test_offer_price_is_cents_and_never_above_reference(ref, d):
    p = offer_price(Money(ref), d)
    assert p.has_cents_only()
    assert p <= Money(ref)


# ---------------- cases found by mutation testing (scripts/mutation.sh, 2026-09-25) ----------------
def _line(code, discount, priority):
    price = offer_price(ROUTES[code].reference, discount) if code in ROUTES else None
    return OfferLine(code, discount, price, price, priority)


def test_duplicate_first_priority_and_line_identity():
    routes = {**ROUTES, "26-ΠΠ-Τ1": Route("26-ΠΠ-Τ1", eur("77.55"), eur("40713.75"), 525, client_said_yes=True)}
    lines = [OfferLine(c, 3, offer_price(routes[c].reference, 3), offer_price(routes[c].reference, 3), 1)
             for c in ("G26-0703-Τ2", "26-ΠΠ-Τ1")]
    checks = validate_offer(lines, routes)
    assert [c.error for c in checks] == [LineError.PRIORITY_DUPLICATE] * 2
    assert all(c.line is line for c, line in zip(checks, lines, strict=True))


def test_same_discount_across_a_group_is_clean():
    group = {c: Route(c, eur("50.00"), eur("26250.00"), 525, group="Ο1", client_said_yes=True) for c in ("A", "B")}
    lines = [OfferLine(c, 5, eur("47.50"), eur("47.50"), p) for p, c in enumerate(("A", "B"), start=1)]
    assert [c.error for c in validate_offer(lines, group)] == [None, None]


def test_guarantee_without_its_kind_is_missing_data():
    assert check_participation_guarantee(eur("53.74"), eur("60.00"), dt.date(2027, 10, 1), None,
                                         dt.date(2027, 9, 19)) is GuaranteeCheck.MISSING_DATA


@pytest.mark.parametrize(("value", "message"), [(0.1, "floats and booleans"), (True, "floats and booleans"),
                                                (object(), "is not a number")])
def test_to_decimal_refuses(value, message):
    with pytest.raises(TypeError, match=message):
        to_decimal(value)
