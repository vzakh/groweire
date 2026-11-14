"""Request id, body-size guard, CORS and trusted hosts (plan 20 task 27)."""

from __future__ import annotations

import json
import re
import time
import uuid

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from loguru import logger
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from core.config import Settings
from core.logging import request_id_var

MAX_BODY_BYTES = 1_000_000
_SAFE_ID = re.compile(r"^[A-Za-z0-9._-]{1,64}$")
_QUIET_PATHS = ("/health/live", "/metrics")


class _BodyTooLarge(Exception):
    pass


class RequestContextMiddleware:
    """Reads or creates X-Request-ID, echoes it, logs one line per request, caps the body size."""

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        headers = dict(scope.get("headers", []))
        incoming = headers.get(b"x-request-id", b"").decode("latin-1")
        rid = incoming if _SAFE_ID.match(incoming) else uuid.uuid4().hex[:16]
        token = request_id_var.set(rid)
        started = time.perf_counter()
        status = {"code": 500, "started": False}
        received = 0

        async def reject_too_large() -> None:
            if status["started"]:
                return
            body = json.dumps(
                {"detail": "The request is too large.", "code": "payload_too_large"}
            ).encode()
            status["code"] = 413
            await send(
                {
                    "type": "http.response.start",
                    "status": 413,
                    "headers": [
                        (b"content-type", b"application/json"),
                        (b"content-length", str(len(body)).encode()),
                        (b"x-request-id", rid.encode()),
                    ],
                }
            )
            await send({"type": "http.response.body", "body": body})

        async def send_wrapper(message: Message) -> None:
            if message["type"] == "http.response.start":
                status["code"] = message["status"]
                status["started"] = True
                message["headers"] = [*message.get("headers", []), (b"x-request-id", rid.encode())]
            await send(message)

        async def receive_wrapper() -> Message:
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > MAX_BODY_BYTES:
                    raise _BodyTooLarge()
            return message

        try:
            declared = int(headers.get(b"content-length", b"0") or 0)
        except ValueError:
            declared = 0
        try:
            if declared > MAX_BODY_BYTES:
                await reject_too_large()
            else:
                try:
                    await self.app(scope, receive_wrapper, send_wrapper)
                except _BodyTooLarge:
                    await reject_too_large()
        finally:
            path = scope.get("path", "")
            if not path.endswith(_QUIET_PATHS):
                logger.info(
                    "request method={} path={} status={} ms={:.1f}",
                    scope.get("method"),
                    path,
                    status["code"],
                    (time.perf_counter() - started) * 1000,
                )
            request_id_var.reset(token)


def install_middleware(app: FastAPI, settings: Settings) -> None:
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    if settings.is_prod:
        app.add_middleware(TrustedHostMiddleware, allowed_hosts=[settings.domain])
    else:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=[settings.frontend_origin],
            allow_methods=["GET", "POST"],
            allow_headers=["Content-Type", "X-Request-ID"],
            expose_headers=["X-Request-ID"],
        )
    app.add_middleware(RequestContextMiddleware)  # added last = outermost
