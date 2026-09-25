"""Deadlines and the transactional outbox of their reminders (docs/architecture.md §6.5, AD11).

A deadline and every notification it causes are written in one transaction (`api.add_deadline`); the sender
job delivers them. Reminders carry the minimum: tender, step, date (§6.5 Security).
"""

from django.db import models

from tenderer.apps.engagements.models import TenantModel


class Deadline(TenantModel):
    """A date by which the client must act. `due_on` is the conservative `remind_by` of `core/rules` (H1)."""
    engagement = models.ForeignKey("engagements.Engagement", on_delete=models.PROTECT, related_name="deadlines")
    step = models.CharField(max_length=120)  # what the client must do, e.g. "Ανανέωση ΕΕΕΣ"; never a person's name
    due_on = models.DateField()
    legal_latest = models.DateField(null=True, blank=True)  # shown as information only (§6.2)
    ambiguous = models.BooleanField(default=False)  # no reviewed holiday calendar for a year in the count
    source_section = models.CharField(max_length=40, blank=True)
    acknowledged_at = models.DateTimeField(null=True, blank=True)  # the client confirmed they saw it
    closed_at = models.DateTimeField(null=True, blank=True)  # done or withdrawn: no more reminders
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["due_on"]

    def __str__(self) -> str:
        return f"{self.due_on:%d/%m/%Y} · {self.step} · {self.engagement.client}"


class UpcomingDeadline(Deadline):
    """The operator dashboard: open deadlines up to 14 days ahead, and every overdue one (S5)."""
    class Meta:
        proxy = True
        verbose_name = "deadline in the next 14 days"
        verbose_name_plural = "deadlines in the next 14 days"


class Outbox(TenantModel):
    """One e-mail, the only channel that leaves the system (the .ics rides on it; the dashboard is the third).
    The unique idempotency key makes planning and retries safe (§6.5)."""
    class Kind(models.TextChoices):
        CALENDAR = "calendar", "calendar"  # sent at once with the .ics file: the date lives in the client's calendar
        T7 = "T-7", "T-7"
        T3 = "T-3", "T-3"
        T1 = "T-1", "T-1"

    idempotency_key = models.CharField(max_length=80, unique=True)
    deadline = models.ForeignKey(Deadline, on_delete=models.PROTECT, related_name="outbox")
    kind = models.CharField(max_length=16, choices=Kind.choices)
    due_at = models.DateTimeField(db_index=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    attempts = models.PositiveSmallIntegerField(default=0)
    last_error = models.CharField(max_length=80, blank=True)  # exception class only: provider errors may hold addresses

    class Meta:
        ordering = ["due_at"]

    def __str__(self) -> str:
        return self.idempotency_key
