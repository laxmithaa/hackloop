"""Compatibility API for the Next.js frontend (demo integration layer).

The frontend under ``frontend/`` was built against a different contract than
this backend's versioned API: it calls ``/api/bills/*`` and ``/api/chat``,
while the real API lives under ``/api/v1``. Rather than rewriting either side
for the demo, this router translates between them.

Everything financial here comes from PostgreSQL through :mod:`app.db`, and
only through :func:`app.db.access.get_verified_record`, which refuses unless
the patient's session is verified and unexpired. Nothing reads
``bill_financials`` directly, so the access-code gate still holds.

The access-code flow is per-challenge: ``access/challenge`` creates a row in
``verification_sessions`` and returns an opaque handle, and
``access/verify`` spends one attempt against it. The handle doubles as the
bearer token the frontend passes to ``verify``, ``financials`` and
``explain``.
"""

from __future__ import annotations

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Body, Depends, Header, HTTPException, Request
from psycopg import AsyncConnection

from app.db.access import get_verified_record, start_verification, submit_access_code
from app.db.lookup import lookup_bill
from app.db.models import FIELD_KEYS, VerifiedRecord
from app.services.identification import extract_candidates
from app.services.image_validation import read_upload_limited, validate_image

router = APIRouter(tags=["Demo compatibility"], include_in_schema=False)

#: challenge id -> session details. Demo-only, single process, reset on restart.
_CHALLENGES: dict[str, dict[str, Any]] = {}
_MAX_CHALLENGES = 1000

_HEADINGS = {
    "en": {
        "billTotalAfterDiscounts": "Bill Total After Discounts",
        "insuranceApprovedButNotPaid": "Insurance Approved (Pending Settlement)",
        "insurancePaidOrCredited": "Insurance Paid / Credited",
        "patientPayments": "Patient Advance / Payments",
        "printedAmountDue": "Net Amount Due",
    },
    "hi": {
        "billTotalAfterDiscounts": "छूट के बाद कुल बिल (Bill Total)",
        "insuranceApprovedButNotPaid": "बीमा द्वारा स्वीकृत (स्वीकृत पर अनिर्णीत)",
        "insurancePaidOrCredited": "बीमा भुगतान / क्रेडिट",
        "patientPayments": "मरीज द्वारा किया गया अग्रिम भुगतान",
        "printedAmountDue": "देय कुल शेष राशि (Amount Due)",
    },
    "kn": {
        "billTotalAfterDiscounts": "ರಿಯಾಯಿತಿ ನಂತರ ಒಟ್ಟು ಬಿಲ್ (Bill Total)",
        "insuranceApprovedButNotPaid": "ವಿಮೆ ಅನುಮೋದಿತ ಮೊತ್ತ (ಇತ್ಯರ್ಥ ಬಾಕಿ)",
        "insurancePaidOrCredited": "ವಿಮೆ ಪಾವತಿಸಿದ ಮೊತ್ತ",
        "patientPayments": "ರೋಗಿಯ ಮುಂಗಡ ಪಾವತಿ",
        "printedAmountDue": "ಪಾವತಿಸಬೇಕಾದ ಅಂತಿಮ ಬಾಕಿ ಮೊತ್ತ",
    },
}

