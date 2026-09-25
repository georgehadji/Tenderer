"""The only way to create deadlines and deliver their reminders (docs/architecture.md §6.5, AD11, H1).

Transactional outbox: a deadline and all its notifications commit together. `send_due` delivers them at least
once: each row is locked, sent and marked in one transaction, so a failed send is retried on the next run and a
sent row is never picked again. A crash between the provider accepting a message and the commit resends it; the
Message-ID is the idempotency key, so the client's mail program shows one message. `backlog` feeds the heartbeat.
"""

import logging
from datetime import date, datetime, time, timedelta
from email.utils import parseaddr
from enum import StrEnum

from django.conf import settings
from django.core.mail import EmailMessage
from django.db import transaction
from django.db.models import Exists, OuterRef, QuerySet
from django.utils import timezone

from tenderer.apps.alerts import ics
from tenderer.apps.alerts.models import Deadline, Outbox, UpcomingDeadline
from tenderer.apps.audit import api as audit

log = logging.getLogger(__name__)

REMINDER_DAYS = {Outbox.Kind.T7: 7, Outbox.Kind.T3: 3, Outbox.Kind.T1: 1}  # escalation ladder (§6.5)
PHONE_AT = 3  # not acknowledged by T-3: the dashboard turns red and the operator phones
SEND_AT = time(9)  # local time of each reminder
HORIZON = timedelta(days=14)  # the operator dashboard (S5)
MAX_LAG = timedelta(minutes=30)  # a notification unsent for this long withholds the heartbeat, which pages
NEVER_ASK = ("Δεν ζητάμε ποτέ κωδικούς ΕΣΗΔΗΣ ή Taxisnet. Αν κάποιος σας τους ζητήσει στο όνομά μας, "
             "μην απαντήσετε και τηλεφωνήστε μας.")  # X7: on every e-mail


class NoRecipient(Exception):
    """The client has no e-mail address. The row stays pending, the dashboard turns red, the heartbeat stops."""


class Signal(StrEnum):
    RED = "red"
    AMBER = "amber"
    GREEN = "green"


@transaction.atomic
def add_deadline(deadline: Deadline, now: datetime | None = None) -> Deadline:
    """Save a new deadline with its calendar e-mail (sent at once) and the T-7/T-3/T-1 reminders still ahead."""
    now = now or timezone.now()
    today = timezone.localdate(now)
    if deadline.due_on < today:
        raise ValueError(f"deadline {deadline.due_on} has already passed")
    deadline.tenant_id = deadline.engagement.tenant_id
    deadline.save()
    rows = [(Outbox.Kind.CALENDAR, now)]
    zone = timezone.get_current_timezone()
    for kind, days in REMINDER_DAYS.items():
        day = deadline.due_on - timedelta(days=days)
        if day >= today:
            rows.append((kind, datetime.combine(day, SEND_AT, tzinfo=zone)))
    for kind, due_at in rows:
        Outbox.objects.create(tenant_id=deadline.tenant_id, idempotency_key=f"deadline-{deadline.pk}-{kind}",
                              deadline=deadline, kind=kind, due_at=due_at)
    audit.record("deadline.added", deadline, {"engagement": deadline.engagement_id, "reminders": len(rows)})
    return deadline


def acknowledge(deadline: Deadline, now: datetime | None = None) -> Deadline:
    deadline.acknowledged_at = deadline.acknowledged_at or now or timezone.now()
    deadline.save(update_fields=["acknowledged_at"])
    audit.record("deadline.acknowledged", deadline)
    return deadline


def close(deadline: Deadline, now: datetime | None = None) -> Deadline:
    """Done or withdrawn: reminders not yet sent are no longer sent."""
    deadline.closed_at = deadline.closed_at or now or timezone.now()
    deadline.save(update_fields=["closed_at"])
    audit.record("deadline.closed", deadline)
    return deadline


