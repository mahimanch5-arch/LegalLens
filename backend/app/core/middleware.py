"""Pure-ASGI middleware, so streamed (SSE) responses pass through untouched."""

import contextvars
import logging
import time

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.ids import new_id

log = logging.getLogger("legallens.access")

request_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar("request_id", default=None)


class RequestContextMiddleware:
    """Assigns ``X-Request-ID`` and writes one access-log line per request.

    The log line carries method, path, status and duration only — never bodies (DR-5).
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        incoming = dict(scope.get("headers", [])).get(b"x-request-id", b"").decode()[:64]
        rid = incoming or new_id("req", 12)
        token = request_id_var.set(rid)
        started = time.perf_counter()
        status = 500

        async def send_wrapper(message: Message) -> None:
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
                message.setdefault("headers", [])
                message["headers"] = [*message["headers"], (b"x-request-id", rid.encode())]
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            ms = (time.perf_counter() - started) * 1000
            log.info("%s %s %s %.0fms rid=%s", scope["method"], scope["path"], status, ms, rid)
            request_id_var.reset(token)


class BodySizeLimitMiddleware:
    """Rejects requests whose declared Content-Length exceeds the cap with a 413."""

    def __init__(self, app: ASGIApp, max_bytes: int) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http":
            length = dict(scope.get("headers", [])).get(b"content-length")
            if length and length.isdigit() and int(length) > self.max_bytes:
                body = (
                    b'{"code":"unknown","message":"The upload is too large. Upload fewer files at once; '
                    b'each file may be at most 50 MB."}'
                )
                await send(
                    {
                        "type": "http.response.start",
                        "status": 413,
                        "headers": [(b"content-type", b"application/json")],
                    }
                )
                await send({"type": "http.response.body", "body": body})
                return
        await self.app(scope, receive, send)
