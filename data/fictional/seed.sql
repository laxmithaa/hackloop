-- seed.sql: FICTIONAL DATA. DO NOT USE FOR REAL DATA.
-- Every hospital, bill, name and code below is invented for the prototype.
-- Load with:  python -m app.db.setup --reset      (from backend/)
--        or:  psql "$DATABASE_URL" -f data/fictional/seed.sql
--
-- 20 bills across 3 registered hospitals. "Hospital not registered" and
-- "bill not found" need no rows: they are absences.
--
-- Edge cases covered (bill number: what it tests)
--   INV-2026-0042  insurer paid part and still owes part (the main demo)
--   SMC/2026/118   insurance-approved amount NOT provided (missing != 0);
--                  insurance paid is a real 0.00
--   CC-0007        fully settled: amount due is a real 0.00
--   INV-2026-0100  no insurance at all
--   INV-2026-0101  small co-payment after insurance
--   INV-2026-0102  claim approved but nothing paid yet
--   INV-2026-0103  overdue (due date already passed)
--   INV-2026-0104  amounts with paise (12345.50)
--   INV-2026-0105  several partial payments on a large bill
--   INV-2026-0106  sparse record: only total and patient payments
--   SMC/2026/119   minimal record: only total and amount due
--   SMC/2026/120   very large bill (payment-plan sized)
--   SMC/2026/121   advance payment covers the whole bill
--   SMC/2026/122   fully waived: total is 0.00
--   CC-0008        small outpatient bill, no insurance
--   CC-0009        insurance covers everything but has not paid yet
--   CC-0010        record has NO due date
--   CC/0011-A      bill number with a slash and a hyphen
--   CC-0012        amount due NOT provided
--   CC-0013        no patient payments on record
--
-- Access codes: DEMO-1234, DEMO-5678, DEMO-0007, DEMO-0100 for the first four
-- bills, then DEMO-2005 ... DEMO-2020 for the rest in the order listed below.

begin;

insert into hospitals (id, name, registration_no) values
  ('11111111-1111-1111-1111-111111111111', 'City General Hospital',  'REG-DEMO-001'),
  ('22222222-2222-2222-2222-222222222222', 'Sunrise Medical Centre', 'REG-DEMO-002'),
  ('33333333-3333-3333-3333-333333333333', 'Coastal Care Clinic',    'REG-DEMO-003');

-- One row per bill. A NULL amount means "the hospital record does not provide it".
create temp table seed_bills (
  bill_number  text,
  hospital_reg text,
  bill_date    date,
  due_date     date,
  code         text,
  fixed_id     uuid,
  total        numeric(12,2),  -- billTotalAfterDiscounts
  approved     numeric(12,2),  -- insuranceApprovedButNotPaid
  paid         numeric(12,2),  -- insurancePaidOrCredited
  patient      numeric(12,2),  -- patientPayments
  due          numeric(12,2)   -- printedAmountDue
) on commit drop;

