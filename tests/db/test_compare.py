"""Pure logic: no database needed."""

from datetime import date
from uuid import uuid4

from app.db.lookup import compare_scanned_to_record
from app.db.models import VerifiedRecord


def _record(**amounts):
    full = {
        "billTotalAfterDiscounts": "50000.00",
        "insuranceApprovedButNotPaid": None,
        "insurancePaidOrCredited": "15000.00",
        "patientPayments": "5000.00",
        "printedAmountDue": "30000.00",
    }
    full.update(amounts)
    return VerifiedRecord(
        bill_id=uuid4(),
        hospital_name="City General Hospital",
        bill_number="INV-2026-0042",
        currency="INR",
        bill_date=date(2026, 9, 20),
        due_date=date(2026, 10, 30),
        amounts=full,
    )


def test_matching_scan_is_reported_as_matched():
    scanned = {"billTotalAfterDiscounts": "50000", "printedAmountDue": "30000.00"}
    result = compare_scanned_to_record(scanned, _record())
    assert result.status == "matched"
    assert result.differing == ()
    assert result.compared == 2


def test_different_amount_is_reported():
    scanned = {"printedAmountDue": "35000.00"}
    result = compare_scanned_to_record(scanned, _record())
    assert result.status == "amounts_differ"
    assert result.differing == ("printedAmountDue",)
    assert result.compared == 1


def test_unread_fields_are_skipped():
    result = compare_scanned_to_record({"patientPayments": None}, _record())
    # Nothing at all was read: this is absence of evidence, not a match.
    assert result.status == "insufficient_evidence"
    assert result.compared == 0


def test_no_scanned_amounts_is_never_reported_as_a_match():
    result = compare_scanned_to_record({}, _record())
    assert result.status == "insufficient_evidence"
    assert result.differing == ()


def test_scanned_value_the_record_does_not_provide_is_a_difference():
    scanned = {"insuranceApprovedButNotPaid": "0.00"}  # record says "not provided"
    result = compare_scanned_to_record(scanned, _record())
    assert result.status == "amounts_differ"
    assert result.differing == ("insuranceApprovedButNotPaid",)


def test_garbage_number_is_a_difference_not_a_crash():
    result = compare_scanned_to_record({"patientPayments": "five"}, _record())
    assert result.status == "amounts_differ"
    assert result.differing == ("patientPayments",)


def test_one_difference_outweighs_other_matches():
    scanned = {
        "billTotalAfterDiscounts": "50000.00",
        "printedAmountDue": "31000.00",
    }
    result = compare_scanned_to_record(scanned, _record())
    assert result.status == "amounts_differ"
    assert result.differing == ("printedAmountDue",)
    assert result.compared == 2
