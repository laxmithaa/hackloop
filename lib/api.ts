/**
 * Typed client for the Healthcare Bill Navigator FastAPI backend.
 *
 * The contract implemented here mirrors the running backend in `hackloop2`:
 *
 * - POST /api/v1/sessions                        -> { session_id, consent }
 * - POST /api/v1/sessions/{id}/consent           -> { session_id, decision, ... }
 * - POST /api/v1/sessions/{id}/consent/withdraw  -> { session_id, decision, ... }
 * - POST /api/v1/identifications                 -> IdentificationResponse
 * - POST /api/v1/identifications/upload          -> IdentificationResponse (multipart: session_id + file)
 * - POST /api/v1/identifications/{id}/verify     -> VerificationResponse
 * - GET  /api/v1/verified-bills/{id}            -> VerifiedBillResponse (X-Session-ID header)
 *
 * Every non-2xx response uses the backend error envelope
 * `{ "error": { "code", "message", "request_id", "details" } }`.
 */

export const API_BASE_URL = (
  process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://127.0.0.1:8000'
).replace(/\/+$/, '');

/**
 * Consent policy version the frontend asks the patient to accept. It must match
 * the backend's HBN_CONSENT_POLICY_VERSION; the backend rejects stale versions.
 */
export const CONSENT_POLICY_VERSION =
  process.env.NEXT_PUBLIC_CONSENT_POLICY_VERSION ?? 'patient-consent-2026-10-v1';

export type IdentificationStatus =
  | 'access_code_required'
  | 'bill_not_found'
  | 'bill_number_not_found'
  | 'hospital_not_registered'
  | 'unreadable_image'
  | 'ambiguous_hospital';

export type IdentificationNextAction =
  | 'verify_access_code'
  | 'enter_bill_number_manually'
  | 'provide_hospital_identifier'
  | 'check_bill_number'
  | 'check_hospital_name';

export type IdentificationResult = {
  identification_id: string;
  status: IdentificationStatus;
  hospital_name: string | null;
  bill_number: string | null;
  message: string;
  next_action: IdentificationNextAction;
};

export type ComparisonStatus =
  | 'matched'
  | 'amounts_differ'
  | 'insufficient_evidence'
  | 'no_uploaded_image';

export type ComparisonSummary = { status: ComparisonStatus; message: string };

export type VerificationResult = {
  identification_id: string;
  status: 'verified';
  verified_at: string;
  comparison: ComparisonSummary | null;
};

export type RecordedAmount = {
  label: 'total' | 'patient_payable';
  value: string;
  authoritative: true;
};

export type UploadedAmount = {
  label: 'total' | 'patient_payable';
  value: string;
  authoritative: false;
};

export type VerifiedBill = {
  identification_id: string;
  status: 'verified';
  verified_at: string;
  bill_number: string;
  hospital_name: string;
  bill_date: string;
  amounts: Partial<Record<string, RecordedAmount>>;
  comparison: ComparisonSummary | null;
  uploaded_amounts: UploadedAmount[] | null;
};

export type SessionInfo = {
  sessionId: string;
  consentRecorded: boolean;
};

export type ApiErrorInit = {
  code: string;
  status: number;
  message: string;
  requestId?: string;
  details?: unknown;
};

/** A failed API call with the backend's stable error code and HTTP status. */
export class ApiError extends Error {
  readonly code: string;
  readonly status: number;
  readonly requestId?: string;
  readonly details?: unknown;

  constructor(init: ApiErrorInit) {
    super(init.message);
    this.name = 'ApiError';
    this.code = init.code;
    this.status = init.status;
    this.requestId = init.requestId;
    this.details = init.details;
  }
}

export function isApiError(value: unknown): value is ApiError {
  return value instanceof ApiError;
}

/** True for a fetch aborted by the caller (cancel button, navigation, restart). */
export function isAbortError(value: unknown): boolean {
  return (
    typeof value === 'object' &&
    value !== null &&
    (value as { name?: unknown }).name === 'AbortError'
  );
}

type JsonRecord = Record<string, unknown>;

