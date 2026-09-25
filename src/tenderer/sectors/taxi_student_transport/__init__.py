"""Taxi (Ε.Δ.Χ.) student transport: resource kinds, document types, go/no-go cost model (§6.12)."""

from tenderer.core.catalog.packs import JsonSchema, SectorPack
from tenderer.sectors.taxi_student_transport import costs

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
            "certificate_valid_until": _DATE,  # expiry of the medical certificate only, never its content (AD5)
        },
        "x-schema-version": 1,
    },
}

# What the client reads for each cost line and warning code of `costs.py`.
LABELS = {
    "fuel": "Καύσιμο",
    "wear": "Φθορά οχήματος",
    "escort": "Συνοδός",
    "insurance": "Επιπλέον ασφάλιστρο",
    "opportunity": "Κόστος του χρόνου σας",
    "guarantee_bank_costs": "Προμήθειες και τόκος τράπεζας για την εγγύηση συμμετοχής",
    "deductions": "Κρατήσεις επί της πληρωμής",
    "performance_guarantee_carry": "Κόστος εγγύησης καλής εκτέλεσης",
    "fuel_no_adjustment": "Η τιμή δεν αναπροσαρμόζεται αν ακριβύνει το καύσιμο (§6.6.4).",
    "cancellation_no_compensation": "Αν ακυρωθεί δρομολόγιο, δεν δίνεται αποζημίωση (§7.6.1).",
    "escort_zero_cost": "Τον συνοδό τον πληρώνει ο ανάδοχος, αλλά το κόστος του μπήκε 0. Ελέγξτε το (§4.3.2.2).",
    "loss_at_zero": "Ζημιά ακόμη και χωρίς έκπτωση.",
}

PACK = SectorPack(id="taxi_student_transport", resource_kinds=RESOURCE_KINDS, document_types=DOCUMENT_TYPES,
                  labels=LABELS, gonogo=costs.gonogo)
