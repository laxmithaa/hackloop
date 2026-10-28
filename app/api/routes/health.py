"""Unversioned health endpoint used by uptime checks and load balancers."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request

from app.api.health_report import collect_health_report
from app.schemas.errors import ErrorResponse
from app.schemas.health import HealthResponse

HEALTH_RESPONSES: dict[int | str, dict[str, Any]] = {
    200: {"model": HealthResponse},
    500: {
        "model": ErrorResponse,
        "description": (
            "Unexpected server error. Every error uses the standard envelope: "
            '`{"error": {"code", "message", "request_id", "details"}}`.'
        ),
    },
}

router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check",
    description=(
        "Report the health of the API process: its status, name, version, "
        "environment and a UTC timestamp. Phase 1 performs no dependency checks."
    ),
    operation_id="get_health",
    responses=HEALTH_RESPONSES,
)
async def get_health(request: Request) -> HealthResponse:
    return collect_health_report(request.app.state.settings)
