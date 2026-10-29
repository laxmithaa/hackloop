import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { AppProvider } from '../components/AppProvider';
import { Navigator } from '../components/Navigator';
import { ACCESS_CODE, SESSION_ID, backend, installFetch, resetBackend } from './fakeBackend';

let path = '/';
const push = vi.fn();
vi.mock('next/navigation', () => ({ usePathname: () => path, useRouter: () => ({ push }) }));
vi.mock('next/link', () => ({
  default: ({ children, href, onClick, ...rest }: { children: React.ReactNode; href: string; onClick?: React.MouseEventHandler<HTMLAnchorElement> }) => (
    <a href={href} {...rest} onClick={(event) => { event.preventDefault(); onClick?.(event); }}>{children}</a>
  ),
}));

const CONSENT_PAGES = ['/patient/identify', '/patient/verify', '/patient/result', '/patient/bill', '/patient/explanation', '/patient/questions', '/caregiver'];

async function show(p: string, { prepare = true }: { prepare?: boolean } = {}) {
  path = prepare && CONSENT_PAGES.includes(p) ? '/patient' : p;
  const view = render(<AppProvider><Navigator /></AppProvider>);
  const go = (next: string) => { path = next; view.rerender(<AppProvider><Navigator /></AppProvider>); };

  if (prepare && CONSENT_PAGES.includes(p)) {
    fireEvent.click(screen.getByRole('button', { name: 'Agree and continue' }));
    await screen.findByRole('link', { name: 'Continue' });
    go('/patient/identify');

    if (p !== '/patient/identify') {
      fireEvent.change(screen.getByLabelText('Bill number'), { target: { value: 'SUN-2026-004512' } });
      fireEvent.click(screen.getByRole('button', { name: /Check bill number/ }));
      await screen.findByRole('link', { name: 'Continue to access code' });
      go('/patient/verify');

      if (p !== '/patient/verify') {
        fireEvent.change(screen.getByLabelText('Access code'), { target: { value: ACCESS_CODE } });
        fireEvent.click(screen.getByRole('button', { name: 'Verify access code' }));
        await waitFor(() => expect(push).toHaveBeenCalledWith('/patient/result'));
        go(p);
      }
    }
  }

  return { ...view, go };
}

async function choosePhoto(name = 'bill.png', type = 'image/png') {
  const file = new File(['image-bytes'], name, { type });
  fireEvent.change(screen.getByLabelText('Choose a photo'), { target: { files: [file] } });
  return file;
}

