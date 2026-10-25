"""Tests for the shared JSON error envelope and status-code mapping."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest
from fastapi import APIRouter, FastAPI
from httpx import AsyncClient

from app.core.errors import BadRequestError, NotFoundError

demo_router = APIRouter(prefix="/api/v1/demo", include_in_schema=False)


@demo_router.get("/missing")
async def raise_not_found() -> None:
    raise NotFoundError("Sample record was not found.")


@demo_router.get("/bad-request")
async def raise_bad_request() -> None:
    raise BadRequestError("Page size must be between 1 and 50.")


@demo_router.get("/boom")
async def raise_unexpected() -> None:
    raise RuntimeError("boom: patient ssn 123-45-6789")


@pytest.fixture
def app_with_demo_routes(app: FastAPI) -> FastAPI:
    app.include_router(demo_router)
    return app


@pytest.fixture
async def demo_client(app_with_demo_routes: FastAPI, client_factory) -> Iterator[AsyncClient]:
    async with client_factory(app_with_demo_routes) as http_client:
        yield http_client


def assert_error_envelope(
    body: dict[str, Any],
    *,
    code: str,
    status_code: int,
) -> dict[str, Any]:
    error = body["error"]
    assert set(error) == {"code", "message", "request_id", "details"}
    assert error["code"] == code
    assert error["message"]
    assert isinstance(error["message"], str)
    assert status_code >= 400
    return error


async def test_unknown_route_returns_json_404(demo_client: AsyncClient) -> None:
    response = await demo_client.get("/api/v1/does-not-exist")

    assert response.status_code == 404
    error = assert_error_envelope(response.json(), code="not_found", status_code=404)
    assert error["message"] == "The requested resource was not found."
    assert error["request_id"] == response.headers["x-request-id"]


async def test_method_not_allowed_returns_json_405(demo_client: AsyncClient) -> None:
    response = await demo_client.post("/health")

    assert response.status_code == 405
    error = assert_error_envelope(response.json(), code="method_not_allowed", status_code=405)
    assert error["message"] == "The HTTP method is not allowed for this resource."


async def test_expected_app_error_keeps_safe_message(demo_client: AsyncClient) -> None:
    response = await demo_client.get("/api/v1/demo/missing")

    assert response.status_code == 404
    error = assert_error_envelope(response.json(), code="not_found", status_code=404)
    assert error["message"] == "Sample record was not found."


async def test_bad_request_error_returns_400(demo_client: AsyncClient) -> None:
    response = await demo_client.get("/api/v1/demo/bad-request")

    assert response.status_code == 400
    error = assert_error_envelope(response.json(), code="bad_request", status_code=400)
    assert error["message"] == "Page size must be between 1 and 50."


async def test_unhandled_exception_returns_generic_500(demo_client: AsyncClient) -> None:
    response = await demo_client.get("/api/v1/demo/boom")

    assert response.status_code == 500
    error = assert_error_envelope(response.json(), code="internal_error", status_code=500)
    assert error["message"] == "An unexpected error occurred. Please try again later."
    assert error["request_id"] == response.headers["x-request-id"]
    # Internal details must never reach the client.
    assert "123-45-6789" not in response.text
    assert "RuntimeError" not in response.text
    assert "Traceback" not in response.text


async def test_error_envelope_uses_header_request_id(demo_client: AsyncClient) -> None:
    response = await demo_client.get(
        "/api/v1/demo/missing", headers={"X-Request-ID": "client-supplied-id"}
    )

    assert response.headers["x-request-id"] == "client-supplied-id"
    assert response.json()["error"]["request_id"] == "client-supplied-id"
