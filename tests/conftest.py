import pytest
from django_otp import DEVICE_ID_SESSION_KEY
from django_otp.plugins.otp_totp.models import TOTPDevice

from tenderer.core.catalog.tender import Tender, load_tender
from tenderer.shell.packs import PACKS, REPO

TENDER_DIR = REPO / "tenders" / "pkm-meth-student-transport-dsa-2026"


@pytest.fixture(scope="session")
def tender() -> Tender:
    return load_tender(TENDER_DIR, PACKS, commit="0" * 40)


def verified(client, user):
    """Sign `user` in with a verified second factor, as the OTP admin site requires (§10.2)."""
    device = TOTPDevice.objects.create(user=user, name="test", confirmed=True)
    client.force_login(user)
    session = client.session
    session[DEVICE_ID_SESSION_KEY] = device.persistent_id
    session.save()
    return client


@pytest.fixture
def admin_client(client, admin_user):
    """pytest-django's fixture, plus the second factor."""
    return verified(client, admin_user)
