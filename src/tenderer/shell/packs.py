"""The one place that knows every pack (docs/architecture.md §5.2 rule 7). Core and apps receive `PACKS`."""

from pathlib import Path

from tenderer.core.catalog.packs import Packs
from tenderer.core.pricing.offer import OFFER_SHAPES
from tenderer.core.rules.dates import Calendar, load_calendar
from tenderer.jurisdictions import gr
from tenderer.sectors import taxi_student_transport

REPO = Path(__file__).resolve().parents[3]

PACKS = Packs(
    sectors={p.id: p for p in (taxi_student_transport.PACK,)},
    jurisdictions={p.id: p for p in (gr.PACK,)},
    lifecycles=frozenset({"dps"}),  # ponytail: names only until core/lifecycle (M4) supplies the templates
    offer_shapes=OFFER_SHAPES,
)


def calendar(jurisdiction: str) -> Calendar:
    return load_calendar(sorted((REPO / "reference" / jurisdiction).glob("holidays-*.csv")))
