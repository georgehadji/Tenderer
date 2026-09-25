"""Django settings, 12-factor: every secret and host comes from the environment (docs/architecture.md §6.10).

Production is the default. Development sets DJANGO_DEBUG=1 and a local database; real client data never
leaves production (§9).
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[3]

SECRET_KEY = os.environ["DJANGO_SECRET_KEY"]
DEBUG = os.environ.get("DJANGO_DEBUG") == "1"
ALLOWED_HOSTS = [h for h in os.environ.get("DJANGO_ALLOWED_HOSTS", "").split(",") if h]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "tenderer.apps.engagements",
    "tenderer.apps.alerts",
    "tenderer.apps.documents",
    "tenderer.apps.privacy",
    "tenderer.apps.v0import",
    "django_otp",
    "django_otp.plugins.otp_totp",
    "django_otp.plugins.otp_static",  # sealed break-glass codes (§10.2)
    "tenderer.apps.audit",  # last: its post_migrate hook sets the roles from every other app's permissions
]

TENDERER_PACKS = "tenderer.shell.packs.PACKS"  # apps reach packs only through this registry (§5.2 rule 7)
TENDERER_TENDERS_DIR = BASE_DIR / "tenders"  # tender modules; documents reads their declaration drafts
TENDERER_COMMIT = os.environ.get("TENDERER_COMMIT", "uncommitted")  # part of Tender.version (S4); set at build

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "tenderer.shell.middleware.SecurityHeadersMiddleware",  # CSP, Permissions-Policy (§10.3)
    "whitenoise.middleware.WhiteNoiseMiddleware",  # admin static files from the one container (§9)
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django_otp.middleware.OTPMiddleware",
    "tenderer.apps.audit.middleware.CorrelationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "tenderer.shell.urls"
WSGI_APPLICATION = "tenderer.shell.wsgi.application"

TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "APP_DIRS": True,
    "OPTIONS": {"context_processors": [
        "django.template.context_processors.request",
        "django.contrib.auth.context_processors.auth",
        "django.contrib.messages.context_processors.messages",
    ]},
}]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("PGDATABASE", "tenderer"),
        "USER": os.environ.get("PGUSER", "tenderer"),
        "PASSWORD": os.environ.get("PGPASSWORD", ""),
        "HOST": os.environ.get("PGHOST", "localhost"),
        "PORT": os.environ.get("PGPORT", "5432"),
        "CONN_MAX_AGE": 60,
        "OPTIONS": {"sslmode": os.environ.get("PGSSLMODE", "require")},
    }
}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LANGUAGE_CODE = "el"
TIME_ZONE = "Europe/Athens"
USE_I18N = True
USE_TZ = True  # stored in UTC, shown in Europe/Athens (§6.2)

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedStaticFilesStorage"},
}

# Transport and cookies (ASVS L2, §10). The app runs behind a TLS-terminating proxy.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = not DEBUG
SECURE_HSTS_SECONDS = 0 if DEBUG else 31_536_000
SECURE_HSTS_INCLUDE_SUBDOMAINS = not DEBUG
SECURE_HSTS_PRELOAD = not DEBUG
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_AGE = 8 * 60 * 60
X_FRAME_OPTIONS = "DENY"

# E-mail (§6.5, §9): an EU transactional provider over SMTP with TLS. The sending domain publishes SPF, DKIM and
# DMARC p=reject (DNS, outside this code).
EMAIL_HOST = os.environ.get("EMAIL_HOST", "localhost")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = True
EMAIL_TIMEOUT = 30
DEFAULT_FROM_EMAIL = os.environ["DJANGO_DEFAULT_FROM_EMAIL"]
SERVER_EMAIL = DEFAULT_FROM_EMAIL

# Retention (§10.8): months after the last engagement ends; set with the lawyer. purge_expired refuses without it.
_retention = os.environ.get("TENDERER_RETENTION_MONTHS")
TENDERER_RETENTION_MONTHS = int(_retention) if _retention else None

# Dead man's switch (AD11): the external monitor's ping URL; `manage.py heartbeat` refuses to run without it.
ALERTS_HEARTBEAT_URL = os.environ.get("ALERTS_HEARTBEAT_URL", "")

# Logs to stdout for the platform, through a filter that removes personal data (§10.3).
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {"redact": {"()": "tenderer.shell.logs.RedactPersonalData"}},
    "handlers": {"console": {"class": "logging.StreamHandler", "filters": ["redact"]}},
    "root": {"handlers": ["console"], "level": "INFO"},
}
