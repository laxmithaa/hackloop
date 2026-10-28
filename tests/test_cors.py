"""Tests for configurable CORS behaviour on configured origins."""

from __future__ import annotations

from httpx import AsyncClient


async def test_preflight_from_allowed_origin_is_accepted(client: AsyncClient) -> None:
    response = await client.options(
        "/health",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
    assert response.headers["access-control-allow-credentials"] == "true"


async def test_actual_request_from_allowed_origin_is_marked(client: AsyncClient) -> None:
    response = await client.get("/health", headers={"Origin": "http://localhost:3000"})

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"


async def test_disallowed_origin_gets_no_corse_header(client: AsyncClient) -> None:
    response = await client.get("/health", headers={"Origin": "https://evil.example.test"})

    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers


async def test_error_responses_carry_cors_headers(client: AsyncClient) -> None:
    response = await client.get("/does-not-exist", headers={"Origin": "http://localhost:3000"})

    assert response.status_code == 404
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"


async def test_actual_response_exposes_request_id_header_to_browsers(
    client: AsyncClient,
) -> None:
    response = await client.get("/health", headers={"Origin": "http://localhost:3000"})

    assert response.status_code == 200
    assert "x-request-id" in response.headers.get("access-control-expose-headers", "").lower()


async def test_preflight_permits_request_id_header(client: AsyncClient) -> None:
    response = await client.options(
        "/health",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "X-Request-ID",
        },
    )

    assert response.status_code == 200
    allowed = response.headers.get("access-control-allow-headers", "").lower()
    assert "x-request-id" in allowed
