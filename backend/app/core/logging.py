"""loguru JSON logs to stdout, with the request id on every line (brief §12.4)."""

from __future__ import annotations

import sys
from contextvars import ContextVar

from loguru import logger

request_id_var: ContextVar[str] = ContextVar("request_id", default="-")


def _patch(record: dict) -> None:
    record["extra"]["request_id"] = request_id_var.get()


def setup_logging(level: str = "INFO", json_logs: bool = True) -> None:
    logger.remove()
    logger.configure(patcher=_patch)
    logger.add(
        sys.stdout, level=level.upper(), serialize=json_logs, backtrace=False, diagnose=False
    )
