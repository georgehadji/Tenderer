"""No tables of its own: data-subject requests act on the records of engagements and alerts (§6.4, §10.8)."""

from tenderer.apps.engagements.models import Client


class DataSubject(Client):
    """Clients, seen as data subjects: export and erasure live on this admin screen, for the admin role only."""
    class Meta:
        proxy = True
        verbose_name = "data subject"
