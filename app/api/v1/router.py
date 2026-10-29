"""Aggregate router for ``/api/v1``.

Later phases register their routers here (access-code verification, amount
comparison, explanations, caregiver summaries and support requests).
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.routes import (
    caregiver,
    explanations,
    health,
    help,
    identifications,
    personalization,
    questions,
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
api_v1_router.include_router(personalization.router)
# Phase 9: grounded Q&A and caregiver summaries.
api_v1_router.include_router(questions.router)
api_v1_router.include_router(caregiver.router)
