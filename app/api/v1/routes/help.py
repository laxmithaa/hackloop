"""Help-request endpoints (``/api/v1/help-requests``, ``/api/v1/staff``).

Two clearly separated permission levels:

- **Patient** — ``POST /api/v1/help-requests`` and
  ``GET /api/v1/help-requests/{ticket_id}``: needs its own live session with
  granted processing consent, an identification *of that session*, and an
  explicit sharing-consent flag in the body. No verification required (a
  patient may need help precisely because verification failed). Responses
  carry the ticket id, status, language and callback window only.
- **Support worker** — endpoints under ``/api/v1/staff/help-requests``: every
  call must present the ``X-Support-Staff-Token`` header matching the server
  token configured via ``SUPPORT_STAFF_API_TOKEN`` (constant-time compare).
  Fail closed when not configured. Requests whose sharing consent is
  withdrawn are never exposed.

Free-text reasons are treated strictly as data: they are stored once and are
never logged, and they never influence authorization.
"""

from __future__ import annotations

import hmac
import logging
from datetime import UTC, datetime
from typing import Annotated, Any
from uuid import uuid4

from fastapi import APIRouter, Header, Request

from app.core.config import Settings
from app.core.errors import (
    ConsentRequiredError,
    HelpTicketNotFoundError,
    IdentificationNotFoundError,
    SupportStaffAuthError,
    SupportStaffNotConfiguredError,
)
from app.schemas.errors import ErrorResponse
from app.schemas.help import (
    HelpRequestCreate,
    HelpTicketResponse,
    StaffStatusUpdate,
    StaffTicketDetail,
    StaffTicketSummary,
)
from app.schemas.verification import validate_session_id_format
from app.services.help_requests import (
    HelpRequestStore,
    VerificationSnapshot,
    build_case_summary,
    snapshot_verification_state,
)
from app.services.session_store import CONSENT_GRANTED, PatientSession, SessionStore

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Support"], prefix="/help-requests")
staff_router = APIRouter(tags=["Support"], prefix="/staff/help-requests")


def _staff_error_docs() -> dict[int | str, dict[str, Any]]:
    def doc(status: int, text: str) -> dict[str, Any]:
        return {"model": ErrorResponse, "description": text}

    return {
        401: doc(401, "Support-worker authentication is required."),
        403: doc(403, "Staff access is denied."),
        404: doc(
            404,
            "Unknown ticket, or one whose sharing consent was withdrawn: "
            "never distinguishes the two.",
        ),
        409: doc(409, "Invalid workflow status transition."),
        503: doc(503, "Support-worker access is not configured (fail closed)."),
    }


def _consented_session(request: Request, session_id: str) -> PatientSession:
    """Live session with granted consent, or the appropriate error."""

    store: SessionStore = request.app.state.session_store
    session = store.get(session_id)  # raises 404 for unknown/expired sessions
    if session.consent_decision != CONSENT_GRANTED:
        raise ConsentRequiredError(
            "Patient consent must remain granted to request human help."
        )
    return session


def _verification_state_for(session: PatientSession, identification_id: str) -> str:
    """Snapshot the session's verification outcome for one identification."""

    record = session.verifications.get(identification_id)
    if record is None:
        return snapshot_verification_state(VerificationSnapshot(False, None))
    comparison = record.comparison
    if comparison is None or comparison.status == "no_uploaded_image":
        return snapshot_verification_state(VerificationSnapshot(True, None))
    return snapshot_verification_state(VerificationSnapshot(True, comparison.status))


def _staff_is_authorized(request: Request, staff_token: str | None) -> None:
    """Constant-time staff-token check; fails closed when not configured."""

    settings: Settings = request.app.state.settings
    configured = settings.support_staff_api_token
    if not configured:
        raise SupportStaffNotConfiguredError()
    if not staff_token or not hmac.compare_digest(
        staff_token.encode(), configured.encode()
    ):
        raise SupportStaffAuthError()


def _staff_ticket_or_none(request: Request, ticket_id: str):
    """Ticket lookup for staff that also honours withdrawn sharing."""

    store: HelpRequestStore = request.app.state.help_request_store
    ticket = store.get(ticket_id)
    if ticket is None or ticket.sharing_withdrawn:
        return None
    session_store: SessionStore = request.app.state.session_store
    session = session_store._sessions.get(ticket.session_id)
    if session is None or session.consent_decision != CONSENT_GRANTED:
        return None  # withdrawn/removed session consent hides the request
    return ticket


def _summary_fields(ticket) -> dict[str, Any]:
    """Safe field set for staff responses (no amounts, no tokens, no codes)."""

    return {
        "ticket_id": ticket.ticket_id,
        "status": ticket.status,
        "language": ticket.language,
        "callback_window": ticket.callback_window,
        "created_at": ticket.created_at.isoformat(),
        "verification_state": ticket.verification_state,
    }


