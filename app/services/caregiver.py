"""Part C: authorized caregiver summaries.

Authorization model (in memory, no database):

- The patient's own session, with consent still granted and a successfully
  verified bill, creates a *share* and receives a random share code once.
- Only a SHA-256 digest of that code is stored, so the service cannot replay
  it; comparisons are constant-time.
- Share codes expire, can be revoked by the patient, and are limited per bill
  and per session, so a leaked/guessed identifier is never enough.
- Every summary request re-validates the *patient's* session, consent and
  verification; a share is not a standing grant and does not survive consent
  withdrawal, session expiry or process restart.

The summary is a fixed template populated from verified structured data. The
local model may only re-word it; any failure or unsafe output falls back to
the template. Nothing here decides whether a charge is correct or whether the
patient should pay.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import secrets
import threading
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.core.errors import CaregiverShareLimitError
from app.services.ai_validation import UNSUPPORTED_CLAIM_PATTERNS, validate_generated
from app.services.bill_facts import (
    ExplanationFacts,
    facts_summary_lines,
    recorded_amounts,
    recorded_dates,
    render_amount,
)
from app.services.bill_glossary import comparison_sentence
from app.services.ollama_client import OllamaChatClient, OllamaChatError

logger = logging.getLogger(__name__)

CAREGIVER_SOURCE_GENERATED = "generated"
CAREGIVER_SOURCE_FALLBACK = "fallback"

_LANGUAGES = {"en": "English", "hi": "Hindi", "kn": "Kannada"}


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _digest(code: str) -> str:
    return hashlib.sha256(code.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class CaregiverShare:
    """One consent record for sharing a single verified bill."""

    share_id: str
    identification_id: str
    session_id: str
    language: str
    created_at: datetime
    expires_at: datetime


@dataclass
class _ShareEntry:
    share: CaregiverShare
    digest: str


class CaregiverShareStore:
    """In-memory, thread-safe store of caregiver share grants.

    ``now_fn`` is injectable so expiry is deterministically testable. All state
    is lost on restart, which also invalidates every outstanding code.
    """

    def __init__(
        self,
        *,
        ttl_minutes: int = 60,
        now_fn: Callable[[], datetime] | None = None,
        max_per_identification: int = 3,
        max_per_session: int = 10,
    ) -> None:
        self._ttl = timedelta(minutes=ttl_minutes)
        self._now_fn = now_fn or _utcnow
        self._max_per_identification = max_per_identification
        self._max_per_session = max_per_session
        self._shares: dict[str, _ShareEntry] = {}
        self._lock = threading.Lock()

    def create(
        self, *, identification_id: str, session_id: str, language: str
    ) -> tuple[CaregiverShare, str]:
        """Mint a share and its one-time display code. Raises on limits."""

        now = self._now_fn()
        with self._lock:
            self._prune_locked(now)
            by_bill = sum(
                1
                for entry in self._shares.values()
                if entry.share.identification_id == identification_id
            )
            if by_bill >= self._max_per_identification:
                raise CaregiverShareLimitError(
                    "Too many active caregiver shares exist for this bill. "
                    "Revoke an existing share first."
                )
            by_session = sum(
                1 for entry in self._shares.values() if entry.share.session_id == session_id
            )
            if by_session >= self._max_per_session:
                raise CaregiverShareLimitError(
                    "Too many active caregiver shares exist for this session. "
                    "Revoke an existing share first."
                )

            code = secrets.token_urlsafe(24)
            share = CaregiverShare(
                share_id=uuid4().hex,
                identification_id=identification_id,
                session_id=session_id,
                language=language,
                created_at=now,
                expires_at=now + self._ttl,
            )
            self._shares[share.share_id] = _ShareEntry(share=share, digest=_digest(code))
            logger.info(
                "caregiver share created identification=%s expires_at=%s",
                identification_id,
                share.expires_at.isoformat(),
            )
            return share, code

    def authorize(self, identification_id: str, code: str | None) -> CaregiverShare | None:
        """Resolve a share for *this* bill from a presented code, or ``None``.

        Expired entries are pruned first; comparison is constant-time.
        """

        if not code:
            return None
        candidate = _digest(code)
        now = self._now_fn()
        with self._lock:
            self._prune_locked(now)
            for entry in self._shares.values():
                if entry.share.identification_id != identification_id:
                    continue
                if hmac.compare_digest(entry.digest, candidate):
                    return entry.share
        return None

    def revoke_identification(self, identification_id: str) -> int:
        """Revoke every active share for one bill (patient-initiated)."""

        with self._lock:
            stale = [
                share_id
                for share_id, entry in self._shares.items()
                if entry.share.identification_id == identification_id
            ]
            for share_id in stale:
                self._shares.pop(share_id, None)
        return len(stale)

    def revoke_session(self, session_id: str) -> int:
        """Drop every share minted by one session (session expiry/withdrawal)."""

        with self._lock:
            stale = [
                share_id
                for share_id, entry in self._shares.items()
                if entry.share.session_id == session_id
            ]
            for share_id in stale:
                self._shares.pop(share_id, None)
        return len(stale)

    def active_count(self) -> int:
        """Current number of live shares (for diagnostics/tests)."""

        now = self._now_fn()
        with self._lock:
            self._prune_locked(now)
            return len(self._shares)

    def _prune_locked(self, now: datetime) -> None:
        stale = [
            share_id for share_id, entry in self._shares.items() if entry.share.expires_at <= now
        ]
        for share_id in stale:
            self._shares.pop(share_id, None)


# --- Summary ---------------------------------------------------------------------


@dataclass(frozen=True)
class CaregiverSummaryOutcome:
    """The summary text plus which layer produced it."""

    text: str
    source: str
    reason: str | None = None


def caregiver_template(facts: ExplanationFacts, language: str) -> str:
    """Fixed \"What you need to know\" block built only from recorded values."""

    total = render_amount(facts.total_minor_units)
    payable = render_amount(facts.patient_payable_minor_units)
    message = comparison_sentence(facts, language)

    if language == "hi":
        return "\n".join(
            [
                "जानने योग्य बातें:",
                f"अस्पताल: {facts.hospital_name}",
                f"बिल: {facts.bill_number}, दिनांक {facts.bill_date}",
                f"रिकॉर्ड में कुल बिल राशि: {total}",
                f"रिकॉर्ड में रोगी द्वारा देय राशि: {payable}",
                "सत्यापन: यह बिल एक्सेस कोड सत्यापन से गुजर चुका है",
                f"अपलोड की गई राशियों की तुलना: {message}",
                (
                    "देय राशि रोगी का हिस्सा है; कुल राशि बिल पर छपी पूरी राशि है। "
                    "सत्यापन का अर्थ यह नहीं कि शुल्क सही हैं।"
                ),
                "किसी भी स्पष्टीकरण के लिए अस्पताल के बिलिंग डेस्क से संपर्क करें।",
            ]
        )
    if language == "kn":
        return "\n".join(
            [
                "ತಿಳಿಯಬೇಕಾದ ಅಂಶಗಳು:",
                f"ಆಸ್ಪತ್ರೆ: {facts.hospital_name}",
                f"ಬಿಲ್: {facts.bill_number}, ದಿನಾಂಕ {facts.bill_date}",
                f"ದಾಖಲೆಯಲ್ಲಿ ಒಟ್ಟು ಬಿಲ್ ಮೊತ್ತ: {total}",
                f"ದಾಖಲೆಯಲ್ಲಿ ರೋಗಿ ಪಾವತಿಸಬೇಕಾದ ಮೊತ್ತ: {payable}",
                "ಪರಿಶೀಲನೆ: ಈ ಬಿಲ್ ಪ್ರವೇಶ ಕೋಡ್ ಪರಿಶೀಲನೆಯಲ್ಲಿ ಯಶಸ್ವಿಯಾಗಿದೆ",
                f"ಅಪ್‌ಲೋಡ್ ಮಾಡಿದ ಮೊತ್ತಗಳ ಹೋಲಿಕೆ: {message}",
                (
                    "ಪಾವತಿಸಬೇಕಾದ ಮೊತ್ತ ರೋಗಿಯ ಪಾಲು; ಒಟ್ಟು ಮೊತ್ತ ಬಿಲ್‌ನಲ್ಲಿ "
                    "ಮುದ್ರಿಸಿರುವ ಪೂರ್ಣ ಮೊತ್ತ. ಪರಿಶೀಲನೆ ಎಂದರೆ ಶುಲ್ಕಗಳು ಸರಿಯಾಗಿವೆ "
                    "ಎಂದಲ್ಲ."
                ),
                "ಸ್ಪಷ್ಟನೆಗಾಗಿ ಆಸ್ಪತ್ರೆಯ ಬಿಲ್ಲಿಂಗ್ ಡೆಸ್ಕ್ ಸಂಪರ್ಕಿಸಿ.",
            ]
        )
    return "\n".join(
        [
            "What you need to know:",
            f"Hospital: {facts.hospital_name}",
            f"Bill: {facts.bill_number}, dated {facts.bill_date}",
            f"Recorded total bill amount: {total}",
            f"Recorded amount payable by the patient: {payable}",
            "Verification: this bill passed access-code verification",
            f"Uploaded-amount comparison: {message}",
            (
                "The payable amount is the patient's share; the total is the full "
                "amount printed on the bill. Verification does not mean the charges "
                "are correct."
            ),
            "For any clarification, contact the hospital billing desk.",
        ]
    )


