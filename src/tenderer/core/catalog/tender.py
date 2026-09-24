"""Load `tenders/<id>/` into immutable objects, or refuse the whole tender (docs/architecture.md §6.1).

Parse, don't validate: every value leaves this module typed. Any invalid row or field makes the tender
fail to load, and the error names every problem with its row and column (fail closed, S1).
"""

import csv
import hashlib
import re
import tomllib
from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from pathlib import Path

from tenderer.core.catalog.packs import Packs

SCHEMA_VERSION = 2
MANIFEST = "tender.toml"
REQUIREMENTS = "requirements.csv"
COLUMNS = (
    "id", "requirement", "stage", "issuer", "validity", "source_section",
    "doc_type", "applies_to", "validity_kind", "validity_amount", "validity_unit", "validity_anchor",
    "espd_criterion",
)
ENGAGEMENT_SUBJECTS = frozenset({"client", "offer", "engagement"})  # resource kinds come from the sector pack
_STAGE = re.compile(r"[Α-Ω]\d*")
_UUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")


class ValidityKind(StrEnum):
    IN_FORCE = "in_force"          # valid_until >= anchor
    ISSUED_WITHIN = "issued_within"  # issued inside the window of `amount unit` that ends on the anchor
    SIGNED_AFTER = "signed_after"  # anchor < signed <= submission
    VALID_UNTIL = "valid_until"    # valid_until >= anchor + amount unit
    NONE = "none"                  # a record is enough
    MANUAL = "manual"              # the tender is vague; an operator decides


class Unit(StrEnum):
    DAYS = "days"
    WORKING_DAYS = "working_days"
    MONTHS = "months"


class Anchor(StrEnum):
    SUBMISSION = "submission"            # the planned submission of the stage being checked
    INVITATION_SENT = "invitation_sent"
    OFFER_VALIDITY_END = "offer_validity_end"
    CONTRACT_END = "contract_end"


_NEEDS = {  # kind -> (amount and unit required, anchor required)
    ValidityKind.IN_FORCE: (False, True),
    ValidityKind.ISSUED_WITHIN: (True, True),
    ValidityKind.SIGNED_AFTER: (False, True),
    ValidityKind.VALID_UNTIL: (True, True),
    ValidityKind.NONE: (False, False),
    ValidityKind.MANUAL: (False, False),
}


@dataclass(frozen=True)
class Validity:
    kind: ValidityKind
    amount: int | None = None
    unit: Unit | None = None
    anchor: Anchor | None = None


@dataclass(frozen=True)
class Requirement:
    id: str
    text: str
    stages: tuple[str, ...]
    issuer: str
    validity_text: str
    source_section: str
    doc_type: str
    applies_to: tuple[str, ...]
    validity: Validity
    espd_criterion: str | None


@dataclass(frozen=True)
class OfferTerms:
    offer_validity_months: int
    participation_guarantee_rate: Decimal
    participation_guarantee_extra_days: int
    performance_guarantee_rate: Decimal
    performance_guarantee_extra_months: int


@dataclass(frozen=True)
class Tender:
    id: str
    title: str
    sector: str
    jurisdiction: str
    lifecycle: str
    offer_shape: str
    sources: tuple[tuple[str, str], ...]
    offer: OfferTerms
    requirements: tuple[Requirement, ...]
    version: str  # git commit + content hash (S4)

    def requirement(self, requirement_id: str) -> Requirement:
        return next(r for r in self.requirements if r.id == requirement_id)


class TenderLoadError(Exception):
    def __init__(self, tender_dir: Path, problems: list[str]) -> None:
        self.problems = problems
        super().__init__(f"{tender_dir}: {len(problems)} problem(s)\n  " + "\n  ".join(problems))