_EXPLANATIONS = {
    "en": {
        "billTotalAfterDiscounts": (
            "Total hospital charges billed after all authorized institutional discounts. "
        ),
        "insuranceApprovedButNotPaid": (
            "Amount approved by the health insurer awaiting final claim settlement. "
        ),
        "insurancePaidOrCredited": "Amount paid directly by insurance to the hospital.",
        "patientPayments": "Direct payments or advances previously deposited by the patient.",
        "printedAmountDue": (
            "The net remaining amount payable by the patient according to the hospital record. "
        ),
    },
    "hi": {
        "billTotalAfterDiscounts": "सभी मान्य संस्थागत छूटों के बाद कुल अस्पताल शुल्क।",
        "insuranceApprovedButNotPaid": (
            "स्वास्थ्य बीमा कंपनी द्वारा स्वीकृत राशि जिसका अंतिम भुगतान लंबित है। "
        ),
        "insurancePaidOrCredited": "बीमा कंपनी द्वारा सीधे अस्पताल को भुगतान की गई राशि।",
        "patientPayments": "मरीज या परिजनों द्वारा पहले जमा किया गया अग्रिम या भुगतान।",
        "printedAmountDue": "सत्यापित अस्पताल रिकॉर्ड के अनुसार मरीज द्वारा देय शेष राशि।",
    },
    "kn": {
        "billTotalAfterDiscounts": "ಎಲ್ಲಾ ರಿಯಾಯಿತಿಗಳ ನಂತರ ಆಸ್ಪತ್ರೆ ವಿಧಿಸಿದ ಒಟ್ಟು ಮೊತ್ತ.",
        "insuranceApprovedButNotPaid": ("ವಿಮಾ ಸಂಸ್ಥೆಯಿಂದ ಅನುಮೋದಿಸಲಾದ ಅಂತಿಮ ಇತ್ಯರ್ಥಕ್ಕೆ ಬಾಕಿ ಇರುವ ಮೊತ್ತ. "),
        "insurancePaidOrCredited": "ವಿಮಾ ಸಂಸ್ಥೆಯು ಆಸ್ಪತ್ರೆಗೆ ನೇರವಾಗಿ ಪಾವತಿಸಿದ ಮೊತ್ತ.",
        "patientPayments": "ರೋಗಿ ಅಥವಾ ಕುಟುಂಬವು ಮೊದಲೇ ಪಾವತಿಸಿದ ಮುಂಗಡ ಹಣ.",
        "printedAmountDue": "ಪರಿಶೀಲಿಸಿದ ಆಸ್ಪತ್ರೆ ದಾಖಲೆಯ ಪ್ರಕಾರ ರೋಗಿಯಿಂದ ಪಾವತಿಸಬೇಕಾದ ಅಂತಿಮ ಮೊತ್ತ.",
    },
}

_CHAT_INTROS = {
    "en": "According to the hospital's verified record for this bill:",
    "hi": "इस बिल के लिए अस्पताल के सत्यापित रिकॉर्ड के अनुसार:",
    "kn": "ಈ ಬಿಲ್‌ನ ಆಸ್ಪತ್ರೆಯ ಪರಿಶೀಲಿತ ದಾಖಲೆಯ ಪ್ರಕಾರ:",
}

_CHAT_FALLBACK = {
    "en": (
        "I can only explain the amounts on your verified bill. Ask me what a specific "
        "charge means, or why an amount is due. "
    ),
    "hi": ("मैं केवल आपके सत्यापित बिल की राशियों की व्याख्या कर सकता हूँ। पूछें कि कोई शुल्क किस लिए है। "),
    "kn": "ನಾನು ನಿಮ್ಮ ಪರಿಶೀಲಿತ ಬಿಲ್‌ನ ಮೊತ್ತಗಳನ್ನು ಮಾತ್ರ ವಿವರಿಸಬಲ್ಲೆ. ಯಾವುದೇ ಶುಲ್ಕದ ಬಗ್ಗೆ ಕೇಳಿ.",
}


async def _db(request: Request):
    """Request-scoped connection; 503 when the database is not configured."""
    pool = getattr(request.app.state, "db_pool", None)
    if pool is None:
        raise HTTPException(
            status_code=503,
            detail="The database is not configured. Set DATABASE_URL and restart.",
        )
    async with pool.connection() as connection:
        yield connection


DbConnection = Annotated[AsyncConnection, Depends(_db)]


def _language(value: Any) -> str:
    return value if value in ("en", "hi", "kn") else "en"


async def _hospital_for_bill(conn: AsyncConnection, bill_number: str) -> str | None:
    """The frontend only sends a bill number, so resolve the hospital first."""
    async with conn.cursor() as cur:
        await cur.execute(
            "select h.name from bills b join hospitals h on h.id = b.hospital_id"
            " where b.bill_number = %s",
            (bill_number,),
        )
        row = await cur.fetchone()
    return row["name"] if row else None


