"""Temporary in-memory patient sessions and consent records.

Everything in this module lives in process memory only: sessions, consent
decisions and identification records are lost when the application restarts.
Nothing is ever written to disk.

Session identifiers are unpredictable (``secrets.token_urlsafe``), not
sequential or derived from patient data, so they cannot be guessed.
"""

from __future__ import annotations

import secrets
import threading
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from app.core.errors import SessionExpiredError, SessionNotFoundError
from app.services.amount_comparison import ComparisonResult

CONSENT_GRANTED = "granted"
CONSENT_WITHDRAWN = "withdrawn"


def _utcnow() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True)
class IdentificationRecord:
    """One completed identification attempt inside a session.

    ``extracted`` keeps raw OCR candidates (bill dates, monetary strings) for a
    later verification phase. These values are never serialised into API
    responses; that would leak financial information before verification.
    """

    identification_id: str
    created_at: datetime
    status: str
    hospital_id: str | None = None
    hospital_name: str | None = None
    bill_number: str | None = None
    extracted: dict[str, list[str]] = field(default_factory=dict)


@dataclass
class VerificationChallenge:
    """One server-owned access-code challenge for a single identification.

    Created at identification time (that is the challenge lifetime's defined
    starting point). Only bookkeeping lives here — the access code itself is
    held as a PBKDF2 digest by the verification service, never in the session.
    Mutations (attempt counting, locking) happen under the verification
    service's lock.
    """

    challenge_id: str
    identification_id: str
    bill_id: str
    created_at: datetime
    expires_at: datetime
    failed_attempts: int = 0
    locked: bool = False


@dataclass(frozen=True)
class VerificationRecord:
    """The outcome of one successful access-code verification, kept in memory.

    ``comparison`` stays separate: verification success is recorded even when
    the uploaded amounts could not be compared reliably.
    """

    verification_id: str
    identification_id: str
    verified_at: datetime
    challenge_expires_at: datetime
    failed_attempts_before_success: int = 0
    comparison: ComparisonResult | None = None


@dataclass
class PatientSession:
    """One anonymous patient workflow, kept until it expires or the process ends."""

    session_id: str
    created_at: datetime
    consent_decision: str | None = None
    consent_policy_version: str | None = None
    consent_recorded_at: datetime | None = None
    identifications: list[IdentificationRecord] = field(default_factory=list)
    challenges: dict[str, VerificationChallenge] = field(default_factory=dict)
    verifications: dict[str, VerificationRecord] = field(default_factory=dict)
    #: Phase 9: follow-up questions asked through this session. Kept in memory
    #: only; reset when consent is withdrawn and lost on restart.
    ai_questions_asked: int = 0

    @property
    def consent_recorded(self) -> bool:
        return self.consent_decision in {CONSENT_GRANTED, CONSENT_WITHDRAWN}

    @property
    def processing_allowed(self) -> bool:
        return self.consent_decision == CONSENT_GRANTED


class SessionStore:
    """Owns all temporary sessions. Thread-safe, purely in-memory."""

    def __init__(self, ttl_minutes: int) -> None:
        self._ttl = timedelta(minutes=ttl_minutes)
        self._sessions: dict[str, PatientSession] = {}
        self._lock = threading.Lock()

    def create(self) -> PatientSession:
        session = PatientSession(
            session_id=secrets.token_urlsafe(32),
            created_at=_utcnow(),
        )
        with self._lock:
            self._sessions[session.session_id] = session
        return session

    def get(self, session_id: str) -> PatientSession:
        """Return a live session or raise the appropriate error.

        Expired sessions are reported distinct from unknown ones and are evicted
        so that their memory is reclaimed even if nobody touches them again.
        """

        session = self._sessions.get(session_id)
        if session is None:
            raise SessionNotFoundError()
        if _utcnow() - session.created_at >= self._ttl:
            with self._lock:
                self._sessions.pop(session_id, None)
            raise SessionExpiredError()
        return session

    def record_consent(
        self,
        session: PatientSession,
        *,
        decision: str = CONSENT_GRANTED,
        policy_version: str,
        recorded_at: datetime | None = None,
    ) -> None:
        """Overwrite the consent state; the server never trusts the client twice."""

        session.consent_decision = decision
        session.consent_policy_version = policy_version
        session.consent_recorded_at = recorded_at or _utcnow()

    def withdraw_consent(self, session: PatientSession) -> None:
        """Withdraw consent; further bill processing through this session is blocked."""

        session.consent_decision = CONSENT_WITHDRAWN
        session.consent_recorded_at = _utcnow()

    def add_identification(self, session: PatientSession, record: IdentificationRecord) -> None:
        session.identifications.append(record)

    def get_identification(self, session: PatientSession, identification_id: str):
        """One identification **of this session** by id, or ``None``.

        Callers treat ``None`` as 'does not exist in this session'; a correct id
        belonging to another session must produce the same answer.
        """

        for record in session.identifications:
            if record.identification_id == identification_id:
                return record
        return None

    def set_challenge(self, session: PatientSession, challenge: VerificationChallenge) -> None:
        """Register a challenge keyed by its identification id."""

        with self._lock:
            session.challenges[challenge.identification_id] = challenge

    def drop_challenge(self, session: PatientSession, identification_id: str) -> None:
        """Invalidate a challenge (used or expired)."""

        with self._lock:
            session.challenges.pop(identification_id, None)

    def record_verification(self, session: PatientSession, record: VerificationRecord) -> None:
        """Mark one identification of this session as verified."""

        with self._lock:
            session.verifications[record.identification_id] = record

    def consume_ai_question(self, session: PatientSession, *, limit: int) -> int | None:
        """Atomically count one accepted question.

        Returns the number of questions still available after this one, or
        ``None`` when the session has exhausted its budget (the caller then
        raises the rate-limit error **before** any generation). The budget is
        per session and enforced here, in the backend, so a client cannot
        raise it.
        """

        with self._lock:
            if session.ai_questions_asked >= limit:
                return None
            session.ai_questions_asked += 1
            return limit - session.ai_questions_asked

    def reset_ai_state(self, session: PatientSession) -> None:
        """Drop Phase 9 conversation bookkeeping (consent withdrawn/revoked)."""

        with self._lock:
            session.ai_questions_asked = 0
