# Frontend integration (demo)

The UI is a Next.js 14 app in `frontend/` (App Router, Tailwind). It was built
against its own API contract, so a compatibility router
(`app/api/compat/bills.py`) translates between it and this backend.

**Flow:** Next.js `:3000` → FastAPI `:8000` → PostgreSQL `navigator`.
Amounts are read only through `app.db.access.get_verified_record`, so the
access-code gate applies to the demo too.

## Run all three

PostgreSQL must be running with the schema and seed loaded
(see `docs/DATABASE.md`), and `.env` must contain `DATABASE_URL`.

```bash
# 1. backend (must use app.serve, see "Why not uvicorn" below)
backend/.venv/Scripts/python.exe -m app.serve --port 8000

# 2. frontend (new terminal)
cd frontend
npm install
echo NEXT_PUBLIC_API_BASE_URL=http://localhost:8000 > .env.local   # once
npm run dev
```

Open http://localhost:3000. The backend's default CORS origins already allow
`http://localhost:3000`.

## Demo data (from `data/fictional/seed.sql`)

| Bill number | Hospital | Code | Amount due |
| --- | --- | --- | --- |
| `INV-2026-0042` | City General Hospital | `DEMO-1234` | ₹30,000 of ₹50,000 |

Use `INV-2026-0042` with `DEMO-1234`. The frontend's lookup tries
`DEMO-1234` first, so this bill verifies on the first attempt; other seeded
bills use different codes (`DEMO-0007`, `DEMO-0100`, ...) and would spend
attempts before failing. `git status` is not needed for the demo — the data
above is in the database.

## Endpoints the bridge adds

| Route | Purpose |
| --- | --- |
| `POST /api/bills/identify` | OCR candidates from a photo, or a bill number |
| `POST /api/bills/access/challenge` | starts a 3-try, 5-minute verification session |
| `POST /api/bills/access/verify` | spends one attempt, returns an opaque token |
| `POST /api/bills/verify` | confirms the token is verified and unexpired |
| `GET /api/bills/financials` | the five recorded amounts (`not_provided`, never 0) |
| `POST /api/bills/explain` | multilingual sections from the record |
| `POST /api/chat` | deterministic answers grounded in the bill context |

These are demo-only (`include_in_schema=False`). The real API stays at
`/api/v1`; keep new features there.

## Known gaps

- `/patient/verify` validates the code **client-side**; the real check already
  happened during the lookup. A wrong code on that screen does not reach the
  backend.
- Photo identification returns OCR candidates only; the upload screen still
  ends in the frontend's demo bill.
- `/caregiver`, `/patient/help` and `/support` remain mock-driven.
- The frontend keeps its own demo fallback when a call fails, so a backend
  outage shows sample data rather than an error. Check the browser network tab
  during a rehearsal to confirm the calls are real.

## Why `app.serve` and not `uvicorn`

Uvicorn picks the event loop itself and on Windows chooses `ProactorEventLoop`.
Async psycopg needs `add_reader()`, which only the selector loop provides, so
the pool times out on startup. `python -m app.serve` builds the server and runs
it on a selector loop. In-memory mode (no `DATABASE_URL`) works under plain
uvicorn as well.
