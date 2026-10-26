"""Centralised exception handling that always answers with the same JSON shape.

Every failure — validation, expected application error, unknown route, wrong
method, or an unhandled bug — becomes::

    {"error": {"code": ..., "message": ..., "request_id": ..., "details": [...]}}

Unhandled exceptions are logged with a stack trace for operators, while the
client only receives a generic message plus the correlation id.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.errors import AppError
from app.core.logging import get_request_id
from app.schemas.errors import ErrorDetail, ErrorResponse, FieldError

logger = logging.getLogger(__name__)

STATUS_CODES: dict[int, str] = {
    400: "bad_request",
    401: "unauthorized",
    403: "forbidden",
    404: "not_found",
    405: "method_not_allowed",
    409: "conflict",
    413: "payload_too_large",
    415: "unsupported_media_type",
    422: "validation_error",
    429: "too_many_requests",
    500: "internal_error",
    503: "service_unavailable",
}

STATUS_MESSAGES: dict[int, str] = {
    400: "The request could not be processed.",
    401: "Authentication is required for this request.",
    402: "Payment is required for this request.",
    403: "You do not have permission to perform this action.",
    404: "The requested resource was not found.",
    405: "The HTTP method is not allowed for this resource.",
    406: "The requested response format is not available.",
    409: "The request conflicts with the current state of the resource.",
    413: "The uploaded content is too large.",
    415: "The request content type is not supported.",
    422: "Request validation failed.",
    429: "Too many requests. Please try again later.",
    500: "An unexpected error occurred. Please try again later.",
    502: "A dependency returned an invalid response.",
    503: "The service is temporarily unavailable. Please try again later.",
    504: "A dependency did not respond in time.",
}


def error_code_for_status(status_code: int) -> str:
    """Stable error code for a given HTTP status."""

    return STATUS_CODES.get(status_code, "http_error")


def error_message_for_status(status_code: int) -> str:
    """Canonical, client-safe message for a given HTTP status."""

    return STATUS_MESSAGES.get(status_code, "The request could not be completed.")


def request_id_for(request: Request) -> str:
    """Correlation id of the request being handled.

    ``request.state`` is preferred because it survives the context variable
    being reset when middleware unwinds, which happens for unhandled errors
    answered by Starlette's outermost error middleware.
    """

    return getattr(request.state, "request_id", None) or get_request_id()


def build_error_response(
    request: Request,
    *,
    status_code: int,
    code: str,
    message: str,
    details: list[FieldError] | None = None,
    headers: Mapping[str, str] | None = None,
) -> JSONResponse:
    """Serialise the shared error envelope and stamp the correlation id header."""

    request_id = request_id_for(request)
    response_headers = dict(headers or {})
    header_name = getattr(request.app.state.settings, "request_id_header", "X-Request-ID")
    response_headers[header_name] = request_id

    payload = ErrorResponse(
        error=ErrorDetail(
            code=code,
            message=message,
            request_id=request_id,
            details=details,
        )
    )
    return JSONResponse(
        status_code=status_code,
        content=payload.model_dump(mode="json"),
        headers=response_headers,
    )


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    logger.info(
        "application error code=%s status=%s path=%s",
        exc.code,
        exc.status_code,
        request.url.path,
    )
    return build_error_response(
        request,
        status_code=exc.status_code,
        code=exc.code,
        message=exc.message,
        details=exc.details,
        headers=exc.headers,
    )


async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    details = [
        FieldError(
            field=".".join(str(part) for part in error.get("loc", ())),
            message=str(error.get("msg", "Invalid value.")),
            type=str(error.get("type", "value_error")),
        )
        for error in exc.errors()
    ]
    logger.info(
        "request validation failed path=%s problems=%s",
        request.url.path,
        len(details),
    )
    return build_error_response(
        request,
        status_code=422,
        code="validation_error",
        message=error_message_for_status(422),
        details=details,
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    status_code = exc.status_code
    # One canonical message per status keeps responses predictable and never
    # exposes framework or driver internals. Domain-specific, client-safe
    # messages belong to AppError subclasses.
    message = error_message_for_status(status_code)

    if status_code >= 500:
        logger.error("http error status=%s path=%s", status_code, request.url.path)
    else:
        logger.info("http error status=%s path=%s", status_code, request.url.path)

    headers = dict(getattr(exc, "headers", None) or {})
    return build_error_response(
        request,
        status_code=status_code,
        code=error_code_for_status(status_code),
        message=message,
        headers=headers,
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception(
        "unhandled exception method=%s path=%s",
        request.method,
        request.url.path,
    )
    return build_error_response(
        request,
        status_code=500,
        code="internal_error",
        message=error_message_for_status(500),
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Install the handlers on an application instance."""

    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
