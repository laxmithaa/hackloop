"""In-memory patient help requests (support tickets) — Phase 4.

Follows the repository's existing conventions: everything lives in process
memory only, session/identification references are stored internally, and
this module contains no HTTP logic.

This is a *workflow record* system only: nothing here ever places a real
phone call, SMS, email, or payment action, and nothing claims that a callback
was actually made. Patient-supplied reason text is strictly data: it never
influences authorization and never triggers tools.

Verification state is snapshotted at ticket creation so the deterministic
summary can name the known verification outcome without ever containing
financial amounts (only the *state name* of the outcome, e.g. 'not_verified').
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import UTC, datetime

from app.core.errors import InvalidHelpStatusTransitionError

#: Ticket statuses (forward-only workflow).
STATUS_NEW = "new"
STATUS_CALLBACK_SCHEDULED = "callback_scheduled"
STATUS_CONTACTED = "contacted"
STATUS_RESOLVED = "resolved"

#: Verification-state snapshot names. Financial values are never included.
VERIFICATION_VERIFIED_NO_UPLOAD = "verified_no_upload"
VERIFICATION_VERIFIED_MATCHED = "verified_matched"
VERIFICATION_VERIFIED_DIFFER = "verified_amounts_differ"
VERIFICATION_VERIFIED_INSUFFICIENT = "verified_comparison_unavailable"
VERIFICATION_NOT_VERIFIED = "not_verified"

#: Allowed transitions. ``resolved`` is terminal; ``new`` may go straight to
#: ``contacted`` (a worker may reach the patient immediately) or to
#: ``callback_scheduled``.
STATUS_TRANSITIONS: dict[str, frozenset[str]] = {
    STATUS_NEW: frozenset(
        {STATUS_CALLBACK_SCHEDULED, STATUS_CONTACTED, STATUS_RESOLVED}
    ),
    STATUS_CALLBACK_SCHEDULED: frozenset({STATUS_CONTACTED, STATUS_RESOLVED}),
    STATUS_CONTACTED: frozenset({STATUS_RESOLVED}),
    STATUS_RESOLVED: frozenset(),
}


def validate_status_transition(current: str, new_status: str) -> None:
    """Raise unless ``current -> new_status`` is an allowed forward transition."""

    allowed = STATUS_TRANSITIONS.get(current)
    if new_status not in (allowed or frozenset()):
        raise InvalidHelpStatusTransitionError()


@dataclass(frozen=True)
class HelpRequestTicket:
    """One patient request for a human callback.

    ``reason`` is patient free text kept verbatim as data (length-limited at
    the API boundary). ``verification_state`` snapshots the verification
    outcome at creation and never contains amounts.
    """

    ticket_id: str
    created_at: datetime
    session_id: str
    identification_id: str
    language: str
    callback_window: str
    reason: str
    verification_state: str
    status: str = STATUS_NEW
    sharing_withdrawn: bool = False


@dataclass(frozen=True)
class VerificationSnapshot:
    """Inputs used for the verification-state snapshot (no amounts)."""

    verified: bool
    comparison_status: str | None


def snapshot_verification_state(snapshot: VerificationSnapshot) -> str:
    """Deterministically name the verification outcome for a ticket."""

    if not snapshot.verified:
        return VERIFICATION_NOT_VERIFIED
    if snapshot.comparison_status is None:
        return VERIFICATION_VERIFIED_NO_UPLOAD
    if snapshot.comparison_status == "matched":
        return VERIFICATION_VERIFIED_MATCHED
    if snapshot.comparison_status == "amounts_differ":
        return VERIFICATION_VERIFIED_DIFFER
    if snapshot.comparison_status == "no_uploaded_image":
        return VERIFICATION_VERIFIED_NO_UPLOAD
    return VERIFICATION_VERIFIED_INSUFFICIENT


def build_case_summary(ticket: HelpRequestTicket) -> str:
    """Deterministic, template-driven staff summary. Ordinary logic, no AI.

    Names the nature of the request and the verification snapshot. Never
    invents facts, advice, deadlines, or amounts.
    """

    if ticket.verification_state == VERIFICATION_VERIFIED_DIFFER:
        outcome = (
            "Access-code verification succeeded, but the uploaded amounts could "
            "not be matched to the recorded amounts. Use human judgement; the "
            "mismatch does not prove fraud."
        )
    elif ticket.verification_state == VERIFICATION_VERIFIED_MATCHED:
        outcome = (
            "Access-code verification succeeded and the uploaded labelled amounts "
            "matched the recorded amounts."
        )
    elif ticket.verification_state == VERIFICATION_VERIFIED_INSUFFICIENT:
        outcome = (
            "Access-code verification succeeded, but the uploaded amounts could "
            "not be compared reliably (insufficient evidence)."
        )
    elif ticket.verification_state == VERIFICATION_VERIFIED_NO_UPLOAD:
        outcome = (
            "Access-code verification succeeded with no bill image uploaded, "
            "so no amount comparison exists."
        )
    else:
        outcome = (
            "The bill has not been verified (unverified). Do not treat the bill "
            "or any amounts as confirmed."
        )
    return (
        f"Patient requests a '{ticket.callback_window}' callback in "
        f"'{ticket.language}'. Verification state: {ticket.verification_state} — "
        f"{outcome} Patient's stated reason (verbatim): \u201c{ticket.reason}\u201d"
    )


class HelpRequestStore:
    """Owns all help-request tickets. Thread-safe, purely in-memory."""

    def __init__(self) -> None:
        self._tickets: dict[str, HelpRequestTicket] = {}

    def create(
        self,
        *,
        ticket_id: str,
        session_id: str,
        identification_id: str,
        language: str,
        callback_window: str,
        reason: str,
        verification_state: str,
        created_at: datetime | None = None,
    ) -> HelpRequestTicket:
        ticket = HelpRequestTicket(
            ticket_id=ticket_id,
            created_at=created_at or datetime.now(UTC),
            session_id=session_id,
            identification_id=identification_id,
            language=language,
            callback_window=callback_window,
            reason=reason,
            verification_state=verification_state,
        )
        self._tickets[ticket_id] = ticket
        return ticket

    def get(self, ticket_id: str) -> HelpRequestTicket | None:
        return self._tickets.get(ticket_id)

    def get_for_session(self, session_id: str, ticket_id: str) -> HelpRequestTicket | None:
        """Ticket lookup restricted to one owning session (patient isolation)."""

        ticket = self._tickets.get(ticket_id)
        if ticket is None or ticket.session_id != session_id:
            return None
        return ticket

    def list_shareable(self, session_consented: dict[str, bool]) -> list[HelpRequestTicket]:
        """Staff listing: only sharing-consented, non-withdrawn requests.

        ``session_consented`` maps session id -> whether its consent is still
        granted, so withdrawn *session* consent also hides the request.
        """

        return [
            ticket
            for ticket in self._tickets.values()
            if not ticket.sharing_withdrawn and session_consented.get(ticket.session_id, False)
        ]

    def mark_session_sharing_withdrawn(self, session_id: str) -> None:
        """Explicit internal flag when the session's consent is withdrawn."""

        for ticket in self._tickets.values():
            if not ticket.sharing_withdrawn and ticket.session_id == session_id:
                self._tickets[ticket.ticket_id] = replace(
                    ticket, sharing_withdrawn=True
                )

    def transition_status(self, ticket_id: str, new_status: str) -> HelpRequestTicket:
        """Small explicit transition function; rejects invalid transitions."""

        ticket = self._tickets.get(ticket_id)
        if ticket is None:
            return None
        validate_status_transition(ticket.status, new_status)
        moved = replace(ticket, status=new_status)
        self._tickets[ticket_id] = moved
        return moved

    def tickets_for_session(self, session_id: str) -> list[HelpRequestTicket]:
        return [t for t in self._tickets.values() if t.session_id == session_id]

    def __len__(self) -> int:
        return len(self._tickets)

    def __repr__(self) -> str:
        # Never reveal stored reason text, ids or counts in repr.
        return "HelpRequestStore(<redacted>)"
