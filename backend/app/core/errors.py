"""Error shape for the whole API: {"detail": str, "code": str} (brief §9)."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from loguru import logger
from starlette.exceptions import HTTPException as StarletteHTTPException


class AppError(Exception):
    """An expected failure with a stable machine-readable code."""

    def __init__(self, code: str, detail: str, status: int = 400, extra: dict | None = None):
        super().__init__(detail)
        self.code = code
        self.detail = detail
        self.status = status
        self.extra = extra or {}


class UpstreamError(Exception):
    """An external API failed. Services turn this into an information gap, not a 500."""

    def __init__(self, code: str, detail: str = ""):
        super().__init__(detail or code)
        self.code = code


def _clean_errors(errors: list[dict]) -> list[dict]:
    """Keep validation errors JSON-safe and small (no echo of the raw input)."""
    return [
        {"loc": [str(p) for p in e.get("loc", ())], "msg": e.get("msg", ""), "type": e.get("type")}
        for e in errors
    ]


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(_: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status, content={"detail": exc.detail, "code": exc.code, **exc.extra}
        )

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError) -> JSONResponse:
        errors = _clean_errors(exc.errors())
        # A model_validator can pick its own code by raising ValueError("code=<code>: message").
        code, detail = "validation_error", "The request is not valid."
        for err in errors:
            msg = err["msg"]
            if "code=" in msg:
                tail = msg.split("code=", 1)[1]
                code, _, rest = tail.partition(":")
                code, detail = code.strip(), rest.strip() or detail
                break
        return JSONResponse(
            status_code=422, content={"detail": detail, "code": code, "errors": errors}
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = {404: "not_found", 405: "method_not_allowed"}.get(exc.status_code, "http_error")
        return JSONResponse(
            status_code=exc.status_code, content={"detail": str(exc.detail), "code": code}
        )

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception) -> JSONResponse:
        logger.opt(exception=exc).error("unhandled_error path={}", request.url.path)
        return JSONResponse(
            status_code=500,
            content={"detail": "Something went wrong on our side.", "code": "internal_error"},
        )
