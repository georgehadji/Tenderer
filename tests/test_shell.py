"""shell: the log filter removes personal data (docs/architecture.md §10.3), and no admin screen relies on
inline script, which the Content Security Policy blocks."""

import datetime as dt
import logging
import re
import sys

import pytest
from django.conf import settings
from django.urls import reverse
from django.utils import timezone

from tenderer.apps.alerts import api as alerts
from tenderer.apps.alerts.models import Deadline
from tenderer.apps.engagements import api as engagements
from tenderer.apps.engagements.models import Client
from tenderer.shell.logs import RedactPersonalData, redact


def test_redact_tax_ids_phones_and_emails():
    text = "client 123456783 phone +306912345678 or 2310123456, mail client@example.com, route G26-0703-Τ2, 51.18"
    assert redact(text) == ("client [tax-id] phone [phone] or [phone], mail [email], route G26-0703-Τ2, 51.18")
    assert redact("1234567890123 and 12345678") == "1234567890123 and 12345678"  # not 9 or 10 digits


def test_filter_rewrites_the_record_and_its_traceback():
    try:
        raise ValueError("bad ΑΦΜ 123456783")
    except ValueError:
        record = logging.LogRecord("x", logging.ERROR, __file__, 1, "sent to %s", ("client@example.com",), None)
        record.exc_info = sys.exc_info()
    assert RedactPersonalData().filter(record)
    assert record.getMessage() == "sent to [email]"
    assert "[tax-id]" in record.exc_text and "123456783" not in record.exc_text


def test_every_handler_carries_the_filter():
    assert all("redact" in h.get("filters", []) for h in settings.LOGGING["handlers"].values())


# ---------------- the admin under the Content Security Policy (§10.3) ----------------
INLINE_SCRIPT = re.compile(r"<script(?![^>]*\bsrc=)[^>]*>", re.I)
INLINE_HANDLER = re.compile(r"<[^>]+\son[a-z]+\s*=", re.I)


@pytest.mark.django_db
def test_no_admin_screen_needs_inline_script(admin_client, tender):
    """`script-src 'self'` blocks inline scripts and on* handlers: no screen we serve may rely on them."""
    client = Client.objects.create(name="Πελάτης Δοκιμής", tax_id="123456783", email="client@example.com")
    engagement = engagements.open_engagement(client, tender)
    engagements.open_bid(engagement, "ΑΔΑΜ-TEST-1")
    due = timezone.localdate() + dt.timedelta(days=2)
    alerts.add_deadline(Deadline(engagement=engagement, step="Βήμα", due_on=due))
    urls = [reverse("admin:index")]  # the login page: checked in a browser on 2026-09-25, no CSP violation
    for model in ("engagements_client", "engagements_resource", "engagements_documentrecord", "engagements_engagement",
                  "engagements_bid", "alerts_deadline", "alerts_upcomingdeadline", "alerts_outbox",
                  "documents_clientplan", "privacy_datasubject", "audit_auditevent"):
        urls.append(reverse(f"admin:{model}_changelist"))
    for model in ("engagements_client", "engagements_engagement", "alerts_deadline"):
        urls.append(reverse(f"admin:{model}_add"))
    urls.append(reverse("admin:engagements_client_change", args=[client.pk]))
    for url in urls:
        response = admin_client.get(url, secure=True)
        assert response.status_code == 200, url
        html = response.content.decode()
        assert not INLINE_SCRIPT.search(html), f"{url}: {INLINE_SCRIPT.search(html).group(0)}"
        assert not INLINE_HANDLER.search(html), f"{url}: {INLINE_HANDLER.search(html).group(0)}"