beforeEach(() => {
  push.mockClear();
  resetBackend();
  installFetch();
  vi.stubGlobal('URL', Object.assign(URL, {
    createObjectURL: vi.fn(() => 'blob:test'),
    revokeObjectURL: vi.fn(),
  }));
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('patient frontend', () => {
  it('switches language on the welcome page', async () => {
    await show('/');
    fireEvent.change(screen.getByLabelText('Language'), { target: { value: 'hi' } });
    expect(screen.getByRole('link', { name: /अपना अस्पताल बिल समझें/ })).toBeInTheDocument();
  });

  it('declines consent without proceeding', async () => {
    await show('/patient');
    fireEvent.click(screen.getByRole('button', { name: 'Decline' }));
    expect(await screen.findByRole('status')).toHaveTextContent('You declined');
    expect(push).not.toHaveBeenCalled();
    expect(screen.queryByRole('link', { name: 'Continue' })).not.toBeInTheDocument();
  });

  it('records consent on the server before continuing', async () => {
    await show('/patient');
    fireEvent.click(screen.getByRole('button', { name: 'Agree and continue' }));
    await screen.findByRole('link', { name: 'Continue' });
    expect(backend.consentCalls).toBe(1);
    expect(backend.lastConsentBody).toMatchObject({
      decision: 'granted',
      policy_version: 'patient-consent-2026-10-v1',
    });
  });

  it('reports a consent that the server refused', async () => {
    backend.consentError = { status: 503, code: 'service_unavailable' };
    await show('/patient');
    fireEvent.click(screen.getByRole('button', { name: 'Agree and continue' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('not available right now');
    expect(screen.queryByRole('link', { name: 'Continue' })).not.toBeInTheDocument();
  });

  it('validates a bill number and sends it to the backend', async () => {
    await show('/patient/identify');
    fireEvent.click(screen.getByRole('button', { name: /Check bill number/ }));
    expect(screen.getByRole('alert')).toHaveTextContent('Enter a bill number');
    expect(backend.numberCalls).toBe(0);

    fireEvent.change(screen.getByLabelText('Bill number'), { target: { value: 'SUN-2026-004512' } });
    fireEvent.click(screen.getByRole('button', { name: /Check bill number/ }));
    expect(await screen.findByRole('link', { name: 'Continue to access code' })).toBeInTheDocument();
    expect(backend.lastNumberBody).toEqual({
      session_id: SESSION_ID,
      bill_number: 'SUN-2026-004512',
    });
  });

  it('rejects unsupported bill photo files before any request', async () => {
    await show('/patient/identify');
    fireEvent.change(screen.getByLabelText('Choose a photo'), {
      target: { files: [new File(['text'], 'bill.txt', { type: 'text/plain' })] },
    });
    expect(screen.getByRole('alert')).toHaveTextContent('Please choose a JPG');
    expect(backend.uploadCalls).toBe(0);
  });

  it('selects, replaces, and removes a photo preview locally', async () => {
    await show('/patient/identify');
    await choosePhoto('first.png');
    expect(screen.getByText(/first.png/)).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText('Replace photo'), {
      target: { files: [new File(['two'], 'second.png', { type: 'image/png' })] },
    });
    expect(screen.getByText(/second.png/)).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Remove photo' }));
    expect(screen.queryByText(/second.png/)).not.toBeInTheDocument();
  });

  it('uploads the real file with the session id and shows the backend result', async () => {
    await show('/patient/identify');
    await choosePhoto();
    fireEvent.click(screen.getByRole('button', { name: 'Send photo for reading' }));

    expect(await screen.findByRole('link', { name: 'Continue to access code' })).toBeInTheDocument();
    expect(screen.getByText('Sunrise Multispeciality Hospital')).toBeInTheDocument();
    expect(screen.getByText('SUN-2026-004512')).toBeInTheDocument();
    expect(backend.uploadCalls).toBe(1);
    const form = backend.lastUpload as FormData;
    expect(form.get('session_id')).toBe(SESSION_ID);
    expect((form.get('file') as File).name).toBe('bill.png');
    expect(backend.lastUploadHeaders).toBeNull();
  });

  it('does not start a second upload on a repeated click', async () => {
    backend.delayMs = 30;
    await show('/patient/identify');
    await choosePhoto();
    const button = screen.getByRole('button', { name: 'Send photo for reading' });
    fireEvent.click(button);
    fireEvent.click(button);

    expect(await screen.findByRole('link', { name: 'Continue to access code' })).toBeInTheDocument();
    expect(backend.uploadCalls).toBe(1);
  });

  it.each([
    ['unreadable image', 'unreadable_image', /could not read this photo clearly/i],
    ['bill not found', 'bill_not_found', /No bill matches that number/i],
    ['bill number not found', 'bill_number_not_found', /could read the hospital name but not a bill number/i],
    ['hospital not registered', 'hospital_not_registered', /not in the demonstration records/i],
    ['ambiguous hospital', 'ambiguous_hospital', /matches more than one hospital/i],
  ])('shows the backend outcome for %s', async (_label, status, text) => {
    backend.identificationStatus = status as typeof backend.identificationStatus;
    await show('/patient/identify');
    await choosePhoto();
    fireEvent.click(screen.getByRole('button', { name: 'Send photo for reading' }));
    expect(await screen.findByText(text)).toBeInTheDocument();
    expect(screen.queryByRole('link', { name: 'Continue to access code' })).not.toBeInTheDocument();
  });

  it('clears the session and disables submission when the backend rejects it', async () => {
    backend.identificationError = { status: 404, code: 'session_not_found' };
    await show('/patient/identify');
    fireEvent.change(screen.getByLabelText('Bill number'), { target: { value: 'SUN-2026-004512' } });
    fireEvent.click(screen.getByRole('button', { name: /Check bill number/ }));

    expect(await screen.findByText(/no active secure session/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Check bill number/ })).toBeDisabled();
    expect(screen.getByRole('link', { name: 'Review consent' })).toHaveAttribute('href', '/patient');
  });

  it.each<[string, number, string, RegExp]>([
    ['400 unsupported image', 400, 'unsupported_image_format', /not a supported photo/i],
    ['403 consent required', 403, 'consent_required', /Consent is required on the server/i],
    ['413 payload too large', 413, 'payload_too_large', /larger than 5 MB/i],
    ['422 validation', 422, 'validation_error', /details were not accepted/i],
    ['500 server error', 500, 'internal_error', /Something went wrong/i],
    ['503 OCR unavailable', 503, 'ocr_unavailable', /Photo reading is not available/i],
  ])('maps %s to a clear message', async (_label, status, code, text) => {
    backend.identificationError = { status, code };
    await show('/patient/identify');
    await choosePhoto();
    fireEvent.click(screen.getByRole('button', { name: 'Send photo for reading' }));
    expect(await screen.findByRole('alert')).toHaveTextContent(text);
    expect(screen.queryByRole('link', { name: 'Continue to access code' })).not.toBeInTheDocument();
  });

  it('offers a recovery state when the service is unreachable', async () => {
    await show('/patient/identify');
    backend.networkError = true;
    fireEvent.change(screen.getByLabelText('Bill number'), { target: { value: 'SUN-2026-004512' } });
    fireEvent.click(screen.getByRole('button', { name: /Check bill number/ }));
    expect(await screen.findByRole('alert')).toHaveTextContent('could not reach the bill service');
    expect(screen.getByText(/If the problem continues/)).toBeInTheDocument();
  });

  it('reports an incorrect access code and keeps the form', async () => {
    await show('/patient/verify');
    fireEvent.change(screen.getByLabelText('Access code'), { target: { value: '9999' } });
    fireEvent.click(screen.getByRole('button', { name: 'Verify access code' }));

    expect(await screen.findByRole('alert')).toHaveTextContent('not correct');
    expect(screen.getByLabelText('Access code')).toBeInTheDocument();
    expect(backend.verifyCalls).toBe(1);
    expect(backend.lastVerifyBody).toMatchObject({ session_id: SESSION_ID });
  });

  it('locks the challenge after three incorrect codes and offers a retry', async () => {
    await show('/patient/verify');
    for (let attempt = 1; attempt <= 3; attempt += 1) {
      fireEvent.change(screen.getByLabelText('Access code'), { target: { value: '9999' } });
      fireEvent.click(screen.getByRole('button', { name: 'Verify access code' }));
      await waitFor(() => expect(backend.verifyCalls).toBe(attempt));
    }

    expect(await screen.findByText(/Too many incorrect attempts/i)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Try again' })).toHaveAttribute('href', '/patient/identify');
  });

  it('handles an expired verification challenge', async () => {
    backend.verificationError = { status: 410, code: 'verification_challenge_expired' };
    await show('/patient/verify');
    fireEvent.change(screen.getByLabelText('Access code'), { target: { value: ACCESS_CODE } });
    fireEvent.click(screen.getByRole('button', { name: 'Verify access code' }));

    expect(await screen.findByText(/verification window has expired/i)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Try again' })).toHaveAttribute('href', '/patient/identify');
    expect(push).not.toHaveBeenCalledWith('/patient/result');
  });

  it('protects financial information before verification', async () => {
    await show('/patient/bill', { prepare: false });
    expect(screen.getByText(/This step needs an earlier step/)).toBeInTheDocument();
    expect(screen.queryByText(/₹/)).not.toBeInTheDocument();
  });

  it('shows the verified amounts supplied by the backend', async () => {
    await show('/patient/bill');
    expect(await screen.findByText('₹12,480.00')).toBeInTheDocument();
    expect(screen.getByText('₹6,240.00')).toBeInTheDocument();
    expect(screen.getByText(/match the recorded values/i)).toBeInTheDocument();
    expect(screen.getByText(/Fictional record · Access code verified/)).toBeInTheDocument();
    expect(screen.queryByText('₹24,000')).not.toBeInTheDocument();
    expect(backend.billCalls).toBe(1);
    expect(backend.lastSessionHeader).toBe(SESSION_ID);
  });

  it('recovers when protected bill information is refused', async () => {
    backend.billError = { status: 403, code: 'verification_required' };
    await show('/patient/bill');
    expect(await screen.findByText(/needs an earlier step/i)).toBeInTheDocument();
    expect(screen.queryByText(/₹/)).not.toBeInTheDocument();
  });

  it('reports a bill-loading failure with a retry action', async () => {
    backend.billError = { status: 500, code: 'internal_error' };
    await show('/patient/bill');
    expect(await screen.findByText(/could not load the verified bill information/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Try again' })).toBeInTheDocument();
  });

  it('simplifies the fixed explanation with the verified amounts', async () => {
    await show('/patient/explanation');
    expect(await screen.findByText(/FIXED-TEMPLATE EXPLANATION/)).toBeInTheDocument();
    expect(screen.getByText(/₹12,480.00/)).toBeInTheDocument();
    expect(screen.getByText(/Audio is not available/)).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Simplify explanation' }));
    expect(screen.getByText('Simpler explanation')).toBeInTheDocument();
  });

  it('does not invent answers to unsupported questions', async () => {
    await show('/patient/questions');
    fireEvent.change(screen.getByLabelText('Your question'), { target: { value: 'Can I have a refund?' } });
    fireEvent.click(screen.getByRole('button', { name: 'Ask question' }));
    expect(screen.getByText(/A demo answer is not available/)).toBeInTheDocument();
  });

  it('requires consent and a reason for a demo help request', async () => {
    await show('/patient/help');
    fireEvent.click(screen.getByRole('button', { name: 'Submit demo request' }));
    expect(screen.getAllByRole('alert')).toHaveLength(2);
    fireEvent.change(screen.getByLabelText(/Why would you like help/), { target: { value: 'Understand my bill' } });
    fireEvent.click(screen.getByRole('checkbox'));
    fireEvent.click(screen.getByRole('button', { name: 'Submit demo request' }));
    expect(screen.getByText(/No request was sent/)).toBeInTheDocument();
  });

  it('labels caregiver information as fictional and uses verified amounts', async () => {
    await show('/caregiver');
    expect(await screen.findByRole('heading', { name: 'What You Need to Know' })).toBeInTheDocument();
    expect(screen.getByText(/not an authorized patient record/)).toBeInTheDocument();
    expect(await screen.findByText(/Sunrise Multispeciality Hospital · Amount left to pay: ₹6,240.00/)).toBeInTheDocument();
  });

  it('changes a demo ticket status', async () => {
    await show('/support');
    fireEvent.change(screen.getByLabelText('Change demo status'), { target: { value: 'resolved' } });
    expect(screen.getAllByText('Resolved').length).toBeGreaterThan(0);
  });
});

describe('phase 2 interactions', () => {
  it('guards sensitive pages and allows consent to be reconsidered', async () => {
    const view = await show('/patient/bill', { prepare: false });
    expect(screen.getByText(/This step needs an earlier step/)).toBeInTheDocument();

    view.go('/patient');
    fireEvent.click(screen.getByRole('button', { name: 'Decline' }));
    view.go('/patient/identify');
    expect(screen.queryByLabelText('Bill number')).not.toBeInTheDocument();

    view.go('/patient');
    fireEvent.click(screen.getByRole('button', { name: 'Agree and continue' }));
    expect(await screen.findByRole('link', { name: 'Continue' })).toBeInTheDocument();
  });

  it('opens a glossary and clears question history', async () => {
    const view = await show('/patient/bill');
    await screen.findByText('₹12,480.00');
    fireEvent.click(screen.getByText('Bill terms'));
    fireEvent.click(screen.getByText('Covered by insurance', { selector: 'summary' }));
    expect(screen.getByText(/Insurance coverage is the amount/)).toBeInTheDocument();

    view.go('/patient/questions');
    fireEvent.click(screen.getByRole('button', { name: 'What does insurance cover mean?' }));
    fireEvent.click(screen.getByRole('button', { name: 'Ask question' }));
    expect(screen.getByText(/Insurance coverage is the amount/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Clear question history' }));
    expect(screen.getByText(/Your questions and responses will appear/)).toBeInTheDocument();
  });

  it('creates a labelled ticket with the selected preferences', async () => {
    await show('/patient/help');
    fireEvent.change(screen.getByLabelText('Preferred callback time'), { target: { value: 'evening' } });
    fireEvent.change(screen.getByLabelText(/Why would you like help/), { target: { value: 'A fictional question' } });
    fireEvent.click(screen.getByRole('checkbox'));
    fireEvent.click(screen.getByRole('button', { name: 'Submit demo request' }));
    expect(screen.getByText(/Fictional ticket reference: DEMO-/)).toBeInTheDocument();
    expect(screen.getByText(/Evening/)).toBeInTheDocument();
    expect(screen.getByText(/No request was sent/)).toBeInTheDocument();
  });

  it('filters, updates, and resets demo tickets', async () => {
    await show('/support');
    fireEvent.change(screen.getByLabelText('Filter by status'), { target: { value: 'resolved' } });
    expect(screen.getByRole('button', { name: /DEMO-004/ })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /DEMO-001/ })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: /DEMO-004/ }));
    fireEvent.change(screen.getByLabelText('Change demo status'), { target: { value: 'new' } });
    expect(screen.getByRole('status')).toHaveTextContent('changed locally');
    fireEvent.click(screen.getByRole('button', { name: 'Reset demo tickets' }));
    expect(screen.getByRole('button', { name: /DEMO-001/ })).toBeInTheDocument();
  });

  it('clears journey state when restarting', async () => {
    const view = await show('/patient/bill');
    expect(await screen.findByText('₹12,480.00')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('link', { name: 'Restart demonstration' }));
    view.go('/patient/bill');
    expect(screen.queryByText('₹12,480.00')).not.toBeInTheDocument();
    expect(screen.getByText(/This step needs an earlier step/)).toBeInTheDocument();
  });
});

describe('translation coverage', () => {
  it('provides every English key in Hindi and Kannada dictionaries', async () => {
    const { translations } = await import('../lib/translations');
    const en = Object.keys(translations.en);
    for (const lang of ['hi', 'kn'] as const) {
      const missing = en.filter((key) => translations[lang][key as keyof typeof translations.en] === undefined);
      expect(missing, `missing keys in ${lang}`).toEqual([]);
    }
  });
});

describe('accessibility smoke check', () => {
  it('has no detectable axe violations on the welcome screen', async () => {
    const axe = (await import('axe-core')).default;
    const view = await show('/');
    const results = await axe.run(view.container);
    expect(results.violations).toEqual([]);
  });
});
