"""The only entry point other modules and the admin use to change engagements and bids (§5.2 rule 6).

State never changes by editing a field: every change goes through `fire_*`, which asks the transition table.
Recording a new offer check on a CHECKED bid sends it back to DRAFT, so a changed offer is checked again.
"""

from collections.abc import Iterable

from django.db import transaction

from tenderer.apps.engagements.models import Bid, Client, Engagement
from tenderer.core.catalog.tender import Tender
from tenderer.core.lifecycle.machine import GuardContext, Moved, Refused, fire
from tenderer.core.lifecycle.templates import TEMPLATES
from tenderer.core.pricing.gonogo import GoNoGo
from tenderer.core.pricing.offer import LineCheck
from tenderer.core.rules.checklist import Item, Status


class TransitionRefused(Exception):
    def __init__(self, refused: Refused) -> None:
        self.refused = refused
        super().__init__(f"{refused.reason}: {refused.detail}")


@transaction.atomic
def open_engagement(client: Client, tender: Tender) -> Engagement:
    template = TEMPLATES[tender.lifecycle]
    return Engagement.objects.create(
        tenant_id=client.tenant_id, client=client, tender_id=tender.id, tender_version=tender.version,
        lifecycle=template.id, state=template.engagement.initial,
    )


@transaction.atomic
def fire_engagement(engagement: Engagement, event: str) -> Engagement:
    engagement = Engagement.objects.select_for_update().get(pk=engagement.pk)
    result = fire(TEMPLATES[engagement.lifecycle].engagement, engagement.state, event)
    if isinstance(result, Refused):
        raise TransitionRefused(result)
    engagement.state = result.target
    engagement.save(update_fields=["state"])
    return engagement  # ponytail: audit event written here from M7


@transaction.atomic
def open_bid(engagement: Engagement, invitation_ref: str) -> Bid:
    return Bid.objects.create(tenant_id=engagement.tenant_id, engagement=engagement, invitation_ref=invitation_ref,
                              state=TEMPLATES[engagement.lifecycle].bid.initial)


@transaction.atomic
def fire_bid(bid: Bid, event: str) -> Bid:
    bid = Bid.objects.select_for_update().select_related("engagement").get(pk=bid.pk)
    result = fire(TEMPLATES[bid.engagement.lifecycle].bid, bid.state, event, guard_context(bid))
    if isinstance(result, Refused):
        raise TransitionRefused(result)
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
    bid.checklist_snapshot = [{"requirement_id": i.requirement_id, "subject": i.subject, "status": i.status.value,
                               "reason": i.reason, "source_section": i.source_section} for i in items]
    return _save_and_reopen(bid, "checklist_snapshot")


def _save_and_reopen(bid: Bid, field: str) -> Bid:
    bid.save(update_fields=[field])
    if bid.state == "CHECKED":
        result = fire(TEMPLATES[bid.engagement.lifecycle].bid, bid.state, "reopen")
        if isinstance(result, Moved):
            bid.state = result.target
            bid.save(update_fields=["state"])
    return bid
