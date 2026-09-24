"""apps/engagements against PostgreSQL: validation at every write, state only through the transition table,
the DRAFT → CHECKED guard (H7), and a schema review for prohibited data (AD5). Synthetic data only."""

import datetime as dt
from decimal import Decimal as D

import pytest
from django.apps import apps
from django.core.exceptions import ValidationError
from django.db import IntegrityError, models

from tenderer.apps.engagements import api
from tenderer.apps.engagements.models import Client, DocumentRecord, Engagement, Resource
from tenderer.core.catalog.tender import Anchor
from tenderer.core.pricing.gonogo import Costs, Line, go_no_go
from tenderer.core.pricing.money import Money
from tenderer.core.pricing.offer import OfferLine, Route, offer_price, validate_offer
from tenderer.core.rules.checklist import DocumentFact, Status, evaluate
from tenderer.shell.packs import PACKS

pytestmark = pytest.mark.django_db


@pytest.fixture
def client_():
    return Client.objects.create(name="Πελάτης Δοκιμής", tax_id="123456783", phone="6912345678")


def vehicle(client, plate="nbk 1234", **extra):
    return Resource.objects.create(client=client, sector="taxi_student_transport", kind="vehicle", label="όχημα 1",
                                   attributes={"plate": plate, "seats": 4, "base_municipality": "Θεσσαλονίκη", **extra})


def test_client_normalised_and_shown_with_last_tax_id_digits(client_):
    assert client_.phone == "+306912345678"
    assert str(client_) == "Πελάτης Δοκιμής (ΑΦΜ …783)"


def test_bad_tax_id_cannot_be_saved():
    with pytest.raises(ValidationError, match="check digit"):
        Client.objects.create(name="x", tax_id="123456784")


def test_resource_attributes_follow_the_sector_schema(client_):
    v = vehicle(client_)
    assert v.attributes["plate"] == "ΝΒΚ-1234" and v.schema_version == 1
    with pytest.raises(ValidationError, match="seats"):
        vehicle(client_, plate="ΝΒΚ-9999", seats=0)
    with pytest.raises(ValidationError, match="Additional properties"):
        vehicle(client_, plate="ΝΒΚ-9998", criminal_record="clean")
    with pytest.raises(ValidationError, match="another vehicle"):
        vehicle(client_, plate="ΝΒΚ 1234")
    with pytest.raises(ValidationError, match="not a resource kind"):
        Resource.objects.create(client=client_, sector="taxi_student_transport", kind="boat", label="x", attributes={})


def test_driver_dates_are_checked(client_):
    with pytest.raises(ValidationError, match="date"):
        Resource.objects.create(client=client_, sector="taxi_student_transport", kind="driver", label="οδηγός 1",
                                attributes={"display_name": "Οδηγός", "licence_valid_until": "31/12/2027"})


def test_document_dates_constraint_holds_in_the_database(client_):
    with pytest.raises((ValidationError, IntegrityError)):
        DocumentRecord.objects.create(client=client_, doc_type="tax_clearance", issued_on=dt.date(2026, 5, 1),
                                      valid_until=dt.date(2026, 4, 1))
    with pytest.raises(IntegrityError):  # bulk paths skip save(); the CHECK still binds them
        DocumentRecord.objects.bulk_create([DocumentRecord(
            client=client_, doc_type="tax_clearance", issued_on=dt.date(2026, 5, 1), valid_until=dt.date(2026, 4, 1))])


def test_engagement_moves_only_through_the_table(client_, tender):
    e = api.open_engagement(client_, tender)
    assert (e.lifecycle, e.state, e.tender_version) == ("dps", "ONBOARDING", tender.version)
    with pytest.raises(api.TransitionRefused, match="illegal_event"):
        api.fire_engagement(e, "admitted")
    for event in ("registered", "applied", "admitted"):
        e = api.fire_engagement(e, event)
    assert e.state == "ADMITTED"
    with pytest.raises(IntegrityError):
        Engagement.objects.filter(pk=e.pk).update(state="MADE_UP")  # unknown states refused by the database


def _clean_inputs(tender):
    route = Route("G26-0703-Τ2", Money(D("51.18")), Money(D("26869.50")), 525, client_said_yes=True)
    price = offer_price(route.reference, 3)
    checks = validate_offer([OfferLine(route.code, 3, price, price, 1)], {route.code: route})
    result = go_no_go(route.reference, Costs((Line("fuel", D("10")),), ()), D("166.25"))
    offer_stage = [r for r in tender.requirements if {"Β4", "Β5"} & set(r.stages)]
    facts = [DocumentFact(r.doc_type, manual_status=Status.SATISFIED, issued_on=dt.date(2026, 8, 10),
                          valid_until=dt.date(2027, 12, 31)) for r in offer_stage]
    items = evaluate(offer_stage, facts, {Anchor.SUBMISSION: dt.date(2026, 8, 19),
                                          Anchor.INVITATION_SENT: dt.date(2026, 8, 7),
                                          Anchor.OFFER_VALIDITY_END: dt.date(2027, 8, 20)})
    return route, checks, result, items


def test_h7_bid_reaches_checked_only_with_every_record(client_, tender):
    e = api.open_engagement(client_, tender)
    bid = api.open_bid(e, "ΑΔΑΜ-TEST-1")
    route, checks, result, items = _clean_inputs(tender)
    with pytest.raises(api.TransitionRefused, match="offer_valid, gonogo_recorded, offer_stage_clear"):
        api.fire_bid(bid, "check")
    bid = api.record_offer_check(bid, checks)
    bid = api.record_gonogo(bid, route.code, result, ["fuel_no_adjustment"])
    with pytest.raises(api.TransitionRefused, match="offer_stage_clear"):
        api.fire_bid(bid, "check")
    bid = api.record_checklist(bid, items)
    assert all(i.status in (Status.SATISFIED, Status.NOT_APPLICABLE) for i in items), items
    bid = api.fire_bid(bid, "check")
    assert bid.state == "CHECKED"
    # a changed offer is checked again
    bad = validate_offer([OfferLine(route.code, D("3.5"), None, None, 1)], {route.code: route})
    bid = api.record_offer_check(bid, bad)
    assert bid.state == "DRAFT"
    with pytest.raises(api.TransitionRefused, match="offer_valid"):
        api.fire_bid(bid, "check")


PROHIBITED = ("criminal", "health", "medical", "password", "credential", "secret", "signature", "exclusion_answer",
              "taxisnet", "pin", "otp")


def test_schema_review_no_field_for_prohibited_data():
    """AD5 and docs/architecture.md §8: no model and no resource schema has a place for prohibited data."""
    for model in apps.get_app_config("engagements").get_models():
        for field in model._meta.get_fields():
            assert not isinstance(field, models.FileField), f"{model.__name__}.{field.name} stores a file"
            assert not any(word in field.name.lower() for word in PROHIBITED), f"{model.__name__}.{field.name}"
    for sector in PACKS.sectors.values():
        for kind, schema in sector.resource_kinds.items():
            for name in schema["properties"]:  # type: ignore[index]
                assert not any(word in name.lower() for word in PROHIBITED), f"{sector.id}.{kind}.{name}"
