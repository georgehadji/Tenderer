"""apps/privacy against PostgreSQL: data-subject export and erasure (each audited with ids and counts only),
erasure refused while an engagement is open, and the retention job (docs/architecture.md §10.8). Synthetic data."""

import datetime as dt
import json

import pytest
from django.core.management import CommandError, call_command
from django.urls import reverse
from django.utils import timezone

from tenderer.apps.alerts import api as alerts
from tenderer.apps.alerts.models import Deadline, Outbox
from tenderer.apps.audit.models import AuditEvent
from tenderer.apps.engagements import api as engagements
from tenderer.apps.engagements.models import Client, DocumentRecord, Engagement, Resource
from tenderer.apps.privacy import api
from tenderer.core.rules.dates import add_months

pytestmark = pytest.mark.django_db


def client_with_history(tender, tax_id="123456783", name="Πελάτης Δοκιμής"):
    client = Client.objects.create(name=name, tax_id=tax_id, email="client@example.com")
    Resource.objects.create(client=client, sector="taxi_student_transport", kind="vehicle", label="όχημα 1",
                            attributes={"plate": "ΝΒΚ-1234", "seats": 4, "base_municipality": "Θεσσαλονίκη"})
    DocumentRecord.objects.create(client=client, doc_type="tax_clearance", valid_until=dt.date(2027, 1, 1))
    engagement = engagements.open_engagement(client, tender)
    engagements.open_bid(engagement, "ΑΔΑΜ-TEST-1")
    alerts.add_deadline(Deadline(engagement=engagement, step="Ανανέωση ΕΕΕΣ",
                                 due_on=timezone.localdate() + dt.timedelta(days=20)))
    return client, engagement


def test_export_holds_every_record_and_is_audited(tender):
    client, _ = client_with_history(tender)
    data = api.export(client)
    assert data["client"]["tax_id"] == "123456783"
    assert {k: len(v) for k, v in data.items() if isinstance(v, list)} == {
        "resources": 1, "documents": 1, "engagements": 1, "bids": 1, "acknowledgements": 0, "deadlines": 1}
    event = AuditEvent.objects.get(action="client.exported")
    assert "123456783" not in json.dumps(event.details) and "Πελάτης" not in json.dumps(event.details)


def test_erasure_waits_for_open_work_then_removes_everything(tender):
    client, engagement = client_with_history(tender)
    with pytest.raises(api.StillOpen):
        api.erase(client)
    engagements.fire_engagement(engagement, "withdraw")
    pk = client.pk
    counts = api.erase(client)
    assert counts == {"outbox": 4, "deadlines": 1, "acknowledgements": 0, "bids": 1, "engagements": 1,
                      "documents": 1, "resources": 1}
    assert not Client.objects.exists() and not Outbox.objects.exists() and not Engagement.objects.exists()
    event = AuditEvent.objects.get(action="client.erased")
    assert event.object_ref == f"engagements.client:{pk}" and event.details["reason"] == "request"
    assert "Πελάτης" not in json.dumps(event.details)


def test_retention_job(tender, settings):
    settings.TENDERER_RETENTION_MONTHS = None
    with pytest.raises(CommandError, match="TENDERER_RETENTION_MONTHS"):
        call_command("purge_expired")
    settings.TENDERER_RETENTION_MONTHS = 24
    today = timezone.localdate()
    ended, e1 = client_with_history(tender)
    engagements.fire_engagement(e1, "withdraw")
    expired, e2 = client_with_history(tender, tax_id="111111114", name="Πελάτης Δύο")
    engagements.fire_engagement(e2, "withdraw")
    Client.objects.filter(pk=expired.pk).update(retention_until=today - dt.timedelta(days=1))
    active, _ = client_with_history(tender, tax_id="222222228", name="Πελάτης Τρία")
    assert api.purge_expired(today) == (1, 1)
    assert not Client.objects.filter(pk=expired.pk).exists()
    ended.refresh_from_db()
    assert ended.retention_until == add_months(today, 24)
    assert Client.objects.get(pk=active.pk).retention_until is None  # open work: no date yet
    assert AuditEvent.objects.filter(action="client.erased", details__reason="retention").count() == 1
    call_command("purge_expired")  # idempotent: nothing left to do
    assert Client.objects.count() == 2


def test_admin_export_and_confirmed_erasure(tender, admin_client):
    client, engagement = client_with_history(tender)
    url = reverse("admin:privacy_datasubject_changelist")
    response = admin_client.post(url, {"action": "export", "_selected_action": [client.pk]}, secure=True)
    assert response["Content-Disposition"] == f'attachment; filename="client-{client.pk}.json"'
    assert json.loads(response.content)["client"]["tax_id"] == "123456783"
    engagements.fire_engagement(engagement, "withdraw")
    response = admin_client.post(url, {"action": "erase", "_selected_action": [client.pk]}, secure=True)
    assert response.status_code == 200 and "cannot be undone" in response.content.decode()
    assert Client.objects.exists()  # nothing happens before the confirmation
    admin_client.post(url, {"action": "erase", "_selected_action": [client.pk], "confirm": "yes"}, secure=True)
    assert not Client.objects.exists()