def send_due(now: datetime | None = None) -> tuple[int, int]:
    """Send every due notification once. Returns (sent, failed); failed rows are retried on the next run."""
    now = now or timezone.now()
    due = Outbox.objects.filter(sent_at__isnull=True, due_at__lte=now, deadline__closed_at__isnull=True)
    sent = failed = 0
    for pk in list(due.values_list("pk", flat=True)):
        with transaction.atomic():
            row = due.select_for_update(skip_locked=True, of=("self",)).filter(pk=pk).first()
            if row is None:
                continue  # sent meanwhile, or another sender holds it
            row.attempts += 1
            try:
                message(row, now).send()
            except Exception as e:  # recorded, retried next run, and a backlog withholds the heartbeat
                row.last_error = type(e).__name__
                log.warning("outbox %s failed: %s", row.idempotency_key, row.last_error)
                failed += 1
            else:
                row.sent_at, row.last_error = now, ""
                sent += 1
            row.save(update_fields=["attempts", "sent_at", "last_error"])
            audit.record("notification.sent" if row.sent_at else "notification.failed", row,
                         {"kind": row.kind, "attempt": row.attempts, "error": row.last_error})
    return sent, failed


def backlog(now: datetime | None = None) -> int:
    now = now or timezone.now()
    return Outbox.objects.filter(sent_at__isnull=True, deadline__closed_at__isnull=True,
                                 due_at__lte=now - MAX_LAG).count()


def message(row: Outbox, now: datetime) -> EmailMessage:
    deadline = row.deadline
    to = deadline.engagement.client.email
    if not to:
        raise NoRecipient
    subject, body = render(row, now)
    domain = parseaddr(settings.DEFAULT_FROM_EMAIL)[1].rpartition("@")[2]
    msg = EmailMessage(subject, body, to=[to], headers={"Message-ID": f"<{row.idempotency_key}@{domain}>"})
    if row.kind == Outbox.Kind.CALENDAR:
        msg.attach("prothesmia.ics", ics.calendar(f"{row.idempotency_key}@{domain}", deadline.due_on, deadline.step,
                                                  _facts(deadline), now), "text/calendar")
    return msg


def render(row: Outbox, now: datetime) -> tuple[str, str]:
    """Subject and plain-text body: tender, step, date, source, and the never-ask line. Nothing else (§6.5)."""
    deadline = row.deadline
    when = f"{deadline.due_on:%d/%m/%Y}"
    if row.kind == Outbox.Kind.CALENDAR:
        subject = f"Νέα προθεσμία {when}: {deadline.step}"
        lead = ("Καταγράψαμε νέα προθεσμία. Το συνημμένο αρχείο τη βάζει στο ημερολόγιό σας, "
                "με ειδοποίηση 3 ημέρες και 1 ημέρα πριν.")
    else:
        subject = f"Υπενθύμιση: {deadline.step} έως {when}"
        lead = _left((deadline.due_on - timezone.localdate(now)).days)
    return subject, "\n".join([lead, "", _facts(deadline), "", NEVER_ASK, ""])


def signal(due_on: date, today: date, acknowledged: bool, failing: bool) -> Signal:
    left = (due_on - today).days
    if failing or left < 0 or (not acknowledged and left <= PHONE_AT):
        return Signal.RED
    return Signal.AMBER if left <= max(REMINDER_DAYS.values()) else Signal.GREEN


def open_deadlines(engagement_id: int) -> QuerySet[Deadline]:
    return Deadline.objects.filter(engagement_id=engagement_id, closed_at__isnull=True)


def upcoming(today: date) -> QuerySet[UpcomingDeadline]:
    """Open deadlines up to 14 days ahead (and overdue ones), each marked `failing` if a send has failed."""
    failing = Outbox.objects.filter(deadline=OuterRef("pk"), sent_at__isnull=True, attempts__gt=0)
    return (UpcomingDeadline.objects.filter(closed_at__isnull=True, due_on__lte=today + HORIZON)
            .annotate(failing=Exists(failing)).select_related("engagement__client"))


def _facts(deadline: Deadline) -> str:
    engagement = deadline.engagement
    lines = [f"Διαγωνισμός: {engagement.tender_title or engagement.tender_id}",
             f"Βήμα: {deadline.step}",
             f"Προθεσμία: {deadline.due_on:%d/%m/%Y}"]
    if deadline.source_section:
        lines.append(f"Πηγή: {deadline.source_section} της διακήρυξης")
    return "\n".join(lines)


def _left(days: int) -> str:
    if days < 0:
        return "Η προθεσμία έχει λήξει."
    if days == 0:
        return "Η προθεσμία λήγει σήμερα."
    return "Απομένει 1 ημέρα." if days == 1 else f"Απομένουν {days} ημέρες."
