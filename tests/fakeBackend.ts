import { vi } from 'vitest';
import type { ComparisonStatus, IdentificationStatus } from '../lib/api';

export const SESSION_ID = 'test-session-0123456789abcdef';
export const ACCESS_CODE = 'DEMO1234';
export const IDENTIFICATION_ID = 'ident-123';

type BackendError = { status: number; code: string; message?: string };

type BillFixture = {
  total: string;
  payable: string;
  comparison: ComparisonStatus | null;
  uploaded: { label: 'total'; value: string }[];
};

const DEFAULT_BILL: BillFixture = {
  total: '12480.00',
  payable: '6240.00',
  comparison: 'matched',
  uploaded: [],
};

/** Mutable scenario shared by the fake HTTP layer and the tests. */
export const backend = {
  identificationStatus: 'access_code_required' as IdentificationStatus,
  identificationError: null as BackendError | null,
  consentError: null as BackendError | null,
  verificationError: null as BackendError | null,
  billError: null as BackendError | null,
  networkError: false,
  delayMs: 0,
  bill: { ...DEFAULT_BILL } as BillFixture,
  attempts: 0,
  consentDecision: null as string | null,
  uploadCalls: 0,
  numberCalls: 0,
  consentCalls: 0,
  withdrawCalls: 0,
  verifyCalls: 0,
  billCalls: 0,
  lastUpload: null as FormData | null,
  lastUploadHeaders: null as Record<string, string> | null,
  lastNumberBody: null as Record<string, unknown> | null,
  lastVerifyBody: null as Record<string, unknown> | null,
  lastConsentBody: null as Record<string, unknown> | null,
  lastSessionHeader: null as string | null,
};

export function resetBackend() {
  backend.identificationStatus = 'access_code_required';
  backend.identificationError = null;
  backend.consentError = null;
  backend.verificationError = null;
  backend.billError = null;
  backend.networkError = false;
  backend.delayMs = 0;
  backend.bill = { ...DEFAULT_BILL };
  backend.attempts = 0;
  backend.consentDecision = null;
  backend.uploadCalls = 0;
  backend.numberCalls = 0;
  backend.consentCalls = 0;
  backend.withdrawCalls = 0;
  backend.verifyCalls = 0;
  backend.billCalls = 0;
  backend.lastUpload = null;
  backend.lastUploadHeaders = null;
  backend.lastNumberBody = null;
  backend.lastVerifyBody = null;
  backend.lastConsentBody = null;
  backend.lastSessionHeader = null;
}

function respond(status: number, body: unknown): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    text: async () => JSON.stringify(body),
  } as unknown as Response;
}

function errorResponse(error: BackendError): Response {
  return respond(error.status, {
    error: {
      code: error.code,
      message: error.message ?? error.code,
      request_id: 'req-test-1234',
      details: null,
    },
  });
}

function identificationBody(status: IdentificationStatus) {
  const base = {
    identification_id: IDENTIFICATION_ID,
    status,
    hospital_name: null as string | null,
    bill_number: null as string | null,
    message: 'Fake backend outcome.',
    next_action: 'enter_bill_number_manually',
  };
  switch (status) {
    case 'access_code_required':
      return {
        ...base,
        hospital_name: 'Sunrise Multispeciality Hospital',
        bill_number: 'SUN-2026-004512',
        next_action: 'verify_access_code',
      };
    case 'bill_not_found':
      return { ...base, bill_number: 'NOPE-0001', next_action: 'check_bill_number' };
    case 'bill_number_not_found':
      return {
        ...base,
        hospital_name: 'Sunrise Multispeciality Hospital',
        next_action: 'enter_bill_number_manually',
      };
    case 'hospital_not_registered':
      return { ...base, next_action: 'check_hospital_name' };
    case 'ambiguous_hospital':
      return { ...base, next_action: 'provide_hospital_identifier' };
    default:
      return base;
  }
}

type Handler = (input: unknown, init?: RequestInit) => Promise<Response>;

