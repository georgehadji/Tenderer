"""apps/audit and access against PostgreSQL: the audit log is append-only for everyone (trigger) and for the app
role (grants), every transition writes one event with a correlation id, views are audited, the admin needs a
second factor, and the roles hold the permissions of docs/architecture.md §10.2. Synthetic data only."""

from pathlib import Path

import pytest
from django.contrib.auth.models import Group, User
from django.db import DatabaseError, connection, transaction
from django.urls import reverse

from tenderer.apps.audit import api as audit
from tenderer.apps.audit.models import AuditEvent
from tenderer.apps.engagements import api as engagements
from tenderer.apps.engagements.models import Client
from tests.conftest import verified

pytestmark = pytest.mark.django_db

ROLES_SQL = Path(__file__).resolve().parents[1] / "deploy" / "roles.sql"


@pytest.fixture
def engagement(tender):
    client = Client.objects.create(name="Πελάτης Δοκιμής", tax_id="123456783")
    return engagements.open_engagement(client, tender)


def test_the_database_refuses_update_and_delete():
    event = audit.record("test.event", "engagements.client:1")
    with pytest.raises(PermissionError):
        event.save()
    with pytest.raises(PermissionError):
        event.delete()
    for statement in (lambda: AuditEvent.objects.filter(pk=event.pk).update(action="changed"),
                      lambda: AuditEvent.objects.filter(pk=event.pk).delete()):
        with pytest.raises(DatabaseError, match="append-only"), transaction.atomic():
            statement()
    assert AuditEvent.objects.get(pk=event.pk).action == "test.event"


def test_the_app_role_can_only_insert_and_read_audit_events():
    with connection.cursor() as cur:
        cur.execute("DO $$ BEGIN IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'tenderer_app') "
                    "THEN CREATE ROLE tenderer_app NOLOGIN; END IF; END $$;")
        cur.execute(ROLES_SQL.read_text(encoding="utf-8"))
        cur.execute("SET ROLE tenderer_app")
        try:
            cur.execute("INSERT INTO audit_auditevent (at, tenant_id, action, object_ref, details, correlation_id) "
                        "VALUES (now(), 1, 'app.insert', '', '{}', 'c') RETURNING id")
            (pk,) = cur.fetchone()
            cur.execute("SELECT action FROM audit_auditevent WHERE id = %s", [pk])
            assert cur.fetchone() == ("app.insert",)
            for sql in ("UPDATE audit_auditevent SET action = 'x'", "DELETE FROM audit_auditevent",
                        "TRUNCATE audit_auditevent"):
                with pytest.raises(DatabaseError, match="permission denied"), transaction.atomic():
                    cur.execute(sql)
            cur.execute("UPDATE engagements_client SET phone = phone")  # ordinary tables stay writable
        finally:
            cur.execute("RESET ROLE")


def test_every_transition_writes_one_event_with_the_correlation_id(engagement):
    with audit.correlated(actor_id=7) as cid:
        engagement = engagements.fire_engagement(engagement, "registered")
        bid = engagements.open_bid(engagement, "ΑΔΑΜ-TEST-1")
        engagements.fire_bid(bid, "abandon")
    events = AuditEvent.objects.filter(correlation_id=cid).order_by("pk")
    assert [(e.action, e.details.get("to")) for e in events] == [
        ("engagement.transition", "REGISTERED"), ("bid.opened", None), ("bid.transition", "ABANDONED")]
    assert {e.actor_id for e in events} == {7}
    assert events[0].object_ref == f"engagements.engagement:{engagement.pk}"
    assert events[0].details == {"event": "registered", "from": "ONBOARDING", "to": "REGISTERED"}
    with pytest.raises(engagements.TransitionRefused):
        engagements.fire_engagement(engagement, "admitted")
    assert AuditEvent.objects.filter(action="engagement.transition").count() == 1  # a refusal changes nothing


def test_views_are_audited_and_requests_carry_a_correlation_id(engagement, admin_client, admin_user):
    url = reverse("admin:engagements_client_change", args=[engagement.client_id])
    response = admin_client.get(url, secure=True)
    assert response.status_code == 200
    viewed = AuditEvent.objects.get(action="viewed")
    assert (viewed.object_ref, viewed.actor_id) == (f"engagements.client:{engagement.client_id}", admin_user.pk)
    assert viewed.correlation_id == response["X-Correlation-ID"]
    assert "script-src 'self'" in response["Content-Security-Policy"]  # §10.3: no inline or foreign scripts
    assert response["X-Frame-Options"] == "DENY" and response["X-Content-Type-Options"] == "nosniff"
    admin_client.get(reverse("admin:engagements_client_changelist"), secure=True)
    assert AuditEvent.objects.filter(action="listed", object_ref="engagements.client").count() == 1


def test_the_admin_needs_a_second_factor(client, admin_user):
    client.force_login(admin_user)  # password only
    response = client.get(reverse("admin:index"), secure=True)
    assert response.status_code == 302 and reverse("admin:login") in response["Location"]


def test_sign_ins_are_audited(client):
    user = User.objects.create_user("operator1", password="a-long-test-password-1")
    assert client.login(username="operator1", password="a-long-test-password-1")
    assert not client.login(username="operator1", password="wrong")
    assert AuditEvent.objects.filter(action="auth.signed_in", object_ref=f"auth.user:{user.pk}").exists()
    failed = AuditEvent.objects.get(action="auth.sign_in_failed")
    assert failed.details == {} and failed.object_ref == ""  # no username stored


def test_roles_hold_the_permissions_of_the_design(client):
    perms = {g.name: {f"{p.content_type.app_label}.{p.codename}" for p in g.permissions.all()}
             for g in Group.objects.prefetch_related("permissions__content_type")}
    assert {"engagements.change_bid", "alerts.add_deadline", "documents.view_clientplan"} <= perms["operator"]
    assert not any(p.startswith(("privacy.", "audit.", "auth.")) or p.split(".")[1].startswith("delete_")
                   for p in perms["operator"])
    assert all(p.split(".")[1].startswith("view_") for p in perms["reviewer"])
    assert {"privacy.delete_datasubject", "audit.view_auditevent", "auth.change_user",
            "otp_totp.add_totpdevice"} <= perms["admin"]
    operator = User.objects.create_user("operator2", password="x", is_staff=True)
    operator.groups.add(Group.objects.get(name="operator"))
    verified(client, operator)
    assert client.get(reverse("admin:engagements_client_changelist"), secure=True).status_code == 200
    assert client.get(reverse("admin:privacy_datasubject_changelist"), secure=True).status_code == 403
    assert client.get(reverse("admin:audit_auditevent_changelist"), secure=True).status_code == 403
