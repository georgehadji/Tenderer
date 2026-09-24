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
]

TENDERER_PACKS = "tenderer.shell.packs.PACKS"  # apps reach packs only through this registry (§5.2 rule 7)

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
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
