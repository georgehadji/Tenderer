"""Greece: holidays, number words, deductions on public payments, national document types (§6.13)."""

from datetime import date, timedelta
from decimal import Decimal

from tenderer.core.catalog.packs import JurisdictionPack

DOCUMENT_TYPES = frozenset({
    "qualified_signature_certificate", "esidis_registration", "espd_response",
    "declaration_no_russian_involvement", "declarations_exclusion_grounds", "financial_offer",
    "participation_guarantee", "performance_guarantee", "criminal_record_extract", "tax_clearance",
    "social_security_clearance", "insolvency_certificate", "tax_registry_printout",
    "business_registry_certificate", "payment_documents",
})

# 0.1% ΕΑΑΔΗΣΥ + 0.02% ΟΠΣ ΕΣΗΔΗΣ, plus 3% stamp duty on them and 20% ΟΓΑ on the stamp duty
# (§4.3.2.2 and §6.6.2 of ΑΔΑ ΨΡΘ97ΛΛ-ΕΕΚ).
PAYMENT_DEDUCTION_RATE = Decimal("0.0012") * (1 + Decimal("0.03") * Decimal("1.2"))


def orthodox_easter(year: int) -> date:
    """Meeus Julian algorithm, shifted to the Gregorian calendar (valid 1900-2099)."""
    a, b, c = year % 4, year % 7, year % 19
    d = (19 * c + 15) % 30
    e = (2 * a + 4 * b - d + 34) % 7
    month, day = divmod(d + e + 114, 31)
    return date(year, month, day + 1) + timedelta(days=13)


def public_holidays(year: int) -> dict[date, str]:
    """Non-working days for deadlines that run against public bodies. Moved holidays are not predictable:
    the reviewed file in reference/gr/ is authoritative (docs/architecture.md §6.2)."""
    easter = orthodox_easter(year)
    fixed = {
        (1, 1): "Πρωτοχρονιά", (1, 6): "Θεοφάνεια", (3, 25): "25η Μαρτίου", (5, 1): "Εργατική Πρωτομαγιά",
        (8, 15): "Κοίμηση της Θεοτόκου", (10, 28): "28η Οκτωβρίου", (12, 25): "Χριστούγεννα",
        (12, 26): "Σύναξη της Θεοτόκου",
    }
    days = {date(year, m, d): name for (m, d), name in fixed.items()}
    days |= {
        easter - timedelta(days=48): "Καθαρά Δευτέρα",
        easter - timedelta(days=2): "Μεγάλη Παρασκευή",
        easter + timedelta(days=1): "Δευτέρα του Πάσχα",
        easter + timedelta(days=50): "Αγίου Πνεύματος",
    }
    return dict(sorted(days.items()))


_UNITS = ("μηδέν", "ένα", "δύο", "τρία", "τέσσερα", "πέντε", "έξι", "επτά", "οκτώ", "εννέα",
          "δέκα", "έντεκα", "δώδεκα")
_TENS = ("", "", "είκοσι", "τριάντα", "σαράντα", "πενήντα", "εξήντα", "εβδομήντα", "ογδόντα", "ενενήντα")


def number_in_words(n: int) -> str:
    """0-99 in Greek, as the offer template wants the discount written out (§4.3.2.3 β)."""
    if not 0 <= n <= 99:
        raise ValueError(f"{n} is outside 0-99")
    if n <= 12:
        return _UNITS[n]
    tens, unit = divmod(n, 10)
    if tens == 1:
        return "δεκα" + _UNITS[unit]
    return _TENS[tens] + (f" {_UNITS[unit]}" if unit else "")


PACK = JurisdictionPack(
    id="gr",
    document_types=DOCUMENT_TYPES,
    public_holidays=public_holidays,
    payment_deduction_rate=PAYMENT_DEDUCTION_RATE,
)
