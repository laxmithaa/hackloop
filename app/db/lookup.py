"""Identify a bill and load its verified record."""

from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Literal
from uuid import UUID

from psycopg import AsyncConnection

from .models import FIELD_KEYS, BillLookup, BillRecord, VerifiedRecord


async def lookup_bill(conn: AsyncConnection, hospital_name: str, bill_number: str) -> BillLookup:
    """Identification step: returns one of three outcomes and NO amounts.

    hospital_not_registered: no hospital with that name
    bill_not_found:          hospital exists, but not that bill number
    found:                   both match (hospital name is case-insensitive)
    """
    name = " ".join(hospital_name.split())
    number = bill_number.strip()
    async with conn.cursor() as cur:
        await cur.execute("select id, name from hospitals where lower(name) = lower(%s)", (name,))
        hospital = await cur.fetchone()
        if hospital is None:
            return BillLookup(outcome="hospital_not_registered")

        await cur.execute(
            "select id from bills where hospital_id = %s and bill_number = %s",
            (hospital["id"], number),
        )
        bill = await cur.fetchone()
        if bill is None:
            return BillLookup(outcome="bill_not_found")

    return BillLookup(
        outcome="found",
        bill=BillRecord(
            bill_id=bill["id"],
            hospital_id=hospital["id"],
            hospital_name=hospital["name"],
            bill_number=number,
        ),
    )


async def load_record_unchecked(conn: AsyncConnection, bill_id: UUID) -> VerifiedRecord:
    """Read the verified record WITHOUT checking authorization.

    Do not call this from an API route. Use access.get_verified_record(),
    which refuses unless the patient's session is verified and unexpired.
    """
    async with conn.cursor() as cur:
        await cur.execute(
            """select b.id, b.bill_number, b.currency, b.bill_date, b.due_date,
                      h.name as hospital_name
                 from bills b join hospitals h on h.id = b.hospital_id
                where b.id = %s""",
            (bill_id,),
        )
        bill = await cur.fetchone()
        if bill is None:
            raise LookupError(f"No bill {bill_id}")

        await cur.execute(
            "select field_key, amount_rupees from bill_financials where bill_id = %s",
            (bill_id,),
        )
        rows = await cur.fetchall()

    provided = {r["field_key"]: r["amount_rupees"] for r in rows}
    amounts = {
        key: (f"{provided[key]:.2f}" if provided.get(key) is not None else None)
        for key in FIELD_KEYS
    }
    return VerifiedRecord(
        bill_id=bill["id"],
        hospital_name=bill["hospital_name"],
        bill_number=bill["bill_number"],
        currency=bill["currency"],
        bill_date=bill["bill_date"],
        due_date=bill["due_date"],
        amounts=amounts,
    )


ScanComparisonStatus = Literal["matched", "amounts_differ", "insufficient_evidence"]


@dataclass(frozen=True)
class ScanComparison:
    """Outcome of comparing scanned amounts against the stored record.

    ``insufficient_evidence`` is deliberately separate from ``matched``: a
    scan that read no usable amount proves nothing and must never be reported
    as agreeing with the record.
    """

    status: ScanComparisonStatus
    differing: tuple = ()
    compared: int = 0


def compare_scanned_to_record(
    scanned: Mapping[str, str | Decimal | None], record: VerifiedRecord
) -> ScanComparison:
    """Compare scanned amounts with the record and report explicit evidence.

    Returns one of:

    - ``matched``            at least one amount was read and every read value
                              equals the recorded value;
    - ``amounts_differ``     at least one read value disagrees with the record;
    - ``insufficient_evidence`` the scan supplied no usable amount at all, so
                              no conclusion can be drawn.

    Fields the scan did not read (``None``) are skipped. A scanned value the
    record does not provide counts as a difference, as does an unparsable one.
    """

    differing: list = []
    compared = 0
    for key in FIELD_KEYS:
        value = scanned.get(key)
        if value is None:
            continue
        compared += 1
        expected = record.amounts.get(key)
        try:
            same = expected is not None and Decimal(str(value)) == Decimal(expected)
        except InvalidOperation:
            same = False
        if not same:
            differing.append(key)

    if compared == 0:
        return ScanComparison(status="insufficient_evidence")
    if differing:
        return ScanComparison(
            status="amounts_differ", differing=tuple(differing), compared=compared
        )
    return ScanComparison(status="matched", compared=compared)
