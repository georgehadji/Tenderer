"""Go/no-go breakdown (docs/plan.md §5, docs/architecture.md §6.3). Explainable: every number keeps its lines.

net(d) = offer price at discount d × (1 − Σ price shares) − Σ costs per day. The break-even discount is the
largest integer d with net(d) ≥ 0. It is shown to the client; it is never proposed as the discount.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal

from tenderer.core.pricing.money import Money
from tenderer.core.pricing.offer import MAX_DISCOUNT, offer_price


@dataclass(frozen=True)
class Line:
    name: str
    amount: Decimal


@dataclass(frozen=True)
class Costs:
    per_day: tuple[Line, ...]  # € per paid day
    price_share: tuple[Line, ...]  # fractions of the price withheld or spent (deductions, guarantee carry)

    @property
    def per_day_total(self) -> Decimal:
        return sum((line.amount for line in self.per_day), Decimal(0))

    @property
    def share_total(self) -> Decimal:
        return sum((line.amount for line in self.price_share), Decimal(0))


@dataclass(frozen=True)
class GoNoGo:
    reference: Money
    costs: Costs
    paid_days_per_year: Decimal
    net_by_discount: tuple[Decimal, ...]  # index = integer discount 0..MAX_DISCOUNT, € per day
    break_even: int | None  # None: loss even at 0%

    def net(self, discount: int) -> Decimal:
        return self.net_by_discount[discount]

    def net_per_year(self, discount: int) -> Decimal:
        return self.net_by_discount[discount] * self.paid_days_per_year


def go_no_go(reference: Money, costs: Costs, paid_days_per_year: Decimal) -> GoNoGo:
    keep = 1 - costs.share_total
    fixed = costs.per_day_total
    grid = tuple(offer_price(reference, d).amount * keep - fixed for d in range(MAX_DISCOUNT + 1))
    viable: Sequence[int] = [d for d, net in enumerate(grid) if net >= 0]
    break_even = max(viable) if grid[0] >= 0 else None
    return GoNoGo(reference, costs, paid_days_per_year, grid, break_even)
