"""Approved financial glossary for the patient-facing GenAI layers.

Definitions here are prewritten by the product team and are the *only* source
of term explanations. The local model may reuse them, but it may never invent
a definition at runtime: if a term is not listed here, the feature says the
information is unavailable instead of guessing.

Each entry records whether the verified bill record actually contains that
figure (``available_in_record``). A missing figure is described as "not
recorded" — never as zero, and never estimated.

Every definition is deliberately factual and advice-free: it explains what a
term means, never whether a charge is correct or whether the patient should
pay.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.services.amount_comparison import (
    COMPARISON_AMOUNTS_DIFFER,
    COMPARISON_INSUFFICIENT_EVIDENCE,
    COMPARISON_MATCHED,
    COMPARISON_NO_UPLOADED_IMAGE,
)
from app.services.bill_facts import ExplanationFacts, render_amount


@dataclass(frozen=True)
class GlossaryEntry:
    """One approved term: stable code, label and definitions in en/hi/kn."""

    code: str
    label_en: str
    available_in_record: bool
    definitions: dict[str, str]


GLOSSARY_TERMS: dict[str, GlossaryEntry] = {
    "total_bill_amount": GlossaryEntry(
        code="total_bill_amount",
        label_en="Total bill amount",
        available_in_record=True,
        definitions={
            "en": (
                "The total bill amount is the full amount printed on the hospital bill, "
                "covering every charge listed for the visit before insurance or payments "
                "are taken into account. Your verified record lists this total."
            ),
            "hi": (
                "कुल बिल राशि अस्पताल के बिल पर छपी पूरी राशि है, जिसमें इस दौरे के सभी "
                "शुल्क शामिल होते हैं और बीमा या भुगतान को लेखे में लेने से पहले की "
                "स्थिति दिखती है। आपके सत्यापित रिकॉर्ड में यह कुल राशि दर्ज है।"
            ),
            "kn": (
                "ಒಟ್ಟು ಬಿಲ್ ಮೊತ್ತ ಎಂದರೆ ಆಸ್ಪತ್ರೆಯ ಬಿಲ್‌ನಲ್ಲಿ ಮುದ್ರಿಸಿರುವ ಪೂರ್ಣ ಮೊತ್ತ; "
                "ಭೇಟಿಯ ಎಲ್ಲಾ ಶುಲ್ಕಗಳು ಇದರಲ್ಲಿ ಸೇರಿವೆ ಮತ್ತು ವಿಮೆ ಅಥವಾ ಪಾವತಿಗಳನ್ನು "
                "ಲೆಕ್ಕಕ್ಕೆ ತೆಗೆದುಕೊಳ್ಳುವ ಮೊದಲಿನ ಮೊತ್ತ ಇದು. ನಿಮ್ಮ ಪರಿಶೀಲಿತ "
                "ದಾಖಲೆಯಲ್ಲಿ ಈ ಒಟ್ಟು ಮೊತ್ತ ದಾಖಲಾಗಿದೆ."
            ),
        },
    ),
    "insurance_covered_amount": GlossaryEntry(
        code="insurance_covered_amount",
        label_en="Insurance-covered amount",
        available_in_record=False,
        definitions={
            "en": (
                "The insurance-covered amount is the part of the bill that an insurer "
                "agrees to pay. It depends on your policy and on the insurer's own "
                "decision. This record does not include insurance information."
            ),
            "hi": (
                "बीमा-कवर राशि बिल का वह हिस्सा है जो बीमा कंपनी देने के लिए सहमत होती "
                "है। यह आपकी पॉलिसी और बीमा कंपनी के निर्णय पर निर्भर करता है। इस "
                "रिकॉर्ड में बीमा की जानकारी शामिल नहीं है।"
            ),
            "kn": (
                "ವಿಮೆ ಒಳಗೊಂಡ ಮೊತ್ತ ಎಂದರೆ ವಿಮಾ ಕಂಪನಿಯು ಪಾವತಿಸಲು ಒಪ್ಪುವ ಬಿಲ್‌ನ ಭಾಗ. "
                "ಇದು ನಿಮ್ಮ ಪಾಲಿಸಿ ಮತ್ತು ವಿಮಾ ಕಂಪನಿಯ ನಿರ್ಣಯವನ್ನು ಅವಲಂಬಿಸಿರುತ್ತದೆ. "
                "ಈ ದಾಖಲೆಯಲ್ಲಿ ವಿಮಾ ಮಾಹಿತಿ ಇಲ್ಲ."
            ),
        },
    ),
    "amount_already_paid": GlossaryEntry(
        code="amount_already_paid",
        label_en="Amount already paid",
        available_in_record=False,
        definitions={
            "en": (
                "The amount already paid is money the hospital has recorded as received "
                "for this bill. This record does not include payment history, so please "
                "confirm any payment with the billing counter."
            ),
            "hi": (
                "पहले से भुगतान की गई राशि वह पैसा है जो अस्पताल ने इस बिल के लिए "
                "प्राप्त दर्ज किया है। इस रिकॉर्ड में भुगतान का इतिहास शामिल नहीं है, "
                "इसलिए किसी भी भुगतान की पुष्टि बिलिंग काउंटर से करें।"
            ),
            "kn": (
                "ಈಗಾಗಲೇ ಪಾವತಿಸಿದ ಮೊತ್ತ ಎಂದರೆ ಈ ಬಿಲ್‌ಗಾಗಿ ಆಸ್ಪತ್ರೆ ಸ್ವೀಕರಿಸಿದೆ ಎಂದು "
                "ದಾಖಲಿಸಿರುವ ಹಣ. ಈ ದಾಖಲೆಯಲ್ಲಿ ಪಾವತಿ ಇತಿಹಾಸ ಇಲ್ಲ, ಆದ್ದರಿಂದ ಯಾವುದೇ "
                "ಪಾವತಿಯನ್ನು ಬಿಲ್ಲಿಂಗ್ ಕೌಂಟರ್‌ನಲ್ಲಿ ಖಚಿತಪಡಿಸಿ."
            ),
        },
    ),
    "patient_payable": GlossaryEntry(
        code="patient_payable",
        label_en="Amount payable by the patient",
        available_in_record=True,
        definitions={
            "en": (
                "The amount payable by the patient is the part of the bill the patient is "
                "expected to pay, after insurance or other payments are taken into "
                "account. Your record lists a separate figure for it."
            ),
            "hi": (
                "रोगी द्वारा देय राशि बिल का वह हिस्सा है जो रोगी को देना होता है, "
                "बीमा या अन्य भुगतानों को ध्यान में रखने के बाद। आपके रिकॉर्ड में इसके "
                "लिए अलग राशि दर्ज है।"
            ),
            "kn": (
                "ರೋಗಿ ಪಾವತಿಸಬೇಕಾದ ಮೊತ್ತ ಎಂದರೆ ವಿಮೆ ಅಥವಾ ಇತರ ಪಾವತಿಗಳನ್ನು "
                "ಗಣನೆಗೆ ತೆಗೆದುಕೊಂಡ ನಂತರ ರೋಗಿ ಪಾವತಿಸಬೇಕಾದ ಬಿಲ್‌ನ ಭಾಗ. ನಿಮ್ಮ "
                "ದಾಖಲೆಯಲ್ಲಿ ಇದಕ್ಕೆ ಪ್ರತ್ಯೇಕ ಮೊತ್ತ ದಾಖಲಾಗಿದೆ."
            ),
        },
    ),
    "outstanding_balance": GlossaryEntry(
        code="outstanding_balance",
        label_en="Outstanding balance",
        available_in_record=False,
        definitions={
            "en": (
                "The outstanding balance is the part of the patient's share that has not "
                "been paid yet. This record does not include payment history, so no "
                "balance can be shown."
            ),
            "hi": (
                "बकाया राशि रोगी के हिस्से का वह भाग है जो अभी तक नहीं चुकाया गया। इस "
                "रिकॉर्ड में भुगतान का इतिहास शामिल नहीं है, इसलिए बकाया नहीं दिखाया "
                "जा सकता।"
            ),
            "kn": (
                "ಬಾಕಿ ಮೊತ್ತ ಎಂದರೆ ರೋಗಿಯ ಪಾಲಿನಲ್ಲಿ ಇನ್ನೂ ಪಾವತಿಸದ ಭಾಗ. ಈ ದಾಖಲೆಯಲ್ಲಿ "
                "ಪಾವತಿ ಇತಿಹಾಸ ಇಲ್ಲ, ಆದ್ದರಿಂದ ಬಾಕಿ ಮೊತ್ತವನ್ನು ತೋರಿಸಲು ಸಾಧ್ಯವಿಲ್ಲ."
            ),
        },
    ),
    "bill_verification": GlossaryEntry(
        code="bill_verification",
        label_en="Bill verification",
        available_in_record=True,
        definitions={
            "en": (
                "Bill verification checks that you know the access code printed on this "
                "bill. It confirms the bill belongs to your session; it does not judge "
                "whether the charges are correct."
            ),
            "hi": (
                "बिल सत्यापन यह जाँचता है कि आपको इस बिल पर छपा एक्सेस कोड पता है। यह "
                "पुष्टि करता है कि बिल आपके सत्र का है; यह नहीं बताता कि शुल्क सही हैं "
                "या नहीं।"
            ),
            "kn": (
                "ಬಿಲ್ ಪರಿಶೀಲನೆ ಎಂದರೆ ಈ ಬಿಲ್‌ನಲ್ಲಿ ಮುದ್ರಿಸಿರುವ ಪ್ರವೇಶ ಕೋಡ್ ನಿಮಗೆ "
                "ತಿಳಿದಿದೆಯೇ ಎಂದು ಪರಿಶೀಲಿಸುವುದು. ಇದು ಬಿಲ್ ನಿಮ್ಮ ಸೆಷನ್‌ಗೆ ಸೇರಿದೆ ಎಂದು "
                "ಖಚಿತಪಡಿಸುತ್ತದೆ; ಶುಲ್ಕಗಳು ಸರಿಯಾಗಿವೆಯೇ ಎಂದು ನಿರ್ಣಯಿಸುವುದಿಲ್ಲ."
            ),
        },
    ),
    "amount_discrepancy": GlossaryEntry(
        code="amount_discrepancy",
        label_en="Amount discrepancy",
        available_in_record=True,
        definitions={
            "en": (
                "An amount discrepancy means a labelled amount read from your uploaded "
                "photo is different from the amount in our record. It does not say which "
                "side is wrong."
            ),
            "hi": (
                "राशि में अंतर का अर्थ है कि आपकी अपलोड की गई तस्वीर से पढ़ी गई कोई "
                "राशि हमारे रिकॉर्ड की राशि से अलग है। यह नहीं बताता कि कौन सी ओर गलत "
                "है।"
            ),
            "kn": (
                "ಮೊತ್ತದ ವ್ಯತ್ಯಾಸ ಎಂದರೆ ನೀವು ಅಪ್‌ಲೋಡ್ ಮಾಡಿದ ಫೋಟೋದಿಂದ ಓದಿದ ಯಾವುದೇ "
                "ಮೊತ್ತ ನಮ್ಮ ದಾಖಲೆಯ ಮೊತ್ತಕ್ಕಿಂತ ಬೇರೆಯಾಗಿರುವುದು. ಯಾವ ಕಡೆ ತಪ್ಪು ಎಂದು "
                "ಇದು ಹೇಳುವುದಿಲ್ಲ."
            ),
        },
    ),
    "co_payment": GlossaryEntry(
        code="co_payment",
        label_en="Co-payment / co-insurance",
        available_in_record=False,
        definitions={
            "en": (
                "Co-payment (or co-insurance) is the share of a bill that a patient pays "
                "even when insurance applies. This record does not include policy or "
                "co-payment details."
            ),
            "hi": (
                "सह-भुगतान (को-पेमेंट) बिल का वह हिस्सा है जो बीमा लागू होने पर भी रोगी "
                "को देना होता है। इस रिकॉर्ड में पॉलिसी या सह-भुगतान की जानकारी शामिल "
                "नहीं है।"
            ),
            "kn": (
                "ಸಹ-ಪಾವತಿ (ಕೋ-ಪೇಮೆಂಟ್) ಎಂದರೆ ವಿಮೆ ಅನ್ವಯವಾದರೂ ರೋಗಿ ಪಾವತಿಸಬೇಕಾದ "
                "ಬಿಲ್‌ನ ಭಾಗ. ಈ ದಾಖಲೆಯಲ್ಲಿ ಪಾಲಿಸಿ ಅಥವಾ ಸಹ-ಪಾವತಿ ಮಾಹಿತಿ ಇಲ್ಲ."
            ),
        },
    ),
}

#: Term codes in a stable order (request enum and docs use this).
GLOSSARY_TERM_CODES: tuple[str, ...] = tuple(GLOSSARY_TERMS)

#: Keyword → term mapping for free-text questions ("what does copay mean?").
#: Longest/most specific phrases come first so "already paid" wins over "paid".
_TERM_KEYWORDS: tuple[tuple[tuple[str, ...], str], ...] = (
    (("co-payment", "copayment", "co-pay", "copay", "co-insurance", "coinsurance"), "co_payment"),
    (
        ("insurance covered", "insurance-covered", "insurance coverage", "insurance cover"),
        "insurance_covered_amount",
    ),
    (
        ("amount already paid", "already paid", "amount paid", "paid so far", "have i paid"),
        "amount_already_paid",
    ),
    (("outstanding balance", "outstanding", "balance due", "balance"), "outstanding_balance"),
    (
        ("patient payable", "amount payable", "payable", "amount due"),
        "patient_payable",
    ),
    (("total bill", "total amount", "grand total", "total"), "total_bill_amount"),
    (("bill verification", "verification", "verified"), "bill_verification"),
    (
        ("amount discrepancy", "discrepancy", "difference", "mismatch", "differ"),
        "amount_discrepancy",
    ),
)

_WHITESPACE = re.compile(r"\s+")


def normalise_question(text: str) -> str:
    """Lowercase, single-spaced text used for keyword matching only."""

    return _WHITESPACE.sub(" ", text.casefold()).strip()


def match_glossary_term(text: str) -> str | None:
    """The approved term a question is about, or ``None`` (never guesses)."""

    normalised = normalise_question(text)
    if not normalised:
        return None
    for keywords, code in _TERM_KEYWORDS:
        for keyword in keywords:
            if keyword in normalised:
                return code
    return None


def glossary_definition(code: str, language: str) -> str | None:
    """Approved definition in one language, or ``None`` when unavailable."""

    entry = GLOSSARY_TERMS.get(code)
    if entry is None:
        return None
    return entry.definitions.get(language)


def comparison_sentence(facts: ExplanationFacts, language: str) -> str:
    """One approved sentence describing the comparison outcome."""

    sentences = {
        COMPARISON_MATCHED: {
            "en": "The labelled amounts read from your upload match this record.",
            "hi": "आपके अपलोड से पढ़ी गई राशियाँ इस रिकॉर्ड से मेल खाती हैं।",
            "kn": "ನಿಮ್ಮ ಅಪ್‌ಲೋಡ್‌ನಿಂದ ಓದಿದ ಮೊತ್ತಗಳು ಈ ದಾಖಲೆಗೆ ಹೊಂದಿಕೆಯಾಗುತ್ತವೆ.",
        },
        COMPARISON_AMOUNTS_DIFFER: {
            "en": (
                "In this case the labelled amounts you uploaded differ from this record. "
                "We cannot tell which side is wrong; please contact human support before "
                "paying."
            ),
            "hi": (
                "इस मामले में आपके अपलोड की गई राशियाँ इस रिकॉर्ड से अलग हैं। हम नहीं "
                "बता सकते कि कौन सी ओर गलती है; भुगतान से पहले सहायता टीम से संपर्क "
                "करें।"
            ),
            "kn": (
                "ಈ ಸಂದರ್ಭದಲ್ಲಿ ನೀವು ಅಪ್‌ಲೋಡ್ ಮಾಡಿದ ಮೊತ್ತಗಳು ಈ ದಾಖಲೆಗಿಂತ ಭಿನ್ನವಾಗಿವೆ. "
                "ಯಾವ ಕಡೆ ತಪ್ಪು ಎಂದು ನಮಗೆ ತಿಳಿದಿಲ್ಲ; ಪಾವತಿಸುವ ಮೊದಲು ಸಹಾಯ ತಂಡವನ್ನು "
                "ಸಂಪರ್ಕಿಸಿ."
            ),
        },
        COMPARISON_INSUFFICIENT_EVIDENCE: {
            "en": "No comparison could be performed because the upload was not readable.",
            "hi": "अपलोड स्पष्ट न होने के कारण कोई तुलना नहीं की जा सकी।",
            "kn": "ಅಪ್‌ಲೋಡ್ ಸ್ಪಷ್ಟವಾಗಿಲ್ಲದ ಕಾರಣ ಯಾವುದೇ ಹೋಲಿಕೆ ಮಾಡಲಾಗಲಿಲ್ಲ.",
        },
        COMPARISON_NO_UPLOADED_IMAGE: {
            "en": "No bill photo was uploaded, so no comparison was performed.",
            "hi": "कोई बिल तस्वीर अपलोड नहीं हुई, इसलिए कोई तुलना नहीं की गई।",
            "kn": "ಯಾವುದೇ ಬಿಲ್ ಫೋಟೋ ಅಪ್‌ಲೋಡ್ ಆಗಿಲ್ಲ, ಆದ್ದರಿಂದ ಹೋಲಿಕೆ ಮಾಡಲಾಗಿಲ್ಲ.",
        },
    }
    return sentences[facts.comparison_status][language]


def record_sentence(code: str, facts: ExplanationFacts, language: str) -> str:
    """A grounded sentence tying an available term to *this* verified record."""

    total = render_amount(facts.total_minor_units)
    payable = render_amount(facts.patient_payable_minor_units)

    if code == "total_bill_amount":
        return {
            "en": f"On your verified record, the total bill amount is {total}.",
            "hi": f"आपके सत्यापित रिकॉर्ड में कुल बिल राशि {total} है।",
            "kn": f"ನಿಮ್ಮ ಪರಿಶೀಲಿತ ದಾಖಲೆಯಲ್ಲಿ ಒಟ್ಟು ಬಿಲ್ ಮೊತ್ತ {total}.",
        }[language]
    if code == "patient_payable":
        return {
            "en": f"On your verified record, the amount payable by the patient is {payable}.",
            "hi": f"आपके सत्यापित रिकॉर्ड में रोगी द्वारा देय राशि {payable} है।",
            "kn": f"ನಿಮ್ಮ ಪರಿಶೀಲಿತ ದಾಖಲೆಯಲ್ಲಿ ರೋಗಿ ಪಾವತಿಸಬೇಕಾದ ಮೊತ್ತ {payable}.",
        }[language]
    if code == "bill_verification":
        return {
            "en": (
                f"Bill {facts.bill_number} dated {facts.bill_date} has passed "
                "access-code verification."
            ),
            "hi": (
                f"बिल {facts.bill_number}, दिनांक {facts.bill_date}, एक्सेस कोड सत्यापन से गुजर चुका है।"
            ),
            "kn": (f"ಬಿಲ್ {facts.bill_number}, ದಿನಾಂಕ {facts.bill_date}, ಪ್ರವೇಶ ಕೋಡ್ ಪರಿಶೀಲನೆಯಲ್ಲಿ ಯಶಸ್ವಿಯಾಗಿದೆ."),
        }[language]
    if code == "amount_discrepancy":
        return comparison_sentence(facts, language)
    # Unavailable figures never get a fabricated sentence.
    return {
        "en": "This record does not include that information.",
        "hi": "इस रिकॉर्ड में वह जानकारी शामिल नहीं है।",
        "kn": "ಈ ದಾಖಲೆಯಲ್ಲಿ ಆ ಮಾಹಿತಿ ಇಲ್ಲ.",
    }[language]


def glossary_answer(code: str, facts: ExplanationFacts, language: str) -> str | None:
    """Approved definition plus a grounded sentence, or ``None`` if unknown."""

    definition = glossary_definition(code, language)
    if definition is None:
        return None
    entry = GLOSSARY_TERMS[code]
    if not entry.available_in_record:
        # The definition already states that the figure is not in the record.
        return definition
    return f"{definition} {record_sentence(code, facts, language)}"
