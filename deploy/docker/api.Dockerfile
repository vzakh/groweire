# syntax=docker/dockerfile:1.7
# AgroLens API image (brief §12.5). Build context = repo root:
#   docker build -f deploy/docker/api.Dockerfile --build-arg MODEL_VERSION=$(cat ml/artifacts/CURRENT) .
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS build
# The venv is built at its final path: console scripts (alembic, uvicorn) hard-code it in their
# shebang, so a venv built elsewhere and copied over would not start.
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=0 UV_PROJECT_ENVIRONMENT=/srv/.venv
WORKDIR /src
# 1) third-party deps only: cached until uv.lock / pyproject files change
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    --mount=type=bind,source=backend/pyproject.toml,target=backend/pyproject.toml \
    --mount=type=bind,source=ml/pyproject.toml,target=ml/pyproject.toml \
    uv sync --locked --no-dev --no-install-workspace --package agrolens-backend
# 2) our code (agrolens_ml installed non-editable into the venv)
COPY pyproject.toml uv.lock ./
COPY ml/pyproject.toml ml/
COPY ml/src ml/src
COPY backend backend
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --no-editable --package agrolens-backend

FROM python:3.12-slim-bookworm AS runtime
# libgomp1: OpenMP runtime that the LightGBM wheel links against.
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd -r app && useradd -r -g app -u 10001 app
WORKDIR /srv/app
COPY --from=build --chown=app:app /srv/.venv /srv/.venv
COPY --from=build --chown=app:app /src/backend/app /srv/app
COPY --from=build --chown=app:app /src/backend/alembic /srv/alembic
COPY --from=build --chown=app:app /src/backend/alembic.ini /srv/alembic.ini
# Only the promoted bundle goes into the image: a model change is a new image tag.
ARG MODEL_VERSION
COPY --chown=app:app ml/artifacts/${MODEL_VERSION}/ /srv/model/
ENV PATH=/srv/.venv/bin:$PATH PYTHONPATH=/srv/app MODEL_DIR=/srv/model \
    PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
USER app
EXPOSE 8080
HEALTHCHECK --interval=10s --timeout=3s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request as u; u.urlopen('http://127.0.0.1:8080/api/v1/health/live', timeout=2)"
# --proxy-headers: we run behind Traefik (TLS termination). '*' is safe ONLY because the API port
# is not published in prod; it is reachable solely from Traefik on the private Docker network.
CMD ["sh", "-c", "exec uvicorn main:app --host 0.0.0.0 --port 8080 --workers ${WEB_CONCURRENCY:-2} --proxy-headers --forwarded-allow-ips='*' --timeout-graceful-shutdown 20 --no-server-header"]