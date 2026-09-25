"""Data-subject screen for the admin role: export as a JSON download, and erasure after a confirmation page."""

import json
from typing import Any

from django.contrib import admin, messages
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import QuerySet
from django.http import HttpRequest, HttpResponse
from django.template.response import TemplateResponse

from tenderer.apps.audit.admin import AuditedAdmin
from tenderer.apps.privacy import api
from tenderer.apps.privacy.models import DataSubject


@admin.action(description="Export all data of the selected client (JSON)", permissions=["delete"])
def export(modeladmin: admin.ModelAdmin, request: HttpRequest, queryset: QuerySet[Any]) -> HttpResponse | None:
    if queryset.count() != 1:
        modeladmin.message_user(request, "Select exactly one client to export.", messages.WARNING)
        return None
    client = queryset.get()
    response = HttpResponse(json.dumps(api.export(client), cls=DjangoJSONEncoder, ensure_ascii=False, indent=2),
                            content_type="application/json; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="client-{client.pk}.json"'
    return response


@admin.action(description="Erase all data of the selected clients", permissions=["delete"])
def erase(modeladmin: admin.ModelAdmin, request: HttpRequest, queryset: QuerySet[Any]) -> HttpResponse | None:
    if request.POST.get("confirm") != "yes":
        return TemplateResponse(request, "privacy/confirm_erase.html", {
            **modeladmin.admin_site.each_context(request), "subjects": list(queryset)})
    for client in queryset:
        label = str(client)
        try:
            api.erase(client)
            modeladmin.message_user(request, f"{label}: erased", messages.SUCCESS)
        except api.StillOpen:
            modeladmin.message_user(request, f"{label}: not erased, an engagement is still open", messages.ERROR)
    return None


@admin.register(DataSubject)
class DataSubjectAdmin(AuditedAdmin):
    list_display = ("__str__", "retention_until")
    search_fields = ("name", "tax_id")
    actions = [export, erase]

    def get_readonly_fields(self, request: HttpRequest, obj: Any = None) -> list[str]:
        return [f.name for f in self.model._meta.fields]

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def get_actions(self, request: HttpRequest) -> dict[str, Any]:
        actions = super().get_actions(request)
        actions.pop("delete_selected", None)  # erasure goes through `erase`, which also clears related records
        return actions