insert into seed_bills values
  ('INV-2026-0042', 'REG-DEMO-001', '2026-09-20', '2026-10-30', 'DEMO-1234', 'aaaaaaaa-0000-0000-0000-000000000001',  50000.00, 15000.00, 15000.00,  5000.00, 30000.00),
  ('SMC/2026/118',  'REG-DEMO-002', '2026-09-25', '2026-11-05', 'DEMO-5678', 'aaaaaaaa-0000-0000-0000-000000000002',  12500.00,     null,     0.00,  2000.00, 10500.00),
  ('CC-0007',       'REG-DEMO-003', '2026-09-10', '2026-10-10', 'DEMO-0007', 'aaaaaaaa-0000-0000-0000-000000000003',   8000.00,     0.00,  6000.00,  2000.00,     0.00),
  ('INV-2026-0100', 'REG-DEMO-001', '2026-10-01', '2026-11-15', 'DEMO-0100', 'aaaaaaaa-0000-0000-0000-000000000004',  75000.00,     null,     null, 10000.00, 65000.00),
  ('INV-2026-0101', 'REG-DEMO-001', '2026-09-22', '2026-11-01', 'DEMO-2005', null,  40000.00,     0.00, 37500.00,     0.00,  2500.00),
  ('INV-2026-0102', 'REG-DEMO-001', '2026-10-02', '2026-11-20', 'DEMO-2006', null,  60000.00, 60000.00,     0.00,     0.00, 60000.00),
  ('INV-2026-0103', 'REG-DEMO-001', '2026-08-20', '2026-10-05', 'DEMO-2007', null,  22000.00,     null,     0.00,  5000.00, 17000.00),
  ('INV-2026-0104', 'REG-DEMO-001', '2026-10-10', '2026-11-25', 'DEMO-2008', null,  12345.50,     0.00,  8000.25,  1000.00,  3345.25),
  ('INV-2026-0105', 'REG-DEMO-001', '2026-09-05', '2026-10-31', 'DEMO-2009', null, 120000.00, 20000.00, 80000.00, 15000.00, 25000.00),
  ('INV-2026-0106', 'REG-DEMO-001', '2026-10-12', '2026-11-30', 'DEMO-2010', null,  35000.00,     null,     null,  5000.00,     null),
  ('SMC/2026/119',  'REG-DEMO-002', '2026-09-28', '2026-11-10', 'DEMO-2011', null,  18000.00,     null,     null,     null, 18000.00),
  ('SMC/2026/120',  'REG-DEMO-002', '2026-09-01', '2026-10-25', 'DEMO-2012', null, 250000.00,     0.00, 150000.00, 25000.00, 75000.00),
  ('SMC/2026/121',  'REG-DEMO-002', '2026-10-05', '2026-11-12', 'DEMO-2013', null,   9000.00,     null,     null,  9000.00,     0.00),
  ('SMC/2026/122',  'REG-DEMO-002', '2026-10-08', '2026-11-08', 'DEMO-2014', null,      0.00,     null,     null,     0.00,     0.00),
  ('CC-0008',       'REG-DEMO-003', '2026-10-15', '2026-11-15', 'DEMO-2015', null,   1200.00,     null,     null,     0.00,  1200.00),
  ('CC-0009',       'REG-DEMO-003', '2026-10-16', '2026-12-01', 'DEMO-2016', null,  18000.00, 18000.00,     0.00,     0.00, 18000.00),
  ('CC-0010',       'REG-DEMO-003', '2026-10-18', null,         'DEMO-2017', null,  14000.00,     0.00,  9000.00,  1000.00,  4000.00),
  ('CC/0011-A',     'REG-DEMO-003', '2026-10-20', '2026-11-20', 'DEMO-2018', null,   5500.00,     null,  2500.00,     0.00,  3000.00),
  ('CC-0012',       'REG-DEMO-003', '2026-09-30', '2026-10-31', 'DEMO-2019', null,  26000.00,     null,     null,  6000.00,     null),
  ('CC-0013',       'REG-DEMO-003', '2026-10-22', '2026-11-22', 'DEMO-2020', null,  30000.00,     null, 20000.00,     null, 10000.00);

insert into bills (id, hospital_id, bill_number, bill_date, due_date)
select coalesce(s.fixed_id, gen_random_uuid()), h.id, s.bill_number, s.bill_date, s.due_date
  from seed_bills s
  join hospitals h on h.registration_no = s.hospital_reg;

-- Turn each row into one bill_financials row per amount that is provided.
insert into bill_financials (bill_id, field_key, amount_rupees)
select b.id, f.field_key, f.amount
  from seed_bills s
  join bills b on b.bill_number = s.bill_number
  cross join lateral (values
    ('billTotalAfterDiscounts',     s.total),
    ('insuranceApprovedButNotPaid', s.approved),
    ('insurancePaidOrCredited',     s.paid),
    ('patientPayments',             s.patient),
    ('printedAmountDue',            s.due)
  ) as f(field_key, amount)
 where f.amount is not null;

-- Access codes (bcrypt via pgcrypto; Python's bcrypt verifies these hashes).
insert into access_codes (bill_id, code_hash)
select b.id, crypt(s.code, gen_salt('bf', 10))
  from seed_bills s
  join bills b on b.bill_number = s.bill_number;

insert into support_workers (id, name, role, hospital_id, languages) values
  ('bbbbbbbb-0000-0000-0000-000000000001', 'Demo Counselor A', 'counselor', '11111111-1111-1111-1111-111111111111', '{en,hi}'),
  ('bbbbbbbb-0000-0000-0000-000000000002', 'Demo Health Worker B', 'chw',   '22222222-2222-2222-2222-222222222222', '{en,kn}');

commit;
