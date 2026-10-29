"""Health route: ``GET /health`` and ``GET /api/v1/health``.

Phase 1 has no persistence layer, so the health check reports the state of the
API process only and performs no dependency I/O.
"""

from __future__ import annotations

from datetime import UTC, datetime

from app.core.config import Settings
from app.schemas.health import ApplicationInfo, HealthResponse


def collect_health_report(settings: Settings) -> HealthResponse:
    """Build the health payload shared by every health endpoint."""

    return HealthResponse(
        status="ok",
        application=ApplicationInfo(
            name=settings.app_name,
            version=settings.app_version,
            environment=settings.environment,
        ),
        timestamp=datetime.now(UTC),
    )