async function handle(input: unknown, init?: RequestInit): Promise<Response> {
  const rawUrl =
    typeof input === 'string'
      ? input
      : typeof input === 'object' && input !== null && 'url' in input
        ? String((input as { url: unknown }).url)
        : String(input);
  const path = new URL(rawUrl).pathname;
  const method = init?.method ?? 'GET';
  const jsonBody = () => JSON.parse(String(init?.body ?? '{}')) as Record<string, unknown>;

  if (backend.delayMs > 0) {
    await new Promise((resolve) => setTimeout(resolve, backend.delayMs));
  }
  if (backend.networkError) {
    throw new TypeError('Failed to fetch');
  }

  if (method === 'POST' && path === '/api/v1/sessions') {
    return respond(201, {
      session_id: SESSION_ID,
      consent: { recorded: false, decision: null, policy_version: null, recorded_at: null },
    });
  }

  if (method === 'POST' && /\/consent\/withdraw$/.test(path)) {
    backend.withdrawCalls += 1;
    backend.consentDecision = 'withdrawn';
    return respond(200, {
      session_id: SESSION_ID,
      decision: 'withdrawn',
      policy_version: 'patient-consent-2026-10-v1',
      recorded_at: '2026-03-14T10:00:00Z',
    });
  }

  if (method === 'POST' && /\/consent$/.test(path)) {
    backend.consentCalls += 1;
    if (backend.consentError) return errorResponse(backend.consentError);
    const body = jsonBody();
    backend.lastConsentBody = body;
    backend.consentDecision = String(body.decision);
    return respond(200, {
      session_id: SESSION_ID,
      decision: body.decision,
      policy_version: body.policy_version,
      recorded_at: '2026-03-14T10:00:00Z',
    });
  }

  if (method === 'POST' && path === '/api/v1/identifications/upload') {
    backend.uploadCalls += 1;
    const body = init?.body;
    if (!(body instanceof FormData)) {
      return errorResponse({ status: 422, code: 'validation_error' });
    }
    backend.lastUpload = body;
    backend.lastUploadHeaders = (init?.headers as Record<string, string> | undefined) ?? null;
    if (!body.get('session_id') || !body.get('file')) {
      return errorResponse({
        status: 422,
        code: 'validation_error',
        message: 'session_id and file are required.',
      });
    }
    if (backend.identificationError) return errorResponse(backend.identificationError);
    return respond(200, identificationBody(backend.identificationStatus));
  }

  if (method === 'POST' && path === '/api/v1/identifications') {
    backend.numberCalls += 1;
    backend.lastNumberBody = jsonBody();
    if (backend.identificationError) return errorResponse(backend.identificationError);
    return respond(200, identificationBody(backend.identificationStatus));
  }

  if (method === 'POST' && /^\/api\/v1\/identifications\/[^/]+\/verify$/.test(path)) {
    backend.verifyCalls += 1;
    const body = jsonBody();
    backend.lastVerifyBody = body;
    if (backend.verificationError) return errorResponse(backend.verificationError);
    if (String(body.access_code) !== ACCESS_CODE) {
      backend.attempts += 1;
      if (backend.attempts >= 3) {
        return errorResponse({
          status: 403,
          code: 'verification_locked',
          message: 'Too many incorrect access-code attempts.',
        });
      }
      return errorResponse({
        status: 401,
        code: 'access_code_invalid',
        message: 'The access code is not correct.',
      });
    }
    return respond(200, {
      identification_id: IDENTIFICATION_ID,
      status: 'verified',
      verified_at: '2026-03-14T10:05:00Z',
      comparison: backend.bill.comparison
        ? { status: backend.bill.comparison, message: 'Comparison summary.' }
        : null,
    });
  }

  if (method === 'GET' && /^\/api\/v1\/verified-bills\/[^/]+$/.test(path)) {
    backend.billCalls += 1;
    backend.lastSessionHeader =
      ((init?.headers as Record<string, string> | undefined)?.['X-Session-ID']) ?? null;
    if (backend.billError) return errorResponse(backend.billError);
    return respond(200, {
      identification_id: IDENTIFICATION_ID,
      status: 'verified',
      verified_at: '2026-03-14T10:05:00Z',
      bill_number: 'SUN-2026-004512',
      hospital_name: 'Sunrise Multispeciality Hospital',
      bill_date: '2026-03-14',
      amounts: {
        total_amount: { label: 'total', value: backend.bill.total, authoritative: true },
        patient_payable: {
          label: 'patient_payable',
          value: backend.bill.payable,
          authoritative: true,
        },
      },
      comparison: backend.bill.comparison
        ? { status: backend.bill.comparison, message: 'Comparison summary.' }
        : null,
      uploaded_amounts: backend.bill.uploaded,
    });
  }

  throw new Error(`Unexpected fake-backend request: ${method} ${path}`);
}

export function installFetch() {
  const mock = vi.fn(handle as Handler);
  vi.stubGlobal('fetch', mock);
  return mock;
}
