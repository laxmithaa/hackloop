"""Shared output validation for every GenAI text layer.

One validator is used by the Phase 8 explanation service and by the Phase 9
grounded Q&A, personalised-explanation and caregiver-summary services, so the
financial safeguards cannot drift apart between features.

What it enforces on a completion:

- every monetary figure must equal a recorded (server-owned) amount, with its
  decimal precision intact — ``Rs 12480.005`` is rejected, never rounded to
  ``12480.00``;
- every date must equal a recorded date, in one of the accepted formats;
- an amount attached to a field label must match *that* field: a sentence that
  calls the patient-payable amount the "total" is rejected even though the
  number itself is a recorded value;
- claims about payment status, insurance coverage/approval, wrongdoing,
  deadlines or percentages are rejected in English, Hindi and Kannada;
- the output must respect its character ceiling;
- Hindi/Kannada output must actually be written in that script.

Passing these checks proves the generated text contains no invented or
misattributed financial figure; it does not by itself prove the whole answer
is on-topic, so callers also classify the question and keep their
deterministic answers as the truth of last resort.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from contextlib import suppress
from decimal import Decimal, InvalidOperation

#: A monetary token: a rupee marker (``₹``, ``Rs``, ``Rs.``, ``INR``) followed
#: by a grouped decimal. The fraction may be arbitrarily long so over-precise
#: amounts can be *rejected* rather than silently truncated to two decimals.
MONEY_TOKEN = re.compile(r"(?i)(?:₹|rs\.?|inr)\s*([0-9][0-9,]*(?:\.[0-9]+)?)(?![0-9])")

#: An ISO date or a dotted/slashed day-first date.
DATE_TOKEN = re.compile(r"\b(\d{4}-\d{2}-\d{2}|\d{1,2}[/.]\d{1,2}[/.]\d{2,4})\b")

#: An amount written without a currency marker: Indian-grouped digits or a
#: two-decimal figure. Dates are masked before this runs, so ``14.03.2026``
#: is never mistaken for ``14.03`` rupees. Sentence counts and years stay
#: unmatched (no decimals, no grouping).
_BARE_MONEY = re.compile(r"(?<![\d.,])([0-9]{1,3}(?:,[0-9]{2,3})+|[0-9]+\.[0-9]{2})(?![\d,]|\.\d)")

#: An over-precise bare figure (three or more decimals) is flagged instead of
#: being partially matched as a two-decimal amount.
_BARE_OVERPRECISE = re.compile(r"(?<![\d.,])([0-9][0-9,]*\.[0-9]{3,})(?!\d|\.\d)")

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
#: approval guarantees, discounts, deadlines and percentages. These are
#: regexes (not substrings) so variants such as "was paid", "over-charged"
#: and extra whitespace are still caught, and English/Hindi/Kannada are
#: covered consistently.
UNSUPPORTED_CLAIM_PATTERNS: tuple[str, ...] = (
    # Wrongdoing / correctness judgements.
    r"\bfraud\w*",
    r"\bovercharg\w*",
    r"\bover\s+charged?\b",
    r"\bscam\w*",
    r"\bcheat\w*",
    r"\bfalsif\w*",
    r"\bmoney\s+launder\w*",
    r"\binflated\b",
    r"\billega\w*",
    r"\bno\s+charges\b",
    r"\bfree\s+of\s+cost\b",
    r"धोखा",
    r"ठगी",
    r"अधिक\s+शुल्क",
    r"गलत\s+बिल",
    r"फर्जी",
    r"अवैध",
    r"ಮೋಸ",
    r"ವಂಚನೆ",
    r"ಹೆಚ್ಚು\s+ಶುಲ್ಕ",
    r"ತಪ್ಪು\s+ಬಿಲ್",
    r"ಅಕ್ರಮ",
    # Payment status the record does not track.
    r"\b(?:has|have|had|was|were|is|are)\s+(?:already\s+)?(?:been\s+)?paid\b",
    r"\balready\s+been\s+paid\b",
    r"\bpaid\s+in\s+full\b",
    r"\bpayment\s+(?:has\s+been\s+)?received\b",
    r"\bsettled\b",
    r"\bcleared\s+(?:the\s+)?(?:bill|balance|dues)\b",
    r"\byou\s+owe\b",
    r"\byou\s+have\s+to\s+pay\b",
    r"\bno\s+(?:outstanding\s+)?balance\b",
    r"भुगतान\s+(?:हो\s+चुका|कर\s+दिया|पूरा\s+हो\s+चुका)",
    r"पूरा\s+भुगतान",
    r"बकाया\s+नहीं",
    r"ಭಾಕಿ\s+ಇಲ್ಲ",
    r"ಪಾವತಿಸಲಾಗಿದೆ",
    r"ಪಾವತಿಯಾಗಿದೆ",
    r"ಪೂರ್ಣ\s+ಪಾವತಿ",
    r"ಬಾಕಿ\s+ಇಲ್ಲ",
    # Coverage, approval and outcome guarantees.
    r"\binsurance\s+(?:will|would|should|does|did|has|is)\b[^.\n]{0,40}"
    r"\b(?:cover|covered|pay|paid|approve|approved)\b",
    r"\binsurance\s+covers?\b",
    r"\binsurance\s+(?:has\s+)?approved\b",
    r"\bclaim\s+(?:was\s+|has\s+been\s+)?approved\b",
    r"\bguarantee\w*",
    r"\bwaiv\w*",
    r"\bdiscount\w*",
    r"\brefund\w*",
    r"बीमा[^।\n]{0,30}(?:कवर|देगा|देगी|स्वीकृत)",
    r"बीमा\s+कंपनी[^।\n]{0,20}देगी",
    r"विमा[^.\n]{0,40}(?:ಒಳಗೊಳ್ಳುತ್ತದೆ|ನೀಡುತ್ತದೆ|ಅನುಮೋದಿಸಿದೆ)",
    # Deadlines and obligations that are not in the data.
    r"\bdeadline\b",
    r"\bdue\s+date\b",
    r"\boverdue\b",
    r"\bpast\s+due\b",
    r"\bpenalt\w*",
    r"\binterest\s+will\s+be\s+charged\b",
    r"\bmust\s+pay\b",
    r"\blegally\s+(?:owed|required|due)\b",
    r"नियत\s+तारीख",
    r"अंतिम\s+तारीख",
    r"देय\s+तिथि",
    r"जुर्माना",
    r"ब्याज\s+लगेगा",
    r"ನಿಗದಿತ\s+ದಿನಾಂಕ",
    r"ಕೊನೆಯ\s+ದಿನಾಂಕ",
    r"ದಂಡ",
    # Percentages are never recorded, so any percentage claim is unsupported.
    r"\d+(?:\.\d+)?\s*%",
    r"\bpercent\b",
    r"प्रतिशत",
    r"ಶೇಕಡಾ",
)

#: Field labels used to tie an amount to the field it describes. Matching is
#: done on a hyphen-normalised copy (same length, so offsets stay valid).
_TOTAL_LABELS = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"\bgrand\s+total\b",
        r"\btotal\s+bill\s+amount\b",
        r"\bbill\s+total\b",
        r"\btotal(?:\s+amount|\s+charges?)?\b",
        r"कुल(?:\s+बिल\s+राशि|\s+राशि)?",
        r"ಒಟ್ಟು(?:\s+ಬಿಲ್\s+ಮೊತ್ತ)?",
    )
)
_PAYABLE_LABELS = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"\bamount\s+payable\b",
        r"\bpatient\s+payable\b",
        r"\bpayable(?:\s+amount)?\b",
        r"\bamount\s+due\b",
        r"\b(?:your|patient'?s?)\s+share\b",
        r"\byou\s+pay\b",
        r"\bpay\b",
        r"देय(?:\s+राशि)?",
        r"रोगी\s+का\s+हिस्सा",
        r"आपका\s+हिस्सा",
        r"पावतिस",
        r"ಒಟ್ಟು\s+ಪಾವತಿಸಬೇಕಾದ\s+ಮೊತ್ತ",
        r"ಪಾವತಿಸಬೇಕಾದ\s+ಮೊತ್ತ",
        r"ರೋಗಿಯ\s+ಪಾಲು",
        r"ನಿಮ್ಮ\s+ಪಾಲು",
        r"ಪಾಲು",
    )
)

#: How far around an amount a label may sit to be considered attached to it.
_LABEL_BEFORE_WINDOW = 48
_LABEL_AFTER_WINDOW = 32
_LABEL_INTEGER_WINDOW = 40

#: A bare integer immediately after a label (no currency marker, no grouping).
_LABEL_ADJACENT_INTEGER = re.compile(r"[^.\n\d]{0,16}?(?<![\d.,])(\d{3,})(?!\d|[.,]\d)")

_DASHES = re.compile(r"[\u2010-\u2015\-]")
_WHITESPACE = re.compile(r"\s+")


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


def money_matches(text: str) -> list[tuple[str, int, int]]:
    """Every monetary rendering in ``text`` with its span.

    Dates are masked first so their dotted/slashed parts are never parsed as
    amounts; currency-marked amounts are masked before the bare-number scan so
    one figure is not reported twice. Over-precise bare figures are included so
    they can be rejected explicitly.
    """

    normalised = normalise_digits(text)
    masked = DATE_TOKEN.sub(lambda match: " " * len(match.group(0)), normalised)

    matches: list[tuple[str, int, int]] = [
        (match.group(1), match.start(1), match.end(1)) for match in MONEY_TOKEN.finditer(masked)
    ]
    without_prefixed = MONEY_TOKEN.sub(lambda match: " " * len(match.group(0)), masked)
    matches.extend(
        (match.group(1), match.start(1), match.end(1))
        for match in _BARE_MONEY.finditer(without_prefixed)
    )
    matches.extend(
        (match.group(1), match.start(1), match.end(1))
        for match in _BARE_OVERPRECISE.finditer(without_prefixed)
    )
    return matches


def money_candidates(text: str) -> list[str]:
    """Every monetary rendering in ``text``, currency-marked or bare."""

    return [raw for raw, _start, _end in money_matches(text)]


def amount_problems(text: str, allowed: set[Decimal]) -> list[str]:
    """Report monetary tokens that are over-precise or not recorded amounts."""

    problems: list[str] = []
    for raw, _start, _end in money_matches(text):
        cleaned = raw.replace(",", "")
        fraction = cleaned.partition(".")[2]
        if len(fraction) > 2:
            # Never silently truncate: an over-precise figure is invalid even
            # when its first two decimals would equal a recorded amount.
            problems.append(f"unsupported_amount_precision:{raw}")
            continue
        try:
            amount = Decimal(cleaned)
        except InvalidOperation:  # pragma: no cover - regex already guards
            problems.append("unsupported_amount:unparsable")
            continue
        # Exact numeric equality: whole-number, one-decimal and two-decimal
        # renderings of the same value are equivalent; anything else is not.
        if not any(amount == value for value in allowed):
            problems.append(f"unsupported_amount:{raw}")
    return problems


def _nearest_label_kind(text: str, start: int, end: int) -> str | None:
    """Which field label (if any) is attached to the amount at ``start:end``.

    The closest label wins, but only when no other number lies between the
    label and the amount — that prevents a label in one sentence from being
    applied to an amount in the next.
    """

    normalised = _DASHES.sub(" ", text)

    before_start = max(0, start - _LABEL_BEFORE_WINDOW)
    before = normalised[before_start:start]
    preceding: list[tuple[int, str]] = []
    for kind, patterns in (("total", _TOTAL_LABELS), ("patient_payable", _PAYABLE_LABELS)):
        for pattern in patterns:
            for match in pattern.finditer(before):
                gap = before[match.end() :]
                if any(character.isdigit() for character in gap):
                    continue
                preceding.append((len(gap), kind))

    # A label before the amount ("the total is Rs X") owns it. Only when no
    # such label exists does a trailing label ("Rs X in total") apply, so a
    # later sentence's "your share" cannot steal the total's figure.
    if preceding:
        preceding.sort(key=lambda candidate: candidate[0])
        return preceding[0][1]

    after = normalised[end : end + _LABEL_AFTER_WINDOW]
    trailing: list[tuple[int, str]] = []
    for kind, patterns in (("total", _TOTAL_LABELS), ("patient_payable", _PAYABLE_LABELS)):
        for pattern in patterns:
            for match in pattern.finditer(after):
                gap = after[: match.start()]
                if any(character.isdigit() for character in gap):
                    continue
                trailing.append((len(gap), kind))

    if not trailing:
        return None
    trailing.sort(key=lambda candidate: candidate[0])
    return trailing[0][1]


def label_amount_problems(
    text: str,
    *,
    total_minor_units: int | None,
    patient_payable_minor_units: int | None,
) -> list[str]:
    """Report amounts attached to the wrong field, or invented label figures.

    ``The total bill amount is Rs 6240.00`` is rejected even though 6240.00 is
    the recorded patient-payable value. Bare integers immediately after a
    label (e.g. ``The total is 9999``) are validated too, closing the gap where
    an unformatted number escaped amount scanning entirely.
    """

    if total_minor_units is None or patient_payable_minor_units is None:
        return []

    expected = {
        "total": Decimal(total_minor_units) / Decimal(100),
        "patient_payable": Decimal(patient_payable_minor_units) / Decimal(100),
    }
    problems: list[str] = []
    matches = money_matches(text)
    covered = [(start, end) for _raw, start, end in matches]

    for raw, start, end in matches:
        cleaned = raw.replace(",", "")
        if len(cleaned.partition(".")[2]) > 2:
            continue  # already reported as a precision problem
        with suppress(InvalidOperation):
            amount = Decimal(cleaned)
            kind = _nearest_label_kind(text, start, end)
            if kind is not None and amount != expected[kind]:
                problems.append(f"mislabelled_amount:{kind}:{raw}")

    # Bare integers attached to a label are amounts that the scanner above
    # cannot see; validate the nearest one per label occurrence.
    normalised = _DASHES.sub(" ", text)
    for kind, patterns in (("total", _TOTAL_LABELS), ("patient_payable", _PAYABLE_LABELS)):
        for pattern in patterns:
            for label_start in pattern.finditer(normalised):
                window = normalised[label_start.end() : label_start.end() + _LABEL_INTEGER_WINDOW]
                integer = _LABEL_ADJACENT_INTEGER.search(window)
                if integer is None:
                    continue
                start = label_start.end() + integer.start(1)
                end = label_start.end() + integer.end(1)
                overlaps_amount = any(
                    start < cover_end and end > cover_start for cover_start, cover_end in covered
                )
                if overlaps_amount:
                    continue  # part of an already-validated formatted amount
                value = integer.group(1)
                if len(value) == 4 and 1900 <= int(value) <= 2099:
                    continue  # a year, not an amount
                with suppress(InvalidOperation):
                    amount = Decimal(value)
                    if amount != expected[kind]:
                        problems.append(f"unsupported_amount:{value}")

    return problems


def date_problems(text: str, allowed_forms: set[str]) -> list[str]:
    """Report every date that is not a recorded date."""

    return [
        f"unsupported_date:{match.group(1)}"
        for match in DATE_TOKEN.finditer(normalise_digits(text))
        if match.group(1) not in allowed_forms
    ]


def phrase_problems(text: str, patterns: Iterable[str] = UNSUPPORTED_CLAIM_PATTERNS) -> list[str]:
    """Report forbidden claims (payment status, coverage, wrongdoing...).

    Matching is case-insensitive and tolerant of hyphen/spacing variants, so
    ``over-charged``, ``was paid`` and ``insurance  will cover`` are caught.
    """

    normalised = _WHITESPACE.sub(" ", _DASHES.sub(" ", text)).casefold()
    problems: list[str] = []
    for pattern in patterns:
        compiled = re.compile(pattern, re.IGNORECASE) if isinstance(pattern, str) else pattern
        if compiled.search(normalised):
            problems.append(f"forbidden_claim:{getattr(pattern, 'pattern', pattern)}")
    return problems


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
    forbidden_patterns: Iterable[str] = UNSUPPORTED_CLAIM_PATTERNS,
    max_chars: int,
    total_minor_units: int | None = None,
    patient_payable_minor_units: int | None = None,
) -> list[str]:
    """Full validation pipeline for one completion. Empty list means valid."""

    problems = length_problems(text, max_chars)
    problems += script_problems(text, language)
    problems += phrase_problems(text, forbidden_patterns)
    problems += amount_problems(text, allowed_amount_values(allowed_minor_units))
    problems += date_problems(text, allowed_date_forms(allowed_iso_dates))
    problems += label_amount_problems(
        text,
        total_minor_units=total_minor_units,
        patient_payable_minor_units=patient_payable_minor_units,
    )
    return problems
