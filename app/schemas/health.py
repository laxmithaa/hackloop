"""Schemas for the health endpoint."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ServiceStatus = Literal["ok", "degraded"]


class ApplicationInfo(BaseModel):
    """Identity of the running application process."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Healthcare Bill Navigator API",
                "version": "0.1.0",
                "environment": "local",
            }
        }
    )

    name: str = Field(description="Human-readable service name.")
    version: str = Field(description="Deployed application version.")
    environment: str = Field(description="Deployment environment, e.g. 'local' or 'production'.")


class HealthResponse(BaseModel):
    """Overall health of the API process.

    Phase 1 has no persistence layer, so there are no dependency checks yet;
    a successful response means the API process is running and able to answer.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "ok",
                "application": {
                    "name": "Healthcare Bill Navigator API",
                    "version": "0.1.0",
                    "environment": "local",
                },
                "timestamp": "2026-10-25T12:00:00Z",
            }
        }
    )

    status: ServiceStatus = Field(description="'ok' when the API process can serve requests.")
    application: ApplicationInfo
    timestamp: datetime = Field(description="Time at which the check completed (UTC).")
