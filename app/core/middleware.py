"""HTTP middleware: request correlation ids and access logging."""

from __future__ import annotations

import logging
import re
import time
from collections.abc import Awaitable, Callable
from uuid import uuid4

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.logging import reset_request_id, set_request_id

logger = logging.getLogger("app.request")

#: Client-supplied ids are accepted only when they are short and log-safe.
REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{1,64}$")

#: Conservative response headers for a JSON API: never sniff content, never
#: leak the referring page. HTTPS itself is a deployment-boundary concern and
#: is documented in the README rather than faked here.
SECURITY_HEADERS: dict[str, str] = {
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
}


def resolve_request_id(incoming: str | None) -> str:
    """Return a safe request id, generating one when the header is absent or invalid."""

    candidate = (incoming or "").strip()
    if candidate and REQUEST_ID_PATTERN.fullmatch(candidate):
        return candidate
    return uuid4().hex


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Attach a correlation id to every request, response header and log line."""

    def __init__(self, app, header_name: str = "X-Request-ID") -> None:
        super().__init__(app)
        self.header_name = header_name

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        request_id = resolve_request_id(request.headers.get(self.header_name))
        request.state.request_id = request_id
        token = set_request_id(request_id)
        started = time.perf_counter()
        try:
            try:
                response = await call_next(request)
            except Exception:
                logger.exception(
                    "request failed method=%s path=%s duration_ms=%.2f",
                    request.method,
                    request.url.path,
                    (time.perf_counter() - started) * 1000,
                )
                raise
            response.headers[self.header_name] = request_id
            logger.info(
                "request completed method=%s path=%s status=%s duration_ms=%.2f",
                request.method,
                request.url.path,
                response.status_code,
                (time.perf_counter() - started) * 1000,
            )
            return response
        finally:
            reset_request_id(token)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Stamp conservative security headers onto every response.

    Kept separate from :class:`RequestIdMiddleware` so each concern has one
    narrow responsibility. Managed by :mod:`app.main` alongside the other
    middlewares; header values are constants, never user input.
    """

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        response = await call_next(request)
        for name, value in SECURITY_HEADERS.items():
            response.headers.setdefault(name, value)
        return response
