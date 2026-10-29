# Healthcare Bill Navigator — Run & Testing Guide

## 📍 Project Location
- **Directory:** `C:\Users\Hp\.gemini\antigravity\scratch\patient-financial-navigator`

---

## 🚀 How to Run the Next.js Application

### Start Development Server:
```bash
npm run dev
```
Open **`http://localhost:3000`** in your browser.

### Run Production Build:
```bash
npm run build
npm run start
```

---

## 🧪 Automated Testing & Quality Checks

### Run All 26 Component & Workflow Tests (Vitest):
```bash
npm test
```

### Run Strict TypeScript Typecheck:
```bash
npm run typecheck
```

---

## 🗺️ Implemented Routes

| Route | Screen Name | Key Features |
|---|---|---|
| `/` | **Welcome Page** | Application overview, prominent primary CTA, language selector (EN, HI, KN), privacy statement, official bill notice |
| `/patient` | **Consent Experience** | Plain-language explanations of what/why/how info is used, Agree and Decline controls, respectful limitation notice |
| `/patient/identify` | **Bill Identification** | Option A (Photo Upload with camera/preview/cancel) + Option B (Low-Bandwidth Bill Number), 7 distinct visual result states |
| `/patient/verify` | **Access-Code Screen** | Receipt/SMS code entry, remaining attempts indicator, invalid error, expired state, temporary security lockout |
| `/patient/bill` | **Bill Information** | Total Charges, Insurance Covered, Already Paid, Patient Payable, Dates, Verification badge, Amount discrepancy notice |
| `/patient/explanation` | **Verified Bill Explanation** | "Understand Your Bill", exact label **"Generated from hospital-provided bill information."**, Web Speech TTS AudioPlayer, Simplify Explanation toggle |
| `/patient/questions` | **Follow-Up Questions & Voice** | Clickable sample questions, conversation history, medical scope boundary refusal, Web Speech Voice-First interface with edit & confirm |
| `/patient/help` | **Human Assistance Request** | Patient name, phone number, preferred language, callback time (Now, Morning, Afternoon, Evening), reason, consent checkbox, reference ID |
| `/caregiver` | **Caregiver Summary** | Heading **"What You Need to Know"**, essential numbers, financial terms decoded, dates, questions to ask billing desk, next steps |
| `/support` | **Support-Worker Dashboard** | Request list, search & status filter (New, Callback scheduled, Contacted, Resolved), ticket details, case note audit trail, Demo Data badge |

---

## 🌐 Supported Languages
- **English** (`en`)
- **हिंदी (Hindi)** (`hi`)
- **ಕನ್ನಡ (Kannada)** (`kn`)

Accessible via the language switcher in the header and on every relevant patient screen.
