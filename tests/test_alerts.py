"""apps/alerts against PostgreSQL: the outbox commits with its deadline, every notification is sent once across
retries, the heartbeat stops on a backlog, and every e-mail carries the never-ask line (X7). Synthetic data only."""

import datetime as dt
import threading
import urllib.request
from datetime import UTC
from zoneinfo import ZoneInfo

import pytest
from django.core import mail
from django.core.exceptions import ValidationError
from django.core.mail.backends import locmem
from django.core.management import CommandError, call_command
from django.db import IntegrityError, connection, transaction
from django.urls import reverse
from django.utils import timezone

from tenderer.apps.alerts import api, ics
from tenderer.apps.alerts.models import Deadline, Outbox
from tenderer.apps.engagements import api as engagements
from tenderer.apps.engagements.models import Client

pytestmark = pytest.mark.django_db

NOW = dt.datetime(2026, 10, 1, 7, 0, tzinfo=UTC)  # 10:00 in Athens
ATHENS = ZoneInfo("Europe/Athens")


@pytest.fixture
def engagement(tender):
    client = Client.objects.create(name="Πελάτης Δοκιμής", tax_id="123456783", email="client@example.com")
    return engagements.open_engagement(client, tender)


def add(engagement, due_on, now=NOW, **extra):
    return api.add_deadline(Deadline(engagement=engagement, step="Ανανέωση ΕΕΕΣ", due_on=due_on, **extra), now)


class FlakyBackend(locmem.EmailBackend):
    failures = 0

    def send_messages(self, messages):
        if FlakyBackend.failures:
            FlakyBackend.failures -= 1
            raise ConnectionError("provider down")
        return super().send_messages(messages)


def test_deadline_and_its_reminders_commit_together(engagement):
    d = add(engagement, dt.date(2026, 10, 12), source_section="§3.1")
    assert {r.kind: r.due_at for r in d.outbox.all()} == {
        "calendar": NOW,
        "T-7": dt.datetime(2026, 10, 5, 9, tzinfo=ATHENS),
        "T-3": dt.datetime(2026, 10, 9, 9, tzinfo=ATHENS),
        "T-1": dt.datetime(2026, 10, 11, 9, tzinfo=ATHENS),
    }
    assert sorted(d.outbox.values_list("idempotency_key", flat=True)) == [
        f"deadline-{d.pk}-{k}" for k in ("T-1", "T-3", "T-7", "calendar")]
    with pytest.raises(ValidationError):
        Outbox.objects.create(idempotency_key=f"deadline-{d.pk}-T-1", deadline=d, kind="T-1", due_at=NOW)
    with pytest.raises(IntegrityError):  # bulk paths skip save(); the unique key still binds them
        Outbox.objects.bulk_create([Outbox(idempotency_key=f"deadline-{d.pk}-T-1", deadline=d, kind="T-1",
                                           due_at=NOW)])


def test_only_reminders_still_ahead_are_planned(engagement):
    d = add(engagement, dt.date(2026, 10, 4))  # T-7 was 27/09; T-3 is today, after 09:00, so it goes on the next run
    assert sorted(d.outbox.values_list("kind", flat=True)) == ["T-1", "T-3", "calendar"]
    with pytest.raises(ValueError, match="already passed"):
        add(engagement, dt.date(2026, 9, 30))


def test_each_notification_is_sent_once(engagement, mailoutbox):
    d = add(engagement, dt.date(2026, 10, 12))
    assert api.send_due(NOW) == (1, 0)
    assert api.send_due(NOW) == (0, 0)
    first = mailoutbox[0]
    assert first.to == ["client@example.com"]
    assert first.extra_headers["Message-ID"] == f"<deadline-{d.pk}-calendar@tenderer.example>"
    (name, content, mimetype), = first.attachments
    assert (name, mimetype) == ("prothesmia.ics", "text/calendar")
    assert "DTSTART;VALUE=DATE:20261012" in content
    later = dt.datetime(2026, 10, 11, 12, tzinfo=UTC)
    assert api.send_due(later) == (3, 0)
    assert api.send_due(later) == (0, 0)
    assert len({m.extra_headers["Message-ID"] for m in mailoutbox}) == len(mailoutbox) == 4


