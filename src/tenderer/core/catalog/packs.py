"""Pack contracts and the registry that `shell` fills at start-up (docs/architecture.md §5.2 rule 7, §6.12-§6.13).

Core never imports a pack. Packs build these frozen objects; `shell` collects them into `Packs` and passes
that registry to whoever needs it (dependency injection by argument, no global state).
"""

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

JsonSchema = Mapping[str, object]


@dataclass(frozen=True)
class SectorPack:
    id: str
    resource_kinds: Mapping[str, JsonSchema]  # kind -> JSON Schema of its attributes (AD15)
    document_types: frozenset[str]


@dataclass(frozen=True)
class JurisdictionPack:
    id: str
    document_types: frozenset[str]
    public_holidays: Callable[[int], Mapping[date, str]]  # computed; reviewed files in reference/<cc>/ win
    payment_deduction_rate: Decimal  # withheld from every public payment, as a fraction of the price


@dataclass(frozen=True)
class Packs:
    sectors: Mapping[str, SectorPack] = field(default_factory=dict)
    jurisdictions: Mapping[str, JurisdictionPack] = field(default_factory=dict)
    lifecycles: frozenset[str] = frozenset()
    offer_shapes: frozenset[str] = frozenset()
