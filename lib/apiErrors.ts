import { isApiError } from './api';
import type { TranslationKey } from './translations';

/**
 * A user-facing description of a failed API call.
 *
 * `key` is a translation key when the failure has a known, localizable meaning;
 * `message` keeps the server's own (English) explanation for unknown codes.
 */
export type ApiFailure = {
  code: string;
  status: number;
  key: TranslationKey | null;
  message: string;
  requestId?: string;
};

const CODE_KEYS: Partial<Record<string, TranslationKey>> = {
  network_error: 'networkError',
  ocr_unavailable: 'ocrUnavailable',
  ocr_processing_failed: 'ocrFailed',
  unsupported_image_format: 'unsupportedImage',
  corrupt_image: 'corruptImage',
  image_dimensions_exceed_limit: 'imageTooLargeDims',
  payload_too_large: 'fileTooLarge',
  consent_required: 'consentRequiredServer',
  session_not_found: 'sessionExpired',
  session_expired: 'sessionExpired',
  verification_challenge_expired: 'codeExpired',
  verification_locked: 'codeLocked',
  access_code_invalid: 'codeIncorrect',
  identification_not_found: 'identificationMissing',
  identification_not_verifiable: 'notVerifiable',
  verification_required: 'verificationRequired',
  validation_error: 'invalidRequest',
  unexpected_response: 'unexpectedResponse',
  service_unavailable: 'serviceUnavailable',
  internal_error: 'serviceError',
};

/** Translate an unknown thrown value into a stable UI description. */
export function describeApiError(error: unknown): ApiFailure {
  if (isApiError(error)) {
    const known = CODE_KEYS[error.code];
    const fallback: TranslationKey | null =
      known ??
      (error.status === 0
        ? 'networkError'
        : error.status >= 500
          ? 'serviceError'
          : error.status === 413
            ? 'fileTooLarge'
            : error.status === 422
              ? 'invalidRequest'
              : error.status === 404
                ? 'identificationMissing'
                : null);
    return {
      code: error.code,
      status: error.status,
      key: fallback,
      message: error.message,
      requestId: error.requestId,
    };
  }

  return {
    code: 'unknown_error',
    status: 0,
    key: 'serviceError',
    message: error instanceof Error ? error.message : 'Unknown error.',
  };
}

/** The message to render for a failure, preferring the localized key. */
export function failureMessage(
  failure: ApiFailure,
  t: (key: TranslationKey) => string,
): string {
  return failure.key ? t(failure.key) : failure.message;
}
