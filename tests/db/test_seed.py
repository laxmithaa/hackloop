"""Checks that the fictional seed data is complete and every code works."""

import pytest

from app.db import (
    get_verified_record,
    lookup_bill,
    start_verification,
    submit_access_code,
)

from .conftest import T0

pytestmark = pytest.mark.asyncio

CITY = "City General Hospital"
SUNRISE = "Sunrise Medical Centre"
COASTAL = "Coastal Care Clinic"

SEEDED = [
    (CITY, "INV-2026-0042", "DEMO-1234"),
    (SUNRISE, "SMC/2026/118", "DEMO-5678"),
    (COASTAL, "CC-0007", "DEMO-0007"),
    (CITY, "INV-2026-0100", "DEMO-0100"),
    (CITY, "INV-2026-0101", "DEMO-2005"),
    (CITY, "INV-2026-0102", "DEMO-2006"),
    (CITY, "INV-2026-0103", "DEMO-2007"),
    (CITY, "INV-2026-0104", "DEMO-2008"),
    (CITY, "INV-2026-0105", "DEMO-2009"),
    (CITY, "INV-2026-0106", "DEMO-2010"),
    (SUNRISE, "SMC/2026/119", "DEMO-2011"),
    (SUNRISE, "SMC/2026/120", "DEMO-2012"),
    (SUNRISE, "SMC/2026/121", "DEMO-2013"),
    (SUNRISE, "SMC/2026/122", "DEMO-2014"),
    (COASTAL, "CC-0008", "DEMO-2015"),
    (COASTAL, "CC-0009", "DEMO-2016"),
    (COASTAL, "CC-0010", "DEMO-2017"),
    (COASTAL, "CC/0011-A", "DEMO-2018"),
    (COASTAL, "CC-0012", "DEMO-2019"),
    (COASTAL, "CC-0013", "DEMO-2020"),
]


async def _unlock(conn, hospital, number, code):
    found = await lookup_bill(conn, hospital, number)
    assert found.outcome == "found", number
    session = await start_verification(conn, found.bill.bill_id, now=T0)
    result = await submit_access_code(conn, session.session_id, code, now=T0)
    assert result.status == "ok", number
    record = await get_verified_record(conn, session.session_id, now=T0)
    assert record is not None
    return record


@pytest.mark.parametrize(("hospital", "number", "code"), SEEDED)
async def test_every_seeded_bill_can_be_found_and_unlocked(conn, hospital, number, code):
    record = await _unlock(conn, hospital, number, code)
    assert record.bill_number == number


async def test_there_are_exactly_twenty_bills(conn):
    async with conn.cursor() as cur:
        await cur.execute("select count(*) as n from bills")
        assert (await cur.fetchone())["n"] == 20


async def test_edge_cases_are_present(conn):
    paise = await _unlock(conn, CITY, "INV-2026-0104", "DEMO-2008")
    assert paise.amounts["billTotalAfterDiscounts"] == "12345.50"

    sparse = await _unlock(conn, CITY, "INV-2026-0106", "DEMO-2010")
    assert sparse.amounts["insuranceApprovedButNotPaid"] is None
    assert sparse.amounts["printedAmountDue"] is None

    waived = await _unlock(conn, SUNRISE, "SMC/2026/122", "DEMO-2014")
    assert waived.amounts["billTotalAfterDiscounts"] == "0.00"

    no_deadline = await _unlock(conn, COASTAL, "CC-0010", "DEMO-2017")
    assert no_deadline.due_date is None

    overdue = await _unlock(conn, CITY, "INV-2026-0103", "DEMO-2007")
    assert str(overdue.due_date) == "2026-10-05"