def test_a_failed_send_is_retried_and_never_duplicated(engagement, settings):
    settings.EMAIL_BACKEND = "tests.test_alerts.FlakyBackend"
    FlakyBackend.failures = 1
    d = add(engagement, dt.date(2026, 10, 12))
    assert api.send_due(NOW) == (0, 1)
    row = d.outbox.get(kind="calendar")
    assert (row.attempts, row.last_error, row.sent_at) == (1, "ConnectionError", None)
    assert mail.outbox == []
    assert api.backlog(NOW + api.MAX_LAG) == 1
    assert api.send_due(NOW) == (1, 0)
    assert api.send_due(NOW) == (0, 0)
    assert len(mail.outbox) == 1
    row.refresh_from_db()
    assert (row.attempts, row.last_error) == (2, "")
    assert api.backlog(NOW + api.MAX_LAG) == 0


def test_closed_deadline_sends_nothing_more(engagement, mailoutbox):
    d = add(engagement, dt.date(2026, 10, 12))
    api.send_due(NOW)
    api.close(d)
    assert api.send_due(dt.datetime(2026, 10, 12, tzinfo=UTC)) == (0, 0)
    assert len(mailoutbox) == 1
    assert api.backlog(dt.datetime(2026, 10, 12, tzinfo=UTC)) == 0


def test_client_without_email_turns_red_and_fails_the_job(engagement):
    Client.objects.filter(pk=engagement.client_id).update(email="")
    today = timezone.localdate()
    d = add(engagement, today + dt.timedelta(days=10), now=timezone.now())
    with pytest.raises(CommandError, match="1 notification"):
        call_command("send_outbox")
    assert d.outbox.get(kind="calendar").last_error == "NoRecipient"
    row = api.upcoming(today).get(pk=d.pk)
    assert row.failing
    assert api.signal(row.due_on, today, acknowledged=False, failing=row.failing) is api.Signal.RED


@pytest.mark.parametrize(("left", "acknowledged", "failing", "expected"), [
    (10, False, False, "green"), (7, False, False, "amber"), (4, False, False, "amber"),
    (3, False, False, "red"), (3, True, False, "amber"), (0, True, False, "amber"),
    (-1, True, False, "red"), (10, True, True, "red"),
])
def test_signal(left, acknowledged, failing, expected):
    today = dt.date(2026, 10, 1)
    assert api.signal(today + dt.timedelta(days=left), today, acknowledged, failing) == expected


def test_every_email_carries_the_never_ask_line(engagement):
    """Snapshot of one reminder; the never-ask line on every kind (X7, build-plan M5)."""
    d = add(engagement, dt.date(2026, 10, 12), source_section="§3.1")
    rendered = {r.kind: api.render(r, dt.datetime(2026, 10, 9, 6, tzinfo=UTC)) for r in d.outbox.all()}
    assert set(rendered) == {"calendar", "T-7", "T-3", "T-1"}
    assert all(api.NEVER_ASK in body for _, body in rendered.values())
    assert rendered["T-3"] == (
        "Υπενθύμιση: Ανανέωση ΕΕΕΣ έως 12/10/2026",
        "Απομένουν 3 ημέρες.\n\n"
        "Διαγωνισμός: ΔΣΑ Μεταφοράς Μαθητών Μ.Ε. Θεσσαλονίκης 2026–2029, κατηγορία Β (Ε.Δ.Χ.)\n"
        "Βήμα: Ανανέωση ΕΕΕΣ\n"
        "Προθεσμία: 12/10/2026\n"
        "Πηγή: §3.1 της διακήρυξης\n\n"
        "Δεν ζητάμε ποτέ κωδικούς ΕΣΗΔΗΣ ή Taxisnet. Αν κάποιος σας τους ζητήσει στο όνομά μας, "
        "μην απαντήσετε και τηλεφωνήστε μας.\n",
    )


@pytest.mark.parametrize(("days", "text"), [
    (-1, "Η προθεσμία έχει λήξει."), (0, "Η προθεσμία λήγει σήμερα."), (1, "Απομένει 1 ημέρα."),
    (7, "Απομένουν 7 ημέρες."),
])
def test_days_left_wording(days, text):
    assert api._left(days) == text


