"""Shared response schemas, including the consistent error envelope."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class FieldError(BaseModel):
    """A single validation problem reported back to the client."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "field": "body.patient_reference",
                "message": "String should have at least 6 characters",
                "type": "string_too_short",
            }
        }
    )

    field: str = Field(description="Location of the offending value, e.g. 'body.email'.")
    message: str = Field(description="Human-readable description of the problem.")
    type: str = Field(description="Stable machine-readable validator identifier.")


class ErrorDetail(BaseModel):
    """Machine-readable error payload."""

    code: str = Field(description="Stable error code, e.g. 'not_found' or 'validation_error'.")
    message: str = Field(description="Safe, human-readable explanation of the failure.")
    request_id: str = Field(
        description="Correlation id of the request; also returned in the request-id header."
    )
    details: list[FieldError] | None = Field(
        default=None, description="Field-level problems, present for validation failures."
    )


class ErrorResponse(BaseModel):
    """Envelope used for every non-2xx response produced by the API."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "error": {
                    "code": "not_found",
                    "message": "The requested resource was not found.",
                    "request_id": "7f1a9f0c2f6d4c0b8b9e3a6f5f0d1e2c",
                    "details": None,
                }
            }
        }
    )

    error: ErrorDetail
