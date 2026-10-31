"""The error envelope: every non-2xx response is ``ApiErrorBody`` = {code, message, retryAfterSec?}.

Messages are written for the attorney and name the next action (FR-28). They never carry
document text or stack traces (DR-5).
"""

import logging
from typing import Literal

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

log = logging.getLogger("legallens.errors")

ErrorCode = Literal["llm_unavailable", "rate_limited", "timeout", "parse_failure", "unknown"]


class AppError(Exception):
    def __init__(
        self,
        status: int,
        message: str,
        code: ErrorCode = "unknown",
        retry_after_sec: int | None = None,
    ) -> None:
        super().__init__(message)
        self.status = status
        self.message = message
        self.code = code
        self.retry_after_sec = retry_after_sec


def not_found(what: str) -> AppError:
    return AppError(404, f"{what} not found. It may have been deleted.")


def unauthorized() -> AppError:
    return AppError(401, "Not signed in. Sign in to continue.")


def conflict(message: str) -> AppError:
    return AppError(409, message)


def bad_request(message: str) -> AppError:
    return AppError(422, message)


def error_body(code: ErrorCode, message: str, retry_after_sec: int | None = None) -> dict[str, object]:
    body: dict[str, object] = {"code": code, "message": message}
    if retry_after_sec is not None:
        body["retryAfterSec"] = retry_after_sec
    return body


def _response(status: int, code: ErrorCode, message: str, retry_after: int | None = None) -> JSONResponse:
    headers = {"Retry-After": str(retry_after)} if retry_after is not None else None
    return JSONResponse(error_body(code, message, retry_after), status_code=status, headers=headers)


def _describe_validation(exc: RequestValidationError) -> str:
    parts = []
    for err in exc.errors()[:3]:
        loc = ".".join(str(p) for p in err.get("loc", ()) if p not in ("body", "query", "path"))
        parts.append(f"{loc or 'request'}: {err.get('msg', 'invalid')}")
    return "The request was not valid — " + "; ".join(parts) + "."


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(_: Request, exc: AppError) -> JSONResponse:
        return _response(exc.status, exc.code, exc.message, exc.retry_after_sec)

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError) -> JSONResponse:
        return _response(422, "unknown", _describe_validation(exc))

    @app.exception_handler(StarletteHTTPException)
    async def _http(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        messages = {
            404: "Not found.",
            405: "That method is not allowed on this endpoint.",
            413: "The upload is too large. Each file may be at most 50 MB.",
        }
        message = messages.get(exc.status_code, str(exc.detail) or "Request failed.")
        return _response(exc.status_code, "unknown", message)

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception) -> JSONResponse:
        log.exception("unhandled error on %s %s", request.method, request.url.path, exc_info=exc)
        return _response(500, "unknown", "Something went wrong on our side. Try again in a moment.")
