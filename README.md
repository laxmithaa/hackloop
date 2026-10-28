# Healthcare Bill Navigator — Backend (Phases 1–4, 6, 8–9)

FastAPI foundation for a service that helps patients and caregivers understand
hospital bills and reach human support workers.

**Phase 1** delivered the backend platform: configuration, request correlation
ids, consistent JSON errors, CORS, versioned routing and health reporting.

**Phase 2** adds the patient bill-identification workflow on top of it:

- Temporary **patient sessions** with unpredictable identifiers
  (`secrets.token_urlsafe`) — purely in-memory, they reset when the process
  restarts and expire after a configurable TTL.
- **Server-validated consent**: identification is impossible until consent is
  explicitly recorded against the current policy version; withdrawal re-blocks
  all further bill processing for that session.
- **Bill image upload** (JPEG/PNG/WebP) validated by decoded content, not by
  filename or client content-type: size limit, dimension limit, corrupt-image
  detection. Uploaded images are never persisted — validated pixels are passed
  to OCR and discarded.
- **Non-generative OCR** via Tesseract + pytesseract: extracts candidate bill
  number, hospital names, bill date and monetary strings. OCR output is treated
  as unverified text; the final outcome always comes from the registry.
- **Bill identification** (by manual bill number or by photo) with clear
  statuses: `access_code_required`, `bill_not_found`,
  `hospital_not_registered`, `unreadable_image`, plus technical results for
  missing bill number, ambiguous hospital, OCR-unavailable (503) and
  OCR-failure (500). **No financial values are ever returned** — extracted
  amounts stay server-side for a later verification phase.

Access-code verification, amount comparison and support workflows from
Phases 3–4 are implemented, as are the local-GenAI explanation (Phase 8) and
the grounded Q&A, personalised-explanation and caregiver-summary layers
(Phase 9). No phase after Phase 9 has started.

**Phase 3** adds the secure verification layer on the existing flow:

- **Access-code verification** (`POST /api/v1/identifications/{identification_id}/verify`):
  a challenge is created the moment an identification returns
  `access_code_required`; it expires **5 minutes** later and allows at most
  **3 failed attempts** before it locks (server-side, also under concurrent
  requests, and it is invalidated on first success). Codes are stored only as
  PBKDF2-HMAC-SHA256 digests with a unique per-bill salt and compared in
  constant time. Punycode-level details: no code is ever returned from any
  endpoint or written to logs.
- **Demo-code provisioning** for local development: each fictional bill's code
  is configured through the environment/`.env` (`HBN_BILL_ACCESS_CODE_<ALPHANUMERIC_BILL_NUMBER>=…`),
  hashed once at startup, then dropped. A bill with no configured code
  **fails closed** — verification is never bypassed.
- **Session authorization**: financial values are released by exactly one
  endpoint, `GET /api/v1/verified-bills/{identification_id}`, and only to the
  session that verified that identification — with the session id passed in
  the `X-Session-ID` header — while consent remains granted and the session is
  still live. Expired sessions are rejected.
- **Labelled amount comparison**: only label-led values (`Total Amount`,
  `Grand Total`, `Amount Payable`, `Amount Due`, …) from OCR participate.
  Everything is parsed strictly (rejected commas/dot grouping, max two
  decimals) into **integer minor units**/`Decimal` — never binary floats.
  Outcomes are kept apart: `matched`, `amounts_differ` (neutral wording — a
  mismatch is not fraud and proves nothing), `insufficient_evidence` (nothing
  comparable) and `no_uploaded_image` (manual entry). Verification still
  succeeds even when the comparison cannot be run; the two are separate
  states. Uploaded (OCR) amounts appear as non-authoritative data next to the
  recorded ones but never overwrite them.

**Phase 4** adds the human-support workflow on top of the verified flow:

- **Patient help requests** (`POST /api/v1/help-requests`): a patient may ask
  for a human callback on one of their *own* identifications — without any
  verification, because help is needed precisely when verification fails or
  amounts differ. The request needs a live session with granted consent, an
  identification of that session, a supported language (`en`/`hi`/`mr`), a
  callback window (`now`/`morning`/`afternoon`/`evening`), a length-limited
  free-text reason, and explicit request-specific sharing consent
  (`"consent_sharing_confirmed": true`); anything else is rejected and
  creates no ticket. The response returns the minimum only:

