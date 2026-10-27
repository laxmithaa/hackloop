"""Application errors that map to consistent JSON error responses.

Raise these types from routes or services when the failure is expected and the
message is safe to show to a client. Unexpected exceptions are converted to a
generic 500 response by the exception handlers so that internal details never
leak.
"""

from __future__ import annotations

from app.schemas.errors import FieldError


class AppError(Exception):
    """Base class for expected, client-safe application failures."""

    status_code: int = 500
    code: str = "internal_error"
    default_message: str = "An unexpected error occurred."

    def __init__(
        self,
        message: str | None = None,
        *,
        code: str | None = None,
        details: list[FieldError] | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.message = message or self.default_message
        self.code = code or type(self).code
        self.details = details
        self.headers = headers or {}
        super().__init__(self.message)


class BadRequestError(AppError):
    """The client sent a request that cannot be processed."""

    status_code = 400
    code = "bad_request"
    default_message = "The request could not be processed."


class NotFoundError(AppError):
    """The requested resource does not exist."""

    status_code = 404
    code = "not_found"
    default_message = "The requested resource was not found."


class ConflictError(AppError):
    """The request conflicts with the current state of the resource."""

    status_code = 409
    code = "conflict"
    default_message = "The request conflicts with the current state of the resource."


class PermissionDeniedError(AppError):
    """The caller is not allowed to perform this action."""

    status_code = 403
    code = "permission_denied"
    default_message = "You do not have permission to perform this action."


# --- Phase 2 domain errors ---------------------------------------------------


class SessionNotFoundError(NotFoundError):
    """No active session exists for the supplied identifier."""

    code = "session_not_found"
    default_message = "No active session was found for this identifier. Please start a new session."


class SessionExpiredError(NotFoundError):
    """The session existed but its validity window has passed."""

    code = "session_expired"
    default_message = "This session has expired. Please start a new session."


class ConsentRequiredError(PermissionDeniedError):
    """Bill processing was attempted without granted (or non-withdrawn) consent."""

    code = "consent_required"
    default_message = "Patient consent must be recorded before bill identification."


class ImageValidationError(BadRequestError):
    """Reusable base for upload-format, corruption and dimension problems.

    ``code`` distinguishes the concrete problem, e.g. ``unsupported_image_format``.
    """

    default_message = "The uploaded image is not valid."


class PayloadTooLargeError(AppError):
    """The upload exceeds the configured size limit."""

    status_code = 413
    code = "payload_too_large"
    default_message = "The uploaded file is too large."


class OcrUnavailableError(AppError):
    """The local OCR engine cannot be used right now (missing dependency or executable).

    This is a technical error, never a business outcome: it must not be reported
    as 'bill not found' or 'bill identified'.
    """

    status_code = 503
    code = "ocr_unavailable"
    default_message = (
        "The OCR engine is currently unavailable. Manual bill-number entry still works."
    )


class OcrProcessingError(AppError):
    """The OCR engine started but failed to process the image."""

    status_code = 500
    code = "ocr_processing_failed"
    default_message = "The OCR engine failed to process the image. Please try again."


# --- Phase 3 domain errors ---------------------------------------------------


class IdentificationNotFoundError(NotFoundError):
    """The identification does not exist (or belongs to a different session).

    Deliberately uses the same response for both cases so that a valid
    identification id from *another* session reveals nothing except its own
    rejection.
    """

    code = "identification_not_found"
    default_message = "No such identification exists in this session."


class IdentificationNotVerifiableError(ConflictError):
    """Only identifications that returned `access_code_required` can be verified."""

    code = "identification_not_verifiable"
    default_message = "This identification does not require access-code verification."


class ChallengeExpiredError(AppError):
    """The verification challenge is gone: it expired or was already used.

    A fresh identification creates a fresh challenge; to recover, re-identify
    the bill (e.g. re-submit the upload) and verify the new identification.
    """

    status_code = 410
    code = "verification_challenge_expired"
    default_message = (
        "This verification request has expired. Please identify the bill again "
        "to get a new verification window."
    )


class ChallengeLockedError(AppError):
    """Too many failed access-code attempts; the challenge refuses further tries."""

    status_code = 403
    code = "verification_locked"
    default_message = (
        "Too many incorrect access-code attempts. Please identify the bill again "
        "to get a new verification attempt."
    )


class AccessCodeInvalidError(AppError):
    """The submitted access code is not correct. No record information is revealed."""

    status_code = 401
    code = "access_code_invalid"
    default_message = "The access code is not correct. Please try again."


class VerificationRequiredError(PermissionDeniedError):
    """Protected bill information was requested without a successful verification."""

    code = "verification_required"
    default_message = "Access-code verification is required before viewing bill amounts."


# --- Phase 4 domain errors ---------------------------------------------------


class HelpTicketNotFoundError(NotFoundError):
    """No such help-request ticket (or it belongs to a different session).

    The same answer for both cases prevents ticket-id guessing.
    """

    code = "help_ticket_not_found"
    default_message = "No such help request is available."


class InvalidHelpStatusTransitionError(ConflictError):
    """The requested workflow status is not reachable from the ticket's current
    status (only forward transitions are allowed; ``resolved`` is terminal)."""

    code = "invalid_status_transition"
    default_message = (
        "This workflow status change is not allowed from the request's current status."
    )


class SupportStaffNotConfiguredError(AppError):
    """Support-worker access fails closed when no staff token is configured."""

    status_code = 503
    code = "support_staff_unavailable"
    default_message = "Support-worker access is not configured on this server."


class SupportStaffAuthError(AppError):
    """The staff token is missing or incorrect. No detail is revealed."""

    status_code = 401
    code = "support_staff_unauthorized"
    default_message = "Support-worker authentication is required."


# --- Phase 9 domain errors ---------------------------------------------------


class QuestionTooLongError(BadRequestError):
    """The follow-up question exceeds the configured character ceiling."""

    status_code = 422
    code = "question_too_long"
    default_message = "The question is longer than the allowed limit."


class AiQuestionLimitError(AppError):
    """The session has used all of its follow-up questions for this bill."""

    status_code = 429
    code = "ai_question_limit_reached"
    default_message = (
        "The question limit for this session has been reached. "
        "Please start a new session to ask more questions."
    )


class CaregiverShareInvalidError(PermissionDeniedError):
    """No live caregiver share matches this bill (missing, expired or revoked)."""

    code = "caregiver_share_invalid"
    default_message = "This caregiver share code is missing, invalid, expired or has been revoked."


class CaregiverShareLimitError(ConflictError):
    """Too many active caregiver shares exist for this bill or session."""

    code = "caregiver_share_limit_reached"
    default_message = "Too many active caregiver shares exist. Revoke an existing share first."
