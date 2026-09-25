"""Operator screen for client plans: preview one, or send the selected ones by e-mail (docs/architecture.md §6.6)."""

from typing import Any

from django.contrib import admin, messages
from django.db.models import QuerySet
from django.http import HttpRequest, HttpResponse

from tenderer.apps.audit import api as audit
from tenderer.apps.audit.admin import AuditedAdmin
from tenderer.apps.documents import api
from tenderer.apps.documents.models import ClientPlan


@admin.action(description="Preview the client plan")
def preview(modeladmin: admin.ModelAdmin, request: HttpRequest, queryset: QuerySet[Any]) -> HttpResponse | None:
    if queryset.count() != 1:
        modeladmin.message_user(request, "Select exactly one bid to preview.", messages.WARNING)
        return None
    bid = queryset.get()
    audit.record("plan.viewed", bid)
    return HttpResponse(api.render_plan(bid)[2])


@admin.action(description="E-mail the client plan to the client")
def send(modeladmin: admin.ModelAdmin, request: HttpRequest, queryset: QuerySet[Any]) -> None:
    for bid in queryset:
        try:
            api.send_plan(bid)
            modeladmin.message_user(request, f"{bid}: plan sent", messages.SUCCESS)
        except Exception as e:  # shown to the operator, who retries; nothing is half-recorded
            modeladmin.message_user(request, f"{bid}: not sent ({type(e).__name__})", messages.ERROR)


@admin.register(ClientPlan)
class ClientPlanAdmin(AuditedAdmin):
    list_display = ("__str__", "invitation_ref", "state")
    list_select_related = ("engagement__client",)
    actions = [preview, send]

    def get_readonly_fields(self, request: HttpRequest, obj: Any = None) -> list[str]:
        return [f.name for f in self.model._meta.fields]

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_delete_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return False
