"""Exact money (AD9). Floats are rejected at the boundary; rounding is explicit at every step."""

from dataclasses import dataclass
from decimal import ROUND_CEILING, ROUND_HALF_UP, Decimal

CENT = Decimal("0.01")


@dataclass(frozen=True, order=True)
class Money:
    amount: Decimal
    currency: str = "EUR"

    def __post_init__(self) -> None:
        if not isinstance(self.amount, Decimal) or not self.amount.is_finite():
            raise TypeError(f"Money needs a finite Decimal, got {self.amount!r}")
        if len(self.currency) != 3 or not self.currency.isupper():
            raise ValueError(f"{self.currency!r} is not an ISO 4217 code")

    def has_cents_only(self) -> bool:
        return self.amount == self.amount.quantize(CENT)


def to_decimal(value: object) -> Decimal:
    """The only way numbers enter pricing: Decimal, int or a decimal string. Never a float."""
    if isinstance(value, bool) or isinstance(value, float):
        raise TypeError(f"{value!r}: floats and booleans are not accepted (AD9)")
    if isinstance(value, Decimal):
        return value
    if isinstance(value, int | str):
        return Decimal(value)
    raise TypeError(f"{value!r} is not a number")


def round_cents(x: Decimal) -> Decimal:
    return x.quantize(CENT, ROUND_HALF_UP)


def ceil_cents(x: Decimal) -> Decimal:
    return x.quantize(CENT, ROUND_CEILING)
