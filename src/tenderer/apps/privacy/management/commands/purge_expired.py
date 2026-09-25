"""Cron, daily: `manage.py purge_expired` (docs/architecture.md §6.4, §10.8)."""

from typing import Any

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from tenderer.apps.audit.api import correlated
from tenderer.apps.privacy import api


class Command(BaseCommand):
    help = "Erase clients whose retention date has passed; set the date for clients whose engagements all ended."

    def handle(self, *args: Any, **options: Any) -> None:
        with correlated():
            try:
                erased, scheduled = api.purge_expired(timezone.localdate())
            except RuntimeError as e:
                raise CommandError(str(e)) from e
        self.stdout.write(f"erased {erased}, retention set for {scheduled}")
