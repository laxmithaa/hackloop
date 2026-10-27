"""Patient session and consent endpoints (``/api/v1/sessions``)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Request

from app.core.config import Settings
from app.core.errors import BadRequestError
from app.schemas.errors import ErrorResponse
from app.schemas.sessions import (
    ConsentRequest,
    ConsentResponse,
    ConsentState,
    CreateSessionResponse,
)
from app.services.session_store import CONSENT_WITHDRAWN, SessionStore

router = APIRouter(tags=["Sessions"], prefix="/sessions")


def _error_docs() -> dict[int | str, dict[str, Any]]:
    def doc(code: int, text: str) -> dict[str, Any]:
        return {"model": ErrorResponse, "description": text}

    return {
        400: doc(
            400,
            "Validation failure, or the accepted consent policy version is not current. "
            "Uses the standard error envelope.",
        ),
        404: doc(
            404,
            "Unknown or expired session identifier. Uses the standard error envelope.",
        ),
        422: doc(
            422,
            "Request body failed validation. Uses the standard error envelope with `details`.",
        ),
    }


@router.post(
    "",
    response_model=CreateSessionResponse,
    status_code=201,
    summary="Create a temporary patient session",
    description=(
        "Creates a new anonymous, in-memory session and returns its identifier plus "
        "the (initially empty) consent state. No bill is processed. Sessions expire "
        "when their validity window passes or the server restarts."
    ),
    operation_id="create_session",
)
async def create_session(request: Request) -> CreateSessionResponse:
    store: SessionStore = request.app.state.session_store
    session = store.create()
    return CreateSessionResponse(
        session_id=session.session_id,
        consent=ConsentState(
            recorded=False,
            decision=None,
            policy_version=None,
            recorded_at=None,
        ),
    )


@router.post(
    "/{session_id}/consent",
    response_model=ConsentResponse,
    summary="Record patient consent",
    description=(
        "Records the patient's consent decision and the consent policy version accepted. "
        "The submitted policy version must match the server's current version; "
        "stale versions are rejected so outdated consent text is never accepted. "
        "Bill identification is only possible once consent is granted."
    ),
    operation_id="record_consent",
    responses=_error_docs(),
)
async def record_consent(
    session_id: str,
    payload: ConsentRequest,
    request: Request,
) -> ConsentResponse:
    store: SessionStore = request.app.state.session_store
    settings: Settings = request.app.state.settings

    # Session existence/expiry is checked first so unknown or expired
    # identifiers are reported as 404, not as a consent-validity 400.
    session = store.get(session_id)

    if payload.policy_version != settings.consent_policy_version:
        raise BadRequestError(
            code="consent_policy_outdated",
            message=(
                "The accepted consent policy version is not current. "
                f"The current version is '{settings.consent_policy_version}'."
            ),
        )

    recorded_at = datetime.now(UTC)
    store.record_consent(
        session,
        decision=payload.decision,
        policy_version=payload.policy_version,
        recorded_at=recorded_at,
    )
    return ConsentResponse(
        session_id=session.session_id,
        decision=payload.decision,
        policy_version=payload.policy_version,
        recorded_at=recorded_at,
    )


@router.post(
    "/{session_id}/consent/withdraw",
    response_model=ConsentResponse,
    summary="Withdraw patient consent",
    description=(
        "Withdraws consent. Further bill identification through this session is "
        "rejected with `consent_required` until a new consent is recorded."
    ),
    operation_id="withdraw_consent",
    responses=_error_docs(),
)
async def withdraw_consent(session_id: str, request: Request) -> ConsentResponse:
    store: SessionStore = request.app.state.session_store
    session = store.get(session_id)
    withdraw_time = datetime.now(UTC)
    store.withdraw_consent(session)

    # Phase 4: hide this session's help requests from the support-worker
    # endpoints immediately. Ticket records themselves are kept (the patient
    # can still look them up through their own session) but the shared
    # consent state is withdrawn and the staff queue never serves them.
    help_store = request.app.state.help_request_store
    help_store.mark_session_sharing_withdrawn(session_id)

    return ConsentResponse(
        session_id=session.session_id,
        decision=CONSENT_WITHDRAWN,
        policy_version=session.consent_policy_version,
        recorded_at=withdraw_time,
    )
