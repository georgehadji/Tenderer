"""Audit app: sign-in events, and the roles `operator`, `reviewer`, `admin` kept in sync after every migrate
(docs/architecture.md §10.2). Listed last in INSTALLED_APPS, so every other app's permissions exist by then."""

from typing import Any

from django.apps import AppConfig
from django.db.models.signals import post_migrate

# role -> (app labels, permission verbs). One person may hold every role until a second person joins (§10.2).
ROLES: dict[str, tuple[tuple[str, ...], tuple[str, ...]]] = {
    "operator": (("engagements", "alerts", "documents"), ("view", "add", "change")),
    "reviewer": (("engagements", "alerts", "documents", "audit"), ("view",)),
    "admin": (("engagements", "alerts", "documents", "privacy", "audit", "auth", "otp_totp", "otp_static"),
              ("view", "add", "change", "delete")),
}


def sync_roles(**kwargs: Any) -> None:
    from django.contrib.auth.models import Group, Permission

    for name, (app_labels, verbs) in ROLES.items():
        group, _ = Group.objects.get_or_create(name=name)
        group.permissions.set(Permission.objects.filter(content_type__app_label__in=app_labels,
                                                        codename__regex=rf"^({'|'.join(verbs)})_"))


def _signed_in(sender: Any, request: Any, user: Any, **kwargs: Any) -> None:
    from tenderer.apps.audit import api
    api.record("auth.signed_in", user)


def _signed_out(sender: Any, request: Any, user: Any, **kwargs: Any) -> None:
    from tenderer.apps.audit import api
    api.record("auth.signed_out", user if user is not None else "")


def _sign_in_failed(sender: Any, credentials: Any, request: Any = None, **kwargs: Any) -> None:
    from tenderer.apps.audit import api
    api.record("auth.sign_in_failed")  # no username: it may be personal data or a mistyped password


class AuditConfig(AppConfig):
    name = "tenderer.apps.audit"
    label = "audit"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self) -> None:
        from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed

        post_migrate.connect(sync_roles, sender=self)
        user_logged_in.connect(_signed_in, dispatch_uid="audit_signed_in")
        user_logged_out.connect(_signed_out, dispatch_uid="audit_signed_out")
        user_login_failed.connect(_sign_in_failed, dispatch_uid="audit_sign_in_failed")