def _challenge(token: str) -> dict[str, Any]:
    challenge = _CHALLENGES.get(token)
    if challenge is None:
        raise HTTPException(status_code=401, detail="Your access has expired.")
    return challenge


def _amount_field(value: str | None) -> dict[str, Any]:
    return {
        "amountRupees": value,
        "status": "found" if value is not None else "not_provided",
    }


@router.post("/api/bills/identify")
async def identify_bill(request: Request, conn: DbConnection):
    """Identify a bill from a photo (OCR) or from a typed bill number."""
    content_type = request.headers.get("content-type", "")
    if content_type.startswith("multipart/form-data"):
        form = await request.form()
        upload = form.get("billImage")
        if upload is None or not hasattr(upload, "read"):
            raise HTTPException(status_code=400, detail="No bill image was uploaded.")
        settings = request.app.state.settings
        data = await read_upload_limited(upload, settings.bill_upload_max_size_bytes)
        image = validate_image(data, max_dimension_px=settings.image_max_dimension_px)
        ocr_result = request.app.state.ocr_adapter.extract_image_text(image)
        candidates = extract_candidates(ocr_result.text)
        return {
            "billNumberCandidate": candidates.bill_number,
            "hospitalNameCandidate": None,
        }

    payload: dict[str, Any] = await request.json()
    bill_number = str(payload.get("billNumber") or "").strip()
    if not bill_number:
        raise HTTPException(status_code=400, detail="A bill number is required.")
    return {
        "billNumberCandidate": bill_number,
        "hospitalNameCandidate": await _hospital_for_bill(conn, bill_number),
    }


@router.post("/api/bills/access/challenge")
async def access_challenge(payload: Annotated[dict[str, Any], Body(...)], conn: DbConnection):
    """Start a verification session for a bill number."""
    bill_number = str(payload.get("billNumber") or "").strip()
    if not bill_number:
        raise HTTPException(status_code=400, detail="A bill number is required.")

    hospital = await _hospital_for_bill(conn, bill_number)
    if hospital is None:
        raise HTTPException(status_code=404, detail="We couldn't find that bill number.")

    found = await lookup_bill(conn, hospital, bill_number)
    if found.outcome != "found" or found.bill is None:
        raise HTTPException(status_code=404, detail="We couldn't find that bill number.")

    session = await start_verification(conn, found.bill.bill_id)
    if len(_CHALLENGES) >= _MAX_CHALLENGES:
        _CHALLENGES.clear()
    challenge_id = uuid.uuid4().hex
    _CHALLENGES[challenge_id] = {
        "session_id": session.session_id,
        "bill_number": found.bill.bill_number,
        "hospital_name": found.bill.hospital_name,
    }
    return {
        "challengeId": challenge_id,
        "billNumber": found.bill.bill_number,
        "hospitalName": found.bill.hospital_name,
    }


@router.post("/api/bills/access/verify")
async def access_verify(payload: Annotated[dict[str, Any], Body(...)], conn: DbConnection):
    """Spend one attempt against a challenge's 5-minute, 3-try window."""
    challenge_id = str(payload.get("challengeId") or "")
    code = str(payload.get("accessCode") or "")
    challenge = _challenge(challenge_id)
    if not code:
        raise HTTPException(status_code=400, detail="An access code is required.")

    result = await submit_access_code(conn, challenge["session_id"], code)
    if result.status == "ok":
        return {"accessToken": challenge_id, "attemptsRemaining": result.attempts_left}

    detail = {
        "status": result.status,
        "attemptsRemaining": result.attempts_left,
        "escalate": result.escalate,
        "message": "That code did not match. Check the code printed on your bill.",
    }
    if result.status == "expired":
        detail["message"] = "This code entry window has expired. Start again."
    if result.status == "locked_out":
        detail["message"] = "Too many incorrect attempts. Please request a callback."
    raise HTTPException(status_code=401, detail=detail)


