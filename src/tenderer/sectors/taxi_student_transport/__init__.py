"""Taxi (Ε.Δ.Χ.) student transport: resource kinds, document types, go/no-go cost model (§6.12)."""

from tenderer.core.catalog.packs import JsonSchema, SectorPack

DOCUMENT_TYPES = frozenset({
    "vehicle_circulation_licence", "vehicle_insurance_passengers", "vehicle_roadworthiness_test",
    "vehicle_lease_or_concession", "declaration_co_owner_consent", "declaration_routes_plates_zones",
    "route_plate_table", "driving_licence_professional", "declaration_driver_escort_offences",
    "escort_health_certificate", "vehicle_staff_table",
})

_DATE = {"type": "string", "format": "date"}

# Minimum fields only (docs/architecture.md §8). `x-personal` marks what export, erasure and log redaction find.
RESOURCE_KINDS: dict[str, JsonSchema] = {
    "vehicle": {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "additionalProperties": False,
        "required": ["plate", "seats", "base_municipality"],
        "properties": {
            "plate": {"type": "string", "minLength": 1, "x-personal": True},
            "seats": {"type": "integer", "minimum": 1},
            "base_municipality": {"type": "string", "minLength": 1},
        },
        "x-unique": ["plate"],
        "x-schema-version": 1,
    },
    "driver": {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "additionalProperties": False,
        "required": ["display_name"],
        "properties": {
            "display_name": {"type": "string", "minLength": 1, "x-personal": True},
            "licence_valid_until": _DATE,
            "professional_licence_valid_until": _DATE,
        },
        "x-schema-version": 1,
    },
    "escort": {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "additionalProperties": False,
        "required": ["display_label"],
        "properties": {
            "display_label": {"type": "string", "minLength": 1, "x-personal": True},
            "health_certificate_valid_until": _DATE,  # the expiry only, never the content (AD5)
        },
        "x-schema-version": 1,
    },
}

PACK = SectorPack(id="taxi_student_transport", resource_kinds=RESOURCE_KINDS, document_types=DOCUMENT_TYPES)
