"""Append-only record of who did what and when (docs/architecture.md §6.7, H8).

The database enforces it twice: a trigger refuses every UPDATE and DELETE (migration 0002), and the app role has
only INSERT and SELECT on this table (`deploy/roles.sql`). Details hold internal ids and codes, never personal data.
"""

from django.db import models
from django.utils import timezone


class AuditEvent(models.Model):
    at = models.DateTimeField(default=timezone.now, db_index=True)
    tenant_id = models.PositiveIntegerField(default=1, db_index=True)
    actor_id = models.PositiveIntegerField(null=True, blank=True)  # auth user id; empty for jobs and failed sign-ins
    action = models.CharField(max_length=64, db_index=True)
    object_ref = models.CharField(max_length=100, blank=True)  # "app.model:pk"
    details = models.JSONField(default=dict, blank=True)
    correlation_id = models.CharField(max_length=32, db_index=True)  # one per request or job run

    class Meta:
        ordering = ["-at", "-pk"]

    def __str__(self) -> str:
        return f"{self.at:%Y-%m-%d %H:%M:%S} {self.action} {self.object_ref}"

    def save(self, *args: object, **kwargs: object) -> None:
        if not self._state.adding:
            raise PermissionError("audit events are append-only")
        super().save(*args, **kwargs)  # type: ignore[arg-type]

    def delete(self, *args: object, **kwargs: object) -> tuple[int, dict[str, int]]:
        raise PermissionError("audit events are append-only")
