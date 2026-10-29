"""Help requests (callback tickets) and the support-worker dashboard."""

import secrets
from uuid import UUID

from psycopg import AsyncConnection

from .models import (
    CallbackRequest,
    CallbackTicket,
    Escalation,
    SupportWorker,
    TicketStatus,
    TicketSummary,
    Triage,
)

_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
_STATUS_ORDER: tuple[TicketStatus, ...] = (
    "new",
    "callback_scheduled",
    "contacted",
    "resolved",
)

_SUMMARY_COLUMNS = """ticket_id, short_code, status, preferred_language,
    effective_language, callback_time, reason, patient_name, phone_number,
    case_summary, triage_suggestion, triage_final, escalation_reason,
    assigned_to, created_at"""


class InvalidTransition(ValueError):
    """A ticket may only move forward: new -> scheduled -> contacted -> resolved."""


def _new_short_code() -> str:
    return "HB-" + "".join(secrets.choice(_CODE_ALPHABET) for _ in range(6))


async def create_callback_ticket(
    conn: AsyncConnection,
    request: CallbackRequest,
    *,
    bill_id: UUID | None = None,
    escalation_reason: Escalation | None = None,
) -> CallbackTicket:
    """Save a help request. Consent is enforced by the model and by the table.

    A language we do not serve falls back to English and the ticket is
    flagged 'unsupported_language' so a human knows to check.
    """
    async with conn.cursor() as cur:
        await cur.execute(
            "select code from languages where code = %s and supported",
            (request.preferred_language,),
        )
        language = await cur.fetchone()
        effective = language["code"] if language else "en"
        if language is None and escalation_reason is None:
            escalation_reason = "unsupported_language"

        for _ in range(5):  # retry on the (very unlikely) short-code clash
            await cur.execute(
                """insert into callback_tickets
                     (short_code, bill_id, preferred_language, effective_language,
                      callback_time, reason, patient_name, phone_number,
                      consent_to_callback, escalation_reason)
                   values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                   on conflict (short_code) do nothing
                   returning ticket_id, short_code, status, effective_language,
                             created_at""",
                (
                    _new_short_code(),
                    bill_id,
                    request.preferred_language,
                    effective,
                    request.callback_time,
                    request.reason,
                    request.patient_name,
                    request.phone_number,
                    request.consent_to_callback,
                    escalation_reason,
                ),
            )
            row = await cur.fetchone()
            if row is not None:
                return CallbackTicket(**row)
    raise RuntimeError("Could not allocate a unique ticket code.")


async def list_support_workers(
    conn: AsyncConnection, hospital_id: UUID | None = None
) -> list[SupportWorker]:
    """People for the 'Viewing as' dropdown."""
    sql = "select id as worker_id, name, role, languages from support_workers where active"
    params: tuple = ()
    if hospital_id is not None:
        sql += " and hospital_id = %s"
        params = (hospital_id,)
    async with conn.cursor() as cur:
        await cur.execute(sql + " order by name", params)
        return [SupportWorker(**r) for r in await cur.fetchall()]


async def list_tickets(
    conn: AsyncConnection,
    *,
    status: TicketStatus | None = None,
    assigned_to: UUID | None = None,
) -> list[TicketSummary]:
    """Dashboard rows, oldest first. Contains contact details: only expose
    this to authenticated support workers."""
    where, params = [], []
    if status is not None:
        where.append("status = %s")
        params.append(status)
    if assigned_to is not None:
        where.append("assigned_to = %s")
        params.append(assigned_to)
    sql = f"select {_SUMMARY_COLUMNS} from callback_tickets"
    if where:
        sql += " where " + " and ".join(where)
    async with conn.cursor() as cur:
        await cur.execute(sql + " order by created_at", params)
        return [TicketSummary(**r) for r in await cur.fetchall()]


async def update_ticket_status(
    conn: AsyncConnection,
    ticket_id: UUID,
    new_status: TicketStatus,
    *,
    worker_id: UUID | None = None,
) -> None:
    """Move a ticket forward (and optionally assign it to a worker)."""
    async with conn.cursor() as cur:
        await cur.execute(
            "select status from callback_tickets where ticket_id = %s for update",
            (ticket_id,),
        )
        row = await cur.fetchone()
        if row is None:
            raise LookupError(f"No ticket {ticket_id}")
        if _STATUS_ORDER.index(new_status) <= _STATUS_ORDER.index(row["status"]):
            raise InvalidTransition(f"{row['status']} -> {new_status}")
        await cur.execute(
            "update callback_tickets set status = %s, "
            "assigned_to = coalesce(%s, assigned_to) where ticket_id = %s",
            (new_status, worker_id, ticket_id),
        )


async def set_case_summary(
    conn: AsyncConnection,
    ticket_id: UUID,
    case_summary: str,
    triage_suggestion: Triage | None = None,
) -> None:
    """Store the generated case summary and the AI's triage SUGGESTION."""
    async with conn.cursor() as cur:
        await cur.execute(
            "update callback_tickets set case_summary = %s, triage_suggestion = %s "
            "where ticket_id = %s",
            (case_summary, triage_suggestion, ticket_id),
        )


async def set_triage_final(conn: AsyncConnection, ticket_id: UUID, triage_final: Triage) -> None:
    """The worker's own choice. The suggestion is never overwritten."""
    async with conn.cursor() as cur:
        await cur.execute(
            "update callback_tickets set triage_final = %s where ticket_id = %s",
            (triage_final, ticket_id),
        )


async def withdraw_consent(conn: AsyncConnection, ticket_id: UUID) -> None:
    """Patient withdrew consent: record it and flag the ticket for a human."""
    async with conn.cursor() as cur:
        await cur.execute(
            "update callback_tickets set consent_withdrawn_at = now(), "
            "escalation_reason = 'consent_withdrawn' where ticket_id = %s",
            (ticket_id,),
        )
