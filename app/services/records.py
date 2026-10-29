"""Temporary fictional hospital and bill records plus the record-access interface.

The registry is deterministic (always the same fake hospitals and bills) and
held entirely in memory. Financial values are fictional and exist only so a
later phase can compare them; they are never serialised into identification
responses.

``BillRecordAccess`` is the seam between business logic and storage:
identification code consumes this interface, so a later phase can swap in a
real persistence implementation without touching the API or the business rules.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Protocol

#: Strip everything that is not a letter or digit so OCR punctuation, spacing
#: and capitalisation variations cannot break a match
#: ("SUN. 2026-004512" == "SUN2026004512").
_NON_ALNUM = re.compile(r"[^A-Za-z0-9]+")

_WHITESPACE = re.compile(r"\s+")


def normalise_bill_number(value: str) -> str:
    """Canonical form of a bill number: uppercase, alphanumeric only."""

    return _NON_ALNUM.sub("", value.upper())


def normalise_text(value: str) -> str:
    """Casefolded single-space text used for hospital alias matching."""

    return _WHITESPACE.sub(" ", value.casefold()).strip()


def match_key(value: str) -> str:
    """Loose comparison key for hospital name/code matching (alphanumeric only)."""

    return _NON_ALNUM.sub("", value.casefold())


@dataclass(frozen=True)
class HospitalRecord:
    """One fictional registered hospital."""

    hospital_id: str
    name: str
    code: str
    aliases: tuple[str, ...]


@dataclass(frozen=True)
class BillRecord:
    """One fictional bill, including values a later phase will verify.

    ``total_amount_cents`` / ``patient_payable_cents`` are fictional and only
    used server-side; identification responses never expose them.
    """

    bill_id: str
    bill_number: str
    hospital_id: str
    bill_date: str
    total_amount_cents: int
    patient_payable_cents: int


# --- Deterministic fictional data (no real hospitals, bills or amounts) -------

HOSPITALS: tuple[HospitalRecord, ...] = (
    HospitalRecord(
        hospital_id="hosp-sunrise",
        name="Sunrise Multispeciality Hospital",
        code="SUNRISE-HSP",
        aliases=("Sunrise Hospital", "Sunrise Multispeciality"),
    ),
    HospitalRecord(
        hospital_id="hosp-greenmeadow",
        name="Greenmeadow City Hospital",
        code="GREENMEADOW-HSP",
        aliases=("Greenmeadow City", "Greenmeadow Hospital"),
    ),
    HospitalRecord(
        hospital_id="hosp-harbourview",
        name="Harbourview Medical Center",
        code="HARBOURVIEW-HSP",
        aliases=("Harbourview Center", "Harbourview Medical"),
    ),
)

BILLS: tuple[BillRecord, ...] = (
    BillRecord(
        bill_id="bill-sun-004512",
        bill_number="SUN-2026-004512",
        hospital_id="hosp-sunrise",
        bill_date="2026-03-14",
        total_amount_cents=1_248_000,
        patient_payable_cents=624_000,
    ),
    BillRecord(
        bill_id="bill-sun-004770",
        bill_number="SUN-2026-004770",
        hospital_id="hosp-sunrise",
        bill_date="2026-03-21",
        total_amount_cents=832_050,
        patient_payable_cents=416_025,
    ),
    BillRecord(
        bill_id="bill-gme-001122",
        bill_number="GME-2026-001122",
        hospital_id="hosp-greenmeadow",
        bill_date="2026-02-02",
        total_amount_cents=594_000,
        patient_payable_cents=297_000,
    ),
    BillRecord(
        bill_id="bill-hbr-555310",
        bill_number="HBR-2026-555310",
        hospital_id="hosp-harbourview",
        bill_date="2026-01-28",
        total_amount_cents=6_315_075,
        patient_payable_cents=1_578_750,
    ),
)


class BillRecordAccess(Protocol):
    """Interface through which business logic reads hospital and bill records."""

    def get_hospital(self, hospital_id: str) -> HospitalRecord | None:
        """One registered hospital by id, or ``None``."""
        ...

    def find_bill_in_hospital(self, bill_number: str, hospital_id: str) -> BillRecord | None:
        """Exact match of one bill within one hospital, or ``None``."""
        ...

    def find_bills_anywhere(self, bill_number: str) -> list[BillRecord]:
        """All registered bills with this number (list allows ambiguity detection)."""
        ...

    def match_hospitals(self, text: str) -> list[HospitalRecord]:
        """Registered hospitals whose name, code or aliases appear in ``text``."""
        ...


class InMemoryBillRecordAccess:
    """Deterministic fictional data backing :class:`BillRecordAccess`."""

    def __init__(
        self,
        hospitals: tuple[HospitalRecord, ...] = HOSPITALS,
        bills: tuple[BillRecord, ...] = BILLS,
    ) -> None:
        self._hospitals = hospitals
        self._bills_by_number: dict[str, list[BillRecord]] = {}
        for bill in bills:
            self._bills_by_number.setdefault(normalise_bill_number(bill.bill_number), []).append(
                bill
            )

    def get_hospital(self, hospital_id: str) -> HospitalRecord | None:
        for hospital in self._hospitals:
            if hospital.hospital_id == hospital_id:
                return hospital
        return None

    def find_bill_in_hospital(self, bill_number: str, hospital_id: str) -> BillRecord | None:
        for bill in self._bills_by_number.get(normalise_bill_number(bill_number), ()):
            if bill.hospital_id == hospital_id:
                return bill
        return None

    def find_bills_anywhere(self, bill_number: str) -> list[BillRecord]:
        return list(self._bills_by_number.get(normalise_bill_number(bill_number), ()))

    def match_hospitals(self, text: str) -> list[HospitalRecord]:
        text_key = match_key(text)
        if not text_key:
            return []
        matched: list[HospitalRecord] = []
        for hospital in self._hospitals:
            for candidate in [hospital.name, hospital.code, *hospital.aliases]:
                candidate_key = match_key(candidate)
                if candidate_key and candidate_key in text_key:
                    matched.append(hospital)
                    break
        return matched
