"""Tests for ``/docs`` and ``/openapi.json`` availability and accuracy."""

from __future__ import annotations

from httpx import AsyncClient


async def test_openapi_schema_is_available(client: AsyncClient) -> None:
    response = await client.get("/openapi.json")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")


async def test_openapi_schema_describes_actual_endpoints(client: AsyncClient) -> None:
    schema = (await client.get("/openapi.json")).json()

    assert schema["info"]["title"] == "Healthcare Bill Navigator API"
    assert schema["info"]["version"]
    # Only the endpoints that really exist: Phase 1 health, the Phase 2
    # session/consent and identification endpoints, and the Phase 3
    # verification/protected-bill endpoints.
    assert set(schema["paths"]) == {
        "/health",
        "/api/v1/health",
        "/api/v1/sessions",
        "/api/v1/sessions/{session_id}/consent",
        "/api/v1/sessions/{session_id}/consent/withdraw",
        "/api/v1/identifications",
        "/api/v1/identifications/upload",
        "/api/v1/identifications/{identification_id}/verify",
        "/api/v1/verified-bills/{identification_id}",
        # Phase 8: local-GenAI bill explanation (protected, verified bills only).
        "/api/v1/verified-bills/{identification_id}/explanation",
        # Phase 9: grounded Q&A, personalised explanations and caregiver sharing.
        "/api/v1/verified-bills/{identification_id}/questions",
        "/api/v1/verified-bills/{identification_id}/personalized-explanation",
        "/api/v1/verified-bills/{identification_id}/caregiver-share",
        "/api/v1/verified-bills/{identification_id}/caregiver-summary",
        # Phase 4: patient help requests and staff (support-worker) queue.
        "/api/v1/help-requests",
        "/api/v1/help-requests/{ticket_id}",
        "/api/v1/staff/help-requests",
        "/api/v1/staff/help-requests/{ticket_id}",
        "/api/v1/staff/help-requests/{ticket_id}/status",
    }
    assert schema["paths"]["/health"]["get"]["operationId"] == "get_health"
    assert schema["paths"]["/api/v1/health"]["get"]["operationId"] == "get_api_v1_health"
    assert schema["paths"]["/api/v1/sessions"]["post"]["operationId"] == "create_session"
    assert (
        schema["paths"]["/api/v1/identifications"]["post"]["operationId"]
        == "identify_bill_manually"
    )
    assert (
        schema["paths"]["/api/v1/identifications/upload"]["post"]["operationId"]
        == "identify_bill_from_image"
    )
    assert {
        "Health",
        "Sessions",
        "Identification",
        "Verification",
        "Explanations",
        "Bill Assistant",
        "Caregiver",
    } <= {tag["name"] for tag in schema["tags"]}


async def test_openapi_schema_documents_response_and_error_models(client: AsyncClient) -> None:
    schema = (await client.get("/openapi.json")).json()

    components = schema["components"]["schemas"]
    assert "HealthResponse" in components
    assert "ApplicationInfo" in components
    assert "ErrorResponse" in components
    assert components["HealthResponse"]["properties"]["status"]["type"] == "string"


async def test_docs_page_is_available(client: AsyncClient) -> None:
    response = await client.get("/docs")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
