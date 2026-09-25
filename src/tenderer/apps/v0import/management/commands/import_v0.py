"""`manage.py import_v0 <file.xlsx> --client <id> --tender <id>`: one v0 workbook copy into v1 (build-plan M8)."""

from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand, CommandError, CommandParser

from tenderer.apps.audit.api import correlated
from tenderer.apps.engagements import api as engagements
from tenderer.apps.engagements.models import Client
from tenderer.apps.v0import import api


class Command(BaseCommand):
    help = "Import one v0 workbook copy and print the reconciliation report; any difference rolls it back."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("path", type=Path)
        parser.add_argument("--client", type=int, required=True, help="client id in v1 (create the client first)")
        parser.add_argument("--tender", required=True, choices=engagements.tender_ids())
        parser.add_argument("--accept-differences", action="store_true",
                            help="keep the import although v0 and v1 disagree (say why in the audit log)")

    def handle(self, *args: Any, **options: Any) -> None:
        client = Client.objects.filter(pk=options["client"]).first()
        if client is None:
            raise CommandError(f"no client {options['client']}")
        with correlated():
            try:
                report = api.import_workbook(options["path"], client, engagements.load(options["tender"]),
                                             accept_differences=options["accept_differences"])
            except api.Differences as e:
                self.stdout.write(e.report.text())
                raise CommandError(f"{e}; nothing was imported") from e
            except api.WorkbookError as e:
                raise CommandError(str(e)) from e
        self.stdout.write(report.text())
        self.stdout.write("imported")
