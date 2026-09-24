"""Test settings: the production settings with a throwaway secret and a local, non-TLS database."""

import os

os.environ.setdefault("DJANGO_SECRET_KEY", "test-only-not-a-secret")
os.environ.setdefault("PGHOST", "127.0.0.1")
os.environ.setdefault("PGSSLMODE", "disable")

from tenderer.shell.settings import *  # noqa: F403