```http
POST /api/v1/help-requests
{
  "session_id": "kR7xQ2mF9vLbC4nH1sD6eA0pT3wY8uZ5iJ_oP2qG4nM=",
  "identification_id": "0f2a6cc4d4b74d02a25a5c9e40f65c31",
  "language": "mr",
  "callback_window": "evening",
  "reason": "I could not verify my bill and need help understanding it.",
  "consent_sharing_confirmed": true
}

201 → {
  "ticket_id": "9f1c0c45e2b84dfdbde2a2d0f9c60b11",
  "status": "new",
  "language": "mr",
  "callback_window": "evening"
}
```

```http
GET /api/v1/help-requests/{ticket_id}
X-Session-ID: <owning session id>

200 → {"ticket_id": "…", "status": "contacted", "language": "mr", "callback_window": "evening"}
```

  A ticket created by another session is answered exactly like an unknown
  ticket (`help_ticket_not_found`), so ticket ids cannot be probed.
- **Support-worker endpoints** under `/api/v1/staff/help-requests`:
  list eligible requests, read one request's detail (including the patient's
  verbatim reason and a deterministic, template-built case summary), and
  record a status transition. Every call must carry
  `X-Support-Staff-Token: <token>` matching `SUPPORT_STAFF_API_TOKEN`,
  compared in constant time. **Fail closed:** with no token configured every
  staff endpoint answers 503; missing or wrong tokens answer 401. Withdrawn
  sharing consent hides a request from the staff queue entirely (404), and
  ungranted session consent does the same.
- **Ticket lifecycle**: `new → callback_scheduled → contacted → resolved`,
  forward-only, applied by a small explicit transition function.
  `new` may jump straight to `contacted` or `resolved`; `resolved` is
  terminal. Invalid transitions (including backwards moves) yield 409
  `invalid_status_transition`; unknown statuses fail validation (422).
  Status values are **workflow records only** — *no phone call, SMS or email
  is ever placed by this prototype*, nothing is scheduled with an external
  provider, and no response claims otherwise.
- **Privacy boundaries**: the deterministic case summary names the
  verification snapshot (`verified_matched`, `verified_amounts_differ`,
  `verified_comparison_unavailable`, `verified_no_upload`, `not_verified`)
  and repeats the patient's stated reason verbatim as data — it never invents
  facts, advice, deadlines or amounts, and no monetary figure appears in any
  Phase 4 response. Reason text never influences authorization and is never
  logged. Withdrawal of session consent (`POST …/consent/withdraw`) marks the
  session's tickets as no-longer-shared internally; a stale session cannot
  bypass this because the staff view re-checks live consent at read time.
- **Limits**: all tickets are in-memory and are lost on restart, like every
  other Phase 1–3 record. There is no persistence, no real callback backend
  and no notification channel in this prototype.

## Stack

- Python 3.11+ (installed here with CPython 3.13)
- FastAPI 0.162 (Pydantic v2)
- Uvicorn
- Pytest + HTTPX for tests, Ruff for lint/format

## Quick start (Windows PowerShell)

```powershell
cd C:\Users\Somnath\OneDrive\hackloop2
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env      # optional; defaults work without a .env
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Then open <http://127.0.0.1:8000/docs> or call
`Invoke-RestMethod http://127.0.0.1:8000/health`.

## Layout

```
hackloop2/
├── app/
│   ├── main.py               # entry point: app factory + lifespan + middleware wiring
│   ├── api/
│   │   ├── error_handlers.py # centralised JSON error handlers
│   │   ├── health_report.py  # health payload shared by both health routes
│   │   ├── routes/health.py  # GET /health
│   │   └── v1/…              # /api/v1 router (add later phase routers here)
│   ├── core/                 # config, logging, request-id middleware, AppError
│   └── schemas/              # Pydantic request/response models
└── tests/                    # pytest + httpx suite (461 tests)
```

Phase 2 modules: `app/services/` (session_store, records, ocr,
image_validation, identification — business logic, no HTTP),
`app/api/v1/routes/sessions.py`, `app/api/v1/routes/identifications.py` and
their schemas in `app/schemas/`. The fictional hospital registry is owned by
`app/services/records.py` behind the `BillRecordAccess` interface, so the
identification logic never talks to storage directly and later phases can swap
in a real persistence layer.

Phase 8–9 GenAI modules: `app/services/ollama_client.py` (transport only — no
business rules), `bill_facts.py` (the single trusted-facts builder),
`ai_validation.py` (the shared output validator), `bill_glossary.py` (approved
multilingual definitions), `explanations.py`, `bill_qa.py`,
`personalization.py` and `caregiver.py` (share store + summary), with routes in
`app/api/v1/routes/{explanations,questions,personalization,caregiver}.py`.

