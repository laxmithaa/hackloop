# Database

PostgreSQL 14+ (developed on 16). Python access layer in `app/db/`
(psycopg 3, async). **All data in this repo is fictional.**

## Set up locally

1. Install PostgreSQL and pgAdmin 4. Remember the `postgres` password.
2. In pgAdmin, create an empty database named `navigator`.
3. Copy `.env.example` to `.env` (repo root) and set `DATABASE_URL`.
4. In a virtual environment: `pip install -r requirements.txt`.
5. Build the tables and load the fictional data (one command):
   `python -m app.db.setup --reset`
6. Check it: `pytest` should pass with no skipped database tests.

`DATABASE_URL` is read from the process environment or the repo-root `.env`
file. Leaving it empty keeps the application in its original in-memory mode:
the PostgreSQL pool is not created and `psycopg` is not even imported.

`python -m app.db.setup --reset` **deletes the database layer's tables**
(`languages`, `hospitals`, `bills`, `bill_financials`, `access_codes`,
`verification_sessions`, `consents`, `support_workers`, `callback_tickets`,
`generated_texts`) and rebuilds them. It no longer drops the whole `public`
schema, so other objects in the database are left alone. It still refuses to
run against a non-local host unless you add `--allow-remote`. Use `--no-seed`
for the schema only. Without `--reset` it only works on an empty database.
**Run `--reset` only against a disposable, dedicated local database.**

`pytest` reads `DATABASE_URL` from the environment or `.env`. Without it the
database tests skip themselves and only the pure-logic tests run. Each database
test runs in a transaction that is rolled back, so the data is left untouched.

## Fictional data

`data/fictional/seed.sql` loads 3 hospitals, 20 bills and a demo access code
per bill (`DEMO-1234`, `DEMO-5678`, `DEMO-0007`, `DEMO-0100`, then
`DEMO-2005` to `DEMO-2020`). The header of the file lists the edge case each
bill covers (missing vs zero, overdue, no due date, paise amounts, waived bill,
sparse records and more). To add a bill, add one row to the table in that file.
The "hospital not registered" and "bill not found" outcomes need no rows.

## Tables

| Table | Purpose |
| --- | --- |
| `languages` | Supported languages (en, hi, regional). Add or remove rows, no schema change |
| `hospitals`, `bills` | Registered hospitals and their bills (with `bill_date`, `due_date`) |
| `bill_financials` | The verified amounts. No row / NULL = "not provided", never 0 |
| `access_codes` | Printed code per bill, bcrypt hash only |
| `verification_sessions` | One unlock attempt: 5-min entry window, 3 tries, verified session, question count |
| `consents` | Consent recorded before processing (DPDP Act 2023) |
| `support_workers` | Fills the "Viewing as" dropdown, ticket assignment |
| `callback_tickets` | Help requests: New, Callback scheduled, Contacted, Resolved |
| `generated_texts` | Log of AI texts: record ID, prompt version, checker result. No personal data |

## How the API should use it

```python
lookup = await lookup_bill(conn, hospital_name, bill_number)   # no amounts
# lookup.outcome: found | hospital_not_registered | bill_not_found

session = await start_verification(conn, lookup.bill.bill_id)
result = await submit_access_code(conn, session.session_id, code)
# result.status: ok | invalid | locked_out | expired | not_found
# result.escalate is True after the last failed try -> offer a human

record = await get_verified_record(conn, session.session_id)   # None unless verified
comparison = compare_scanned_to_record(scanned_amounts, record)
# comparison.status: matched | amounts_differ | insufficient_evidence
```

- `get_verified_record` is the only public way to read amounts, and it
  refuses without a verified, unexpired session. Do not read `bill_financials`
  directly from routes.
- `get_verified_record` checks **only this database layer's** verification
  session. It does not know about the FastAPI patient session, its live
  consent, or which identification owns the bill. Routes must keep running
  the application's existing guards (live session, consent still granted,
  this session verified this identification) **in addition to** this check.
  Never treat a database verification session alone as authorization to
  release amounts.
- `compare_scanned_to_record` reports `insufficient_evidence` when the scan
  read no usable amount. That is not a match: an empty scan proves nothing and
  must never be rendered as "verified".
- Show the **same message** for `invalid` and `not_found`.
- Add an IP rate limit on starting sessions in the API layer.
- `count_question` enforces the per-session cap on free-text questions.
- The connection commits when the request succeeds and rolls back on an error
  (see `pool.py` for the FastAPI wiring).

## Privacy

- Collect only what is needed: the callback ticket keeps a name and phone number,
  nothing else personal. Decide a retention period (for example, delete resolved
  tickets after N days) and record it here.
- `generated_texts` must never hold names, IDs or contact details.
  `log_generated_text` rejects text that looks like a phone number.
- Consent is stored in `consents` before processing, and a ticket records
  withdrawn consent and flags it for a human.

## Known integration gaps

These are not yet connected and should be agreed with the team before the API
switches over to PostgreSQL:

1. **Record contract.** The application's `BillRecordAccess` is synchronous,
   holds two integer amounts (`total`, `patient_payable`) and supports hospital
   aliases for OCR matching. This layer is async, stores five optional decimal
   amounts, and matches hospital names exactly. The service boundary has to be
   migrated deliberately; it has **not** been silently swapped.
2. **Canonical dataset.** The seed contains `INV-2026-0042`, `SMC/2026/118`,
   "City General Hospital", etc. The API's existing demo and tests use
   `SUN-2026-004512`, `GME-2026-001122` and "Sunrise Multispeciality
   Hospital". The two datasets are different; the team must decide which one
   is canonical before `app.state.records` is backed by PostgreSQL.
3. **Callback fields.** `callback_tickets` stores `patient_name` and
   `phone_number`, which the current help-request API does not collect. Do not
   start storing them without an agreed contract and a retention period.
4. **Session and consent.** `consents.session_id` references
   `verification_sessions`, but consent is recorded *before* verification.
   This needs a durable patient-session identity to reference instead.

## Assumptions to confirm with the team

1. **"5-minute expiry"** is implemented as the window to enter the code after
   a bill is identified. A verified session then lasts `VERIFIED_SESSION_MINUTES` (30).
2. **Regional language** is a placeholder (`kn`, Kannada) in the `languages` table.
3. **Field names** for the five amounts match the earlier prototype's contract.
4. **Hospital name matching** is exact (case and spacing aside). OCR output may need fuzzy matching.
5. Glossary terms, cached explanations and evaluation results are not in the
   database; keep them as reviewed files in the repo unless the team prefers tables.
