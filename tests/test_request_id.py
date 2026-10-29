"""Tests for request-id propagation and sanitisation."""

from __future__ import annotations

import re

import pytest
from httpx import AsyncClient

GENERATED_ID = re.compile(r"^[0-9a-f]{32}$")


@pytest.mark.parametrize("incoming", ["abc-123", "A" * 64, "trace_01:span.2", "0123456789abcdef"])
async def test_valid_request_ids_are_echoed(client: AsyncClient, incoming: str) -> None:
    response = await client.get("/health", headers={"X-Request-ID": incoming})

    assert response.headers["x-request-id"] == incoming


@pytest.mark.parametrize(
    "incoming",
    ["bad id with spaces", "A" * 65, "semi;colon", "line\nbreak"],
)
async def test_invalid_request_ids_are_replaced(client: AsyncClient, incoming: str) -> None:
    response = await client.get("/health", headers={"X-Request-ID": incoming})

    generated = response.headers["x-request-id"]
    assert generated != incoming
    assert GENERATED_ID.fullmatch(generated)


async def test_generated_request_ids_are_unique(client: AsyncClient) -> None:
    first = await client.get("/health")
    second = await client.get("/health")

    assert first.headers["x-request-id"] != second.headers["x-request-id"]


async def test_every_response_carries_a_request_id(client: AsyncClient) -> None:
    for path in ("/health", "/api/v1/health", "/does-not-exist"):
        response = await client.get(path)

        assert response.headers["x-request-id"].strip()
