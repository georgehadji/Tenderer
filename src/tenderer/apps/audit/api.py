"""The only way to write audit events. Every module calls `record`; the request middleware and each job set the
correlation id and the actor, so callers never pass them (docs/architecture.md §6.7)."""

import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any

from django.db import models

from tenderer.apps.audit.models import AuditEvent

_correlation: ContextVar[str] = ContextVar("correlation_id", default="")
_actor: ContextVar[int | None] = ContextVar("actor_id", default=None)


@contextmanager
def correlated(actor_id: int | None = None, correlation_id: str | None = None) -> Iterator[str]:
    """Scope of one request or one job run: every event inside it shares one correlation id."""
    cid = correlation_id or uuid.uuid4().hex
    tokens = (_correlation.set(cid), _actor.set(actor_id))
    try:
        yield cid
    finally:
        _correlation.reset(tokens[0])
        _actor.reset(tokens[1])


def ref(obj: models.Model) -> str:
    return f"{obj._meta.label_lower}:{obj.pk}"


def record(action: str, target: models.Model | str = "", details: dict[str, Any] | None = None,
           tenant_id: int | None = None) -> AuditEvent:
    """One event. `details` must hold ids and codes only; `target` is a model instance or an "app.model:pk"."""
    object_ref = target if isinstance(target, str) else ref(target)
    tenant = tenant_id if tenant_id is not None else getattr(target, "tenant_id", 1)
    return AuditEvent.objects.create(action=action, object_ref=object_ref, details=details or {}, tenant_id=tenant,
                                     actor_id=_actor.get(), correlation_id=_correlation.get() or uuid.uuid4().hex)
