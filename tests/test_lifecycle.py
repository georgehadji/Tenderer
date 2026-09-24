"""core/lifecycle: every transition of every template, including illegal ones, and the DRAFT → CHECKED guard."""

import pytest

from tenderer.core.lifecycle.machine import GuardContext, Machine, Moved, Refusal, Refused, Transition, fire
from tenderer.core.lifecycle.templates import BID, DPS, OPEN, TEMPLATES
from tenderer.core.rules.checklist import Status

CLEAN = GuardContext(offer_errors=(None, None), gonogo_recorded=True,
                     offer_stage_statuses=(Status.SATISFIED, Status.NOT_APPLICABLE))

LEGAL = [  # (machine, state, event, target)
    (DPS.engagement, "ONBOARDING", "registered", "REGISTERED"),
    (DPS.engagement, "REGISTERED", "applied", "APPLIED"),
    (DPS.engagement, "APPLIED", "admitted", "ADMITTED"),
    (DPS.engagement, "APPLIED", "rejected", "REJECTED"),
    (DPS.engagement, "ADMITTED", "contracted", "CONTRACTED"),
    (DPS.engagement, "ADMITTED", "closed", "CLOSED"),
    (DPS.engagement, "CONTRACTED", "closed", "CLOSED"),
    (OPEN.engagement, "PREPARING", "submitted", "SUBMITTED"),
    (OPEN.engagement, "SUBMITTED", "awarded", "AWARDED"),
    (OPEN.engagement, "SUBMITTED", "not_awarded", "NOT_AWARDED"),
    (OPEN.engagement, "AWARDED", "contracted", "CONTRACTED"),
    (OPEN.engagement, "CONTRACTED", "closed", "CLOSED"),
    (BID, "DRAFT", "check", "CHECKED"),
    (BID, "DRAFT", "abandon", "ABANDONED"),
    (BID, "CHECKED", "client_submitted", "CLIENT_SUBMITTED"),
    (BID, "CHECKED", "reopen", "DRAFT"),
    (BID, "CHECKED", "abandon", "ABANDONED"),
    (BID, "CLIENT_SUBMITTED", "awarded", "AWARDED"),
    (BID, "CLIENT_SUBMITTED", "not_awarded", "NOT_AWARDED"),
]
LEGAL += [(t.engagement, s, "withdraw", "WITHDRAWN") for t in (DPS, OPEN) for s in t.engagement.states
          if not t.engagement.final(s)]


@pytest.mark.parametrize(("machine", "state", "event", "target"), LEGAL)
def test_legal_transitions(machine, state, event, target):
    assert fire(machine, state, event, CLEAN) == Moved(target)


def test_every_other_pair_is_illegal():
    """Table-driven: each (state, event) not listed above is refused."""
    legal = {(id(m), s, e) for m, s, e, _ in LEGAL}
    machines = {id(t.engagement): t.engagement for t in TEMPLATES.values()} | {id(BID): BID}
    events = {e for m in machines.values() for s in m.states for e in m.events(s)}
    checked = 0
    for mid, m in machines.items():
        for s in m.states:
            for e in events:
                if (mid, s, e) not in legal:
                    assert fire(m, s, e, CLEAN) == Refused(Refusal.ILLEGAL_EVENT, f"{e} from {s}")
                    checked += 1
    assert checked > 50


def test_final_states_accept_nothing_not_even_withdraw():
    assert isinstance(fire(DPS.engagement, "CLOSED", "withdraw"), Refused)
    assert isinstance(fire(DPS.engagement, "NOWHERE", "withdraw"), Refused)


@pytest.mark.parametrize(("context", "failed"), [
    (GuardContext(), "offer_valid, gonogo_recorded, offer_stage_clear"),
    (GuardContext(offer_errors=(None, "form_price_wrong"), gonogo_recorded=True,
                  offer_stage_statuses=(Status.SATISFIED,)), "offer_valid"),
    (GuardContext(offer_errors=(None,), gonogo_recorded=False, offer_stage_statuses=(Status.SATISFIED,)),
     "gonogo_recorded"),
    (GuardContext(offer_errors=(None,), gonogo_recorded=True, offer_stage_statuses=(Status.UNKNOWN,)),
     "offer_stage_clear"),
    (GuardContext(offer_errors=(None,), gonogo_recorded=True, offer_stage_statuses=(Status.NOT_SATISFIED,)),
     "offer_stage_clear"),
    (GuardContext(offer_errors=(), gonogo_recorded=True, offer_stage_statuses=(Status.SATISFIED,)), "offer_valid"),
])
def test_h7_draft_to_checked_needs_every_guard(context, failed):
    assert fire(BID, "DRAFT", "check", context) == Refused(Refusal.GUARD_FAILED, failed)


def test_unknown_guard_or_state_fails_at_build_time():
    with pytest.raises(ValueError, match="unknown guard"):
        Machine("A", {"A": {"go": Transition("A", ("no_such_guard",))}}, {})
    with pytest.raises(ValueError, match="without a row"):
        Machine("A", {"A": {"go": Transition("B")}}, {})
    with pytest.raises(ValueError, match="initial"):
        Machine("Z", {"A": {}}, {})