function isRecord(value: unknown): value is JsonRecord {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function isStringOrNull(value: unknown): value is string | null {
  return typeof value === 'string' || value === null;
}

function unexpectedResponse(message: string): ApiError {
  return new ApiError({ code: 'unexpected_response', status: 0, message });
}

async function readJson(response: Response): Promise<unknown> {
  try {
    const text = await response.text();
    if (!text) return null;
    return JSON.parse(text) as unknown;
  } catch {
    return null;
  }
}

function envelopeOf(payload: unknown): {
  code?: string;
  message?: string;
  requestId?: string;
  details?: unknown;
} {
  if (!isRecord(payload) || !isRecord(payload.error)) return {};
  const { code, message, request_id: requestId, details } = payload.error;
  return {
    code: typeof code === 'string' ? code : undefined,
    message: typeof message === 'string' ? message : undefined,
    requestId: typeof requestId === 'string' ? requestId : undefined,
    details,
  };
}

type RequestOptions = {
  method?: 'GET' | 'POST';
  body?: BodyInit;
  headers?: Record<string, string>;
  signal?: AbortSignal;
};

async function request(path: string, options: RequestOptions = {}): Promise<unknown> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      method: options.method ?? 'GET',
      body: options.body,
      headers: options.headers,
      signal: options.signal,
    });
  } catch (error) {
    if (isAbortError(error)) throw error;
    throw new ApiError({
      code: 'network_error',
      status: 0,
      message: 'The bill service could not be reached.',
    });
  }

  const payload = await readJson(response);
  if (!response.ok) {
    const envelope = envelopeOf(payload);
    throw new ApiError({
      code: envelope.code ?? `http_${response.status}`,
      status: response.status,
      message: envelope.message ?? 'The request could not be completed.',
      requestId: envelope.requestId,
      details: envelope.details,
    });
  }
  return payload;
}

function parseSession(payload: unknown): SessionInfo {
  if (!isRecord(payload) || typeof payload.session_id !== 'string' || !payload.session_id) {
    throw unexpectedResponse('The bill service did not return a valid session.');
  }
  const consent = isRecord(payload.consent) ? payload.consent : {};
  return {
    sessionId: payload.session_id,
    consentRecorded: consent.decision === 'granted' || consent.recorded === true,
  };
}

const IDENTIFICATION_STATUSES: readonly IdentificationStatus[] = [
  'access_code_required',
  'bill_not_found',
  'bill_number_not_found',
  'hospital_not_registered',
  'unreadable_image',
  'ambiguous_hospital',
];

const NEXT_ACTIONS: readonly IdentificationNextAction[] = [
  'verify_access_code',
  'enter_bill_number_manually',
  'provide_hospital_identifier',
  'check_bill_number',
  'check_hospital_name',
];

function parseIdentification(payload: unknown): IdentificationResult {
  if (
    !isRecord(payload) ||
    typeof payload.identification_id !== 'string' ||
    typeof payload.status !== 'string' ||
    !IDENTIFICATION_STATUSES.includes(payload.status as IdentificationStatus) ||
    typeof payload.message !== 'string' ||
    typeof payload.next_action !== 'string' ||
    !NEXT_ACTIONS.includes(payload.next_action as IdentificationNextAction) ||
    !isStringOrNull(payload.hospital_name) ||
    !isStringOrNull(payload.bill_number)
  ) {
    throw unexpectedResponse('The bill service returned an unexpected identification result.');
  }
  return {
    identification_id: payload.identification_id,
    status: payload.status as IdentificationStatus,
    hospital_name: payload.hospital_name,
    bill_number: payload.bill_number,
    message: payload.message,
    next_action: payload.next_action as IdentificationNextAction,
  };
}

function parseComparison(value: unknown): ComparisonSummary | null {
  if (!isRecord(value) || typeof value.status !== 'string' || typeof value.message !== 'string') {
    return null;
  }
  const statuses: readonly ComparisonStatus[] = [
    'matched',
    'amounts_differ',
    'insufficient_evidence',
    'no_uploaded_image',
  ];
  if (!statuses.includes(value.status as ComparisonStatus)) return null;
  return { status: value.status as ComparisonStatus, message: value.message };
}

function parseVerification(payload: unknown): VerificationResult {
  if (
    !isRecord(payload) ||
    typeof payload.identification_id !== 'string' ||
    payload.status !== 'verified' ||
    typeof payload.verified_at !== 'string'
  ) {
    throw unexpectedResponse('The bill service returned an unexpected verification result.');
  }
  return {
    identification_id: payload.identification_id,
    status: 'verified',
    verified_at: payload.verified_at,
    comparison: parseComparison(payload.comparison),
  };
}

