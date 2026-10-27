"""Part B: personalised explanations that preserve verified facts.

- ``simple`` and ``short`` rewrite a deterministic, record-derived
  explanation. The model never receives client-supplied prose and never
  chooses a financial value; its rewrite passes the shared validator, and any
  failure falls back to pre-written text in the requested language.
- ``term`` returns the approved glossary definition (plus a grounded sentence
  when the record contains the figure). Definitions are never generated at
  runtime.
- Distinctions that matter clinically and financially (total bill amount vs
  amount payable) are restated explicitly in the fallback texts, so a
  simplification can never merge them.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from app.services.ai_validation import UNSUPPORTED_CLAIM_PHRASES, validate_generated
from app.services.bill_facts import (
    ExplanationFacts,
    facts_summary_lines,
    recorded_amounts,
    recorded_dates,
    render_amount,
)
from app.services.bill_glossary import (
    GLOSSARY_TERMS,
    comparison_sentence,
    glossary_answer,
)
from app.services.ollama_client import OllamaChatClient, OllamaChatError

logger = logging.getLogger(__name__)

PERSONALIZATION_SOURCE_GENERATED = "generated"
PERSONALIZATION_SOURCE_FALLBACK = "fallback"
PERSONALIZATION_SOURCE_GLOSSARY = "glossary"

MODE_SIMPLE = "simple"
MODE_SHORT = "short"
MODE_TERM = "term"

_LANGUAGES = {"en": "English", "hi": "Hindi", "kn": "Kannada"}


@dataclass(frozen=True)
class PersonalizationOutcome:
    """The personalised text plus which layer produced it."""

    text: str
    source: str
    reason: str | None = None


def base_explanation(facts: ExplanationFacts, language: str) -> str:
    """The deterministic, record-derived text a rewrite must stay within."""

    total = render_amount(facts.total_minor_units)
    payable = render_amount(facts.patient_payable_minor_units)
    message = comparison_sentence(facts, language)

    if language == "hi":
        return (
            f"बिल {facts.bill_number}, {facts.hospital_name}, दिनांक {facts.bill_date}, "
            "एक्सेस कोड सत्यापन से गुजर चुका है। "
            f"रिकॉर्ड में कुल बिल राशि {total} है। "
            f"रिकॉर्ड में रोगी द्वारा देय राशि {payable} है। "
            f"{message} "
            "सत्यापन केवल एक्सेस कोड की पुष्टि करता है, यह नहीं बताता कि शुल्क सही हैं।"
        )
    if language == "kn":
        return (
            f"ಬಿಲ್ {facts.bill_number}, {facts.hospital_name}, ದಿನಾಂಕ {facts.bill_date}, "
            "ಪ್ರವೇಶ ಕೋಡ್ ಪರಿಶೀಲನೆಯಲ್ಲಿ ಯಶಸ್ವಿಯಾಗಿದೆ. "
            f"ದಾಖಲೆಯಲ್ಲಿ ಒಟ್ಟು ಬಿಲ್ ಮೊತ್ತ {total}. "
            f"ದಾಖಲೆಯಲ್ಲಿ ರೋಗಿ ಪಾವತಿಸಬೇಕಾದ ಮೊತ್ತ {payable}. "
            f"{message} "
            "ಪರಿಶೀಲನೆ ಪ್ರವೇಶ ಕೋಡ್ ಅನ್ನು ಮಾತ್ರ ಖಚಿತಪಡಿಸುತ್ತದೆ, ಶುಲ್ಕಗಳು ಸರಿಯಾಗಿವೆಯೇ ಎಂದು ಅಲ್ಲ."
        )
    return (
        f"Bill {facts.bill_number} from {facts.hospital_name}, dated {facts.bill_date}, "
        "has passed access-code verification. "
        f"The recorded total bill amount is {total}. "
        f"The recorded amount payable by the patient is {payable}. "
        f"{message} "
        "Verification confirms the access code only; it does not say whether the "
        "charges are correct."
    )


def simple_fallback(facts: ExplanationFacts, language: str) -> str:
    """Short, easy sentences built only from recorded values."""

    total = render_amount(facts.total_minor_units)
    payable = render_amount(facts.patient_payable_minor_units)
    message = comparison_sentence(facts, language)

    if language == "hi":
        return (
            f"आपका बिल {facts.bill_number} ({facts.hospital_name}), दिनांक "
            f"{facts.bill_date}, सत्यापित है। रिकॉर्ड में कुल राशि {total} है। "
            f"रिकॉर्ड में आपका हिस्सा {payable} है। {message} "
            "कुछ समझ न आए तो अस्पताल में किसी सहायक से पूछें।"
        )
    if language == "kn":
        return (
            f"ನಿಮ್ಮ ಬಿಲ್ {facts.bill_number} ({facts.hospital_name}), ದಿನಾಂಕ "
            f"{facts.bill_date}, ಪರಿಶೀಲಿಸಲ್ಪಟ್ಟಿದೆ. ದಾಖಲೆಯಲ್ಲಿ ಒಟ್ಟು ಮೊತ್ತ {total}. "
            f"ದಾಖಲೆಯಲ್ಲಿ ನಿಮ್ಮ ಪಾಲು {payable}. {message} "
            "ಏನಾದರೂ ಅರ್ಥವಾಗದಿದ್ದರೆ ಆಸ್ಪತ್ರೆಯ ಸಹಾಯಕರನ್ನು ಕೇಳಿ."
        )
    return (
        f"Your bill {facts.bill_number} from {facts.hospital_name}, dated "
        f"{facts.bill_date}, is verified. The total on record is {total}. "
        f"Your share on record is {payable}. {message} "
        "If anything is unclear, ask a helper at the hospital."
    )


def short_fallback(facts: ExplanationFacts, language: str) -> str:
    """The essentials only: hospital, bill, date, total, patient share."""

    total = render_amount(facts.total_minor_units)
    payable = render_amount(facts.patient_payable_minor_units)

    if language == "hi":
        return (
            f"{facts.hospital_name}: बिल {facts.bill_number}, {facts.bill_date}. "
            f"कुल {total}; रोगी हिस्सा {payable}. सत्यापित।"
        )
    if language == "kn":
        return (
            f"{facts.hospital_name}: ಬಿಲ್ {facts.bill_number}, {facts.bill_date}. "
            f"ಒಟ್ಟು {total}; ರೋಗಿ ಪಾಲು {payable}. ಪರಿಶೀಲಿತ."
        )
    return (
        f"{facts.hospital_name}: bill {facts.bill_number}, {facts.bill_date}. "
        f"Total {total}; patient share {payable}. Verified."
    )


_SYSTEM_PROMPT = (
    "You are a careful hospital-bill explainer inside a regulated prototype. You "
    "rewrite one already-approved bill explanation so that a patient with limited "
    "reading ability can understand it.\n"
    "Rules you must follow:\n"
    "- Change wording only. Never add, remove, change, round or estimate any "
    "amount, date, insurance detail, deadline or other fact.\n"
    "- Keep the total bill amount and the amount payable by the patient clearly "
    "distinct; never imply one is the other.\n"
    "- Never say a bill is paid, overdue, correct, incorrect or fraudulent, and "
    "never advise paying or refusing to pay.\n"
    "- Never give medical, legal or insurance-approval advice.\n"
    "- Output only the rewritten text: no lists, headings, markdown or notes."
)

_MODE_INSTRUCTIONS = {
    MODE_SIMPLE: "very common words and short sentences, at most 5 sentences",
    MODE_SHORT: "only the most important facts, at most 2 sentences",
}


def build_user_prompt(facts: ExplanationFacts, mode: str, language: str) -> str:
    """Approved source text plus the requested simplification style."""

    language_name = _LANGUAGES[language]
    return "\n".join(
        [
            f"Rewrite the explanation below in {language_name} ({language}) using "
            f"{_MODE_INSTRUCTIONS[mode]}.",
            "Approved explanation (the only content you may use):",
            "<<<",
            base_explanation(facts, language),
            ">>>",
            "Bill summary (authoritative amounts, for reference only):",
            *facts_summary_lines(facts),
            f"Answer in {language_name}.",
        ]
    )


class PersonalizationService:
    """Produces simple/short rewrites and approved term definitions."""

    def __init__(self, client: OllamaChatClient, *, max_chars: int = 900) -> None:
        self._client = client
        self._max_chars = max_chars

    def _mode_limit(self, mode: str) -> int:
        # A "short" summary has half the budget of a "simple" one.
        return self._max_chars if mode == MODE_SIMPLE else max(200, self._max_chars // 2)

    async def personalize(
        self,
        facts: ExplanationFacts,
        *,
        mode: str,
        language: str,
        term: str | None = None,
    ) -> PersonalizationOutcome:
        if mode == MODE_TERM:
            definition = glossary_answer(term, facts, language) if term else None
            if definition is not None:
                return PersonalizationOutcome(
                    text=definition, source=PERSONALIZATION_SOURCE_GLOSSARY
                )
            logger.info("glossary term unavailable; using simple fallback")
            return PersonalizationOutcome(
                text=simple_fallback(facts, language),
                source=PERSONALIZATION_SOURCE_FALLBACK,
                reason="term_not_in_glossary",
            )

        fallback = (
            simple_fallback(facts, language)
            if mode == MODE_SIMPLE
            else short_fallback(facts, language)
        )

        try:
            generated = await self._client.generate(
                system=_SYSTEM_PROMPT,
                user=build_user_prompt(facts, mode, language),
            )
        except OllamaChatError as exc:
            logger.info("personalised explanation fell back (%s)", exc)
            return PersonalizationOutcome(
                text=fallback, source=PERSONALIZATION_SOURCE_FALLBACK, reason=str(exc)
            )

        problems = validate_generated(
            generated,
            language=language,
            allowed_minor_units=recorded_amounts(facts),
            allowed_iso_dates=recorded_dates(facts),
            forbidden_phrases=UNSUPPORTED_CLAIM_PHRASES,
            max_chars=self._mode_limit(mode),
        )
        if problems:
            logger.info(
                "personalised explanation rejected (%d problem(s)); falling back",
                len(problems),
            )
            return PersonalizationOutcome(
                text=fallback,
                source=PERSONALIZATION_SOURCE_FALLBACK,
                reason=problems[0],
            )

        return PersonalizationOutcome(text=generated, source=PERSONALIZATION_SOURCE_GENERATED)


def known_term(code: str | None) -> bool:
    """Whether a term code exists in the approved glossary."""

    return code in GLOSSARY_TERMS
