"""Read-only view of the audit log, and `AuditedAdmin`, the base of every admin screen that shows client data:
opening a record or a list writes a "viewed" or "listed" event (docs/architecture.md §6.7, §10.1 TB1)."""

from typing import Any

from django.contrib import admin
from django.http import HttpRequest, HttpResponse

from tenderer.apps.audit import api
from tenderer.apps.audit.models import AuditEvent


class AuditedAdmin(admin.ModelAdmin):
    def changeform_view(self, request: HttpRequest, object_id: str | None = None, form_url: str = "",
                        extra_context: dict[str, Any] | None = None) -> HttpResponse:
        if object_id and request.method == "GET":
            api.record("viewed", f"{self.model._meta.label_lower}:{object_id}")
        return super().changeform_view(request, object_id, form_url, extra_context)

    def changelist_view(self, request: HttpRequest, extra_context: dict[str, Any] | None = None) -> HttpResponse:
        if request.method == "GET":
            api.record("listed", self.model._meta.label_lower)
        return super().changelist_view(request, extra_context)


@admin.register(AuditEvent)
class AuditEventAdmin(admin.ModelAdmin):
    list_display = ("at", "action", "object_ref", "actor_id", "correlation_id")
    list_filter = ("action",)
    search_fields = ("object_ref", "correlation_id")

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_change_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return False

    def has_delete_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return False
