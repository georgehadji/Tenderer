"""Operator screens: deadlines (created through `api`, so the outbox rows commit with them), the 14-day dashboard
with its red/amber/green signal (S5), and a read-only view of the outbox."""

from typing import Any

from django.contrib import admin
from django.db.models import QuerySet
from django.http import HttpRequest
from django.utils import timezone
from django.utils.html import format_html
from django.utils.safestring import SafeString

from tenderer.apps.alerts import api
from tenderer.apps.alerts.models import Deadline, Outbox, UpcomingDeadline

COLOURS = {api.Signal.RED: "#b00020", api.Signal.AMBER: "#8a5a00", api.Signal.GREEN: "#1b6e20"}
FIELDS = ("engagement", "step", "due_on", "legal_latest", "ambiguous", "source_section", "acknowledged_at",
          "closed_at", "tenant_id")


@admin.action(description="Client acknowledged")
def acknowledge(modeladmin: admin.ModelAdmin, request: HttpRequest, queryset: QuerySet[Any]) -> None:
    for deadline in queryset:
        api.acknowledge(deadline)


@admin.action(description="Close (done or withdrawn): stop reminders")
def close(modeladmin: admin.ModelAdmin, request: HttpRequest, queryset: QuerySet[Any]) -> None:
    for deadline in queryset:
        api.close(deadline)


@admin.register(Deadline)
class DeadlineAdmin(admin.ModelAdmin):
    list_display = ("due_on", "step", "engagement", "ambiguous", "acknowledged_at", "closed_at")
    list_select_related = ("engagement__client",)
    actions = [acknowledge, close]

    def get_readonly_fields(self, request: HttpRequest, obj: Any = None) -> tuple[str, ...]:
        # A saved deadline is never edited: its reminders were planned from these values. Close it and add a new one.
        return FIELDS if obj else ("acknowledged_at", "closed_at", "tenant_id")

    def save_model(self, request: HttpRequest, obj: Any, form: Any, change: bool) -> None:
        if not change:
            api.add_deadline(obj)

    def has_delete_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return False


@admin.register(UpcomingDeadline)
class UpcomingDeadlineAdmin(DeadlineAdmin):
    list_display = ("signal", "due_on", "step", "engagement", "ambiguous", "acknowledged_at")

    def get_queryset(self, request: HttpRequest) -> QuerySet[Any]:
        return api.upcoming(timezone.localdate())

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    @admin.display(description="signal")
    def signal(self, obj: Any) -> SafeString:
        s = api.signal(obj.due_on, timezone.localdate(), obj.acknowledged_at is not None, obj.failing)
        return format_html('<b style="color:{}">{}</b>', COLOURS[s], s.upper())


@admin.register(Outbox)
class OutboxAdmin(admin.ModelAdmin):
    list_display = ("idempotency_key", "kind", "due_at", "sent_at", "attempts", "last_error")
    list_filter = (("sent_at", admin.EmptyFieldListFilter), "kind")

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_change_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return False

    def has_delete_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return False