def test_ics_is_folded_and_escaped():
    text = ics.calendar("deadline-1-calendar@tenderer.example", dt.date(2026, 10, 12), "Ανανέωση ΕΕΕΣ; μέρος 1, 2",
                        "Διαγωνισμός: " + "Α" * 60 + "\\τέλος\nΒήμα", NOW)
    lines = text.split("\r\n")
    assert lines[-1] == "" and all(len(line.encode()) <= 75 for line in lines)
    assert "\n" not in text.replace("\r\n", "")
    unfolded = text.replace("\r\n ", "")
    assert "SUMMARY:Ανανέωση ΕΕΕΣ\\; μέρος 1\\, 2\r\n" in unfolded
    assert "DESCRIPTION:Διαγωνισμός: " + "Α" * 60 + "\\\\τέλος\\nΒήμα\r\n" in unfolded
    assert "DTSTAMP:20261001T070000Z\r\n" in unfolded
    assert "DTEND;VALUE=DATE:20261013\r\n" in unfolded
    assert unfolded.count("BEGIN:VALARM") == 2


def test_heartbeat_pings_only_while_the_outbox_keeps_up(engagement, settings, monkeypatch, mailoutbox):
    pings = []

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def read(self):
            return b"OK"

    monkeypatch.setattr(urllib.request, "urlopen", lambda url, timeout: pings.append(url) or Response())
    settings.ALERTS_HEARTBEAT_URL = "http://monitor.example/ping"
    with pytest.raises(CommandError, match="https"):
        call_command("heartbeat")
    settings.ALERTS_HEARTBEAT_URL = "https://monitor.example/ping/test"
    add(engagement, timezone.localdate() + dt.timedelta(days=20), now=timezone.now() - dt.timedelta(hours=1))
    with pytest.raises(CommandError, match="heartbeat withheld"):
        call_command("heartbeat")
    assert pings == []
    call_command("send_outbox")
    call_command("heartbeat")
    assert pings == ["https://monitor.example/ping/test"]


def test_admin_add_plans_the_outbox_and_the_dashboard_shows_red(engagement, admin_client):
    far = timezone.localdate() + dt.timedelta(days=30)
    response = admin_client.post(reverse("admin:alerts_deadline_add"), {
        "engagement": engagement.pk, "step": "Υποβολή προσφοράς", "due_on": far.isoformat(), "source_section": "§4.1",
    }, secure=True)
    assert response.status_code == 302, response.content.decode()[:3000]
    assert Deadline.objects.get().outbox.count() == 4
    soon = add(engagement, timezone.localdate() + dt.timedelta(days=2), now=timezone.now())
    response = admin_client.get(reverse("admin:alerts_upcomingdeadline_changelist"), secure=True)
    assert [d.pk for d in response.context["cl"].result_list] == [soon.pk]  # the 30-day one is beyond 14 days
    assert '#b00020">RED</b>' in response.content.decode()
    admin_client.post(reverse("admin:alerts_deadline_changelist"),
                      {"action": "acknowledge", "_selected_action": [soon.pk]}, secure=True)
    soon.refresh_from_db()
    assert soon.acknowledged_at is not None


@pytest.mark.django_db(transaction=True)
def test_two_senders_never_send_the_same_row(engagement, mailoutbox):
    """A second sender skips a row another sender has locked (SKIP LOCKED), then sends it once it is free."""
    d = add(engagement, dt.date(2026, 10, 12))
    row = d.outbox.get(kind="calendar")
    locked, release = threading.Event(), threading.Event()

    def other_sender():
        with transaction.atomic():
            Outbox.objects.select_for_update().get(pk=row.pk)
            locked.set()
            release.wait(10)
        connection.close()

    thread = threading.Thread(target=other_sender)
    thread.start()
    assert locked.wait(10)
    try:
        assert api.send_due(NOW) == (0, 0)
    finally:
        release.set()
        thread.join(10)
    assert api.send_due(NOW) == (1, 0)
    assert len(mailoutbox) == 1
