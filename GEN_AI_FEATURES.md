This file records every GenAI feature implemented in this project (Phase 8 and
beyond), where each piece lives, and what it deliberately does NOT do. It is
documentation only; the backend itself is unchanged by its presence.

# Local GenAI features — Healthcare Bill Navigator

Backend workspace: `C:\Users\Somnath\OneDrive\hackloop2-publish`
(publishing tree; the working tree `C:\Users\Somnath\OneDrive\hackloop2`
carries the same code).

## Implemented features (Phase 8)

### 1. Local-only model configuration

- Settings added to the existing pydantic-settings configuration:
  `HBN_OLLAMA_BASE_URL` (default `http://localhost:11434`),
  `HBN_OLLAMA_MODEL` (default `qwen3:1.7b`),
  `HBN_OLLAMA_TIMEOUT_SECONDS` (default `60`, validated 5–600),
  plus the service-level bound `HBN_OLLAMA_MAX_OUTPUT_CHARS` (default `2000`).
  All are namespaced under `HBN_` like every other setting.
- The base URL is validated on startup: only `http`/`https`, no query strings.
  Placeholders with descriptions were added to `.env.example`.
- No cloud AI provider, no API key, no outbound internet calls. The model
  runtime is Ollama (`POST /api/chat`, non-streaming, `think: false`,
  temperature 0.2, bounded `num_predict`).

### 2. Secure explanation endpoint

- Route: `POST /api/v1/verified-bills/{identification_id}/explanation`
  (file: `app/api/v1/routes/verified_bills.py`, registered in the existing
  `api_v1_router` — a second FastAPI application was never created).
- Authorization reuses the existing Phase 3 guards verbatim: live session with
  granted consent via `X-Session-ID`, followed by proof that *this session*
  verified *this identification*. Foreign or unverified bills →
  404/404-style `not_found` (unchanged from the verified-bill endpoint).
- Additional consent gate: the request body must carry `"ai_consent": true`
  (extra="forbid", so unknown fields are rejected). Missing or withdrawn
  AI consent → 422 before any model call.
- Language selection uses validated ISO-639-1 identifiers (`en`, `hi`, `kn`);
  anything else → 422.
- Server-side services are the only source of bill facts; client-supplied
  amounts/dates/comparison text are not accepted (the request schema has no
  such fields at all).

### 3. Financial-accuracy guardrails

- `ExplanationFacts` (`app/services/explanations.py`) is the whitelisted
  summary sent to the model: hospital name, bill number, bill date, the two
  recorded amounts, comparison status and comparison note. Nothing else
  leaves the backend; no patient identity, no access codes, no session data.
- The system prompt forbids inventing amounts, dates, insurance coverage,
  deadlines, discrepancy reasons, payment obligations and financial-aid
  eligibility, and forbids fraud/overcharging characterisations.
- `validator_problems()` validates every completion before release:
  - banned claims (fraud, overcharging, "has been paid", insurance approval,
    waivers, deadlines, payment obligations),
  - any ₹/Rs/INR amount not equal to a recorded amount → discarded,
  - any date not equal to the recorded bill date (`2026-03-05` or
    `05.03.2026` forms) → discarded,
  - output longer than the character ceiling → discarded (not truncated).
- A failed validation or model failure yields deterministic fallback
  explanations hand-written for the requested language; patients always get
  a useful 200 response (`source: "fallback"`, `fallback_reason`).
- API responses keep trusted and generated text separate: `facts` (with
  `authoritative: true` amounts) vs `explanation` (explicitly
  non-authoritative prose). The record can never be overridden by the model.

### 4. Privacy and logging

- Prompts contain no names, contact details, access codes, session secrets or
  client text. Logging emits only counters/reasons (timeouts, unreachable
  server, oversized output); no prompts, no bill contents, no generated text.
- Errors reuse the shared exception envelope; Ollama failures surface as a
  generic `fallback` path (or 500 with the standard `ai_unavailable`-style
  code), never model details or stack traces.

### 5. Tests ( mocked model, real mechanisms )

- 56 tests in `tests/test_explanations.py`, all using `httpx.MockTransport`
  simulations of Ollama — no downloaded model or running server required.
- Coverage includes: en/hi/kn generated answers; unsupported languages;
  foreign/unauthorized sessions; unverified and nonexistent bills; missing,
  withdrawn and explicit-negative AI consent; ignored client financial data;
  unreachable server, timeout, malformed/empty/oversized completions;
  invented amounts and contradicting dates; deterministic fallbacks for all
  three languages; and log/error leakage checks. The Phase 3 verification and
  consent mechanisms described above are used for real, not stubbed.

### 6. Documentation

- `README.md` gained a full "Local GenAI bill explanation (Phase 8)" section:
  feature scope, hard rules, trusted-vs-generated distinction, Ollama setup
  (`ollama pull qwen3:1.7b`), configuration table, curl exercise, and an
  explicit limitations note. `.env.example` documents the new variables.

## What this phase deliberately does NOT include

- No general-purpose chat, streaming, conversation history, or voice.
- No frontend; the feature is API-only.
- No cloud/model-provider integrations of any kind.
- Nothing below changes the Phase 6 deployment stance: the backend remains an
  in-memory, single-process prototype with fictional synthetic data and must
  never be pointed at real patient records.

## Verification snapshot (working tree at time of writing)

- `pytest`: **298 passed** (242 pre-existing + 56 new). A pre-existing 242
  regression was fully investigated; no existing tests were weakened.
- `ruff check .`: all checks passed. `compileall`: clean.
- `git diff --check`: clean. Full-line whitespace scan: clean.

Commands to re-verify:

```powershell
cd C:\Users\Somnath\OneDrive\hackloop2-publish
.\.venv\Scripts\Activate.ps1
python -m pytest -q
python -m ruff check .
python -m compileall -q app tests
git diff --check
```
