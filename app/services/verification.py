"""Access-code verification service (Phase 3).

Owns the challenge lifecycle and the authorization decision:

- A challenge is created the moment an identification result requires an
  access code — that is the defined start of the five-minute lifetime.
- Access codes exist only as PBKDF2 digests (see ``app.services.access_codes``);
  comparisons are constant-time.
- Server-side expiry and attempt limits are enforced under a lock so repeated
  or concurrent requests cannot slip past the limits.
- Verification and amount comparison are two separate states: a valid code
  with unreliable (or absent) uploaded amounts still verifies, and the
  comparison is reported independently.

``now_fn`` is injectable so expiry boundaries are deterministically testable.
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.core.errors import (
    AccessCodeInvalidError,
    ChallengeExpiredError,
    ChallengeLockedError,
    IdentificationNotVerifiableError,
)
from app.services.access_codes import AccessCodeRecord, verify_access_code
from app.services.amount_comparison import (
    LABEL_PATIENT_PAYABLE,
    LABEL_TOTAL,
    ComparisonResult,
    LabelledAmount,
    compare_uploaded_amounts,
)
from app.services.records import BillRecordAccess
from app.services.session_store import (
    IdentificationRecord,
    PatientSession,
    SessionStore,
    VerificationChallenge,
    VerificationRecord,
)

logger = logging.getLogger(__name__)

VERIFICATION_STATUS_VERIFIED = "verified"


def _utcnow() -> datetime:
    return datetime.now(UTC)


class VerificationService:
    """Fictional in-memory verification. Not a real payment/billing service."""

    def __init__(
        self,
        *,
        records: BillRecordAccess,
        session_store: SessionStore,
        digests: dict[str, AccessCodeRecord],
        challenge_ttl_minutes: int,
        max_attempts: int,
        now_fn: Callable[[], datetime] | None = None,
    ) -> None:
        self._records = records
        self._sessions = session_store
        self._digests = digests
        self._ttl = timedelta(minutes=challenge_ttl_minutes)
        self._max_attempts = max_attempts
        self._now_fn = now_fn or _utcnow
        self._lock = threading.Lock()

    @property
    def now_fn(self) -> Callable[[], datetime]:
        """The injectable clock (exposed for tests that advance time)."""

        return self._now_fn

    @staticmethod
    def build(
        *,
        records: BillRecordAccess,
        session_store: SessionStore,
        digests: dict[str, AccessCodeRecord],
        challenge_ttl_minutes: int,
        max_attempts: int,
        now_fn: Callable[[], datetime] | None = None,
    ) -> VerificationService:
        """Explicit constructor used by the application factory and tests."""

        return VerificationService(
            records=records,
            session_store=session_store,
            digests=digests,
            challenge_ttl_minutes=challenge_ttl_minutes,
            max_attempts=max_attempts,
            now_fn=now_fn,
        )

    def provisioned_bill_ids(self) -> set[str]:
        """Bill ids with a configured code (count only; never the codes)."""

        return set(self._digests)

    def create_challenge(
        self,
        session: PatientSession,
        identification: IdentificationRecord,
        bill_id: str,
    ) -> VerificationChallenge:
        """Start the challenge for one identification (its lifetime starts now)."""

        challenge = VerificationChallenge(
            challenge_id=uuid4().hex,
            identification_id=identification.identification_id,
            bill_id=bill_id,
            created_at=self._now_fn(),
            expires_at=self._now_fn() + self._ttl,
        )
        self._sessions.set_challenge(session, challenge)
        return challenge

    def verify(
        self,
        session: PatientSession,
        identification: IdentificationRecord,
        *,
        submitted_code: str,
    ) -> tuple[VerificationRecord, ComparisonResult | None]:
        """Attempt verification. Raises on every failure mode.

        Returns the verification record plus a comparison result when the
        identification carried uploaded labelled amounts (``None`` for manual
        identifications — no comparison exists).
        """

        if identification.status != "access_code_required":
            raise IdentificationNotVerifiableError()

        with self._lock:  # repeated/concurrent attempts observe consistent state
            challenge = session.challenges.get(identification.identification_id)
            if challenge is None:
                raise ChallengeExpiredError()
            if challenge.locked:
                raise ChallengeLockedError()
            if self._now_fn() >= challenge.expires_at:
                self._sessions.drop_challenge(session, identification.identification_id)
                raise ChallengeExpiredError()

            digest_record = self._digests.get(challenge.bill_id)
            if digest_record is None or not verify_access_code(submitted_code, digest_record):
                challenge.failed_attempts += 1
                attempts_used = challenge.failed_attempts
                logger.info(
                    "access-code rejected identification=%s attempts=%d limit=%d",
                    identification.identification_id,
                    attempts_used,
                    self._max_attempts,
                )
                if attempts_used >= self._max_attempts:
                    challenge.locked = True
                    raise ChallengeLockedError()
                # 401 with the attempts-remaining delta only; never bill data.
                raise AccessCodeInvalidError(
                    "The access code is not correct. "
                    f"{max(self._max_attempts - attempts_used, 0)} "
                    "attempt(s) remain before this verification locks."
                )

            # Success: invalidate the challenge immediately (single use), then
            # evaluate the (independent) uploaded-amount comparison and record
            # verification state — including its comparison result — in memory.
            self._sessions.drop_challenge(session, identification.identification_id)
            comparison = self._compare(identification)
            record = VerificationRecord(
                verification_id=uuid4().hex,
                identification_id=identification.identification_id,
                verified_at=self._now_fn(),
                challenge_expires_at=challenge.expires_at,
                failed_attempts_before_success=challenge.failed_attempts,
                comparison=comparison,
            )
            self._sessions.record_verification(session, record)

        logger.info(
            "verification succeeded identification=%s comparison_status=%s",
            identification.identification_id,
            comparison.status if comparison else "none",
        )
        return record, comparison

    def bill_for_identification(self, identification: IdentificationRecord):
        """Public resolver for the registry bill behind an identification."""

        return self._bill_for(identification)

    def _compare(self, identification: IdentificationRecord) -> ComparisonResult | None:
        """Run the amount comparison in its own terms (independent of the code)."""

        extracted = identification.extracted or {}
        labelled_dicts = extracted.get("labelled_amounts") or []
        # "An upload happened" is a property of the identification path (OCR
        # flow), not of what could be read: manual entry stores no extracted
        # data at all, while an OCR upload stores the (possibly empty) read.
        uploaded = bool(extracted)

        if not uploaded:
            return compare_uploaded_amounts(self._bill_for(identification), [], uploaded=False)

        labelled = [
            LabelledAmount(
                label=item["label"],
                raw=item.get("raw", ""),
                minor_units=int(item["minor_units"]),
            )
            for item in labelled_dicts
            if isinstance(item, dict)
            and item.get("label") in {LABEL_TOTAL, LABEL_PATIENT_PAYABLE}
            and "minor_units" in item
        ]
        return compare_uploaded_amounts(self._bill_for(identification), labelled, uploaded=True)

    def _bill_for(self, identification: IdentificationRecord):
        """Resolve the registry bill behind an identification, or fail closed."""

        if identification.bill_number and identification.hospital_id:
            bill = self._records.find_bill_in_hospital(
                identification.bill_number, identification.hospital_id
            )
            if bill is not None:
                return bill
        raise IdentificationNotVerifiableError()
