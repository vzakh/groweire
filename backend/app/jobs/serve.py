"""Start the API on a hosting platform: run the migrations, then hand over to Uvicorn.

    python -m jobs.serve            # in the API image (WORKDIR /srv/app)

Render's free plan has no pre-deploy step, so migrations run here on every start (they are
idempotent). One plain command also avoids shell quoting in the platform's start command.
"""

from __future__ import annotations

import os
from pathlib import Path

from alembic import command
from alembic.config import Config

# backend/app/jobs/serve.py -> backend/ (in the image: /srv/app/jobs/serve.py -> /srv/)
BACKEND_DIR = Path(__file__).resolve().parents[2]


def migrate() -> None:
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    # alembic.ini says `script_location = alembic`, which Alembic reads from the current folder
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    command.upgrade(cfg, "head")


def serve() -> None:
    import uvicorn  # pylint: disable=import-outside-toplevel

    # Same options as the image's default CMD, started from Python: no shell, no "*" expansion
    uvicorn.run(
        "main:app",
        host="0.0.0.0",  # noqa: S104  the container's public interface
        port=int(os.environ.get("PORT", "8080")),
        workers=int(os.environ.get("WEB_CONCURRENCY", "1")),
        proxy_headers=True,
        forwarded_allow_ips="*",
        timeout_graceful_shutdown=20,
        server_header=False,
    )


if __name__ == "__main__":
    migrate()
    serve()
