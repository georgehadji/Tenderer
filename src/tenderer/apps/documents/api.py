"""What the client receives (docs/architecture.md §6.6): the client plan of one bid as one HTML e-mail.

Rendering is a function of recorded data only: the tender title and version of the engagement, its open deadlines,
the bid's checklist and go/no-go snapshots, and the draft declarations of the tender module. Templates are code
(Django auto-escaping on); draft declarations come from `tenders/<id>/declarations/<requirement>.txt`, reviewed like
any tender data, and carry the watermark. Only declarations without sensitive parts are drafted; the client writes
and signs every declaration in gov.gr, so its final content never passes through us.
"""

import re
from decimal import Decimal
from typing import Any

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template import Context, Engine
from django.template.loader import render_to_string

from tenderer.apps.alerts import api as alerts
from tenderer.apps.audit import api as audit
from tenderer.apps.engagements.models import Bid, Resource, packs

WATERMARK = "ΠΡΟΣΧΕΔΙΟ – ελέγξτε πριν υπογράψετε"  # §6.6
STATUS = {
    "SATISFIED": "Εντάξει",
    "NOT_SATISFIED": "Λείπει ή δεν ισχύει",
    "UNKNOWN": "Δεν έχει ελεγχθεί",
    "NOT_APPLICABLE": "Δεν σας αφορά",
}
_SAFE_ID = re.compile(r"[A-Za-z0-9_-]+")  # ids become path parts: no traversal out of tenders/
_TEXT = Engine(autoescape=False)  # declarations are plain text; the HTML template escapes them when it shows them


class NoRecipient(Exception):
    """The client has no e-mail address."""


def context(bid: Bid) -> dict[str, Any]:
    engagement = bid.engagement
    title = engagement.tender_title or engagement.tender_id
    sector = packs().sectors.get(engagement.sector)
    labels = sector.labels if sector else {}
    checklist = bid.checklist_snapshot or []
    routes = sorted((bid.gonogo_snapshot or {}).items())
    return {
        "tender_title": title,
        "tender_version": engagement.tender_version,
        "invitation": bid.invitation_ref,
        "deadlines": alerts.open_deadlines(engagement.pk),
        "checklist": [{**item, "status_text": STATUS[item["status"]]} for item in checklist],
        "routes": [{
            "code": code,
            "reference": _eur(g["reference"]),
            "net_at_0": _eur(g["net_at_0"]),
            "break_even": g["break_even"],
            "per_day": [(labels.get(name, name), _eur(amount)) for name, amount in g["per_day"]],
            "price_share": [(labels.get(name, name), _pct(amount)) for name, amount in g["price_share"]],
            "warnings": [labels.get(w, w) for w in g["warnings"]],
        } for code, g in routes],
        "declarations": _declarations(bid, title, checklist, [code for code, _ in routes]),
        "watermark": WATERMARK,
        "never_ask": alerts.NEVER_ASK,
    }


def render_plan(bid: Bid) -> tuple[str, str, str]:
    """Subject, plain-text fallback and HTML of the client plan."""
    ctx = context(bid)
    subject = f"Πλάνο συμμετοχής: {ctx['tender_title']}, πρόσκληση {bid.invitation_ref}"
    text = (f"Το πλάνο συμμετοχής σας για την πρόσκληση {bid.invitation_ref} είναι στην έκδοση HTML αυτού του "
            f"μηνύματος.\n\n{alerts.NEVER_ASK}\n")
    return subject, text, render_to_string("documents/client_plan.html", ctx)


def send_plan(bid: Bid) -> None:
    to = bid.engagement.client.email
    if not to:
        raise NoRecipient
    subject, text, html = render_plan(bid)
    msg = EmailMultiAlternatives(subject, text, to=[to])
    msg.attach_alternative(html, "text/html")
    msg.send()
    audit.record("plan.sent", bid)  # client data leaves the system: an export (§6.7)


def _declarations(bid: Bid, title: str, checklist: list[dict[str, Any]],
                  gonogo_routes: list[str]) -> list[dict[str, str]]:
    if not _SAFE_ID.fullmatch(bid.engagement.tender_id):
        return []
    folder = settings.TENDERER_TENDERS_DIR / bid.engagement.tender_id / "declarations"
    offered = [line["route_code"] for line in bid.offer_check or []]
    resources: dict[str, list[dict[str, Any]]] = {}
    for r in Resource.objects.filter(client_id=bid.engagement.client_id).order_by("pk"):
        resources.setdefault(r.kind, []).append(r.attributes)
    data = Context({"invitation": bid.invitation_ref, "tender_title": title, "routes": offered or gonogo_routes,
                    "resources": resources})
    out = []
    for item in checklist:
        rid = item["requirement_id"]
        path = folder / f"{rid}.txt"
        if _SAFE_ID.fullmatch(rid) and path.is_file() and all(d["id"] != rid for d in out):
            out.append({"id": item["requirement_id"], "text": item["text"], "source_section": item["source_section"],
                        "body": _TEXT.from_string(path.read_text(encoding="utf-8")).render(data)})
    return out


def _eur(value: str) -> str:
    """26869.5 -> '26.869,50 €' (Greek grouping and decimal comma)."""
    return f"{Decimal(value):,.2f} €".replace(",", "\0").replace(".", ",").replace("\0", ".")


def _pct(fraction: str) -> str:
    """0.0012432 -> '0,12432%'."""
    return f"{(Decimal(fraction) * 100).normalize():f}".replace(".", ",") + "%"