## OCR installation (installed and verified on this machine, 2026-10-25)

pytesseract is only a wrapper; the **Tesseract executable** must be installed
on the machine. Installed here:

```powershell
winget install --id UB-Mannheim.TesseractOCR -e --accept-source-agreements --accept-package-agreements
# → Tesseract 5.4.0.20240606 at C:\Program Files\Tesseract-OCR (verified working)
```

The installer does not update PATH; the adapter probes the well-known install
locations (`C:/Program Files/Tesseract-OCR/tesseract.exe` and the x86 variant)
and pytesseract's PATH resolution remains the default behaviour. An explicit
setting always wins — set `HBN_OCR_TESSERACT_CMD` to the absolute path of
`tesseract.exe`.

Without any executable the app runs identically, but
`POST /api/v1/identifications/upload` returns **503 `ocr_unavailable`** —
a clear technical error, never disguised as "bill not found". Manual
bill-number entry keeps working in that state. When Tesseract *is* available,
the adapter reports low-confidence text as `unreadable_image` instead of
guessing.

## Configuration

All settings are read from the environment or a local `.env` file with the
`HBN_` prefix. `.env.example` documents every variable with placeholder
values. Validation failures (bad CORS origins, unknown log levels, a
credential-wildcard combination) abort startup with a clear error.

| Variable | Default | Purpose |
| --- | --- | --- |
| `HBN_APP_NAME` | `Healthcare Bill Navigator API` | Service name shown in `/health` and `/docs` |
| `HBN_APP_VERSION` | `0.1.0` | Version reported in `/health` and OpenAPI |
| `HBN_ENVIRONMENT` | `local` | `local` / `test` / `staging` / `production` |
| `HBN_API_V1_PREFIX` | `/api/v1` | Versioned route prefix |
| `HBN_CORS_ORIGINS` | `http://localhost:3000,http://localhost:5173` | Allow-list; comma list or JSON array; `*` only with credentials off |
| `HBN_CORS_ALLOW_CREDENTIALS` | `true` | Sends `access-control-allow-credentials` |
| `HBN_LOG_LEVEL` | `INFO` | `DEBUG`…`CRITICAL` |
| `HBN_REQUEST_ID_HEADER` | `X-Request-ID` | Correlation-id header name |
| `HBN_SESSION_TTL_MINUTES` | `60` | Lifetime of an anonymous patient session |
| `HBN_CONSENT_POLICY_VERSION` | `patient-consent-2026-10-v1` | Policy version consent is validated against |
| `HBN_BILL_UPLOAD_MAX_SIZE_MB` | `5` | Bill-photo size ceiling |
| `HBN_IMAGE_MAX_DIMENSION_PX` | `5000` | Max width/height of a decodable upload |
| `HBN_OCR_ENGINE` | `tesseract` | Local OCR backend (only `tesseract`) |
| `HBN_OCR_LANGUAGE` | `eng` | Tesseract language pack |
| `HBN_OCR_TESSERACT_CMD` | *(empty)* | Optional absolute path to `tesseract.exe` when PATH/well-known-location probing is not enough |
| `HBN_OCR_LOW_CONFIDENCE_THRESHOLD` | `55` | Below this mean confidence OCR text is treated as unreadable |
| `HBN_VERIFICATION_CHALLENGE_TTL_MINUTES` | `5` | Verification challenge lifetime (starts at identification) |
| `HBN_VERIFICATION_MAX_ATTEMPTS` | `3` | Failed access-code attempts per challenge before it locks |
| `HBN_ACCESS_CODE_PBKDF2_ITERATIONS` | `60000` | PBKDF2 work factor for hashing access-code digests |
| `HBN_BILL_ACCESS_CODE_<BILL#>` | *(unset)* | Local-demo access code for one fictional bill (see below) |
| `HBN_AI_QUESTIONS_PER_SESSION` | `10` | Follow-up questions one session may ask (backend-enforced) |
| `HBN_AI_QUESTION_MAX_CHARS` | `500` | Character ceiling for one follow-up question |
| `HBN_AI_ANSWER_MAX_CHARS` | `800` | Generated Q&A answer ceiling (longer output is rejected) |
| `HBN_PERSONALIZED_MAX_CHARS` | `900` | Personalised-explanation ceiling (`short` mode uses half) |
| `HBN_CAREGIVER_SUMMARY_MAX_CHARS` | `900` | Caregiver summary rewrite ceiling |
| `HBN_CAREGIVER_SHARE_TTL_MINUTES` | `60` | Lifetime of a caregiver share code |

