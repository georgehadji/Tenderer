"""Procedure lifecycles as data, evaluated by one pure function (docs/architecture.md §6.14, AD16).

A template is two transition tables, one for the engagement (client × tender) and one for each bid.
Guards are named by id and resolved when a template is built, so a typo fails at import, not at runtime.
"""

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from enum import StrEnum

from tenderer.core.rules.checklist import Status


@dataclass(frozen=True)
class GuardContext:
    """What the guards may look at: recorded results, never live inputs (S4)."""
    offer_errors: tuple[str | None, ...] | None = None  # one entry per offer line; None = not checked yet
    gonogo_recorded: bool = False
    offer_stage_statuses: tuple[Status, ...] | None = None  # checklist of the offer stage; None = not evaluated


Guard = Callable[[GuardContext], bool]

GUARDS: dict[str, Guard] = {
    # DRAFT → CHECKED (§6.4, H2, H7)
    "offer_valid": lambda c: bool(c.offer_errors) and all(e is None for e in c.offer_errors or ()),
    "gonogo_recorded": lambda c: c.gonogo_recorded,
    "offer_stage_clear": lambda c: bool(c.offer_stage_statuses) and all(
        s in (Status.SATISFIED, Status.NOT_APPLICABLE) for s in c.offer_stage_statuses or ()),
}


@dataclass(frozen=True)
class Transition:
    target: str
    guards: tuple[str, ...] = ()


@dataclass(frozen=True)
class Machine:
    initial: str
    table: Mapping[str, Mapping[str, Transition]]  # state -> event -> transition
    any_state: Mapping[str, Transition]  # events allowed from every non-final state (e.g. withdraw)

    def __post_init__(self) -> None:
        targets = {t.target for events in self.table.values() for t in events.values()}
        targets |= {t.target for t in self.any_state.values()}
        unknown = {g for t in self._transitions() for g in t.guards} - GUARDS.keys()
        if unknown:
            raise ValueError(f"unknown guard id(s): {sorted(unknown)}")
        if self.initial not in self.table:
            raise ValueError(f"initial state {self.initial!r} has no row")
        missing = targets - self.table.keys()
        if missing:
            raise ValueError(f"target state(s) without a row: {sorted(missing)}")

    @property
    def states(self) -> frozenset[str]:
        return frozenset(self.table)

    def final(self, state: str) -> bool:
        return not self.table[state]

    def events(self, state: str) -> tuple[str, ...]:
        extra = () if self.final(state) else tuple(self.any_state)
        return tuple(self.table[state]) + extra

    def _transitions(self) -> list[Transition]:
        return [t for events in self.table.values() for t in events.values()] + list(self.any_state.values())


@dataclass(frozen=True)
class Template:
    id: str
    engagement: Machine
    bid: Machine


class Refusal(StrEnum):
    UNKNOWN_STATE = "unknown_state"
    ILLEGAL_EVENT = "illegal_event"
    GUARD_FAILED = "guard_failed"


@dataclass(frozen=True)
class Moved:
    target: str


@dataclass(frozen=True)
class Refused:
    reason: Refusal
    detail: str


NO_FACTS = GuardContext()


def fire(machine: Machine, state: str, event: str, context: GuardContext = NO_FACTS) -> Moved | Refused:
    if state not in machine.table:
        return Refused(Refusal.UNKNOWN_STATE, state)
    transition = machine.table[state].get(event)
    if transition is None and not machine.final(state):
        transition = machine.any_state.get(event)
    if transition is None:
        return Refused(Refusal.ILLEGAL_EVENT, f"{event} from {state}")
    failed = [g for g in transition.guards if not GUARDS[g](context)]
    if failed:
        return Refused(Refusal.GUARD_FAILED, ", ".join(failed))
    return Moved(transition.target)
