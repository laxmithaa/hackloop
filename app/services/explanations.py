"""Phase 8: multilingual explanation of a successfully verified bill.

This is the project's first GenAI feature, and the division of authority is
fixed:

- The backend exclusively owns bill facts (amounts, dates, verification
  state, comparison outcome), read from server-side services. The model
  receives a minimal, whitelisted summary and nothing else.
- The model is an explanation layer only. Its prose is validated before it
  reaches a patient; anything unsupported (invented amounts, dates, coverage,
  fraud/overcharging characterisations, payment obligations) causes the whole
  completion to be discarded in favour of a deterministic fallback text.
- Fallbacks are pre-written for every supported language, so the endpoint
  stays useful when the local model is off, slow or producing nonsense.
- Prompts carry no patient identifiers, no contact details, no access codes,
  no session secrets and no raw prompt/bill logging.

Supported languages: English (``en``), Hindi (``hi``), Kannada (``kn``).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from app.services.ai_validation import (
    UNSUPPORTED_CLAIM_PATTERNS,
    allowed_amount_values,
    allowed_date_forms,
    amount_problems,
    date_problems,
    label_amount_problems,
    phrase_problems,
)
from app.services.amount_comparison import (
    COMPARISON_AMOUNTS_DIFFER,
    COMPARISON_INSUFFICIENT_EVIDENCE,
    COMPARISON_MATCHED,
    COMPARISON_NO_UPLOADED_IMAGE,
)
from app.services.bill_facts import (
    ExplanationFacts,
    recorded_amounts,
    recorded_dates,
    render_amount,
)
from app.services.ollama_client import OllamaChatClient, OllamaChatError

logger = logging.getLogger(__name__)

EXPLANATION_SOURCE_GENERATED = "generated"
EXPLANATION_SOURCE_FALLBACK = "fallback"

SUPPORTED_EXPLANATION_LANGUAGES: dict[str, str] = {
    "en": "English",
    "hi": "Hindi",
    "kn": "Kannada",
}

#: Phrases a local explanation may never use: they assert facts the
#: authoritative record does not establish (payment status, insurance
#: coverage, wrongdoing) or deadlines that do not exist in the data. The
#: shared list keeps Phase 8 and the Phase 9 layers identical.
_FORBIDDEN_CLAIMS = UNSUPPORTED_CLAIM_PATTERNS


@dataclass(frozen=True)
class ExplanationOutcome:
    """The validated layer text plus which path produced it."""

    text: str
    source: str
    reason: str | None = None


def _render_amount(minor_units: int) -> str:
    """Trusted amount in the canonical "Rs 12345.00" shape used everywhere."""

    return render_amount(minor_units)


def build_system_prompt() -> str:
    """Safety contract given to the model on every explanation call."""

    return (
        "You are a careful hospital-bill explainer inside a regulated "
        "prototype. Explain the provided bill summary in simple language.\n"
        "Rules you must follow:\n"
        "- Use ONLY the facts given in the summary. Never invent, estimate or "
        "round amounts, dates, insurance coverage, deadlines, discounts, "
        "reasons for discrepancies, payment obligations, or financial-aid "
        "eligibility.\n"
        "- Never state or imply that a bill has been paid, is overdue, or "
        "that insurance has approved anything.\n"
        "- If amounts differ from an upload, never say which side is wrong "
        "and never call it fraud, overcharging or an error.\n"
        "- Write 3-5 short sentences addressed to the patient. No lists, no "
        "headings, no markdown."
    )


def build_user_prompt(facts: ExplanationFacts, language_code: str) -> str:
    """Minimal whitelist summary + requested language. No patient identity."""

    language_name = SUPPORTED_EXPLANATION_LANGUAGES[language_code]
    lines = [
        f"Explain this bill summary in {language_name} ({language_code}).",
        f"Hospital: {facts.hospital_name}",
        f"Bill number: {facts.bill_number}",
        f"Bill date: {facts.bill_date}",
        f"Total amount on record: {_render_amount(facts.total_minor_units)}",
        (
            "Amount payable by patient on record: "
            f"{_render_amount(facts.patient_payable_minor_units)}"
        ),
        f"Uploaded-amount comparison status: {facts.comparison_status}",
        f"Comparison note (authoritative): {facts.comparison_message}",
    ]
    return "\n".join(lines)


def validator_problems(text: str, facts: ExplanationFacts) -> list[str]:
    """Find unsupported financial facts/claims in generated prose.

    Delegates to the shared validator (``app.services.ai_validation``) so the
    Phase 8 explanation and the Phase 9 layers cannot drift apart.
    """

    problems = phrase_problems(text, _FORBIDDEN_CLAIMS)
    problems += amount_problems(text, allowed_amount_values(recorded_amounts(facts)))
    problems += date_problems(text, allowed_date_forms(recorded_dates(facts)))
    problems += label_amount_problems(
        text,
        total_minor_units=facts.total_minor_units,
        patient_payable_minor_units=facts.patient_payable_minor_units,
    )
    return problems


def fallback_explanation(facts: ExplanationFacts, language_code: str) -> str:
    """Deterministic, safe text per language. No model needed."""

    total = _render_amount(facts.total_minor_units)
    payable = _render_amount(facts.patient_payable_minor_units)
    comparison_sentinel = {
        COMPARISON_MATCHED: {
            "en": "The amounts we could read from your uploaded bill match our records.",
            "hi": "आपके अपलोड किए बिल से पढ़ी गई राशियाँ हमारे रिकॉर्ड से मेल खाती हैं।",
            "kn": (
                "ನೀವು ಅಪ್‌ಲೋಡ್ ಮಾಡಿದ ಬಿಲ್‌ನಿಂದ ಓದಿದ ಮೊತ್ತಗಳು "
                "ನಮ್ಮ ದಾಖಲೆಗಳೊಂದಿಗೆ ಹೊಂದಿಕೆಯಾಗುತ್ತವೆ."
            ),
        },
        COMPARISON_AMOUNTS_DIFFER: {
            "en": (
                "Some amounts on your uploaded bill differ from our records. "
                "We cannot tell which side is wrong; please contact human support "
                "before you pay."
            ),
            "hi": (
                "आपके अपलोड किए बिल की कुछ राशियाँ हमारे रिकॉर्ड से अलग हैं। "
                "हम नहीं बता सकते कि कौन सी ओर गलती है; भुगतान करने से पहले "
                "कृपया सहायता टीम से संपर्क करें।"
            ),
            "kn": (
                "ನೀವು ಅಪ್‌ಲೋಡ್ ಮಾಡಿದ ಬಿಲ್‌ನ ಕೆಲವು ಮೊತ್ತಗಳು ನಮ್ಮ ದಾಖಲೆಗಳಿಗಿಂತ "
                "ಭಿನ್ನವಾಗಿವೆ. ಯಾವ ಕಡೆ ತಪ್ಪು ಎಂದು ನಮಗೆ ತಿಳಿದಿಲ್ಲ; ಪಾವತಿಸುವ "
                "ಮೊದಲು ದಯವಿಟ್ಟು ಸಹಾಯ ತಂಡವನ್ನು ಸಂಪರ್ಕಿಸಿ."
            ),
        },
        COMPARISON_INSUFFICIENT_EVIDENCE: {
            "en": (
                "We could not read clearly labelled amounts from your upload, "
                "so no comparison was performed. Your verification itself succeeded."
            ),
            "hi": (
                "आपके अपलोड से स्पष्ट रूप से अंकित राशियाँ नहीं पढ़ी जा सकीं, "
                "इसलिए तुलना नहीं की गई। आपका सत्यापन सफल रहा।"
            ),
            "kn": (
                "ನಿಮ್ಮ ಅಪ್‌ಲೋಡ್‌ನಿಂದ ಸ್ಪಷ್ಟವಾಗಿ ಗುರುತಿಸಿದ ಮೊತ್ತಗಳನ್ನು ಓದಲು "
                "ಸಾಧ್ಯವಾಗಲಿಲ್ಲ, ಆದ್ದರಿಂದ ಹೋಲಿಕೆ ಮಾಡಲಾಗಿಲ್ಲ. ನಿಮ್ಮ ಪರಿಶೀಲನೆ "
                "ಯಶಸ್ವಿಯಾಗಿದೆ."
            ),
        },
        COMPARISON_NO_UPLOADED_IMAGE: {
            "en": (
                "No bill image was uploaded, so there is nothing to compare. "
                "Upload a photo of the printed bill to compare amounts."
            ),
            "hi": (
                "कोई बिल की तस्वीर अपलोड नहीं हुई, इसलिए तुलना के लिए कुछ नहीं है। "
                "राशियों की तुलना के लिए छपे बिल की तस्वीर अपलोड करें।"
            ),
            "kn": (
                "ಬಿಲ್‌ನ ಚಿತ್ರವನ್ನು ಅಪ್‌ಲೋಡ್ ಮಾಡಲಾಗಿಲ್ಲ, ಆದ್ದರಿಂದ ಹೋಲಿಸಲು "
                "ಏನೂ ಇಲ್ಲ. ಮೊತ್ತಗಳನ್ನು ಹೋಲಿಕೆ ಮಾಡಲು ಮುದ್ರಿತ ಬಿಲ್‌ನ ಫೋಟೋ "
                "ಅಪ್‌ಲೋಡ್ ಮಾಡಿ."
            ),
        },
    }.get(facts.comparison_status)

    if language_code == "hi":
        return (
            f"आपका बिल ({facts.bill_number}) - {facts.hospital_name}, "
            f"दिनांक {facts.bill_date} - सत्यापित हो गया है।\n"
            f"रिकॉर्ड के अनुसार कुल राशि: {total}। रोगी द्वारा देय राशि: {payable}।\n"
            f"{comparison_sentinel}\n"
            "यह जानकारी हमारे रिकॉर्ड से ली गई है; कृपया भुगतान करने से पहले "
            "मूल बिल से राशियाँ मिलान करें।"
        )
    if language_code == "kn":
        return (
            f"ನಿಮ್ಮ ಬಿಲ್ ({facts.bill_number}) - {facts.hospital_name}, "
            f"ದಿನಾಂಕ {facts.bill_date} - ಪರಿಶೀಲಿಸಲ್ಪಟ್ಟಿದೆ.\n"
            f"ದಾಖಲೆಯ ಪ್ರಕಾರ ಒಟ್ಟು ಮೊತ್ತ: {total}। ರೋಗಿ ಪಾವತಿಸಬೇಕಾದ ಮೊತ್ತ: {payable}।\n"
            f"{comparison_sentinel}\n"
            "ಈ ಮಾಹಿತಿ ನಮ್ಮ ದಾಖಲೆಗಳಿಂದ ತೆಗೆದುಕೊಳ್ಳಲಾಗಿದೆ; ಪಾವತಿಸುವ ಮೊದಲು "
            "ಮೂಲ ಬಿಲ್‌ನೊಂದಿಗೆ ಮೊತ್ತಗಳನ್ನು ಪರಿಶೀಲಿಸಿ."
        )
    return (
        f"Your bill {facts.bill_number} from {facts.hospital_name}, dated "
        f"{facts.bill_date}, has passed access-code verification.\n"
        f"Recorded total amount: {total}. Recorded amount payable by the "
        f"patient: {payable}.\n"
        f"{comparison_sentinel}\n"
        "These figures come from our records; please cross-check them against "
        "the printed bill before you pay. Contact human support for anything "
        "you do not understand."
    )


class ExplanationService:
    """Generates (or falls back to) a safe multilingual bill explanation."""

    def __init__(self, client: OllamaChatClient) -> None:
        self._client = client

    async def explain(
        self, facts: ExplanationFacts, language_code: str
    ) -> ExplanationOutcome:
        """The model tries first; anything unsafe or unavailable falls back."""

        try:
            generated = await self._client.generate(
                system=build_system_prompt(),
                user=build_user_prompt(facts, language_code),
            )
        except OllamaChatError as exc:
            # The reason code names the failure class only; never content.
            logger.info("explanation fell back to deterministic text (%s)", exc)
            return ExplanationOutcome(
                text=fallback_explanation(facts, language_code),
                source=EXPLANATION_SOURCE_FALLBACK,
                reason=str(exc),
            )

        problems = validator_problems(generated, facts)
        if problems:
            logger.info(
                "explanation rejected by validation (%d problem(s)); falling back",
                len(problems),
            )
            return ExplanationOutcome(
                text=fallback_explanation(facts, language_code),
                source=EXPLANATION_SOURCE_FALLBACK,
                reason=problems[0],
            )

        return ExplanationOutcome(
            text=generated,
            source=EXPLANATION_SOURCE_GENERATED,
        )