_SYSTEM_PROMPT = (
    "You are a careful hospital-bill explainer inside a regulated prototype. You "
    "rewrite one approved caregiver summary for a family member.\n"
    "Rules you must follow:\n"
    "- Change wording only. Never add, remove, change, round or estimate any "
    "amount, date, insurance detail, deadline or other fact.\n"
    "- Keep the total bill amount and the amount payable by the patient distinct.\n"
    "- Never say a charge is correct, incorrect or overcharged, and never say "
    "whether the patient should pay.\n"
    "- Keep the pointer to the hospital billing desk.\n"
    "- Output only the rewritten text: no lists, headings, markdown or notes, at "
    "most 4 short sentences."
)


class CaregiverSummaryService:
    """Produces the caregiver summary: template first, optional validated rewrite."""

    def __init__(self, client: OllamaChatClient, *, max_chars: int = 900) -> None:
        self._client = client
        self._max_chars = max_chars

    async def summarize(self, facts: ExplanationFacts, language: str) -> CaregiverSummaryOutcome:
        template = caregiver_template(facts, language)
        language_name = _LANGUAGES[language]

        try:
            generated = await self._client.generate(
                system=_SYSTEM_PROMPT,
                user="\n".join(
                    [
                        f"Rewrite this approved caregiver summary in {language_name} "
                        f"({language}), keeping every amount and date exactly.",
                        "Approved summary:",
                        "<<<",
                        template,
                        ">>>",
                        "Authoritative bill summary (reference only):",
                        *facts_summary_lines(facts),
                        f"Answer in {language_name}.",
                    ]
                ),
            )
        except OllamaChatError as exc:
            logger.info("caregiver summary fell back (%s)", exc)
            return CaregiverSummaryOutcome(
                text=template, source=CAREGIVER_SOURCE_FALLBACK, reason=str(exc)
            )

        problems = validate_generated(
            generated,
            language=language,
            allowed_minor_units=recorded_amounts(facts),
            allowed_iso_dates=recorded_dates(facts),
            forbidden_patterns=UNSUPPORTED_CLAIM_PATTERNS,
            max_chars=self._max_chars,
            total_minor_units=facts.total_minor_units,
            patient_payable_minor_units=facts.patient_payable_minor_units,
        )
        if problems:
            logger.info(
                "caregiver summary rejected (%d problem(s)); falling back",
                len(problems),
            )
            return CaregiverSummaryOutcome(
                text=template, source=CAREGIVER_SOURCE_FALLBACK, reason=problems[0]
            )

        return CaregiverSummaryOutcome(text=generated, source=CAREGIVER_SOURCE_GENERATED)
