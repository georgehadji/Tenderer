"""Clients, resources, document metadata, engagements and bids (docs/architecture.md §6.4, §8).

Active record on the ORM; decisions come from `core`. What is never stored (AD5): document files, criminal-record
or health content, exclusion answers, credentials, signatures. `tests/test_engagements.py` checks the schema for it.
Every table carries `tenant_id` (AD19); row-level security arrives in v5.
"""

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.module_loading import import_string
from jsonschema import Draft202012Validator, FormatChecker

from tenderer.core.catalog.packs import Packs
from tenderer.core.lifecycle.templates import BID_STATES, ENGAGEMENT_STATES, TEMPLATES
from tenderer.core.rules.checklist import Status

DEFAULT_TENANT = 1


def packs() -> Packs:
    """The registry that shell fills; apps never import a pack by name (§5.2 rule 7)."""
    registry: Packs = import_string(settings.TENDERER_PACKS)
    return registry


class TenantModel(models.Model):
    tenant_id = models.PositiveIntegerField(default=DEFAULT_TENANT, db_index=True)

    class Meta:
        abstract = True

    def save(self, *args: object, **kwargs: object) -> None:
        self.full_clean()  # every write path validates, not only forms
        super().save(*args, **kwargs)  # type: ignore[arg-type]


class Client(TenantModel):
    jurisdiction = models.CharField(max_length=8, default="gr")
    name = models.CharField(max_length=200)
    tax_id = models.CharField(max_length=20)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    retention_until = models.DateField(null=True, blank=True)  # set when the last engagement closes (§10.8)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["tenant_id", "jurisdiction", "tax_id"], name="client_tax_id_unique"),
        ]

    def __str__(self) -> str:
        return f"{self.name} (ΑΦΜ …{self.tax_id[-3:]})"  # name + last digits on every screen (H6)

    def clean(self) -> None:
        validators = _jurisdiction(self.jurisdiction).validators
        for field, kind in (("tax_id", "tax_id"), ("phone", "phone")):
            value = getattr(self, field)
            if value and kind in validators:
                try:
                    setattr(self, field, validators[kind](value))
                except ValueError as e:
                    raise ValidationError({field: str(e)}) from e


class Resource(TenantModel):
    """A vehicle, driver, escort… of a client. Kinds and attribute schemas come from the sector pack (AD15)."""
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="resources")
    sector = models.CharField(max_length=64)
    kind = models.CharField(max_length=64)
    label = models.CharField(max_length=100)
    attributes = models.JSONField(default=dict)
    schema_version = models.PositiveSmallIntegerField(default=1)

    def __str__(self) -> str:
        return f"{self.kind} {self.label} · {self.client}"

    def clean(self) -> None:
        sector = packs().sectors.get(self.sector)
        if sector is None:
            raise ValidationError({"sector": f"no sector pack {self.sector!r}"})
        schema = sector.resource_kinds.get(self.kind)
        if schema is None:
            raise ValidationError({"kind": f"{self.kind!r} is not a resource kind of {self.sector}"})
        errors = sorted(Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(self.attributes),
                        key=str)
        if errors:
            raise ValidationError({"attributes": [f"{'/'.join(map(str, e.path)) or '(root)'}: {e.message}"
                                                  for e in errors]})
        self.schema_version = int(str(schema.get("x-schema-version", 1)))
        plate = self.attributes.get("plate") if isinstance(self.attributes, dict) else None
        if isinstance(plate, str) and self.client_id is not None:
            validators = _jurisdiction(self.client.jurisdiction).validators
            if "plate" in validators:
                try:
                    self.attributes["plate"] = validators["plate"](plate)
                except ValueError as e:
                    raise ValidationError({"attributes": f"plate: {e}"}) from e
        for key in schema.get("x-unique", ()):  # type: ignore[attr-defined]
            value = self.attributes.get(key)
            clash = Resource.objects.filter(client_id=self.client_id, kind=self.kind, **{f"attributes__{key}": value})
            if value is not None and clash.exclude(pk=self.pk).exists():
                raise ValidationError({"attributes": f"another {self.kind} of this client has {key} {value}"})


