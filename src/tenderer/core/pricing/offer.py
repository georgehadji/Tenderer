"""Offer shape `discount_on_reference` (AD17): price, validator, guarantee amounts (docs/architecture.md §6.3).

The validator checks what the client intends to type into the platform. It never proposes a discount
(CLAUDE.md §5). Violations are codes; wording belongs to the documents module.
"""

from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import StrEnum

from tenderer.core.pricing.money import CENT, Money, ceil_cents, round_cents, to_decimal

OFFER_SHAPES = frozenset({"discount_on_reference"})
MAX_DISCOUNT = 99


def offer_price(reference: Money, discount: int) -> Money:
    """Reference price × (1 − integer discount), to the cent, half up (§4.3.2.1)."""
    if not 0 <= discount <= MAX_DISCOUNT:
        raise ValueError(f"discount {discount} is outside 0-{MAX_DISCOUNT}")
    cents = round_cents(reference.amount) / CENT
    return Money(round_cents(cents * (100 - discount) / 100 * CENT), reference.currency)


def guarantee_amount(base: Money, rate: Decimal) -> Money:
    """A guarantee is at least `rate` of the base, rounded up to the cent (§4.3.1.2, §6.2.1)."""
    return Money(ceil_cents(round_cents(base.amount) * rate), base.currency)


@dataclass(frozen=True)
class Route:
    code: str
    reference: Money
    budget: Money  # without VAT and option
    days: int
    group: str = ""
    client_said_yes: bool = False  # recorded decision of the client, never ours


@dataclass(frozen=True)
class OfferLine:
    route_code: str
    discount: object  # as typed by the operator; parsed here
    form_price: Money | None  # the price the client types into the platform form
    template_price: Money | None  # the price in the signed offer template
    priority: object


class LineError(StrEnum):  # in the order they are checked; a line reports its first error
    UNKNOWN_ROUTE = "unknown_route"
    NO_CLIENT_DECISION = "no_client_decision"
    DISCOUNT_NOT_INTEGER = "discount_not_integer"  # the platform rounds a decimal discount up (§4.3.2.1)
    FORM_PRICE_MISSING = "form_price_missing"
    FORM_PRICE_WRONG = "form_price_wrong"
    TEMPLATE_PRICE_MISSING = "template_price_missing"
    TEMPLATE_MISMATCH = "template_mismatch"
    PRIORITY_INVALID = "priority_invalid"
    PRIORITY_DUPLICATE = "priority_duplicate"
    ROUTE_DUPLICATE = "route_duplicate"
    GROUP_DISCOUNT_MISMATCH = "group_discount_mismatch"


@dataclass(frozen=True)
class LineCheck:
    line: OfferLine
    error: LineError | None
    price: Money | None  # computed price, when the discount is valid


def validate_offer(lines: Sequence[OfferLine], routes: Mapping[str, Route]) -> tuple[LineCheck, ...]:
    discounts = [_integer(line.discount, 0, MAX_DISCOUNT) for line in lines]
    priorities = Counter(_integer(line.priority, 1, None) for line in lines)
    codes = Counter(line.route_code for line in lines)
    group_discounts: dict[str, set[int | None]] = {}
    for line, d in zip(lines, discounts, strict=True):
        route = routes.get(line.route_code)
        if route and route.group:
            group_discounts.setdefault(route.group, set()).add(d)

    out = []
    for line, d in zip(lines, discounts, strict=True):
        route = routes.get(line.route_code)
        price = offer_price(route.reference, d) if route and d is not None else None
        out.append(LineCheck(line, _first_error(line, route, d, price, priorities, codes, group_discounts), price))
    return tuple(out)


def _first_error(
    line: OfferLine, route: Route | None, d: int | None, price: Money | None,
    priorities: Counter[int | None], codes: Counter[str], groups: dict[str, set[int | None]],
) -> LineError | None:
    if route is None:
        return LineError.UNKNOWN_ROUTE
    if not route.client_said_yes:
        return LineError.NO_CLIENT_DECISION
    if d is None or price is None:
        return LineError.DISCOUNT_NOT_INTEGER
    if line.form_price is None:
        return LineError.FORM_PRICE_MISSING
    if not line.form_price.has_cents_only() or line.form_price != price:
        return LineError.FORM_PRICE_WRONG
    if line.template_price is None:
        return LineError.TEMPLATE_PRICE_MISSING
    if line.template_price != line.form_price:
        return LineError.TEMPLATE_MISMATCH
    p = _integer(line.priority, 1, None)
    if p is None:
        return LineError.PRIORITY_INVALID
    if priorities[p] > 1:
        return LineError.PRIORITY_DUPLICATE
    if codes[line.route_code] > 1:
        return LineError.ROUTE_DUPLICATE
    if route.group and len(groups[route.group]) > 1:
        return LineError.GROUP_DISCOUNT_MISMATCH
    return None


def _integer(value: object, low: int, high: int | None) -> int | None:
    try:
        d = to_decimal(value)
    except (TypeError, ArithmeticError):
        return None
    if not d.is_finite() or d != d.to_integral_value() or d < low or (high is not None and d > high):
        return None
    return int(d)


class GuaranteeCheck(StrEnum):
    MISSING_DATA = "missing_data"
    BELOW_MINIMUM = "below_minimum"
    MISSING_REQUIRED_DATE = "missing_required_date"
    EXPIRES_TOO_EARLY = "expires_too_early"
    OK_PAPER = "ok_paper"  # the original must reach the authority before the unsealing (§4.3.1.2)
    OK = "ok"


def check_participation_guarantee(
    minimum: Money, amount: Money | None, expires_on: date | None, paper: bool | None, required_until: date | None,
) -> GuaranteeCheck:
    if amount is None or expires_on is None or paper is None:
        return GuaranteeCheck.MISSING_DATA
    if amount < minimum:
        return GuaranteeCheck.BELOW_MINIMUM
    if required_until is None:
        return GuaranteeCheck.MISSING_REQUIRED_DATE
    if expires_on < required_until:
        return GuaranteeCheck.EXPIRES_TOO_EARLY
    return GuaranteeCheck.OK_PAPER if paper else GuaranteeCheck.OK
