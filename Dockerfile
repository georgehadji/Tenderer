# One image for the web process and the jobs (docs/architecture.md §9). Base images pinned by digest (§10.4).
# Build: docker build --build-arg TENDERER_COMMIT=$(git rev-parse HEAD) -t tenderer .
# Web: gunicorn (default command). Jobs: python manage.py send_outbox | heartbeat | purge_expired
FROM ghcr.io/astral-sh/uv:0.10.4@sha256:4cac394b6b72846f8a85a7a0e577c6d61d4e17fe2ccee65d9451a8b3c9efb4ac AS uv

FROM python:3.14-slim@sha256:caaf356f40667c496d405780745b9ac25771c189a51dfcc42430d531ea09f8a2 AS build
COPY --from=uv /uv /bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never
WORKDIR /app
COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --locked --no-dev --no-install-project
COPY src ./src
RUN uv sync --locked --no-dev

FROM python:3.14-slim@sha256:caaf356f40667c496d405780745b9ac25771c189a51dfcc42430d531ea09f8a2
RUN useradd --system --uid 10001 --home-dir /app app
WORKDIR /app
COPY --from=build /app/.venv ./.venv
COPY --from=build /app/src ./src
COPY manage.py ./
COPY tenders ./tenders
COPY reference ./reference
ARG TENDERER_COMMIT=uncommitted
ENV PATH="/app/.venv/bin:$PATH" DJANGO_SETTINGS_MODULE=tenderer.shell.settings PYTHONUNBUFFERED=1 \
    TENDERER_COMMIT=$TENDERER_COMMIT
RUN DJANGO_SECRET_KEY=collectstatic-only DJANGO_DEFAULT_FROM_EMAIL=build@localhost \
    python manage.py collectstatic --noinput
USER app
EXPOSE 8000
CMD ["gunicorn", "tenderer.shell.wsgi", "--bind", "0.0.0.0:8000", "--workers", "2", "--access-logfile", "-"]
