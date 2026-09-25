"""The only entry point other modules and the admin use to change engagements and bids (§5.2 rule 6).

State never changes by editing a field: every change goes through `fire_*`, which asks the transition table.
Recording a new offer check on a CHECKED bid sends it back to DRAFT, so a changed offer is checked again.
"""

import functools
import re
from collections.abc import Iterable

from django.conf import settings
from django.db import transaction

from tenderer.apps.audit import api as audit
from tenderer.apps.engagements.models import Bid, Client, Engagement, packs
from tenderer.core.catalog.tender import Tender, load_tender
from tenderer.core.lifecycle.machine import GuardContext, Moved, Refused, fire
from tenderer.core.lifecycle.templates import TEMPLATES
from tenderer.core.pricing.gonogo import GoNoGo
from tenderer.core.pricing.offer import LineCheck
from tenderer.core.rules.checklist import Item, Status

_TENDER_ID = re.compile(r"[a-z0-9-]+")


def tender_ids() -> list[str]:
    """Tender modules deployed with this release (`tenders/<id>/tender.toml`)."""
    root = settings.TENDERER_TENDERS_DIR
    return sorted(p.name for p in root.iterdir() if _TENDER_ID.fullmatch(p.name) and (p / "tender.toml").is_file())


@functools.cache
def load(tender_id: str) -> Tender:
    """The tender as this release ships it; files change only with a deploy, so one load per process."""
    if tender_id not in tender_ids():
        raise KeyError(f"no tender module {tender_id!r}")
    return load_tender(settings.TENDERER_TENDERS_DIR / tender_id, packs(), settings.TENDERER_COMMIT)


class TransitionRefused(Exception):
    def __init__(self, refused: Refused) -> None:
        self.refused = refused
        super().__init__(f"{refused.reason}: {refused.detail}")


@transaction.atomic
def open_engagement(client: Client, tender: Tender) -> Engagement:
    template = TEMPLATES[tender.lifecycle]
    engagement = Engagement.objects.create(
        tenant_id=client.tenant_id, client=client, tender_id=tender.id, tender_version=tender.version,
        tender_title=tender.title, sector=tender.sector, lifecycle=template.id, state=template.engagement.initial,
    )
    audit.record("engagement.opened", engagement, {"tender_id": tender.id, "tender_version": tender.version})
    return engagement


@transaction.atomic
def fire_engagement(engagement: Engagement, event: str) -> Engagement:
    engagement = Engagement.objects.select_for_update().get(pk=engagement.pk)
    result = fire(TEMPLATES[engagement.lifecycle].engagement, engagement.state, event)
    if isinstance(result, Refused):
        raise TransitionRefused(result)
    audit.record("engagement.transition", engagement, {"event": event, "from": engagement.state, "to": result.target})
    engagement.state = result.target
    engagement.save(update_fields=["state"])
    return engagement


@transaction.atomic
def open_bid(engagement: Engagement, invitation_ref: str) -> Bid:
    bid = Bid.objects.create(tenant_id=engagement.tenant_id, engagement=engagement, invitation_ref=invitation_ref,
                             state=TEMPLATES[engagement.lifecycle].bid.initial)
    audit.record("bid.opened", bid, {"engagement": engagement.pk})
    return bid


@transaction.atomic
def fire_bid(bid: Bid, event: str) -> Bid:
    bid = Bid.objects.select_for_update().select_related("engagement").get(pk=bid.pk)
    result = fire(TEMPLATES[bid.engagement.lifecycle].bid, bid.state, event, guard_context(bid))
    if isinstance(result, Refused):
        raise TransitionRefused(result)
    audit.record("bid.transition", bid, {"event": event, "from": bid.state, "to": result.target})
    bid.state = result.target
    bid.save(update_fields=["state"])
    return bid


def guard_context(bid: Bid) -> GuardContext:
    offer = bid.offer_check
    items = bid.checklist_snapshot
    return GuardContext(
        offer_errors=tuple(line["error"] for line in offer) if offer else None,
        gonogo_recorded=bid.gonogo_snapshot is not None,
        offer_stage_statuses=tuple(Status(i["status"]) for i in items) if items else None,
    )


@transaction.atomic
def record_offer_check(bid: Bid, checks: Iterable[LineCheck]) -> Bid:
    bid.offer_check = [{
        "route_code": c.line.route_code,
        "discount": str(c.line.discount),
        "price": None if c.price is None else str(c.price.amount),
        "error": None if c.error is None else c.error.value,
    } for c in checks]
    return _save_and_reopen(bid, "offer_check")


@transaction.atomic
def record_gonogo(bid: Bid, route_code: str, result: GoNoGo, warnings: Iterable[str]) -> Bid:
    snapshot = dict(bid.gonogo_snapshot or {})
    snapshot[route_code] = {
        "reference": str(result.reference.amount),
        "break_even": result.break_even,
        "net_at_0": str(result.net(0)),
        "per_day": [[line.name, str(line.amount)] for line in result.costs.per_day],
        "price_share": [[line.name, str(line.amount)] for line in result.costs.price_share],
        "warnings": list(warnings),
    }
    bid.gonogo_snapshot = snapshot
    return _save_and_reopen(bid, "gonogo_snapshot")


@transaction.atomic
def record_checklist(bid: Bid, items: Iterable[Item]) -> Bid:
    bid.checklist_snapshot = [{"requirement_id": i.requirement_id, "text": i.text, "subject": i.subject,
                               "status": i.status.value, "reason": i.reason, "source_section": i.source_section}
                              for i in items]
    return _save_and_reopen(bid, "checklist_snapshot")


def _save_and_reopen(bid: Bid, field: str) -> Bid:
    bid.save(update_fields=[field])
    audit.record("bid.recorded", bid, {"field": field})
    if bid.state == "CHECKED":
        result = fire(TEMPLATES[bid.engagement.lifecycle].bid, bid.state, "reopen")
        if isinstance(result, Moved):
            audit.record("bid.transition", bid, {"event": "reopen", "from": bid.state, "to": result.target})
            bid.state = result.target
            bid.save(update_fields=["state"])
    return bid
