"""Versioned health endpoint (``/api/v1/health``)."""

from __future__ import annotations

from fastapi import APIRouter, Request

from app.api.health_report import collect_health_report
from app.api.routes.health import HEALTH_RESPONSES
from app.schemas.health import HealthResponse

router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check (v1)",
    description="Versioned alias of `GET /health` for the frontend.",
    operation_id="get_api_v1_health",
    responses=HEALTH_RESPONSES,
)
async def get_api_v1_health(request: Request) -> HealthResponse:
    return collect_health_report(request.app.state.settings)
