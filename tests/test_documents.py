"""apps/documents against PostgreSQL: snapshot of a client plan, every item with its tender § and the tender-data
version, the watermark on every draft, the never-ask line, and escaping of every value (template injection).
Synthetic data only."""

import datetime as dt
from datetime import UTC
from pathlib import Path

import pytest
from django.urls import reverse

from tenderer.apps.alerts import api as alerts
from tenderer.apps.alerts.models import Deadline
from tenderer.apps.documents import api
from tenderer.apps.engagements import api as engagements
from tenderer.apps.engagements.models import Client, Engagement, Resource
from tests.test_engagements import _clean_inputs

pytestmark = pytest.mark.django_db

NOW = dt.datetime(2026, 10, 1, 7, 0, tzinfo=UTC)
SNAPSHOT = Path(__file__).parent / "snapshots" / "client_plan.html"


@pytest.fixture
def bid(tender):
    client = Client.objects.create(name="Πελάτης Δοκιμής", tax_id="123456783", email="client@example.com")
    Resource.objects.create(client=client, sector="taxi_student_transport", kind="vehicle", label="όχημα 1",
                            attributes={"plate": "ΝΒΚ-1234", "seats": 4, "base_municipality": "Θεσσαλονίκη"})
    engagement = engagements.open_engagement(client, tender)
    Engagement.objects.filter(pk=engagement.pk).update(tender_version="test-version")  # the commit changes daily
    engagement.refresh_from_db()
    alerts.add_deadline(Deadline(engagement=engagement, step="Υποβολή προσφοράς", due_on=dt.date(2026, 10, 12),
                                 source_section="§4.3"), NOW)
    bid = engagements.open_bid(engagement, "ΑΔΑΜ-TEST-1")
    route, checks, result, items = _clean_inputs(tender)
    bid = engagements.record_offer_check(bid, checks)
    bid = engagements.record_gonogo(bid, route.code, result, ["fuel_no_adjustment", "cancellation_no_compensation"])
    return engagements.record_checklist(bid, items)


def test_client_plan_snapshot(bid):
    """Golden file reviewed by a person; regenerate by deleting it and reviewing the new one."""
    html = api.render_plan(bid)[2]
    if not SNAPSHOT.exists():
        SNAPSHOT.parent.mkdir(exist_ok=True)
        SNAPSHOT.write_text(html, encoding="utf-8", newline="\n")
        pytest.fail(f"snapshot written to {SNAPSHOT}; review it and run again")
    assert html == SNAPSHOT.read_text(encoding="utf-8")


def test_every_item_shows_its_section_and_the_version(bid):
    subject, text, html = api.render_plan(bid)
    assert subject.endswith(", πρόσκληση ΑΔΑΜ-TEST-1")
    assert "Έκδοση δεδομένων διαγωνισμού: test-version" in html
    for item in bid.checklist_snapshot:
        assert f"<td>{item['requirement_id']}</td><td>{item['text']}</td>" in html
        assert f"<td>§{item['source_section']}</td></tr>" in html
    assert "(§4.3.1.1)</h3>" in html  # R9, the declaration drafted for this tender
    assert html.count(api.WATERMARK) == 2
    assert "αριθμός κυκλοφορίας ΝΒΚ-1234, 4 θέσεις επιβατών" in html
    assert "Η τιμή δεν αναπροσαρμόζεται αν ακριβύνει το καύσιμο (§6.6.4)." in html  # pack label, not the code
    assert alerts.NEVER_ASK in html and alerts.NEVER_ASK in text


def test_values_are_escaped(bid):
    Engagement.objects.filter(pk=bid.engagement_id).update(tender_title="{{ settings.SECRET_KEY }}<b>x</b>")
    Deadline.objects.filter(engagement_id=bid.engagement_id).update(step='<img src=x onerror="alert(1)">')
    bid.invitation_ref = "<script>alert(1)</script>{% now 'Y' %}"
    bid.save()
    bid = type(bid).objects.select_related("engagement__client").get(pk=bid.pk)
    html = api.render_plan(bid)[2]
    assert "<script>" not in html and "<img" not in html and "<b>x</b>" not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;{% now &#x27;Y&#x27; %}" in html  # also in the declaration
    assert "{{ settings.SECRET_KEY }}&lt;b&gt;x&lt;/b&gt;" in html
    assert "test-only-not-a-secret" not in html


def test_unsafe_tender_id_drafts_nothing(bid):
    Engagement.objects.filter(pk=bid.engagement_id).update(tender_id="../../etc")
    bid.refresh_from_db()
    assert api.context(type(bid).objects.get(pk=bid.pk))["declarations"] == []


def test_send_plan(bid, mailoutbox):
    api.send_plan(bid)
    [msg] = mailoutbox
    assert msg.to == ["client@example.com"]
    [(html, mimetype)] = msg.alternatives
    assert mimetype == "text/html" and api.WATERMARK in html
    Client.objects.filter(pk=bid.engagement.client_id).update(email="")
    with pytest.raises(api.NoRecipient):
        api.send_plan(type(bid).objects.get(pk=bid.pk))


@pytest.mark.parametrize(("fn", "value", "text"), [
    (api._eur, "26869.5", "26.869,50 €"), (api._eur, "-3.456", "-3,46 €"),
    (api._pct, "0.0012432", "0,12432%"), (api._pct, "0", "0%"),
])
def test_number_formats(fn, value, text):
    assert fn(value) == text


def test_admin_preview_and_send(bid, admin_client, mailoutbox):
    url = reverse("admin:documents_clientplan_changelist")
    response = admin_client.post(url, {"action": "preview", "_selected_action": [bid.pk]}, secure=True)
    assert response.status_code == 200 and api.WATERMARK in response.content.decode()
    admin_client.post(url, {"action": "send", "_selected_action": [bid.pk]}, secure=True)
    assert len(mailoutbox) == 1