class DocumentRecord(TenantModel):
    """Metadata of one document: type and dates, never the file or its content (AD5)."""
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="documents")
    resource = models.ForeignKey(Resource, on_delete=models.CASCADE, null=True, blank=True, related_name="documents")
    doc_type = models.CharField(max_length=64)
    issued_on = models.DateField(null=True, blank=True)
    valid_until = models.DateField(null=True, blank=True)
    manual_status = models.CharField(max_length=16, blank=True,
                                     choices=[(s.value, s.value) for s in (Status.SATISFIED, Status.NOT_SATISFIED)])
    applicable = models.BooleanField(default=True)
    seen_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True)
    seen_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [models.CheckConstraint(
            condition=models.Q(valid_until__isnull=True) | models.Q(issued_on__isnull=True)
            | models.Q(valid_until__gte=models.F("issued_on")), name="document_valid_after_issue")]

    def __str__(self) -> str:
        return f"{self.doc_type} · {self.client}"

    def clean(self) -> None:
        if self.resource_id is not None and self.resource.client_id != self.client_id:
            raise ValidationError({"resource": "the resource belongs to another client"})


class Engagement(TenantModel):
    """One client in one tender. State changes only through `api.fire_engagement` (transition table §6.14)."""
    client = models.ForeignKey(Client, on_delete=models.PROTECT, related_name="engagements")
    tender_id = models.CharField(max_length=100)
    tender_version = models.CharField(max_length=40)  # Tender.version at creation (S4)
    lifecycle = models.CharField(max_length=32, choices=[(t, t) for t in TEMPLATES])
    state = models.CharField(max_length=32, choices=[(s, s) for s in sorted(ENGAGEMENT_STATES)])
    admitted_on = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["tenant_id", "client", "tender_id"], name="engagement_unique"),
            models.CheckConstraint(condition=models.Q(state__in=sorted(ENGAGEMENT_STATES)),
                                   name="engagement_state_known"),
        ]

    def __str__(self) -> str:
        return f"{self.client} · {self.tender_id} · {self.state}"


class Bid(TenantModel):
    """One offer of the client for one invitation. The recorded checks feed the DRAFT → CHECKED guard (H2, H7)."""
    engagement = models.ForeignKey(Engagement, on_delete=models.PROTECT, related_name="bids")
    invitation_ref = models.CharField(max_length=100)
    state = models.CharField(max_length=32, choices=[(s, s) for s in sorted(BID_STATES)])
    offer_check = models.JSONField(null=True, blank=True)  # validator result per line, with prices and discounts
    gonogo_snapshot = models.JSONField(null=True, blank=True)  # break-even and lines shown to the client
    checklist_snapshot = models.JSONField(null=True, blank=True)  # offer-stage checklist items
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["tenant_id", "engagement", "invitation_ref"], name="bid_unique"),
            models.CheckConstraint(condition=models.Q(state__in=sorted(BID_STATES)), name="bid_state_known"),
        ]

    def __str__(self) -> str:
        return f"{self.engagement.client} · {self.invitation_ref} · {self.state}"


class Acknowledgement(TenantModel):
    """The client confirmed something on a date. No free text (§8)."""
    class Kind(models.TextChoices):
        EXCLUSION_GROUNDS_REVIEWED = "exclusion_grounds_reviewed"  # never the answers themselves (§2.2.3)
        FUEL_RISK = "fuel_risk"  # §6.6.4
        CANCELLATION_RISK = "cancellation_risk"  # §7.6.1
        GONOGO_SEEN = "gonogo_seen"

    engagement = models.ForeignKey(Engagement, on_delete=models.CASCADE, related_name="acknowledgements")
    kind = models.CharField(max_length=40, choices=Kind.choices)
    acknowledged_at = models.DateTimeField()

    def __str__(self) -> str:
        return f"{self.kind} · {self.engagement}"


def _jurisdiction(cc: str):  # type: ignore[no-untyped-def]
    pack = packs().jurisdictions.get(cc)
    if pack is None:
        raise ValidationError({"jurisdiction": f"no jurisdiction pack {cc!r}"})
    return pack
