"""Shared output validation for every GenAI text layer.

One validator is used by the Phase 8 explanation service and by the Phase 9
grounded Q&A, personalised-explanation and caregiver-summary services, so the
financial safeguards cannot drift apart between features.

What it enforces on a completion:

- every monetary figure must equal a recorded (server-owned) amount;
- every date must equal a recorded date, in one of the accepted formats;
- claims about payment status, insurance coverage/approval, wrongdoing or
  deadlines are rejected outright;
- the output must respect its character ceiling;
- Hindi/Kannada output must actually be written in that script.

Passing these checks proves the generated text contains no invented financial
figure; it does not by itself prove the whole answer is on-topic, so callers
also classify the question and keep their deterministic answers as the truth
of last resort.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from contextlib import suppress
from decimal import Decimal, InvalidOperation

#: A monetary token: a rupee marker (``₹``, ``Rs``, ``Rs.``, ``INR``) followed
#: by an Indian-grouped decimal. Unmarked numbers are deliberately not treated
#: as money, so sentence counts are never mistaken for amounts.
MONEY_TOKEN = re.compile(r"(?i)(?:₹|rs\.?|inr)\s*([0-9][0-9,]*(?:\.[0-9]{1,2})?)")

#: An ISO date or a dotted/slashed day-first date.
DATE_TOKEN = re.compile(r"\b(\d{4}-\d{2}-\d{2}|\d{1,2}[/.]\d{1,2}[/.]\d{2,4})\b")

#: An amount written without a currency marker: Indian-grouped digits or a
#: two-decimal figure. Dates are masked before this runs, so ``14.03.2026``
#: is never mistaken for ``14.03`` rupees. Sentence counts and years stay
#: unmatched (no decimals, no grouping).
_BARE_MONEY = re.compile(r"(?<![\d.,])([0-9]{1,3}(?:,[0-9]{2,3})+|[0-9]+\.[0-9]{2})(?![\d,]|\.\d)")

_HUNDREDTH = Decimal("0.01")

#: Localised digits are accepted in output and normalised before parsing, so a
#: model writing ``₹ १२४८०`` cannot smuggle an unvalidated amount past the
#: checker.
_DIGIT_TRANSLATION = str.maketrans(
    "०१२३४५६७८९೦೧೨೩೪೫೬೭೮೯",
    "01234567890123456789",
)

_DEVANAGARI_LETTER = re.compile(r"[\u0904-\u0939\u0958-\u0961\u0972-\u097F]")
_KANNADA_LETTER = re.compile(r"[\u0C85-\u0CB9\u0CE0-\u0CF2]")

#: Claims no generated text may make, because the verified record does not
#: establish them: wrongdoing judgements, payment status, coverage or
#: approval guarantees, discounts and deadlines. One list, shared by every
#: GenAI layer, so the three features cannot disagree about what is unsafe.
UNSUPPORTED_CLAIM_PHRASES: tuple[str, ...] = (
    # Wrongdoing / correctness judgements.
    "fraud",
    "overcharg",
    "scam",
    "falsifi",
    "money launder",
    "no charges",
    "free of cost",
    # Payment status the record does not track.
    "has been paid",
    "already paid",
    "paid in full",
    "payment received",
    "you owe",
    "you have to pay",
    # Coverage, approval and outcome guarantees.
    "insurance will cover",
    "insurance covers",
    "insurance has approved",
    "insurance approved",
    "claim approved",
    "guarantee",
    "waiv",
    "discount",
    "refund",
    # Deadlines and obligations that are not in the data.
    "deadline",
    "due date",
    "overdue",
    "past due",
    "penal",
    "interest will be charged",
    "must pay",
    "legally owed",
    "legally required",
)


def normalise_digits(text: str) -> str:
    """Map Devanagari/Kannada digits to ASCII so amounts parse identically."""

    return text.translate(_DIGIT_TRANSLATION)


def iso_to_dotted(iso_date: str) -> str | None:
    """Render ``2026-03-14`` as ``14.03.2026`` when the shape matches."""

    parts = iso_date.split("-")
    if len(parts) == 3 and all(part.isdigit() for part in parts):
        year, month, day = parts
        return f"{day}.{month}.{year}"
    return None


def allowed_date_forms(iso_dates: Iterable[str]) -> set[str]:
    """Every accepted rendering of the recorded dates (ISO, dotted, slashed)."""

    allowed: set[str] = set()
    for iso_date in iso_dates:
        if not iso_date:
            continue
        allowed.add(iso_date)
        dotted = iso_to_dotted(iso_date)
        if dotted:
            allowed.add(dotted)
            allowed.add(dotted.replace(".", "/"))
    return allowed


def allowed_amount_values(minor_units: Iterable[int | None]) -> set[Decimal]:
    """Exact decimal values of the recorded amounts (``None`` ignored)."""

    values: set[Decimal] = set()
    for amount in minor_units:
        if amount is None:
            continue
        with suppress(InvalidOperation):  # pragma: no cover - ints never fail
            values.add(Decimal(amount) / Decimal(100))
    return values


def money_candidates(text: str) -> list[str]:
    """Every monetary rendering in ``text``, currency-marked or bare.

    Dates are masked first so their dotted/slashed parts are never parsed as
    amounts, and currency-marked amounts are masked before the bare-number
    scan so one figure is not reported twice.
    """

    normalised = normalise_digits(text)
    masked = DATE_TOKEN.sub(lambda match: " " * len(match.group(0)), normalised)

    candidates = [match.group(1) for match in MONEY_TOKEN.finditer(masked)]
    without_prefixed = MONEY_TOKEN.sub(" ", masked)
    candidates.extend(match.group(1) for match in _BARE_MONEY.finditer(without_prefixed))
    return candidates


def amount_problems(text: str, allowed: set[Decimal]) -> list[str]:
    """Report every monetary token that does not equal a recorded amount."""

    problems: list[str] = []
    for raw in money_candidates(text):
        try:
            amount = Decimal(raw.replace(",", ""))
        except InvalidOperation:  # pragma: no cover - regex already guards
            problems.append("unsupported_amount:unparsable")
            continue
        # Whole-number and two-decimal renderings of a recorded value are
        # ordinary prose variance; any other value is an invented amount.
        if not any(amount == value or amount == value.quantize(_HUNDREDTH) for value in allowed):
            problems.append(f"unsupported_amount:{raw}")
    return problems


def date_problems(text: str, allowed_forms: set[str]) -> list[str]:
    """Report every date that is not a recorded date."""

    return [
        f"unsupported_date:{match.group(1)}"
        for match in DATE_TOKEN.finditer(normalise_digits(text))
        if match.group(1) not in allowed_forms
    ]


def phrase_problems(text: str, phrases: Iterable[str] = UNSUPPORTED_CLAIM_PHRASES) -> list[str]:
    """Report forbidden claims (payment status, coverage, wrongdoing...)."""

    lowered = text.lower()
    return [f"forbidden_claim:{phrase}" for phrase in phrases if phrase in lowered]


def length_problems(text: str, max_chars: int) -> list[str]:
    """Reject (never truncate) output above the configured ceiling."""

    if len(text) <= max_chars:
        return []
    return [f"output_too_long:{len(text)}"]


def script_problems(text: str, language: str) -> list[str]:
    """Hindi/Kannada answers must actually use the requested script."""

    if language == "hi" and not _DEVANAGARI_LETTER.search(text):
        return ["language_mismatch:hi"]
    if language == "kn" and not _KANNADA_LETTER.search(text):
        return ["language_mismatch:kn"]
    return []


def validate_generated(
    text: str,
    *,
    language: str,
    allowed_minor_units: Iterable[int | None],
    allowed_iso_dates: Iterable[str],
    forbidden_phrases: Iterable[str],
    max_chars: int,
) -> list[str]:
    """Full validation pipeline for one completion. Empty list means valid."""

    problems = length_problems(text, max_chars)
    problems += script_problems(text, language)
    problems += phrase_problems(text, forbidden_phrases)
    problems += amount_problems(text, allowed_amount_values(allowed_minor_units))
    problems += date_problems(text, allowed_date_forms(allowed_iso_dates))
    return problems
