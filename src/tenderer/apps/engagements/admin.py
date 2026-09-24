"""Operator screens. Every screen that acts on a client shows its name and the last ΑΦΜ digits (H6).
States are read-only here: they change only through the admin actions, which call `api` (§6.14)."""

from collections.abc import Callable
from typing import Any

from django.contrib import admin, messages
from django.db.models import QuerySet
from django.http import HttpRequest

from tenderer.apps.engagements import api
from tenderer.apps.engagements.models import Acknowledgement, Bid, Client, DocumentRecord, Engagement, Resource
from tenderer.core.lifecycle.templates import TEMPLATES

ENGAGEMENT_EVENTS = sorted({e for t in TEMPLATES.values() for s in t.engagement.states for e in t.engagement.events(s)})
BID_EVENTS = sorted({e for t in TEMPLATES.values() for s in t.bid.states for e in t.bid.events(s)})


def _action(event: str, fire: Callable[[Any, str], Any]) -> Callable[..., None]:
    def run(modeladmin: admin.ModelAdmin, request: HttpRequest, queryset: QuerySet[Any]) -> None:
        for obj in queryset:
            try:
                fire(obj, event)
                modeladmin.message_user(request, f"{obj}: {event} ✓", messages.SUCCESS)
            except api.TransitionRefused as e:
                modeladmin.message_user(request, f"{obj}: {event} refused ({e})", messages.ERROR)

    run.__name__ = f"fire_{event}"
    run.short_description = f"Event: {event}"  # type: ignore[attr-defined]
    return run


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ("__str__", "phone", "email", "retention_until")
    search_fields = ("name", "tax_id")
    readonly_fields = ("created_at",)


@admin.register(Resource)
class ResourceAdmin(admin.ModelAdmin):
    list_display = ("label", "kind", "sector", "client")
    list_filter = ("sector", "kind")
    readonly_fields = ("schema_version",)


@admin.register(DocumentRecord)
class DocumentRecordAdmin(admin.ModelAdmin):
    list_display = ("doc_type", "client", "resource", "issued_on", "valid_until", "manual_status", "applicable")
    list_filter = ("doc_type",)


@admin.register(Engagement)
class EngagementAdmin(admin.ModelAdmin):
    list_display = ("client", "tender_id", "lifecycle", "state", "admitted_on")
    list_filter = ("state", "tender_id")
    readonly_fields = ("state", "lifecycle", "tender_version", "created_at")
    actions = [_action(e, api.fire_engagement) for e in ENGAGEMENT_EVENTS]


@admin.register(Bid)
class BidAdmin(admin.ModelAdmin):
    list_display = ("__str__", "invitation_ref", "state")
    list_filter = ("state",)
    readonly_fields = ("state", "offer_check", "gonogo_snapshot", "checklist_snapshot", "created_at")
    actions = [_action(e, api.fire_bid) for e in BID_EVENTS]


@admin.register(Acknowledgement)
class AcknowledgementAdmin(admin.ModelAdmin):
    list_display = ("engagement", "kind", "acknowledged_at")
