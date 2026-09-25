"""Dead man's switch (AD11, S5): ping the external monitor only while the outbox keeps up. A stopped scheduler,
a stopped sender or a provider that keeps failing all end the pings, and the monitor pages the operator."""

import urllib.request
from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from tenderer.apps.alerts import api


class Command(BaseCommand):
    help = "Ping ALERTS_HEARTBEAT_URL if no notification is overdue; otherwise fail without pinging."

    def handle(self, *args: Any, **options: Any) -> None:
        url = settings.ALERTS_HEARTBEAT_URL
        if not url.startswith("https://"):
            raise CommandError("ALERTS_HEARTBEAT_URL must be an https:// URL")
        late = api.backlog()
        if late:
            raise CommandError(f"{late} notification(s) unsent for more than {api.MAX_LAG}: heartbeat withheld")
        with urllib.request.urlopen(url, timeout=10) as response:  # noqa: S310 - https only, checked above
            response.read()
        self.stdout.write("heartbeat sent")