@router.post("/api/bills/verify")
async def verify_bill(
    conn: DbConnection,
    authorization: Annotated[str, Header()] = "",
):
    """Confirm the challenge is verified and unexpired."""
    challenge = _challenge(_bearer(authorization))
    record = await get_verified_record(conn, challenge["session_id"])
    if record is None:
        raise HTTPException(status_code=401, detail="Your access has expired.")
    return {
        "verified": True,
        "billNumber": record.bill_number,
        "hospitalName": record.hospital_name,
    }


@router.get("/api/bills/financials")
async def bill_financials(
    conn: DbConnection,
    authorization: Annotated[str, Header()] = "",
):
    """The five recorded amounts, or explicit "not_provided" (never zero)."""
    challenge = _challenge(_bearer(authorization))
    record = await get_verified_record(conn, challenge["session_id"])
    if record is None:
        raise HTTPException(status_code=401, detail="Your access has expired.")

    body: dict[str, Any] = {key: _amount_field(record.amounts.get(key)) for key in FIELD_KEYS}
    body["documentWarnings"] = _record_warnings(record)
    return body


@router.post("/api/bills/explain")
async def explain_bill(
    conn: DbConnection,
    payload: Annotated[dict[str, Any], Body(...)],
    authorization: Annotated[str, Header()] = "",
):
    """Multilingual, record-grounded explanation sections."""
    language = _language(payload.get("language"))
    challenge = _challenge(_bearer(authorization))
    record = await get_verified_record(conn, challenge["session_id"])
    if record is None:
        raise HTTPException(status_code=401, detail="Your access has expired.")

    headings = _HEADINGS[language]
    explanations = _EXPLANATIONS[language]
    sections = [
        {
            "fieldKey": key,
            "heading": headings[key],
            "amountRupees": record.amounts.get(key),
            "explanation": explanations[key],
            "status": "found" if record.amounts.get(key) is not None else "not_provided",
        }
        for key in FIELD_KEYS
    ]
    return {
        "sections": sections,
        "explanation": {
            "verifiedRecordReference": {
                "hospitalName": record.hospital_name,
                "billNumber": record.bill_number,
                "billDate": record.bill_date.isoformat() if record.bill_date else None,
                "dueDate": record.due_date.isoformat() if record.due_date else None,
            },
            "warnings": _record_warnings(record),
            "sourceLabel": "Generated from hospital-provided bill information.",
        },
    }


@router.post("/api/chat")
async def chat(payload: Annotated[dict[str, Any], Body(...)]):
    """Deterministic follow-up answers, grounded in the bill context sent by the UI."""
    language = _language(payload.get("language"))
    message = str(payload.get("message") or "").lower()
    context: dict[str, Any] = payload.get("billContext") or {}
    items = context.get("items") or []

    bill_terms = ("amount", "charge", "cost", "pay", "bill", "due", "insurance", "राशि", "शुल्क")
    if not items or not any(term in message for term in bill_terms):
        return {"reply": _CHAT_FALLBACK[language]}

    lines = [
        f"- {item.get('label')}: ₹{item.get('amount')}"
        for item in items
        if item.get("label") and item.get("amount")
    ]
    total = context.get("total")
    if total:
        lines.append(f"- Total: ₹{total}")
    reply = _CHAT_INTROS[language] + "\n" + "\n".join(lines)
    reply += (
        "\n\nThese figures come from the hospital's record, not from photos."
        if language == "en"
        else ""
    )
    return {"reply": reply}


def _bearer(authorization: str) -> str:
    value = authorization.strip()
    if value.lower().startswith("bearer "):
        return value[7:].strip()
    return value


def _record_warnings(record: VerifiedRecord) -> list[str]:
    missing = [key for key in FIELD_KEYS if record.amounts.get(key) is None]
    if not missing:
        return []
    return [
        f"The hospital record does not provide {len(missing)} of the 5 amounts; "
        "they are shown as not provided, not as zero."
    ]
