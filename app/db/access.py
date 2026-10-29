"""Access-code verification: sessions, attempt limits, and gated reads.

Flow for the API:
  1. lookup_bill(...)                    -> identify the bill (no amounts)
  2. start_verification(bill_id)         -> opens a short code-entry window
  3. submit_access_code(session, code)   -> ok / invalid / locked_out / expired
  4. get_verified_record(session)        -> the amounts, ONLY if step 3 was ok
  5. count_question(session)             -> cap on free-text follow-up questions
"""

import asyncio
import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

import bcrypt
from psycopg import AsyncConnection

from .lookup import load_record_unchecked
from .models import IssuedCode, VerificationSession, VerifiedRecord, VerifyResult
from .settings import DbSettings, get_db_settings

# No 0/O or 1/I, so codes typed from a printout are not mixed up.
_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
# Compared against when a bill has no code, so response time does not reveal it.
_DUMMY_HASH = bcrypt.hashpw(b"dummy", bcrypt.gensalt(rounds=4))


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _normalise(code: str) -> bytes:
    return code.strip().upper()[:128].encode()


async def issue_access_code(conn: AsyncConnection, bill_id: UUID) -> IssuedCode:
    """Create the printed code for a bill and revoke any older one.

    The plain code is returned once, to be printed on the bill. Only a
    bcrypt hash is stored.
    """
    pick = secrets.choice
    code = "-".join("".join(pick(_ALPHABET) for _ in range(4)) for _ in range(2))
    code_hash = await asyncio.to_thread(
        lambda: bcrypt.hashpw(code.encode(), bcrypt.gensalt(rounds=10)).decode()
    )
    async with conn.cursor() as cur:
        await cur.execute(
            "update access_codes set revoked_at = now() where bill_id = %s and revoked_at is null",
            (bill_id,),
        )
        await cur.execute(
            "insert into access_codes (bill_id, code_hash) values (%s, %s) returning id",
            (bill_id, code_hash),
        )
        row = await cur.fetchone()
    return IssuedCode(access_code_id=row["id"], code=code)


async def start_verification(
    conn: AsyncConnection,
    bill_id: UUID,
    *,
    now: datetime | None = None,
    settings: DbSettings | None = None,
) -> VerificationSession:
    s = settings or get_db_settings()
    now = now or _utcnow()
    expires = now + timedelta(minutes=s.access_entry_window_minutes)
    async with conn.cursor() as cur:
        await cur.execute(
            """insert into verification_sessions
                 (bill_id, created_at, entry_expires_at, max_attempts)
               values (%s, %s, %s, %s)
               returning id, bill_id, entry_expires_at, max_attempts""",
            (bill_id, now, expires, s.access_max_attempts),
        )
        row = await cur.fetchone()
    return VerificationSession(
        session_id=row["id"],
        bill_id=row["bill_id"],
        entry_expires_at=row["entry_expires_at"],
        max_attempts=row["max_attempts"],
    )


async def submit_access_code(
    conn: AsyncConnection,
    session_id: UUID,
    code: str,
    *,
    now: datetime | None = None,
    settings: DbSettings | None = None,
) -> VerifyResult:
    """Check a code. Wrong guesses are counted and capped per session.

    The session row is locked (FOR UPDATE) so simultaneous guesses cannot
    slip past the counter. When the last attempt fails the result carries
    escalate=True (the "repeated failed access codes" trigger).

    API tip: show the SAME message for "invalid" and "not_found".
    """
    s = settings or get_db_settings()
    now = now or _utcnow()

    async with conn.cursor() as cur:
        await cur.execute(
            """select id, bill_id, entry_expires_at, max_attempts, failed_attempts,
                      verified_at, session_expires_at
                 from verification_sessions where id = %s for update""",
            (session_id,),
        )
        session = await cur.fetchone()
        if session is None:
            return VerifyResult(status="not_found")

        if session["verified_at"] is not None:
            if session["session_expires_at"] > now:
                return VerifyResult(status="ok")  # already unlocked
            return VerifyResult(status="expired")

        if session["entry_expires_at"] <= now:
            return VerifyResult(status="expired")

        max_attempts = session["max_attempts"]
        failed = session["failed_attempts"]
        if failed >= max_attempts:
            return VerifyResult(status="locked_out", attempts_left=0, escalate=True)

        await cur.execute(
            """select code_hash from access_codes
                where bill_id = %s and revoked_at is null
                order by created_at desc limit 1""",
            (session["bill_id"],),
        )
        stored = await cur.fetchone()
        stored_hash = stored["code_hash"].encode() if stored else _DUMMY_HASH
        matches = await asyncio.to_thread(bcrypt.checkpw, _normalise(code), stored_hash)

        if matches and stored is not None:
            session_end = now + timedelta(minutes=s.verified_session_minutes)
            await cur.execute(
                "update verification_sessions "
                "set verified_at = %s, session_expires_at = %s where id = %s",
                (now, session_end, session_id),
            )
            return VerifyResult(status="ok")

        failed += 1
        await cur.execute(
            "update verification_sessions set failed_attempts = %s where id = %s",
            (failed, session_id),
        )
        left = max_attempts - failed
        if left <= 0:
            return VerifyResult(status="locked_out", attempts_left=0, escalate=True)
        return VerifyResult(status="invalid", attempts_left=left)


async def get_verified_record(
    conn: AsyncConnection, session_id: UUID, *, now: datetime | None = None
) -> VerifiedRecord | None:
    """The ONLY route to the amounts. None if the session is not verified,
    has expired, or does not exist (the API should answer 401/403)."""
    now = now or _utcnow()
    async with conn.cursor() as cur:
        await cur.execute(
            "select bill_id, verified_at, session_expires_at "
            "from verification_sessions where id = %s",
            (session_id,),
        )
        session = await cur.fetchone()
    if session is None or session["verified_at"] is None or session["session_expires_at"] <= now:
        return None
    return await load_record_unchecked(conn, session["bill_id"])


async def count_question(
    conn: AsyncConnection,
    session_id: UUID,
    *,
    now: datetime | None = None,
    settings: DbSettings | None = None,
) -> bool:
    """Use up one free-text question. False once the per-session cap is hit
    (or the session is not verified / expired). Atomic: one SQL statement."""
    s = settings or get_db_settings()
    now = now or _utcnow()
    async with conn.cursor() as cur:
        await cur.execute(
            """update verification_sessions
                  set question_count = question_count + 1
                where id = %s
                  and verified_at is not null
                  and session_expires_at > %s
                  and question_count < %s
            returning question_count""",
            (session_id, now, s.max_questions_per_session),
        )
        return await cur.fetchone() is not None
