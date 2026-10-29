import { afterEach, describe, expect, it, vi } from 'vitest';
import {
  API_BASE_URL,
  CONSENT_POLICY_VERSION,
  ApiError,
  createSession,
  fetchVerifiedBill,
  grantConsent,
  identifyByBillNumber,
  identifyByPhoto,
  verifyAccessCode,
} from '../lib/api';

function mockFetch(status: number, body: unknown) {
  const fn = vi.fn(async () => ({
    ok: status >= 200 && status < 300,
    status,
    text: async () => JSON.stringify(body),
  }));
  vi.stubGlobal('fetch', fn);
  return fn;
}

const SESSION_ID = 'test-session-0123456789abcdef';

const IDENTIFIED = {
  identification_id: 'ident-123',
  status: 'access_code_required',
  hospital_name: 'Sunrise Multispeciality Hospital',
  bill_number: 'SUN-2026-004512',
  message: 'Found a bill.',
  next_action: 'verify_access_code',
};

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('API client contract', () => {
  it('creates a session with a POST and no body', async () => {
    const fn = mockFetch(201, {
      session_id: SESSION_ID,
      consent: { recorded: false, decision: null, policy_version: null, recorded_at: null },
    });

    const session = await createSession();

    expect(session.sessionId).toBe(SESSION_ID);
    expect(fn).toHaveBeenCalledTimes(1);
    const [url, init] = fn.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toBe(`${API_BASE_URL}/api/v1/sessions`);
    expect(init.method).toBe('POST');
    expect(init.body).toBeUndefined();
  });

  it('records consent with the policy version and JSON content type', async () => {
    const fn = mockFetch(200, {
      session_id: SESSION_ID,
      decision: 'granted',
      policy_version: CONSENT_POLICY_VERSION,
      recorded_at: '2026-03-14T10:00:00Z',
    });

    await grantConsent(SESSION_ID);

    const [url, init] = fn.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toBe(`${API_BASE_URL}/api/v1/sessions/${SESSION_ID}/consent`);
    expect(init.headers).toEqual({ 'Content-Type': 'application/json' });
    expect(JSON.parse(String(init.body))).toEqual({
      decision: 'granted',
      policy_version: CONSENT_POLICY_VERSION,
    });
  });

  it('uploads the real file as multipart with the session id and no manual boundary', async () => {
    const fn = mockFetch(200, IDENTIFIED);
    const file = new File(['image-bytes'], 'bill.png', { type: 'image/png' });

    const result = await identifyByPhoto(SESSION_ID, file);

    expect(result.status).toBe('access_code_required');
    const [url, init] = fn.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toBe(`${API_BASE_URL}/api/v1/identifications/upload`);
    expect(init.method).toBe('POST');
    const form = init.body as FormData;
    expect(form.get('session_id')).toBe(SESSION_ID);
    const sent = form.get('file') as File;
    expect(sent.name).toBe('bill.png');
    expect(sent.type).toBe('image/png');
    // The browser must generate the multipart boundary itself.
    expect(init.headers).toBeUndefined();
  });

  it('sends a bill number with an optional hospital identifier', async () => {
    const fn = mockFetch(200, IDENTIFIED);

    await identifyByBillNumber(SESSION_ID, 'SUN-2026-004512', 'Sunrise Hospital');

    const [url, init] = fn.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toBe(`${API_BASE_URL}/api/v1/identifications`);
    expect(JSON.parse(String(init.body))).toEqual({
      session_id: SESSION_ID,
      bill_number: 'SUN-2026-004512',
      hospital_identifier: 'Sunrise Hospital',
    });
  });

  it('omits an empty hospital identifier', async () => {
    const fn = mockFetch(200, IDENTIFIED);

    await identifyByBillNumber(SESSION_ID, 'SUN-2026-004512', '');

    const [, init] = fn.mock.calls[0] as unknown as [string, RequestInit];
    expect(JSON.parse(String(init.body))).not.toHaveProperty('hospital_identifier');
  });

  it('verifies an access code against the identified bill', async () => {
    const fn = mockFetch(200, {
      identification_id: 'ident-123',
      status: 'verified',
      verified_at: '2026-03-14T10:05:00Z',
      comparison: { status: 'matched', message: 'Amounts match.' },
    });

    const result = await verifyAccessCode('ident-123', SESSION_ID, 'DEMO1234');

    expect(result.status).toBe('verified');
    expect(result.comparison?.status).toBe('matched');
    const [url, init] = fn.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toBe(`${API_BASE_URL}/api/v1/identifications/ident-123/verify`);
    expect(JSON.parse(String(init.body))).toEqual({
      session_id: SESSION_ID,
      access_code: 'DEMO1234',
    });
  });

  it('reads the protected bill with the session id in a header', async () => {
    const fn = mockFetch(200, {
      identification_id: 'ident-123',
      status: 'verified',
      verified_at: '2026-03-14T10:05:00Z',
      bill_number: 'SUN-2026-004512',
      hospital_name: 'Sunrise Multispeciality Hospital',
      bill_date: '2026-03-14',
      amounts: {
        total_amount: { label: 'total', value: '12480.00', authoritative: true },
        patient_payable: { label: 'patient_payable', value: '6240.00', authoritative: true },
      },
      comparison: null,
      uploaded_amounts: [
        { label: 'total', value: '12480.00', authoritative: false },
      ],
    });

    const bill = await fetchVerifiedBill('ident-123', SESSION_ID);

    expect(bill.amounts.total_amount?.value).toBe('12480.00');
    expect(bill.amounts.patient_payable?.value).toBe('6240.00');
    expect(bill.uploaded_amounts?.[0].authoritative).toBe(false);
    const [url, init] = fn.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toBe(`${API_BASE_URL}/api/v1/verified-bills/ident-123`);
    expect(init.headers).toEqual({ 'X-Session-ID': SESSION_ID });
  });

  it('surfaces the backend error envelope with status, code and request id', async () => {
    mockFetch(413, {
      error: {
        code: 'payload_too_large',
        message: 'The uploaded file is too large.',
        request_id: 'req-9',
        details: null,
      },
    });

    const failure = await identifyByPhoto(
      SESSION_ID,
      new File(['x'], 'bill.png', { type: 'image/png' }),
    ).catch((error: unknown) => error);

    expect(failure).toBeInstanceOf(ApiError);
    const error = failure as ApiError;
    expect(error.status).toBe(413);
    expect(error.code).toBe('payload_too_large');
    expect(error.requestId).toBe('req-9');
    expect(error.message).toBe('The uploaded file is too large.');
  });

  it('reports an unreachable service as a network error, not a bill result', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => {
        throw new TypeError('Failed to fetch');
      }),
    );

    const failure = await createSession().catch((error: unknown) => error);

    expect(failure).toBeInstanceOf(ApiError);
    expect((failure as ApiError).code).toBe('network_error');
    expect((failure as ApiError).status).toBe(0);
  });

  it('rejects a success response with an unexpected body', async () => {
    mockFetch(200, { status: 'access_code_required' });

    const failure = await identifyByBillNumber(SESSION_ID, 'SUN-2026-004512', '').catch(
      (error: unknown) => error,
    );

    expect(failure).toBeInstanceOf(ApiError);
    expect((failure as ApiError).code).toBe('unexpected_response');
  });

  it('propagates cancellation instead of turning it into an API error', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => {
        throw Object.assign(new Error('Aborted'), { name: 'AbortError' });
      }),
    );

    const failure = await identifyByPhoto(
      SESSION_ID,
      new File(['x'], 'bill.png', { type: 'image/png' }),
    ).catch((error: unknown) => error);

    expect(failure).not.toBeInstanceOf(ApiError);
    expect((failure as Error).name).toBe('AbortError');
  });
});