function parseVerifiedBill(payload: unknown): VerifiedBill {
  if (
    !isRecord(payload) ||
    typeof payload.identification_id !== 'string' ||
    payload.status !== 'verified' ||
    typeof payload.verified_at !== 'string' ||
    typeof payload.bill_number !== 'string' ||
    typeof payload.hospital_name !== 'string' ||
    typeof payload.bill_date !== 'string' ||
    !isRecord(payload.amounts)
  ) {
    throw unexpectedResponse('The bill service returned unexpected bill information.');
  }

  const amounts: VerifiedBill['amounts'] = {};
  for (const [key, amount] of Object.entries(payload.amounts)) {
    if (
      isRecord(amount) &&
      (amount.label === 'total' || amount.label === 'patient_payable') &&
      typeof amount.value === 'string' &&
      amount.authoritative === true
    ) {
      amounts[key] = {
        label: amount.label,
        value: amount.value,
        authoritative: true,
      };
    }
  }

  const uploaded = Array.isArray(payload.uploaded_amounts)
    ? payload.uploaded_amounts.flatMap((item): UploadedAmount[] => {
        if (
          isRecord(item) &&
          (item.label === 'total' || item.label === 'patient_payable') &&
          typeof item.value === 'string'
        ) {
          return [{ label: item.label, value: item.value, authoritative: false }];
        }
        return [];
      })
    : null;

  return {
    identification_id: payload.identification_id,
    status: 'verified',
    verified_at: payload.verified_at,
    bill_number: payload.bill_number,
    hospital_name: payload.hospital_name,
    bill_date: payload.bill_date,
    amounts,
    comparison: parseComparison(payload.comparison),
    uploaded_amounts: uploaded,
  };
}

/** Create an anonymous, in-memory patient session. */
export async function createSession(signal?: AbortSignal): Promise<SessionInfo> {
  const payload = await request('/api/v1/sessions', { method: 'POST', signal });
  return parseSession(payload);
}

/** Record the patient's consent decision on the server. */
export async function grantConsent(
  sessionId: string,
  signal?: AbortSignal,
): Promise<void> {
  await request(`/api/v1/sessions/${encodeURIComponent(sessionId)}/consent`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ decision: 'granted', policy_version: CONSENT_POLICY_VERSION }),
    signal,
  });
}

/** Withdraw a previously recorded consent. */
export async function withdrawConsent(
  sessionId: string,
  signal?: AbortSignal,
): Promise<void> {
  await request(`/api/v1/sessions/${encodeURIComponent(sessionId)}/consent/withdraw`, {
    method: 'POST',
    signal,
  });
}

/** Identify a bill from a photo. The browser sets the multipart boundary itself. */
export async function identifyByPhoto(
  sessionId: string,
  file: File,
  signal?: AbortSignal,
): Promise<IdentificationResult> {
  const form = new FormData();
  form.append('session_id', sessionId);
  form.append('file', file, file.name);
  const payload = await request('/api/v1/identifications/upload', {
    method: 'POST',
    body: form,
    signal,
  });
  return parseIdentification(payload);
}

/** Identify a bill from a typed bill number and optional hospital name/code. */
export async function identifyByBillNumber(
  sessionId: string,
  billNumber: string,
  hospitalIdentifier?: string,
  signal?: AbortSignal,
): Promise<IdentificationResult> {
  const body: JsonRecord = { session_id: sessionId, bill_number: billNumber };
  if (hospitalIdentifier) body.hospital_identifier = hospitalIdentifier;
  const payload = await request('/api/v1/identifications', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    signal,
  });
  return parseIdentification(payload);
}

/** Verify the access code of an identified bill. */
export async function verifyAccessCode(
  identificationId: string,
  sessionId: string,
  accessCode: string,
  signal?: AbortSignal,
): Promise<VerificationResult> {
  const payload = await request(
    `/api/v1/identifications/${encodeURIComponent(identificationId)}/verify`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sessionId, access_code: accessCode }),
      signal,
    },
  );
  return parseVerification(payload);
}

/** Read the protected financial information of a verified bill. */
export async function fetchVerifiedBill(
  identificationId: string,
  sessionId: string,
  signal?: AbortSignal,
): Promise<VerifiedBill> {
  const payload = await request(
    `/api/v1/verified-bills/${encodeURIComponent(identificationId)}`,
    {
      method: 'GET',
      headers: { 'X-Session-ID': sessionId },
      signal,
    },
  );
  return parseVerifiedBill(payload);
}
