"""Aggregate router for ``/api/v1``.

Later phases register their routers here (access-code verification, amount
comparison, explanations, caregiver summaries and support requests).
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.routes import (
    explanations,
    health,
    help,
    identifications,
    sessions,
    verification,
)

api_v1_router = APIRouter()
api_v1_router.include_router(health.router)
api_v1_router.include_router(sessions.router)
api_v1_router.include_router(identifications.router)
api_v1_router.include_router(verification.router)
api_v1_router.include_router(help.router)
api_v1_router.include_router(help.staff_router)
api_v1_router.include_router(explanations.router)
