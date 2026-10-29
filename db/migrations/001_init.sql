-- 001_init.sql: Healthcare Bill Navigator (PostgreSQL 14+)
-- FICTIONAL DATA ONLY in this repo. Never load real patient data.
-- Run: psql "$DATABASE_URL" -f db/migrations/001_init.sql
--
-- Design notes
--  * bills + bill_financials hold the hospital's VERIFIED record. Amounts
--    and dates come only from here; the AI writes wording around them.
--  * A NULL amount means "the hospital record does not provide it". It is
--    never stored as 0, so "unknown" can never be explained as "nothing owed".
--  * Nothing in the logs table identifies a person (requirements, section 9).

begin;

create extension if not exists pgcrypto;  -- crypt() is used by the seed file

-- ---------------------------------------------------------------- languages
-- Reference data, not a hard-coded CHECK, so the regional language can be
-- decided (or changed) without a schema change. 'kn' is a PLACEHOLDER for it.
create table languages (
  code        text primary key,
  name        text not null,
  is_regional boolean not null default false,
  supported   boolean not null default true
);

insert into languages (code, name, is_regional) values
  ('en', 'English', false),
  ('hi', 'Hindi',   false),
  ('kn', 'Kannada', true);

-- ---------------------------------------------------------------- hospitals
create table hospitals (
  id              uuid primary key default gen_random_uuid(),
  name            text not null check (char_length(name) between 2 and 300),
  registration_no text unique,
  created_at      timestamptz not null default now()
);
create unique index hospitals_name_ci_idx on hospitals (lower(name));

-- -------------------------------------------------------------------- bills
create table bills (
  id          uuid primary key default gen_random_uuid(),
  hospital_id uuid not null references hospitals(id) on delete restrict,
  bill_number text not null check (bill_number ~ '^[A-Za-z0-9/._-]{3,100}$'),
  currency    text not null default 'INR' check (currency = 'INR'),
  bill_date   date,
  due_date    date,   -- deadlines come ONLY from the record
  created_at  timestamptz not null default now(),
  unique (hospital_id, bill_number),
  check (due_date is null or bill_date is null or due_date >= bill_date)
);

-- ---------------------------------------------------------- bill_financials
-- One row per amount the hospital record provides. No row (or NULL) = not
-- provided. Check constraint keeps money non-negative and exact.
create table bill_financials (
  bill_id       uuid not null references bills(id) on delete cascade,
  field_key     text not null check (field_key in (
                  'billTotalAfterDiscounts',
                  'insuranceApprovedButNotPaid',
                  'insurancePaidOrCredited',
                  'patientPayments',
                  'printedAmountDue')),
  amount_rupees numeric(12,2) check (amount_rupees >= 0),
  primary key (bill_id, field_key)
);

-- ------------------------------------------------------------- access_codes
-- The printed code on the bill. Only a bcrypt hash is stored.
create table access_codes (
  id         uuid primary key default gen_random_uuid(),
  bill_id    uuid not null references bills(id) on delete cascade,
  code_hash  text not null,
  created_at timestamptz not null default now(),
  revoked_at timestamptz
);
create index access_codes_bill_idx on access_codes (bill_id);

-- ---------------------------------------------------- verification_sessions
-- One row per attempt to unlock a bill: a short window to enter the code
-- (entry_expires_at), a capped number of tries, then a verified session.
create table verification_sessions (
  id                 uuid primary key default gen_random_uuid(),
  bill_id            uuid not null references bills(id) on delete cascade,
  created_at         timestamptz not null default now(),
  entry_expires_at   timestamptz not null,
  max_attempts       integer not null default 3 check (max_attempts > 0),
  failed_attempts    integer not null default 0 check (failed_attempts >= 0),
  verified_at        timestamptz,
  session_expires_at timestamptz,
  question_count     integer not null default 0 check (question_count >= 0),
  check (failed_attempts <= max_attempts),
  check ((verified_at is null) = (session_expires_at is null))
);
create index verification_sessions_bill_idx on verification_sessions (bill_id);

-- ----------------------------------------------------------------- consents
-- Consent is recorded BEFORE processing (DPDP Act 2023 documentation).
create table consents (
  id             uuid primary key default gen_random_uuid(),
  session_id     uuid references verification_sessions(id) on delete set null,
  bill_id        uuid references bills(id) on delete set null,
  purpose        text not null check (purpose in ('process_bill', 'callback')),
  language       text not null references languages(code),
  notice_version text not null default 'v1',
  granted_at     timestamptz not null default now(),
  withdrawn_at   timestamptz
);

-- --------------------------------------------------------- support_workers
-- Fills the "Viewing as" dropdown and ticket assignment.
create table support_workers (
  id          uuid primary key default gen_random_uuid(),
  name        text not null,
  role        text not null check (role in ('chw', 'counselor')),
  hospital_id uuid references hospitals(id) on delete set null,
  languages   text[] not null default '{en}',
  active      boolean not null default true
);

-- --------------------------------------------------------- callback_tickets
create table callback_tickets (
  ticket_id           uuid primary key default gen_random_uuid(),
  short_code          text not null unique,   -- e.g. HB-7K2M9Q, easy to say aloud
  bill_id             uuid references bills(id) on delete set null,
  preferred_language  text not null,           -- what the patient asked for
  effective_language  text not null references languages(code),  -- what we can serve
  callback_time       text not null
                      check (callback_time in ('now','morning','afternoon','evening')),
  reason              text not null check (char_length(reason) between 3 and 1000),
  patient_name        text not null check (char_length(patient_name) between 2 and 200),
  phone_number        text not null check (phone_number ~ '^(\+91|0)?[0-9]{10,15}$'),
  consent_to_callback boolean not null check (consent_to_callback),
  consent_at          timestamptz not null default now(),
  consent_withdrawn_at timestamptz,
  status              text not null default 'new'
                      check (status in ('new','callback_scheduled','contacted','resolved')),
  escalation_reason   text check (escalation_reason in (
                        'distress','failed_access_codes','requested_human',
                        'consent_withdrawn','unsupported_language')),
  case_summary        text,
  triage_suggestion   text check (triage_suggestion in (
                        'billing_question','insurance_mismatch','possible_distress')),
  triage_final        text check (triage_final in (
                        'billing_question','insurance_mismatch','possible_distress')),
  assigned_to         uuid references support_workers(id) on delete set null,
  call_note           text,
  created_at          timestamptz not null default now(),
  updated_at          timestamptz not null default now()
);
create index callback_tickets_status_idx on callback_tickets (status, created_at);

create function set_updated_at() returns trigger language plpgsql as $$
begin
  new.updated_at = now();
  return new;
end $$;

create trigger callback_tickets_updated_at
  before update on callback_tickets
  for each row execute function set_updated_at();

-- ---------------------------------------------------------- generated_texts
-- Log of every AI-generated text. By rule it holds NO names, IDs or contact
-- details: only the record ID, prompt version and the number-checker result.
create table generated_texts (
  id             uuid primary key default gen_random_uuid(),
  bill_id        uuid references bills(id) on delete set null,
  feature        text not null,
  language       text not null references languages(code),
  prompt_version text not null,
  model          text,
  body           text not null,
  checker_result text not null
                 check (checker_result in
                   ('pass','failed_regenerated','fallback_template','not_applicable')),
  created_at     timestamptz not null default now()
);
create index generated_texts_result_idx on generated_texts (checker_result);

commit;
