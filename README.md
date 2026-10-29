# Healthcare Bill Navigator

Next.js frontend connected to the FastAPI backend in `../hackloop2`. Patients enter a bill number or send a bill photo, the backend runs local Tesseract OCR against fictional hospital records, and protected amounts are released only after access-code verification. English, Hindi and Kannada are supported throughout.

The hospital records, bills, amounts and access codes are fictional demonstration data. No real hospital is contacted, no real patient information is processed, and nothing here is professional advice.

## What is connected

| Frontend action | Backend request |
| --- | --- |
| Accept consent | `POST /api/v1/sessions` then `POST /api/v1/sessions/{id}/consent` |
| Decline / restart | `POST /api/v1/sessions/{id}/consent/withdraw` (best effort) |
| Enter a bill number | `POST /api/v1/identifications` (JSON: `session_id`, `bill_number`, optional `hospital_identifier`) |
| Send a bill photo | `POST /api/v1/identifications/upload` (multipart: `session_id` + `file`; the browser sets the multipart boundary) |
| Verify the access code | `POST /api/v1/identifications/{id}/verify` |
| Read amounts | `GET /api/v1/verified-bills/{id}` with the `X-Session-ID` header |

The client lives in [lib/api.ts](lib/api.ts) and is the single source of API URLs. [lib/apiErrors.ts](lib/apiErrors.ts) maps the backend's stable error codes to localized messages. Non-2xx responses are read from the backend envelope `{"error":{"code","message","request_id","details"}}`.

The session identifier lives in React state only. It is never put in a URL, `localStorage`, or `sessionStorage`. The backend keeps sessions in process memory, so restarting the API invalidates them; the UI reports the ended session and asks for consent again.

## Configuration

Frontend ([.env.local](.env.local), template in [.env.example](.env.example)):

```dotenv
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000
NEXT_PUBLIC_CONSENT_POLICY_VERSION=patient-consent-2026-10-v1
```

`NEXT_PUBLIC_CONSENT_POLICY_VERSION` must match the backend's `HBN_CONSENT_POLICY_VERSION`, otherwise consent is rejected. Only public configuration belongs in `NEXT_PUBLIC_*` variables.

The backend needs the frontend origin allowed and at least one fictional access code configured. The local `.env` created for this integration contains:

```dotenv
HBN_CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
HBN_BILL_ACCESS_CODE_SUN2026004512=DEMO1234
HBN_BILL_ACCESS_CODE_GME2026001122=DEMOCODE2
```

These are fictional demo codes, not secrets. Real deployments must keep access codes out of version control. Codes for the other registered demo bills are intentionally not configured; verification for those fails closed.

## Run locally (PowerShell)

Backend:

```powershell
cd "C:\Users\Somnath\OneDrive\hackloop2"
Copy-Item .env.example .env   # only if .env does not exist yet; then set the values above
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Frontend:

```powershell
cd "C:\Users\Somnath\OneDrive\hackloop3"
npm ci
npm run dev
```

Open http://localhost:3000; API docs are at http://127.0.0.1:8000/docs.

## Demo bill numbers and codes

| Bill number | Hospital | Access code |
| --- | --- | --- |
| `SUN-2026-004512` | Sunrise Multispeciality Hospital | `DEMO1234` |
| `GME-2026-001122` | Greenmeadow City Hospital | `DEMOCODE2` |
| `SUN-2026-004770` | Sunrise Multispeciality Hospital | not configured (fails closed) |
| `HBR-2026-555310` | Harbourview Medical Center | not configured (fails closed) |

`bill_good.png` in the backend folder is a fictional sample bill that identifies as `SUN-2026-004512`. Tesseract is required for photo identification; the adapter auto-detects the usual Windows install path.

## Behavior

- **Consent** is recorded on the server before continuing. If the backend refuses, the UI reports the failure and does not pretend consent was accepted. Declining withdraws a previous consent and clears the local journey.
- **Identification** sends the real selected file. Client-side checks mirror the backend limits (JPEG/PNG/WebP, 5 MB), but the backend remains authoritative: 400, 403, 404, 413, 422, 500 and 503 responses each produce a specific localized message and recovery action.
- **Result states** are taken from the backend: `access_code_required`, `bill_not_found`, `bill_number_not_found`, `hospital_not_registered`, `unreadable_image`, `ambiguous_hospital`, plus session expiry, network failure and unexpected responses.
- **No amounts appear during identification.** Only after successful verification does the app call the protected endpoint; missing amounts are shown as unavailable, never as zero, and insurance/previous-payment values are explicitly noted as absent rather than invented. Photo-derived amounts are flagged non-authoritative.
- **Verification** uses the backend's challenge (three attempts, five-minute window). Incorrect (401), locked (403) and expired (410) states are distinct and offer a re-identification path. Access codes are not retained after submission.
- **Still demonstration-only:** the explanation text, follow-up questions, help form, caregiver summary and support dashboard use local demo content; they are not connected to the backend's GenAI/support endpoints. All fictional records remain visibly labelled.

## Checks

```powershell
npm test -- --run   # 52 tests in 2 files
npx tsc --noEmit
npm run lint
npm run build
```

Current results:

- Frontend: **52/52 tests pass** (11 API-client contract tests + 41 UI/interaction tests, including session/consent, upload contract, duplicate-submit prevention, every identification outcome, HTTP error mapping, network recovery, verification states, financial-information protection, and translation coverage). Axe reports no violations on the welcome screen.
- `npx tsc --noEmit` and `npm run lint`: clean.
- `npm run build`: succeeds; `[[...slug]]` is server-rendered on demand.
- Backend: `.\.venv\Scripts\python.exe -m pytest -q` → **445 passed**.
- Manual local end-to-end (real server + real browser):
  - `POST /api/v1/sessions` → 201, consent → 200
  - `POST /api/v1/identifications/upload` with `bill_good.png` → `access_code_required`, `SUN-2026-004512`
  - `POST /api/v1/identifications/{id}/verify` with `DEMO1234` → `verified`, comparison `matched`
  - `GET /api/v1/verified-bills/{id}` → total `12480.00`, patient payable `6240.00`
  - Browser network log confirmed the real upload returned 200 and the UI rendered the backend result; an unknown bill number returned the real `bill_not_found` state.

## Known limitations

- Sessions, consent, identifications and verification challenges are in backend memory. A backend restart loses them; the frontend detects this and asks for consent again.
- Identification depends on configured fictional records, image quality and Tesseract. Arbitrary real hospital bills cannot be identified, and OCR low confidence is reported as unreadable rather than guessed.
- Only two demo bills have access codes configured. The rest fail closed by design.
- Bill photo amounts are comparison data only; the recorded total and payable are authoritative.
- GenAI explanation, grounded Q&A and caregiver summaries remain local demo content in the frontend.
- `npm audit` still reports 5 advisories (postcss inside Next.js 15 and tinypool/@vitest/mocker via Vitest 3). Fixing them requires breaking major upgrades; none were forced. No dependency was added or changed for this integration.
- Axe's canvas/pseudo-element contrast probes cannot fully run in jsdom; colour contrast and screen-reader, mobile and zoom behaviour still need manual review.
