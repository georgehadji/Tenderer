"""Go/no-go cost model for one taxi route (docs/plan.md §5). Reproduces the v0 workbook to the cent.

Every figure comes from the client ("Κόστη του πελάτη" of the workbook) or the tender; nothing is guessed.
A route with a missing input returns `Missing`, which the caller shows as "λείπουν στοιχεία", never as zero.
"""

import math
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from tenderer.core.catalog.tender import OfferTerms
from tenderer.core.pricing.gonogo import Costs, GoNoGo, Line, go_no_go
from tenderer.core.pricing.money import Money
from tenderer.core.pricing.offer import guarantee_amount
from tenderer.core.rules.dates import days360_us


@dataclass(frozen=True)
class ClientCosts:
    fuel_l_per_100km: Decimal
    fuel_price_per_l: Decimal
    wear_per_km: Decimal  # tyres, service, depreciation
    opportunity_per_hour: Decimal  # fares lost while driving the route, after fuel
    extra_insurance_per_year: Decimal
    bank_rate_per_year: Decimal  # commission on guarantees
    bank_fee_per_guarantee: Decimal
    paid_share: Decimal  # share of the Annex I days the client expects to be paid for (§6.6.3)
    fuel_increase: Decimal  # scenario: no fuel adjustment for taxis (§6.6.4)

    def __post_init__(self) -> None:
        if not 0 < self.paid_share <= 1:
            raise ValueError("paid_share must be in (0, 1]")


@dataclass(frozen=True)
class Contract:
    school_years: int
    signed_on: date  # estimate until signed
    ends_on: date

    def __post_init__(self) -> None:
        if self.school_years <= 0 or self.ends_on <= self.signed_on:
            raise ValueError("contract needs school_years > 0 and ends_on after signed_on")


@dataclass(frozen=True)
class RouteInputs:
    reference: Money  # € per day without VAT (Annex I)
    days: int  # Annex I days over the whole contract
    budget: Money  # without VAT and option
    km_per_day: Decimal  # all kilometres, with and without pupils
    hours_per_day: Decimal
    escort: bool
    escort_per_day: Decimal | None


@dataclass(frozen=True)
class Missing:
    fields: tuple[str, ...]


def paid_days_per_year(route: RouteInputs, client: ClientCosts, contract: Contract) -> Decimal:
    return Decimal(route.days) / contract.school_years * client.paid_share


def participation_guarantee_months(terms: OfferTerms) -> int:
    """Assumption of the workbook: the guarantee is held for its whole validity (§4.4.1, §4.3.1.2)."""
    return terms.offer_validity_months + math.ceil(terms.participation_guarantee_extra_days / 30)


def performance_guarantee_months(terms: OfferTerms, contract: Contract) -> Decimal:
    """From signature to `performance_guarantee_extra_months` after the end (§6.2.1), 30/360 like the workbook."""
    months = Decimal(days360_us(contract.signed_on, contract.ends_on)) / 360 * 12
    return months + terms.performance_guarantee_extra_months


def costs(
    route: RouteInputs, client: ClientCosts, contract: Contract, terms: OfferTerms, deduction_rate: Decimal,
) -> Costs | Missing:
    if route.escort and route.escort_per_day is None:
        return Missing(("escort_per_day",))
    paid_days_total = route.days * client.paid_share
    guarantee = guarantee_amount(route.budget, terms.participation_guarantee_rate).amount
    per_day = (
        Line("fuel", route.km_per_day * client.fuel_l_per_100km / 100 * client.fuel_price_per_l),
        Line("wear", route.km_per_day * client.wear_per_km),
        Line("escort", route.escort_per_day if route.escort and route.escort_per_day is not None else Decimal(0)),
        Line("insurance", client.extra_insurance_per_year / paid_days_per_year(route, client, contract)),
        Line("opportunity", route.hours_per_day * client.opportunity_per_hour),
        Line("guarantee_bank_costs", (
            2 * client.bank_fee_per_guarantee
            + client.bank_rate_per_year * guarantee * participation_guarantee_months(terms) / 12
        ) / paid_days_total),
    )
    price_share = (
        Line("deductions", deduction_rate),
        Line("performance_guarantee_carry", terms.performance_guarantee_rate * client.bank_rate_per_year
             * performance_guarantee_months(terms, contract) / 12 / client.paid_share),
    )
    return Costs(per_day, price_share)


def analyse(
    route: RouteInputs, client: ClientCosts, contract: Contract, terms: OfferTerms, deduction_rate: Decimal,
) -> GoNoGo | Missing:
    c = costs(route, client, contract, terms, deduction_rate)
    if isinstance(c, Missing):
        return c
    return go_no_go(route.reference, c, paid_days_per_year(route, client, contract))


def fuel_scenario_net(result: GoNoGo, route: RouteInputs, client: ClientCosts, discount: int) -> Decimal:
    """Net per day if fuel costs `fuel_increase` more for the whole contract, with no adjustment (§6.6.4)."""
    fuel = route.km_per_day * client.fuel_l_per_100km / 100 * client.fuel_price_per_l
    return result.net(discount) - fuel * client.fuel_increase


def warnings(route: RouteInputs, result: GoNoGo | Missing) -> tuple[str, ...]:
    """Always shown with a taxi go/no-go (docs/architecture.md §6.3)."""
    out = ["fuel_no_adjustment", "cancellation_no_compensation"]  # §6.6.4, §7.6.1
    if route.escort and route.escort_per_day == 0:
        out.append("escort_zero_cost")  # the contractor pays the escort (§4.3.2.2)
    if isinstance(result, GoNoGo) and result.break_even is None:
        out.append("loss_at_zero")
    return tuple(out)
