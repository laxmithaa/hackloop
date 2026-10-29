"""AI-generation log, consent records, and the evaluation summary."""

import re
from uuid import UUID

from psycopg import AsyncConnection

CheckerResult = str  # pass | failed_regenerated | fallback_template | not_applicable

# Safety net, not a guarantee: logs must hold no contact details.
_PHONE_LIKE = re.compile(r"(?<!\d)(?:\+91|0)?\d{10}(?!\d)")


async def log_generated_text(
    conn: AsyncConnection,
    *,
    bill_id: UUID | None,
    feature: str,
    language: str,
    prompt_version: str,
    body: str,
    checker_result: CheckerResult,
    model: str | None = None,
) -> UUID:
    """Log one AI text with its record ID, prompt version and checker result.

    Never pass patient names, IDs or contact details. A phone-number-like
    string is rejected as a last line of defence.
    """
    if _PHONE_LIKE.search(body):
        raise ValueError("Generated text looks like it contains a phone number.")
    async with conn.cursor() as cur:
        await cur.execute(
            """insert into generated_texts
                 (bill_id, feature, language, prompt_version, model, body, checker_result)
               values (%s, %s, %s, %s, %s, %s, %s) returning id""",
            (bill_id, feature, language, prompt_version, model, body, checker_result),
        )
        row = await cur.fetchone()
    return row["id"]


async def checker_pass_rates(conn: AsyncConnection) -> dict[str, int]:
    """Counts per checker result, for the evaluation summary. Built from the
    log, not from generated text."""
    async with conn.cursor() as cur:
        await cur.execute(
            "select checker_result, count(*) as n from generated_texts group by checker_result"
        )
        return {r["checker_result"]: r["n"] for r in await cur.fetchall()}


async def record_consent(
    conn: AsyncConnection,
    *,
    purpose: str,
    language: str,
    bill_id: UUID | None = None,
    session_id: UUID | None = None,
    notice_version: str = "v1",
) -> UUID:
    """Record consent BEFORE processing (purpose: 'process_bill' or 'callback')."""
    async with conn.cursor() as cur:
        await cur.execute(
            """insert into consents (session_id, bill_id, purpose, language, notice_version)
               values (%s, %s, %s, %s, %s) returning id""",
            (session_id, bill_id, purpose, language, notice_version),
        )
        row = await cur.fetchone()
    return row["id"]
