# Healthcare Bill Navigator

Frontend-only Next.js demonstration that helps patients understand a hospital bill in simple language, in English, Hindi, or Kannada. **All bill amounts, tickets, codes and explanations are fictional.** This app does not look up bills, verify access codes, upload photos, generate AI answers, send requests, arrange callbacks, or authenticate support workers. Do not enter real patient information.

## Run locally

Node.js 20+ is recommended.

```sh
npm ci
npm run dev
```

Open http://localhost:3000. Production: `npm run build && npm start`.

## Routes

- `/`: welcome, language selector, expandable "how it works" and privacy details
- `/patient`: consent (agree records in-memory consent; decline blocks the flow and is never treated as accepted)
- `/patient/identify`: photo picker (drag-drop, replace/remove, invalid-file and unreadable feedback — nothing is uploaded) or bill-number validation; neither looks anything up. A clearly labelled **fictional sample** is the only way into the journey.
- `/patient/verify`: demonstration access-code form — demo code `1234`, three attempts, five-minute expiry, show/hide, clear, incorrect/expired/locked states, locked-out retry path
- `/patient/result`: verification outcome (explicitly not hospital-verified)
- `/patient/bill`: fictional bill summary, expandable extra details, glossary of bill terms
- `/patient/explanation`: fixed-template explanation (labelled demo), simplify toggle, browser text-to-speech (play/pause/stop with unavailable-audio fallbacks), glossary
- `/patient/questions`: fixed example questions and labelled demo answers; unsupported questions get an explicit "no demo answer" response; optional browser speech recognition with review-before-submit
- `/patient/help`: demonstration support form (language, callback preference, reason, consent) producing a visibly fictional `DEMO-` reference; no request is sent
- `/caregiver`: "What You Need to Know" summary of the fictional sample, with navigation back to the patient flow
- `/support`: demo dashboard with search, status filter, ticket selection, local status changes with feedback, and reset-to-original action; all records are marked Demo Data

A progress stepper on patient pages shows current and completed steps without marking unreachable steps complete, and every sensitive page guards on consent, sample selection, and verification state, with a recovery screen and a restart action that clears journey state. Sensitive data stays in memory only — nothing in URLs or browser storage.

## Checks

```sh
npm test          # 21 interaction regression tests (also: npm test -- --run)
npm run typecheck # tsc --noEmit
npm run lint      # eslint
npm run build     # production build
npm audit         # see limitations below
```

Phase 2 verification results: 21/21 tests pass, typecheck and lint clean, production build succeeds. The axe smoke test reports no violations on the welcome screen; jsdom cannot evaluate axe's canvas/pseudo-element contrast probes, so colour contrast and screen-reader, mobile and zoom behaviour still need manual review before real-world use.

## Limitations

- No backend, authentication, secure patient-data handling, real verification, or professional advice. Integrating any live healthcare system requires a separate privacy and security review.
- The "Generated from hospital-provided bill information." label applies only if real AI generation is added; the current explanation is a fixed template and is labelled as such.
- `npm audit` reports 5 findings: postcss inside Next.js 15 (high; fixed by the Next 16 major upgrade) and tinypool/@vitest/mocker via Vitest 3 (critical/moderate test-runner-only; fixed by the Vitest 5 major upgrade). No fix was forced because both require breaking major upgrades — a deliberate decision for this project. Neither affects the running app: the Next/postcss advisory concerns processing untrusted CSS input, and the Vitest advisories concern running untrusted test code/mocks.
- Translations cover every English interface key in Hindi and Kannada (enforced by a coverage test); sample ticket reason/callback values remain English demo data and the UI marks them as such.
