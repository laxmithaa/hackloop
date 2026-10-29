import psycopg
import pytest
from pydantic import ValidationError

from app.db import (
    InvalidTransition,
    checker_pass_rates,
    create_callback_ticket,
    list_support_workers,
    list_tickets,
    log_generated_text,
    record_consent,
    set_case_summary,
    set_triage_final,
    update_ticket_status,
    withdraw_consent,
)
from app.db.models import CallbackRequest

from .conftest import BILL_1

pytestmark = pytest.mark.asyncio


def _request(**overrides):
    data = {
        "preferred_language": "hi",
        "callback_time": "morning",
        "reason": "Need help understanding my bill",
        "patient_name": "Asha Rao",
        "phone_number": "9876543210",
        "consent_to_callback": True,
    }
    data.update(overrides)
    return CallbackRequest(**data)


async def test_ticket_is_saved_with_a_short_code(conn):
    ticket = await create_callback_ticket(conn, _request(), bill_id=BILL_1)
    assert ticket.status == "new"
    assert ticket.short_code.startswith("HB-") and len(ticket.short_code) == 9
    assert ticket.effective_language == "hi"


async def test_consent_is_required(conn):
    with pytest.raises(ValidationError):
        _request(consent_to_callback=False)


async def test_database_also_refuses_a_ticket_without_consent(conn):
    with pytest.raises(psycopg.errors.CheckViolation):
        await conn.execute(
            """insert into callback_tickets
                 (short_code, preferred_language, effective_language, callback_time,
                  reason, patient_name, phone_number, consent_to_callback)
               values ('HB-TEST01', 'en', 'en', 'now', 'no consent', 'Test Person',
                       '9876543210', false)"""
        )


async def test_unsupported_language_falls_back_to_english_and_is_flagged(conn):
    ticket = await create_callback_ticket(conn, _request(preferred_language="ta"))
    assert ticket.effective_language == "en"
    rows = await list_tickets(conn, status="new")
    row = next(r for r in rows if r.ticket_id == ticket.ticket_id)
    assert row.preferred_language == "ta"
    assert row.escalation_reason == "unsupported_language"


async def test_status_only_moves_forward(conn):
    ticket = await create_callback_ticket(conn, _request())
    await update_ticket_status(conn, ticket.ticket_id, "callback_scheduled")
    await update_ticket_status(conn, ticket.ticket_id, "contacted")
    with pytest.raises(InvalidTransition):
        await update_ticket_status(conn, ticket.ticket_id, "new")
    with pytest.raises(InvalidTransition):
        await update_ticket_status(conn, ticket.ticket_id, "contacted")
    await update_ticket_status(conn, ticket.ticket_id, "resolved")


async def test_dashboard_assignment_summary_and_triage(conn):
    workers = await list_support_workers(conn)
    assert len(workers) == 2
    ticket = await create_callback_ticket(conn, _request())
    await update_ticket_status(
        conn, ticket.ticket_id, "callback_scheduled", worker_id=workers[0].worker_id
    )
    await set_case_summary(
        conn,
        ticket.ticket_id,
        "Insurance still owes part of the bill.",
        "insurance_mismatch",
    )
    await set_triage_final(conn, ticket.ticket_id, "billing_question")

    mine = await list_tickets(conn, assigned_to=workers[0].worker_id)
    row = next(r for r in mine if r.ticket_id == ticket.ticket_id)
    assert row.status == "callback_scheduled"
    assert row.triage_suggestion == "insurance_mismatch"  # suggestion kept
    assert row.triage_final == "billing_question"  # the worker's own choice


async def test_withdrawn_consent_flags_the_ticket(conn):
    ticket = await create_callback_ticket(conn, _request())
    await withdraw_consent(conn, ticket.ticket_id)
    row = next(r for r in await list_tickets(conn) if r.ticket_id == ticket.ticket_id)
    assert row.escalation_reason == "consent_withdrawn"


async def test_generated_text_log_and_pass_rates(conn):
    before = await checker_pass_rates(conn)
    for result in ("pass", "pass", "fallback_template"):
        await log_generated_text(
            conn,
            bill_id=BILL_1,
            feature="explanation",
            language="en",
            prompt_version="v1",
            body="Your bill total is Rs 50000.00.",
            checker_result=result,
        )
    after = await checker_pass_rates(conn)
    assert after.get("pass", 0) - before.get("pass", 0) == 2
    assert after.get("fallback_template", 0) - before.get("fallback_template", 0) == 1


async def test_log_refuses_text_with_a_phone_number(conn):
    with pytest.raises(ValueError):
        await log_generated_text(
            conn,
            bill_id=BILL_1,
            feature="case_summary",
            language="en",
            prompt_version="v1",
            body="Call the patient on 9876543210.",
            checker_result="not_applicable",
        )


async def test_consent_is_recorded(conn):
    consent_id = await record_consent(conn, purpose="process_bill", language="en", bill_id=BILL_1)
    assert consent_id is not None
