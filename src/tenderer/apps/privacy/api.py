"""Data-subject requests and retention (GDPR Art. 15, 17, 5(1)(e); docs/architecture.md §6.4, §10.8).

`export` returns everything we hold about one client; `erase` deletes it in one transaction, and refuses while an
engagement is still open. `purge_expired` erases clients whose retention date has passed and sets that date,
N months ahead, for clients whose engagements have all ended. Each action writes one audit event with ids and
counts only. Backups keep erased data until they rotate out (§9); that window belongs in the retention schedule.
"""

from datetime import date
from typing import Any

from django.conf import settings
from django.db import transaction
from django.forms.models import model_to_dict

from tenderer.apps.alerts.models import Deadline, Outbox
from tenderer.apps.audit import api as audit
from tenderer.apps.engagements.models import Acknowledgement, Bid, Client, DocumentRecord, Engagement, Resource
from tenderer.core.lifecycle.templates import TEMPLATES
from tenderer.core.rules.dates import add_months


class StillOpen(Exception):
    """The client has an engagement that has not ended; close or withdraw it first."""


def export(client: Client) -> dict[str, Any]:
    engagements = Engagement.objects.filter(client=client)
    data = {
        "client": model_to_dict(client),
        "resources": [model_to_dict(r) for r in Resource.objects.filter(client=client)],
        "documents": [model_to_dict(d) for d in DocumentRecord.objects.filter(client=client)],
        "engagements": [model_to_dict(e) for e in engagements],
        "bids": [model_to_dict(b) for b in Bid.objects.filter(engagement__in=engagements)],
        "acknowledgements": [model_to_dict(a) for a in Acknowledgement.objects.filter(engagement__in=engagements)],
        "deadlines": [model_to_dict(d) for d in Deadline.objects.filter(engagement__in=engagements)],
    }
    audit.record("client.exported", client, {k: len(v) for k, v in data.items() if isinstance(v, list)})
    return data


def open_engagements(client: Client) -> list[Engagement]:
    return [e for e in Engagement.objects.filter(client=client)
            if not TEMPLATES[e.lifecycle].engagement.final(e.state)]


@transaction.atomic
def erase(client: Client, reason: str = "request") -> dict[str, int]:
    if open_engagements(client):
        raise StillOpen(f"client {client.pk} has an open engagement")
    engagements = Engagement.objects.filter(client=client)
    deadlines = Deadline.objects.filter(engagement__in=engagements)
    counts = {
        "outbox": Outbox.objects.filter(deadline__in=deadlines).delete()[0],
        "deadlines": deadlines.delete()[0],
        "acknowledgements": Acknowledgement.objects.filter(engagement__in=engagements).delete()[0],
        "bids": Bid.objects.filter(engagement__in=engagements).delete()[0],
        "engagements": engagements.delete()[0],
        "documents": DocumentRecord.objects.filter(client=client).delete()[0],
        "resources": Resource.objects.filter(client=client).delete()[0],
    }
    target, tenant = audit.ref(client), client.tenant_id
    client.delete()
    audit.record("client.erased", target, {**counts, "reason": reason}, tenant_id=tenant)
    return counts


def purge_expired(today: date) -> tuple[int, int]:
    """Returns (erased, scheduled). Needs TENDERER_RETENTION_MONTHS, set with the lawyer (§10.8)."""
    months = settings.TENDERER_RETENTION_MONTHS
    if months is None:
        raise RuntimeError("TENDERER_RETENTION_MONTHS is not set: the retention schedule has no N yet")
    erased = 0
    for client in Client.objects.filter(retention_until__lt=today):
        if not open_engagements(client):  # a client who came back keeps their data until the new work ends
            erase(client, reason="retention")
            erased += 1
    scheduled = 0
    for client in Client.objects.filter(retention_until__isnull=True, engagements__isnull=False).distinct():
        if not open_engagements(client):
            client.retention_until = add_months(today, months)
            client.save(update_fields=["retention_until"])
            audit.record("client.retention_set", client, {"months": months})
            scheduled += 1
    return erased, scheduled