def load_tender(tender_dir: Path, packs: Packs, commit: str) -> Tender:
    problems: list[str] = []
    manifest_bytes = _read(tender_dir / MANIFEST, problems)
    csv_bytes = _read(tender_dir / REQUIREMENTS, problems)
    if problems:
        raise TenderLoadError(tender_dir, problems)

    try:
        manifest = tomllib.loads(manifest_bytes.decode("utf-8"))
    except (tomllib.TOMLDecodeError, UnicodeDecodeError) as e:
        raise TenderLoadError(tender_dir, [f"{MANIFEST}: {e}"]) from e

    head = _parse_manifest(manifest, packs, problems)
    sector = packs.sectors.get(head.get("sector", ""))
    jurisdiction = packs.jurisdictions.get(head.get("jurisdiction", ""))
    subjects = ENGAGEMENT_SUBJECTS | (frozenset(sector.resource_kinds) if sector else frozenset())
    doc_types = (sector.document_types if sector else frozenset()) | (
        jurisdiction.document_types if jurisdiction else frozenset()
    )
    offer = _parse_offer(manifest.get("offer"), problems)
    requirements = _parse_requirements(csv_bytes, subjects, doc_types, problems)
    if problems or offer is None:
        raise TenderLoadError(tender_dir, problems)

    digest = hashlib.sha256(manifest_bytes + b"\0" + csv_bytes).hexdigest()
    return Tender(
        id=head["id"],
        title=head["title"],
        sector=head["sector"],
        jurisdiction=head["jurisdiction"],
        lifecycle=head["lifecycle"],
        offer_shape=head["offer_shape"],
        sources=tuple(sorted((str(k), str(v)) for k, v in manifest.get("sources", {}).items())),
        offer=offer,
        requirements=requirements,
        version=f"{commit[:12]}+{digest[:12]}",
    )


def _read(path: Path, problems: list[str]) -> bytes:
    try:
        return path.read_bytes()
    except OSError as e:
        problems.append(f"{path.name}: cannot read ({e.strerror})")
        return b""


