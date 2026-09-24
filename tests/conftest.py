import pytest

from tenderer.core.catalog.tender import Tender, load_tender
from tenderer.shell.packs import PACKS, REPO

TENDER_DIR = REPO / "tenders" / "pkm-meth-student-transport-dsa-2026"


@pytest.fixture(scope="session")
def tender() -> Tender:
    return load_tender(TENDER_DIR, PACKS, commit="0" * 40)