@router.post(
    "",
    response_model=HelpTicketResponse,
    status_code=201,
    summary="Request human help with a callback",
    description=(
        "Creates a support ticket for one bill identification of this session. "
        "Requires a live session with granted consent and explicit, "
        "request-specific sharing consent (``consent_sharing_confirmed: true``). "
        "Access-code verification is NOT required to ask for help. The response "
        "returns the ticket id, status (new), language and callback window only. "
        "Callbacks are recorded as workflow status only; no real call is placed."
    ),
    operation_id="create_help_request",
    responses={403: {"model": ErrorResponse, "description": "Consent conditions not met."}},
)
async def create_help_request(payload: HelpRequestCreate, request: Request):
    session = _consented_session(request, payload.session_id)
    store: SessionStore = request.app.state.session_store
    identification = store.get_identification(session, payload.identification_id)
    if identification is None:
        raise IdentificationNotFoundError()

    help_store: HelpRequestStore = request.app.state.help_request_store
    ticket = help_store.create(
        ticket_id=uuid4().hex,
        session_id=session.session_id,
        identification_id=identification.identification_id,
        language=payload.language,
        callback_window=payload.callback_window,
        reason=payload.reason,
        verification_state=_verification_state_for(session, identification.identification_id),
        created_at=datetime.now(UTC),
    )
    # No reason text, no codes, no payloads in logs — ids and outcome only.
    logger.info(
        "help request created ticket=%s status=%s verification_state=%s",
        ticket.ticket_id,
        ticket.status,
        ticket.verification_state,
    )
    return HelpTicketResponse(
        ticket_id=ticket.ticket_id,
        status=ticket.status,
        language=ticket.language,
        callback_window=ticket.callback_window,
    )


@router.get(
    "/{ticket_id}",
    response_model=HelpTicketResponse,
    summary="Read own help-request status (patient)",
    description=(
        "Returns the calling session's own ticket status. A ticket created by "
        "another session is answered exactly like an unknown ticket "
        "(safe 404). Contains no staff data, access codes, or amounts."
    ),
    operation_id="get_help_request_status",
)
async def get_help_request_status(
    ticket_id: str,
    request: Request,
    x_session_id: Annotated[str, Header(alias="X-Session-ID", min_length=20, max_length=64)],
):
    validate_session_id_format(x_session_id)
    session_store: SessionStore = request.app.state.session_store
    session = session_store.get(x_session_id)  # 404 for unknown/expired sessions

    help_store: HelpRequestStore = request.app.state.help_request_store
    ticket = help_store.get_for_session(session.session_id, ticket_id)
    if ticket is None:
        raise HelpTicketNotFoundError()

    return HelpTicketResponse(
        ticket_id=ticket.ticket_id,
        status=ticket.status,
        language=ticket.language,
        callback_window=ticket.callback_window,
    )


@staff_router.get(
    "",
    response_model=list[StaffTicketSummary],
    summary="List support requests (staff)",
    description=(
        "Lists help requests whose sharing consent is still valid (never "
        "exposes withdrawn ones). Requires the configured staff token in the "
        "``X-Support-Staff-Token`` header; fails closed when the token is not "
        "configured. No financial amounts, tokens, or codes are returned."
    ),
    operation_id="list_help_requests_staff",
    responses=_staff_error_docs(),
)
async def list_help_requests_staff(
    request: Request,
    x_support_staff_token: Annotated[str | None, Header()] = None,
):
    _staff_is_authorized(request, x_support_staff_token)

    store: HelpRequestStore = request.app.state.help_request_store
    session_store: SessionStore = request.app.state.session_store
    consented = {
        session_id: session.consent_decision == CONSENT_GRANTED
        for session_id, session in session_store._sessions.items()
    }
    tickets = store.list_shareable(consented)
    return [StaffTicketSummary(**_summary_fields(t)) for t in tickets]


@staff_router.get(
    "/{ticket_id}",
    response_model=StaffTicketDetail,
    summary="Retrieve one support request's details (staff)",
    description=(
        "Staff-facing details including the patient's verbatim reason and the "
        "deterministic, template-built case summary. Hidden entirely when the "
        "sharing consent was withdrawn."
    ),
    operation_id="get_help_request_staff",
    responses=_staff_error_docs(),
)
async def get_help_request_staff(
    ticket_id: str,
    request: Request,
    x_support_staff_token: Annotated[str | None, Header()] = None,
):
    _staff_is_authorized(request, x_support_staff_token)

    ticket = _staff_ticket_or_none(request, ticket_id)
    if ticket is None:
        raise HelpTicketNotFoundError()
    return StaffTicketDetail(
        **_summary_fields(ticket),
        reason=ticket.reason,
        summary=build_case_summary(ticket),
    )


@staff_router.post(
    "/{ticket_id}/status",
    response_model=StaffTicketSummary,
    summary="Update a support request's workflow status (staff)",
    description=(
        "Applies one forward status transition of the workflow state machine. "
        "Invalid transitions and unknown statuses are rejected. This records "
        "workflow status only; no callback or communication is performed."
    ),
    operation_id="update_help_request_status_staff",
    responses=_staff_error_docs(),
)
async def update_help_request_status_staff(
    ticket_id: str,
    payload: StaffStatusUpdate,
    request: Request,
    x_support_staff_token: Annotated[str | None, Header()] = None,
):
    _staff_is_authorized(request, x_support_staff_token)

    ticket = _staff_ticket_or_none(request, ticket_id)
    if ticket is None:
        raise HelpTicketNotFoundError()

    store: HelpRequestStore = request.app.state.help_request_store
    moved = store.transition_status(ticket_id, payload.status)
    return StaffTicketSummary(**_summary_fields(moved))