def _parse_manifest(m: dict[str, object], packs: Packs, problems: list[str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for key in ("id", "title", "sector", "jurisdiction", "lifecycle", "offer_shape"):
        value = m.get(key)
        if not isinstance(value, str) or not value:
            problems.append(f"{MANIFEST}: `{key}` must be a non-empty string")
        else:
            out[key] = value
    if m.get("schema_version") != SCHEMA_VERSION:
        problems.append(f"{MANIFEST}: `schema_version` must be {SCHEMA_VERSION}")
    registered = {
        "sector": packs.sectors, "jurisdiction": packs.jurisdictions,
        "lifecycle": packs.lifecycles, "offer_shape": packs.offer_shapes,
    }
    for key, names in registered.items():
        if key in out and out[key] not in names:
            problems.append(f"{MANIFEST}: `{key}` = {out[key]!r} is not registered")
    if not isinstance(m.get("sources", {}), dict):
        problems.append(f"{MANIFEST}: `sources` must be a table")
    return out


def _parse_offer(t: object, problems: list[str]) -> OfferTerms | None:
    if not isinstance(t, dict):
        problems.append(f"{MANIFEST}: [offer] table is missing")
        return None
    n = len(problems)

    def integer(key: str) -> int:
        v = t.get(key)
        if isinstance(v, bool) or not isinstance(v, int) or v < 0:
            problems.append(f"{MANIFEST}: offer.{key} must be a non-negative integer")
            return 0
        return v

    def rate(key: str) -> Decimal:
        v = t.get(key)  # a string, because TOML floats are binary floats (AD9)
        try:
            if not isinstance(v, str):
                raise InvalidOperation
            d = Decimal(v)
            if not (d.is_finite() and 0 <= d <= 1):
                raise InvalidOperation
            return d
        except InvalidOperation:
            problems.append(f"{MANIFEST}: offer.{key} must be a decimal string between 0 and 1")
            return Decimal(0)

    terms = OfferTerms(
        offer_validity_months=integer("offer_validity_months"),
        participation_guarantee_rate=rate("participation_guarantee_rate"),
        participation_guarantee_extra_days=integer("participation_guarantee_extra_days"),
        performance_guarantee_rate=rate("performance_guarantee_rate"),
        performance_guarantee_extra_months=integer("performance_guarantee_extra_months"),
    )
    return terms if len(problems) == n else None


def _parse_requirements(
    data: bytes, subjects: frozenset[str], doc_types: frozenset[str], problems: list[str]
) -> tuple[Requirement, ...]:
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as e:
        problems.append(f"{REQUIREMENTS}: not UTF-8 ({e})")
        return ()
    reader = csv.DictReader(text.splitlines())
    if tuple(reader.fieldnames or ()) != COLUMNS:
        problems.append(f"{REQUIREMENTS}: header must be {','.join(COLUMNS)}")
        return ()
    out: list[Requirement] = []
    seen: set[str] = set()
    for line, row in enumerate(reader, start=2):
        def bad(column: str, why: str, line: int = line) -> None:
            problems.append(f"{REQUIREMENTS} line {line}, column `{column}`: {why}")

        if None in row or any(v is None for v in row.values()):
            bad("*", "wrong number of fields")
            continue
        rid = row["id"].strip()
        if not re.fullmatch(r"R\d+", rid):
            bad("id", f"{rid!r} is not R<number>")
        elif rid in seen:
            bad("id", f"{rid} appears twice")
        seen.add(rid)
        for column in ("requirement", "stage", "issuer", "source_section"):
            if not row[column].strip():
                bad(column, "empty")
        stages = tuple(_STAGE.findall(row["stage"]))
        if row["stage"].strip() and not stages:
            bad("stage", f"no stage code in {row['stage']!r}")
        doc_type = row["doc_type"].strip()
        if doc_type not in doc_types:
            bad("doc_type", f"{doc_type!r} is not a document type of the sector or jurisdiction pack")
        applies = tuple(s.strip() for s in row["applies_to"].split(",") if s.strip())
        if not applies or any(s not in subjects for s in applies):
            bad("applies_to", f"{row['applies_to']!r}: allowed values are {', '.join(sorted(subjects))}")
        validity = _parse_validity(row, bad)
        espd = row["espd_criterion"].strip() or None
        if espd is not None and not _UUID.match(espd):
            bad("espd_criterion", f"{espd!r} is not a lowercase UUID")
        if validity is not None:
            out.append(Requirement(
                id=rid, text=row["requirement"].strip(), stages=stages, issuer=row["issuer"].strip(),
                validity_text=row["validity"].strip(), source_section=row["source_section"].strip(),
                doc_type=doc_type, applies_to=applies, validity=validity, espd_criterion=espd,
            ))
    if not out and not problems:
        problems.append(f"{REQUIREMENTS}: no rows")
    return tuple(out)


def _parse_validity(row: dict[str, str], bad: Callable[[str, str], None]) -> Validity | None:
    try:
        kind = ValidityKind(row["validity_kind"].strip())
    except ValueError:
        bad("validity_kind", f"{row['validity_kind']!r}: allowed values are {', '.join(ValidityKind)}")
        return None
    needs_amount, needs_anchor = _NEEDS[kind]
    amount_s, unit_s, anchor_s = (row[c].strip() for c in ("validity_amount", "validity_unit", "validity_anchor"))
    ok = True
    amount = unit = anchor = None
    if needs_amount:
        if not amount_s.isdigit() or int(amount_s) == 0:
            bad("validity_amount", f"{kind} needs a positive integer")
            ok = False
        else:
            amount = int(amount_s)
        try:
            unit = Unit(unit_s)
        except ValueError:
            bad("validity_unit", f"{kind} needs one of {', '.join(Unit)}")
            ok = False
        if kind is ValidityKind.VALID_UNTIL and unit is Unit.WORKING_DAYS:
            bad("validity_unit", "valid_until counts days or months, not working days")
            ok = False
    elif amount_s or unit_s:
        bad("validity_amount", f"{kind} takes no amount or unit")
        ok = False
    if needs_anchor:
        try:
            anchor = Anchor(anchor_s)
        except ValueError:
            bad("validity_anchor", f"{kind} needs one of {', '.join(Anchor)}")
            ok = False
    elif anchor_s:
        bad("validity_anchor", f"{kind} takes no anchor")
        ok = False
    return Validity(kind, amount, unit, anchor) if ok else None