Note: `HBN_ENVIRONMENT` etc. can come from either real environment variables or
the `.env` file; real environment variables win.

## Demo access codes (local development only)

The fictional bills have no built-in codes. A local developer configures one
per bill in `.env` (git-ignored) or the environment, using the bill number
reduced to uppercase alphanumerics:

```powershell
Copy-Item .env.example .env
Add-Content .env "HBN_BILL_ACCESS_CODE_SUN2026004512=DEMO1234"
Add-Content .env "HBN_BILL_ACCESS_CODE_GME2026001122=DEMOCODE2"
```

At startup each value is hashed (PBKDF2-HMAC-SHA256, 60 000 iterations, fresh
random salt per bill) and only the digest is kept; the plain code is dropped.
No endpoint ever returns a code, no code is ever logged, and a bill without a
configured code simply cannot be verified (fails closed — no bypass). Test
suites hash isolated fixture codes and never read the developer's `.env`.

## Conventions

- **Paths.** `/health` for probes, `/api/v1/…` for the frontend.
- **Errors.** Every non-2xx response uses exactly one envelope:
  `{"error": {"code", "message", "request_id", "details"}}`.
- **Observability.** Every response (and log line) carries a correlation id via
  `X-Request-ID`; clients may supply one, otherwise a uuid4 hex is generated.
  Invalid client values are replaced, never echoed.
- **Secrets.** Nothing is hard-coded and error messages never leak internals.

## Operations (Phase 6)

**Configuration safety.** Placeholder support-worker tokens
(`changeme`, `admin`, `token`, …) are rejected outright like missing ones.
Setting `HBN_ENVIRONMENT=production` enforces two extra requirements at
startup — a real `SUPPORT_STAFF_API_TOKEN` and explicit non-localhost
`HBN_CORS_ORIGINS` — so development defaults cannot silently ship to a
production-like environment; invalid combinations abort the process with a
clear, secret-free error.

**Security response headers.** Every response carries
`X-Content-Type-Options: nosniff` and `Referrer-Policy: no-referrer`. The
application serves plain HTTP and deliberately does not provide HTTPS
itself: terminate TLS at the reverse proxy/load balancer and forward only
to this process. The proxy should also set `Host`/`X-Forwarded-*` headers
faithfully.

**Rate limiting.** The application does not implement request-rate limiting.
In a deployment this belongs at the reverse-proxy layer (or a gateway) —
this is the smallest safe improvement: no extra dependency or component is
bundled into the app. Verification already limits itself to 3 wrong
attempts per challenge, so the brute-force surface from inside the
application stays bounded.

**Logging and privacy.** Access log lines contain method, path, status and
duration only. No access code, staff token, bearer token, free-text
help-request reason, uploaded bill content or financial amount is ever
logged; regression tests assert this. Unhandled errors are logged with a
stack trace locally but clients only ever receive the generic envelope.

**Health endpoints.** `GET /health` and `GET /api/v1/health` report the
process state (`status`, application name/version/environment, UTC
timestamp) and perform no dependency I/O, keeping liveness lightweight.
There is deliberately no readiness endpoint yet: the app has no external
dependencies to probe that it has not already touched at startup. OCR
availability surfaces per-request (503 `ocr_unavailable`), not as a
permanent readiness state.

**Unsupported production capabilities and deployment blockers.** Read this
prototype honestly:

- Everything is process-local (sessions, consent, challenges, attempt
  counters, verification records, help-request tickets). A process restart
  loses all of it; running **more than one worker or instance** would split
  that state arbitrarily between the workers. Single-worker in-memory
  deployment is the only supported configuration — multi-process
  deployments are a **deployment blocker**, not a supported mode.
- No persistence, no database, no external call/SMS/email sender. Callbacks
  are simulated workflow records only.
- The verification attempt limit stays reliable **within one process**;
  it cannot be shared across workers for the same reason as above.
- macOS/Windows local demo only; no container, no public deployment was
  performed in Phase 6.

**Never use real patient records with this prototype.** The demo data is
fictional by design (see `.env.example`); the state and privacy model
(in-memory per-process) has neither the durability, the isolation nor the
audit trail a real clinical or billing system requires.

## Local GenAI bill explanation (Phase 8)

The first GenAI feature: a plain-language, multilingual explanation of a
**successfully verified** bill, produced by a locally running Ollama model —
never by a cloud AI service.

