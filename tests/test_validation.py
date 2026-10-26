"""Validation failures must return the shared 422 envelope with field details.

Phase 1 has no POST endpoints, so the validation path is exercised through a
test-only router (kept out of the OpenAPI schema). The production validation
handler under test is the same one real endpoints use.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi import APIRouter, FastAPI
from httpx import AsyncClient
from pydantic import BaseModel, Field

validation_router = APIRouter(prefix="/api/v1/demo", include_in_schema=False)


class SampleNote(BaseModel):
    patient_reference: str = Field(min_length=6, description="Fictional patient reference.")
    amount_cents: int = Field(ge=0, description="Recorded amount in cents.")


@validation_router.post("/notes")
async def create_note(payload: SampleNote) -> dict[str, object]:
    return {"patient_reference": payload.patient_reference, "amount_cents": payload.amount_cents}


@pytest.fixture
def app_with_validation_route(app: FastAPI) -> FastAPI:
    app.include_router(validation_router)
    return app


@pytest.fixture
async def validation_client(
    app_with_validation_route: FastAPI, client_factory
) -> Iterator[AsyncClient]:
    async with client_factory(app_with_validation_route) as http_client:
        yield http_client


async def test_valid_payload_is_accepted(validation_client: AsyncClient) -> None:
    response = await validation_client.post(
        "/api/v1/demo/notes",
        json={"patient_reference": "HBN-0001", "amount_cents": 1250},
    )

    assert response.status_code == 200
    assert response.json() == {"patient_reference": "HBN-0001", "amount_cents": 1250}


async def test_missing_fields_return_422_with_field_details(
    validation_client: AsyncClient,
) -> None:
    response = await validation_client.post("/api/v1/demo/notes", json={})

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "validation_error"
    assert error["message"] == "Request validation failed."
    assert error["request_id"] == response.headers["x-request-id"]

    fields = {detail["field"] for detail in error["details"]}
    assert fields == {"body.patient_reference", "body.amount_cents"}
    assert all(detail["message"] for detail in error["details"])
    assert all(detail["type"] for detail in error["details"])


async def test_invalid_values_return_422(validation_client: AsyncClient) -> None:
    response = await validation_client.post(
        "/api/v1/demo/notes",
        json={"patient_reference": "abc", "amount_cents": -1},
    )

    assert response.status_code == 422
    details = response.json()["error"]["details"]
    fields = {detail["field"] for detail in details}
    assert fields == {"body.patient_reference", "body.amount_cents"}
    types = {detail["type"] for detail in details}
    assert "string_too_short" in types
    assert "greater_than_equal" in types


async def test_malformed_json_returns_422(validation_client: AsyncClient) -> None:
    response = await validation_client.post(
        "/api/v1/demo/notes",
        content=b"{not-json",
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "validation_error"
    assert error["details"]
    assert "Traceback" not in response.text
