from datetime import timedelta
from uuid import uuid4

import pytest

from app.db import (
    count_question,
    get_verified_record,
    issue_access_code,
    start_verification,
    submit_access_code,
)
from app.db.settings import DbSettings

from .conftest import BILL_1, T0

pytestmark = pytest.mark.asyncio

SETTINGS = DbSettings(max_questions_per_session=2)


async def test_correct_code_unlocks_the_record(conn):
    session = await start_verification(conn, BILL_1, now=T0)
    result = await submit_access_code(conn, session.session_id, " demo-1234 ", now=T0)
    assert result.status == "ok"
    assert await get_verified_record(conn, session.session_id, now=T0) is not None


async def test_amounts_are_refused_before_verification(conn):
    session = await start_verification(conn, BILL_1, now=T0)
    assert await get_verified_record(conn, session.session_id, now=T0) is None


async def test_unknown_session_gets_nothing(conn):
    assert await get_verified_record(conn, uuid4(), now=T0) is None
    assert (await submit_access_code(conn, uuid4(), "X", now=T0)).status == "not_found"


async def test_three_wrong_codes_lock_out_and_escalate(conn):
    session = await start_verification(conn, BILL_1, now=T0)
    first = await submit_access_code(conn, session.session_id, "WRONG-0001", now=T0)
    second = await submit_access_code(conn, session.session_id, "WRONG-0002", now=T0)
    third = await submit_access_code(conn, session.session_id, "WRONG-0003", now=T0)
    assert (first.status, first.attempts_left) == ("invalid", 2)
    assert (second.status, second.attempts_left) == ("invalid", 1)
    assert (third.status, third.escalate) == ("locked_out", True)

    # Even the right code is refused once locked out.
    late = await submit_access_code(conn, session.session_id, "DEMO-1234", now=T0)
    assert late.status == "locked_out"
    assert await get_verified_record(conn, session.session_id, now=T0) is None


async def test_code_entry_window_expires_after_five_minutes(conn):
    session = await start_verification(conn, BILL_1, now=T0)
    late = T0 + timedelta(minutes=5, seconds=1)
    result = await submit_access_code(conn, session.session_id, "DEMO-1234", now=late)
    assert result.status == "expired"


async def test_verified_session_itself_expires(conn):
    session = await start_verification(conn, BILL_1, now=T0)
    await submit_access_code(conn, session.session_id, "DEMO-1234", now=T0)
    much_later = T0 + timedelta(hours=2)
    assert await get_verified_record(conn, session.session_id, now=much_later) is None


async def test_issued_code_works_and_replaces_the_old_one(conn):
    issued = await issue_access_code(conn, BILL_1)
    assert len(issued.code) == 9 and issued.code[4] == "-"

    old = await start_verification(conn, BILL_1, now=T0)
    assert (await submit_access_code(conn, old.session_id, "DEMO-1234", now=T0)).status == "invalid"

    new = await start_verification(conn, BILL_1, now=T0)
    assert (await submit_access_code(conn, new.session_id, issued.code, now=T0)).status == "ok"


async def test_question_cap_per_session(conn):
    session = await start_verification(conn, BILL_1, now=T0)
    assert not await count_question(conn, session.session_id, now=T0, settings=SETTINGS)
    await submit_access_code(conn, session.session_id, "DEMO-1234", now=T0)
    assert await count_question(conn, session.session_id, now=T0, settings=SETTINGS)
    assert await count_question(conn, session.session_id, now=T0, settings=SETTINGS)
    assert not await count_question(conn, session.session_id, now=T0, settings=SETTINGS)