**What it is.** `POST /api/v1/verified-bills/{identification_id}/explanation`
returns model prose plus the authoritative bill facts side by side. Supported
languages: English (`en`), Hindi (`hi`), Kannada (`kn`).

**Hard rules enforced by the backend (not just the prompt).**

- Authorization reuses the Phase 3 guards exactly: live session with granted
  consent (`X-Session-ID` header), and proof that *this session* verified
  *this identification*. Explicit per-request AI-processing consent
  (`"ai_consent": true`) is required; anything else is a 422 before any
  generation happens.
- The model receives only a whitelisted summary (bill number, hospital name,
  bill date, the two recorded amounts, comparison status/message). No patient
  identity, no access codes, no session secrets, no client-supplied values.
- Client-supplied amounts/dates/comparisons in the request body are ignored —
  the record is the single authority.
- Generated prose is validated before it is returned: invented amounts or
  dates that contradict the record, and claims about fraud/overcharging,
  payment status ("has been paid"), insurance approval or deadlines cause the
  whole completion to be discarded. The endpoint then answers with
  deterministic fallback text in the requested language.
- When the model is unavailable (not running, timeout, malformed/empty/output
  too large), the response is still a 200 with `source: "fallback"` and a
  `fallback_reason` — the feature degrades, it never breaks and never
  overrules the record.
- No prompts, bill contents, codes or generated output are logged; errors
  never leak model or stack internals.

**Trusted vs generated.** The `facts` field (amounts marked
`authoritative: true`, bill date, comparison summary) always reflects the
verified record and is the only part a client may rely on. The `explanation`
field is prose and explicitly non-authoritative; responses are not medical,
financial or legal advice.

**Setup (local model only).**

```powershell
# 1) Install Ollama (https://ollama.com), then pull the model once:
ollama pull qwen3:1.7b
# 2) Ensure the server is on http://localhost:11434 (default; no key needed).
# 3) Optionally adjust HBN_OLLAMA_* in .env (see .env.example).
```

**Exercise it.**

```powershell
# start (with demo access codes exported, e.g. HBN_BILL_ACCESS_CODE_SUN2026004512=DEMO1234)
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload

# then, from a consented session that verified its bill:
curl.exe -X POST http://127.0.0.1:8000/api/v1/verified-bills/<identification_id>/explanation `
  -H "X-Session-ID: <session_id>" -H "Content-Type: application/json" `
  -d '{\"language\": \"kn\", \"ai_consent\": true}'
```

**Configuration.**

| Variable | Default | Meaning |
| --- | --- | --- |
| `HBN_OLLAMA_BASE_URL` | `http://localhost:11434` | Local Ollama server (http/https only; no queries) |
| `HBN_OLLAMA_MODEL` | `qwen3:1.7b` | Locally pulled model tag |
| `HBN_OLLAMA_TIMEOUT_SECONDS` | `60` | Per-request timeout (5–600); slow/absent model → fallback |
| `HBN_OLLAMA_MAX_OUTPUT_CHARS` | `2000` | Output ceiling; longer completions are discarded, not truncated |

**Limitations.** Local-only single model, no chat history, no streaming, no
voice; requests without a reachable model silently lose the "generated"
quality but never invent facts; `think: false` is sent for qwen3-style
thinking models and older Ollama builds simply ignore it. This feature does
not change the Phase 6 deployment blockers (in-memory, single process, no
real patient records).

## Grounded Q&A, personalised explanations and caregiver summaries (Phase 9)

