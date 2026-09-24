"""core/catalog: the current tender loads; any invalid row or field refuses the whole tender (S1)."""

import shutil

import pytest

from tenderer.core.catalog.packs import Packs
from tenderer.core.catalog.tender import Anchor, TenderLoadError, Unit, ValidityKind, load_tender
from tenderer.shell.packs import PACKS

from .conftest import TENDER_DIR


def test_current_tender_loads(tender):
    assert tender.id == "pkm-meth-student-transport-dsa-2026"
    assert (tender.sector, tender.jurisdiction, tender.lifecycle, tender.offer_shape) == (
        "taxi_student_transport", "gr", "dps", "discount_on_reference")
    assert [r.id for r in tender.requirements] == [f"R{n}" for n in range(1, 27)]
    r18 = tender.requirement("R18")
    assert (r18.validity.kind, r18.validity.amount, r18.validity.unit, r18.validity.anchor) == (
        ValidityKind.ISSUED_WITHIN, 30, Unit.WORKING_DAYS, Anchor.SUBMISSION)
    assert tender.requirement("R21").applies_to == ("driver", "escort")
    assert tender.requirement("R4").stages == ("Α2", "Β9")
    assert tender.requirement("R23").stages == ("Γ",)


def test_version_is_commit_plus_content_hash(tender):
    commit, digest = tender.version.split("+")
    assert commit == "0" * 12 and len(digest) == 12


def test_loading_is_deterministic(tender):
    assert load_tender(TENDER_DIR, PACKS, commit="0" * 40) == tender


@pytest.fixture
def copy(tmp_path):
    dst = tmp_path / "t"
    shutil.copytree(TENDER_DIR, dst)
    return dst


def edit(path, old, new):
    text = path.read_text(encoding="utf-8")
    assert old in text
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def problems(path, packs=PACKS):
    with pytest.raises(TenderLoadError) as e:
        load_tender(path, packs, commit="x")
    return e.value.problems


def test_invalid_row_names_line_and_column(copy):
    edit(copy / "requirements.csv", "issued_within,3,months", "issued_within,three,months")
    assert problems(copy) == [
        "requirements.csv line 13, column `validity_amount`: issued_within needs a positive integer"]


def test_every_problem_is_reported_at_once(copy):
    edit(copy / "requirements.csv", "criminal_record_extract,client", "no_such_doc,spaceship")
    edit(copy / "requirements.csv", "R2,", "R1,")
    got = problems(copy)
    assert any("line 3, column `id`: R1 appears twice" in p for p in got)
    assert any("`doc_type`: 'no_such_doc'" in p for p in got)
    assert any("`applies_to`: 'spaceship'" in p for p in got)


def test_unregistered_pack_refuses_the_tender(copy):
    assert "tender.toml: `sector` = 'taxi_student_transport' is not registered" in problems(copy, Packs(
        jurisdictions=PACKS.jurisdictions, lifecycles=PACKS.lifecycles, offer_shapes=PACKS.offer_shapes))


def test_float_rate_is_refused(copy):
    edit(copy / "tender.toml", 'participation_guarantee_rate = "0.002"', "participation_guarantee_rate = 0.002")
    assert problems(copy) == [
        "tender.toml: offer.participation_guarantee_rate must be a decimal string between 0 and 1"]


def test_wrong_header_is_refused(copy):
    edit(copy / "requirements.csv", ",espd_criterion", "")
    assert "requirements.csv: header must be" in problems(copy)[0]


def test_valid_until_in_working_days_is_refused(copy):
    edit(copy / "requirements.csv", "valid_until,2,months", "valid_until,2,working_days")
    assert "working days" in problems(copy)[0]
