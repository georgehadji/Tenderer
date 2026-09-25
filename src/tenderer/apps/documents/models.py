"""No tables of its own: documents are rendered from recorded data (docs/architecture.md §6.6)."""

from tenderer.apps.engagements.models import Bid


class ClientPlan(Bid):
    """The bids, seen as the plans the operator previews and sends to the client."""
    class Meta:
        proxy = True
        verbose_name = "client plan"