Three layers built on the Phase 8 foundation: the same local Ollama model,
the same authorization chain, the same trusted-facts builder and output
validator, and deterministic fallbacks in every language. **No cloud AI
provider, no database, no file persistence.** All Phase 9 state is in process
memory and is lost on restart.

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/api/v1/verified-bills/{identification_id}/questions` | Ask one follow-up question |
| `POST` | `/api/v1/verified-bills/{identification_id}/personalized-explanation` | `simple` / `short` rewrite or approved `term` definition |
| `POST` | `/api/v1/verified-bills/{identification_id}/caregiver-share` | Mint a caregiver share (patient only) |
| `GET` | `/api/v1/verified-bills/{identification_id}/caregiver-summary` | Caregiver summary with a share code |
| `DELETE` | `/api/v1/verified-bills/{identification_id}/caregiver-share` | Revoke every share for this bill |

Every endpoint requires the real Phase 3 authorization chain (`X-Session-ID`,
granted consent, this session verified this identification). Requests carry
**no financial input at all**: the only accepted fields are the question or
presentation options, a language and explicit consent. Unknown body fields are
rejected (`extra="forbid"`), so a client cannot smuggle an amount or a record
into the prompt.

### Grounded Q&A

`POST …/questions` with

```json
{"question": "What is the total amount on my bill?", "language": "en", "ai_consent": true}
```

returns an answer plus full provenance:

```json
{
  "identification_id": "…",
  "language": "en",
  "question_intent": "total_amount",
  "status": "answered",
  "source": "generated",
  "answer": "The total amount on the bill is Rs 12480.00. …",
  "fallback_reason": null,
  "questions_remaining": 9,
  "generated_at": "2026-10-27T13:58:58Z"
}
```

- **Classification happens before generation.** Medical, legal, payment-decision,
  charge-correctness, other-patient and prompt-injection requests are refused
  with fixed text (`source: "policy"`, `status: "refused"`) and never reach the
  model. Off-topic questions get a scope response pointing at human support.
- **Figures absent from the record are never estimated.** Insurance share,
  amount already paid, outstanding balance and due date are answered with a
  fixed "this record does not include…" text (`source: "record"`).
- **Term questions** use the approved glossary (`source: "glossary"`); the
  model is not asked to define terms.
- **Answerable questions** go to the model; its prose is validated against the
  record before it is returned, otherwise the deterministic answer for that
  question type is used (`source: "fallback"`, `fallback_reason` names the
  check that failed or the transport error).
- **Rate limiting is server-side**: `HBN_AI_QUESTIONS_PER_SESSION` questions per
  session (default 10, refusals count too), answered `429
  ai_question_limit_reached` afterwards. `questions_remaining` reports the
  budget. The question text is never logged.

### Personalised explanations

`POST …/personalized-explanation` with `mode` = `simple`, `short` or `term`.

- `simple`/`short` rewrite a **deterministic, record-derived explanation**. The
  model never sees client-supplied prose; its rewrite must preserve every
  amount/date and is rejected if it invents one or makes a payment/correctness
  claim. Fallback text restates both the total and the patient share so the two
  can never be merged.
- `term` returns a previewed glossary definition (English/Hindi/Kannada) for
  `total_bill_amount`, `insurance_covered_amount`, `amount_already_paid`,
  `patient_payable`, `outstanding_balance`, `bill_verification`,
  `amount_discrepancy` or `co_payment`. Definitions are never generated at
  runtime; terms whose figure is not in the record say so explicitly.
- The response always carries the authoritative `facts` block alongside the
  non-authoritative prose.

### Caregiver summaries

1. The patient's own session, with granted consent and a verified bill, calls
   `POST …/caregiver-share` with `{"language": "en", "consent_caregiver_sharing": true}`
   and receives a `share_code` **once** (only its SHA-256 digest is stored).
2. The caregiver calls `GET …/caregiver-summary` with
   `X-Caregiver-Share-Code: <code>` and an optional `language`.
3. The response is a short "What you need to know" summary plus `facts`, the
   share's `expires_at` and `verification_status`.

Hard rules:

- A bill identifier alone **never** authorizes anything; a live share code is
  required, and every request additionally re-checks the patient's session,
  consent and verification. Withdrawn consent revokes every share immediately;
  sessions that are unknown/expired, expired shares and revoked shares all
  answer the same `403 caregiver_share_invalid` (no information leakage).
- The summary exposes only `hospital_name`, `bill_number`, `bill_date`, the two
  recorded amounts, verification status and the comparison outcome. OCR-derived
  uploaded amounts are stripped even when they exist.
- Missing figures stay "not recorded"; the summary never replaces them with
  zero, never says a charge is correct/incorrect and never advises paying.
- Shares are limited (3 active per bill, 10 per session), expire after
  `HBN_CAREGIVER_SHARE_TTL_MINUTES` (default 60) and can be revoked with
  `DELETE …/caregiver-share` or by withdrawing consent.

### Shared grounding and validation

Every layer follows the same sequence: authorization/consent → trusted facts
from backend services → minimal structured prompt → bounded local-model call →
format/length check → monetary and date check → unsupported-claim/scope check →
deterministic fallback when anything fails → explicit `source` in the response.

The validator (`app/services/ai_validation.py`) accepts currency-marked amounts
(`Rs`, `₹`, `INR`), bare two-decimal figures and Indian-grouped numbers,
normalises Devanagari/Kannada digits, masks dates before reading amounts, and
rejects any value that does not equal a recorded amount. Over-precise figures
(three or more decimals) are rejected rather than rounded, and an amount
attached to the wrong field label (calling the patient share the "total") is
rejected even when the number itself is recorded. It also rejects
invented dates, claims about payment/coverage/wrongdoing/deadlines, output over
the configured ceiling, and Hindi/Kannada text written in the wrong script.
Passing these checks does not prove an answer is on-topic, which is why
questions are classified first and refusals never reach the model.

Success responses from the Phase 9 endpoints send `Cache-Control: no-store`.
Conversation state is limited to a per-session question counter: **no
transcripts, no share codes and no summaries are logged**.

### Exercise it (PowerShell)

```powershell
$base = "http://127.0.0.1:8000"
$session = Invoke-RestMethod -Method Post "$base/api/v1/sessions"
$sid = $session.session_id
Invoke-RestMethod -Method Post "$base/api/v1/sessions/$sid/consent" -ContentType "application/json" `
  -Body (@{decision="granted"; policy_version="patient-consent-2026-10-v1"} | ConvertTo-Json)
$ident = Invoke-RestMethod -Method Post "$base/api/v1/identifications" -ContentType "application/json" `
  -Body (@{session_id=$sid; bill_number="SUN-2026-004512"} | ConvertTo-Json)
