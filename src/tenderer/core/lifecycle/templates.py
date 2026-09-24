"""Transition tables per procedure type. Data: add a template when a real tender needs one (§6.14)."""

from tenderer.core.lifecycle.machine import Machine, Template
from tenderer.core.lifecycle.machine import Transition as T

# One bid per invitation (dps) or per procedure (open). The client submits, never us (S3).
# A new offer check after CHECKED sends the bid back to DRAFT (`reopen`), so a changed offer is re-checked.
BID = Machine(
    initial="DRAFT",
    table={
        "DRAFT": {"check": T("CHECKED", ("offer_valid", "gonogo_recorded", "offer_stage_clear")),
                  "abandon": T("ABANDONED")},
        "CHECKED": {"client_submitted": T("CLIENT_SUBMITTED"), "reopen": T("DRAFT"), "abandon": T("ABANDONED")},
        "CLIENT_SUBMITTED": {"awarded": T("AWARDED"), "not_awarded": T("NOT_AWARDED")},
        "AWARDED": {},
        "NOT_AWARDED": {},
        "ABANDONED": {},
    },
    any_state={},
)

# Dynamic purchasing system: admission once, then a call-off per invitation (Law 4412/2016 Art. 33; §3.1).
DPS = Template(
    id="dps",
    engagement=Machine(
        initial="ONBOARDING",
        table={
            "ONBOARDING": {"registered": T("REGISTERED")},  # ΕΣΗΔΗΣ registration done by the client
            "REGISTERED": {"applied": T("APPLIED")},  # ΕΕΕΣ submitted by the client
            "APPLIED": {"admitted": T("ADMITTED"), "rejected": T("REJECTED")},
            "ADMITTED": {"contracted": T("CONTRACTED"), "closed": T("CLOSED")},
            "CONTRACTED": {"closed": T("CLOSED")},
            "CLOSED": {},
            "REJECTED": {},
            "WITHDRAWN": {},
        },
        any_state={"withdraw": T("WITHDRAWN")},
    ),
    bid=BID,
)

# One-stage open procedure: the engagement ends with the award decision of its single bid.
OPEN = Template(
    id="open",
    engagement=Machine(
        initial="PREPARING",
        table={
            "PREPARING": {"submitted": T("SUBMITTED")},
            "SUBMITTED": {"awarded": T("AWARDED"), "not_awarded": T("NOT_AWARDED")},
            "AWARDED": {"contracted": T("CONTRACTED")},
            "CONTRACTED": {"closed": T("CLOSED")},
            "NOT_AWARDED": {},
            "CLOSED": {},
            "WITHDRAWN": {},
        },
        any_state={"withdraw": T("WITHDRAWN")},
    ),
    bid=BID,
)

TEMPLATES: dict[str, Template] = {t.id: t for t in (DPS, OPEN)}
ENGAGEMENT_STATES = frozenset().union(*(t.engagement.states for t in TEMPLATES.values()))
BID_STATES = frozenset().union(*(t.bid.states for t in TEMPLATES.values()))
