import pytest

from app.db import (
    get_verified_record,
    lookup_bill,
    start_verification,
    submit_access_code,
)

from .conftest import BILL_1, BILL_2, BILL_3, BILL_4, T0

pytestmark = pytest.mark.asyncio


async def test_found_is_case_insensitive_and_has_no_amounts(conn):
    result = await lookup_bill(conn, "  city GENERAL  hospital ", "INV-2026-0042")
    assert result.outcome == "found"
    assert str(result.bill.bill_id) == BILL_1
    assert not hasattr(result.bill, "amounts")  # identification never leaks money


async def test_unknown_hospital_is_not_registered(conn):
    result = await lookup_bill(conn, "Nowhere Hospital", "INV-2026-0042")
    assert result.outcome == "hospital_not_registered"
    assert result.bill is None


async def test_known_hospital_unknown_bill(conn):
    result = await lookup_bill(conn, "City General Hospital", "NOPE-999")
    assert result.outcome == "bill_not_found"


async def _verified(conn, bill_id, code):
    session = await start_verification(conn, bill_id, now=T0)
    result = await submit_access_code(conn, session.session_id, code, now=T0)
    assert result.status == "ok"
    return session


async def test_amounts_are_exact_strings(conn):
    session = await _verified(conn, BILL_1, "DEMO-1234")
    record = await get_verified_record(conn, session.session_id, now=T0)
    assert record.amounts["billTotalAfterDiscounts"] == "50000.00"
    assert record.amounts["insuranceApprovedButNotPaid"] == "15000.00"
    assert str(record.due_date) == "2026-10-30"


async def test_missing_is_not_zero_but_a_real_zero_stays_zero(conn):
    session = await _verified(conn, BILL_2, "DEMO-5678")
    record = await get_verified_record(conn, session.session_id, now=T0)
    assert record.amounts["insuranceApprovedButNotPaid"] is None  # not provided
    assert record.amounts["insurancePaidOrCredited"] == "0.00"  # a real zero


async def test_settled_and_uninsured_scenarios(conn):
    settled = await _verified(conn, BILL_3, "DEMO-0007")
    rec3 = await get_verified_record(conn, settled.session_id, now=T0)
    assert rec3.amounts["printedAmountDue"] == "0.00"

    uninsured = await _verified(conn, BILL_4, "DEMO-0100")
    rec4 = await get_verified_record(conn, uninsured.session_id, now=T0)
    assert rec4.amounts["insurancePaidOrCredited"] is None