$id = $ident.identification_id
Invoke-RestMethod -Method Post "$base/api/v1/identifications/$id/verify" -ContentType "application/json" `
  -Body (@{session_id=$sid; access_code="DEMO1234"} | ConvertTo-Json)

# Grounded Q&A (expect status=answered, source=generated or fallback)
$answer = Invoke-RestMethod -Method Post "$base/api/v1/verified-bills/$id/questions" `
  -Headers @{ "X-Session-ID" = $sid } -ContentType "application/json" `
  -Body (@{question="What is the total amount on my bill?"; language="en"; ai_consent=$true} | ConvertTo-Json)
$answer | Select-Object question_intent, status, source, answer, questions_remaining

# Refusal (expect status=refused, source=policy, no model latency)
Invoke-RestMethod -Method Post "$base/api/v1/verified-bills/$id/questions" `
  -Headers @{ "X-Session-ID" = $sid } -ContentType "application/json" `
  -Body (@{question="Should I pay this bill?"; language="en"; ai_consent=$true} | ConvertTo-Json) `
  | Select-Object status, source, question_intent, answer

# Hindi question: send the JSON body as UTF-8 bytes (Windows PowerShell 5.1)
$body = @{question="मेरे बिल में कुल राशि कितनी है?"; language="hi"; ai_consent=$true} | ConvertTo-Json
Invoke-RestMethod -Method Post "$base/api/v1/verified-bills/$id/questions" `
  -Headers @{ "X-Session-ID" = $sid } -ContentType "application/json; charset=utf-8" `
  -Body ([System.Text.Encoding]::UTF8.GetBytes($body)) `
  | Select-Object source, answer

# Personalised explanation (mode=term returns instantly, no model call)
Invoke-RestMethod -Method Post "$base/api/v1/verified-bills/$id/personalized-explanation" `
  -Headers @{ "X-Session-ID" = $sid } -ContentType "application/json" `
  -Body (@{mode="term"; term="outstanding_balance"; language="en"; ai_consent=$true} | ConvertTo-Json) `
  | Select-Object source, term, explanation

# Caregiver share + summary
$share = Invoke-RestMethod -Method Post "$base/api/v1/verified-bills/$id/caregiver-share" `
  -Headers @{ "X-Session-ID" = $sid } -ContentType "application/json" `
  -Body (@{language="en"; consent_caregiver_sharing=$true} | ConvertTo-Json)
$summary = Invoke-RestMethod "$base/api/v1/verified-bills/$id/caregiver-summary" `
  -Headers @{ "X-Caregiver-Share-Code" = $share.share_code }
$summary | Select-Object source, verification_status, summary

# Revocation: the next summary call answers 403 caregiver_share_invalid
Invoke-RestMethod -Method Delete "$base/api/v1/verified-bills/$id/caregiver-share" -Headers @{ "X-Session-ID" = $sid }
```

If Ollama is not running, every generated answer degrades to deterministic text
(`source: "fallback"`) while the refusals, glossary definitions and
"not recorded" answers behave identically.

### Limitations (honest list)

- **No caregiver accounts.** Authorization is possession of a live, expiring
  share code plus the patient's still-granted consent; there is no caregiver
  identity, password or staff role, and adding one is a later phase.
