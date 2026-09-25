"""Cron, every 5 minutes: `manage.py send_outbox; manage.py heartbeat` (docs/architecture.md §6.5, AD11)."""

from typing import Any

from django.core.management.base import BaseCommand, CommandError

from tenderer.apps.alerts import api


class Command(BaseCommand):
    help = "Send every due notification of the outbox once; failed ones are retried on the next run."

    def handle(self, *args: Any, **options: Any) -> None:
        sent, failed = api.send_due()
        self.stdout.write(f"sent {sent}, failed {failed}")
        if failed:
            raise CommandError(f"{failed} notification(s) failed; they stay in the outbox for the next run")