- **Single process.** Question counters and shares live in memory; restarting
  the server clears them, and multiple workers would each have their own state.
- Expired shares are pruned lazily (on create/authorize/count), not by a
  background sweeper.
- A bare integer without grouping or decimals (`9999`) is only treated as money
  when it directly follows a total/patient-payable field label; elsewhere it is
  not parsed as an amount. Currency-marked, Indian-grouped and two-decimal
  figures are always validated.
- No streaming, no voice input, no conversation transcript; on a CPU-only
  laptop one generated answer takes roughly 5–30 seconds with `qwen3:1.7b`.
- Caregiver summaries are short by design; a model rewrite may keep the
  template's line structure, and the deterministic template is used whenever
  the rewrite fails validation.
- **Never use real patient records with this prototype.**

## Tests

```powershell
.\.venv\Scripts\Activate.ps1
python -m pytest -v          # 461 passed (Phase 9 adds 163)
ruff check .                 # lint
ruff format --check .        # formatting
python -m compileall -q app tests
```

`ruff check .` is clean. `ruff format --check .` reports formatting drift in
13 files (the pinned Ruff 0.17.2 formatter wants to collapse short multi-line
signatures written in an earlier phase). Only two of those files are touched
by this phase — `app/core/config.py` and `app/services/explanations.py` — and
the affected lines there are pre-existing (the staff-token field and a Phase 8
translation string). Every newly added Phase 9 module and test file is
format-clean. This note exists because
the drift is unrelated to this phase and was deliberately not rewritten.

The Phase 1 suite covers application startup and lifespan, health response
structure, request-id sanitisation, the JSON error envelope (404/405/400/422/500),
validation failures, CORS behaviour, OpenAPI availability/accuracy and
configuration validation.

The Phase 2 suite covers session creation/expiry, consent gating and
withdrawal, manual identification (matching, not-found, unregistered,
ambiguous), the mocked-OCR upload flow (JPEG/PNG/WebP, clean/empty/low-
confidence text, missing bill number, ambiguous hospital), image validation
(unsupported format, oversize, corrupt, dimensions, client content-type
mistrust), OCR-unavailable/OCR-failure paths and the guarantee that no
financial values leak into identification responses. All OCR is mocked in
tests; no test depends on a local Tesseract installation.

The Phase 5 integration suite (`tests/test_end_to_end_workflow.py`, all
in-process, no network and mocked OCR) joins whole workflows across phases:
the complete patient journey from session and consent through manual and
upload identification, access-code verification, the protected
verified-bill endpoint, a Phase 4 help request and the support-worker
status workflow; the identification/verification failure paths (unknown
session, withdrawn consent, unknown bill number, corrupt image, wrong
access code, attempt lock, expired challenge, foreign-session
identification, protected access before verification and after withdrawal,
matching/differing/insufficient-evidence uploads); and cross-phase security
regressions (session-bound financial data, challenge invalidation after
success, tokens and access codes kept out of error envelopes and logs,
request-id presence and upload-size limits).

The Phase 4 suite (`tests/test_help_requests.py`) covers help-request
creation and every validation rejection, cross-session ticket isolation,
consent-withdrawal effects on patient and staff views, staff fail-closed
behaviour, missing/incorrect/staff tokens, the forward-only status machine
(including backwards and terminal transitions), the staff detail reason and
deterministic summary, absence of monetary values in patient/staff payloads,
reason-free logs and an OpenAPI schema without any token. All Phase 4 tests
run over the in-process ASGI client; no test performs a network call or an
external messaging/callback action.

The Phase 9 suite (163 tests: `tests/test_ai_validation.py`,
`tests/test_bill_qa.py`, `tests/test_personalization.py`,
`tests/test_caregiver_summary.py`) covers the shared validator (currency
formats, Indian grouping, Devanagari/Kannada digits, date masking, invented
amounts/dates, claim phrases, length and script checks), question
classification and every refusal category, prompt injection, missing record
fields, glossary answers, English/Hindi/Kannada generation, fallbacks for
timeouts/connection errors/empty/oversized/invalid output, the real
verification-and-consent authorization chain (unverified, foreign session,
withdrawn consent, expired session, missing headers/consent), the
server-enforced question limit, caregiver share creation limits, share-code
scope/expiry/revocation, patient-session invalidation, restricted summary
fields (`uploaded_amounts` stripped), and log privacy. Every model call is
mocked with `httpx.MockTransport`; the suite needs no Ollama server and no
network. Phase 8's 56 explanation tests still pass unchanged.
