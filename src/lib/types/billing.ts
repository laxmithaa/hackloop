/**
 * src/lib/types/billing.ts
 *
 * Strictly typed data contracts for Healthcare Bill Navigator.
 * Supports multilingual interfaces, accessibility states, financial verification,
 * audio playback, follow-up Q&A, and human support workflows.
 */

export type Lang = "en" | "hi" | "kn";

export interface BillLineItem {
  id: string;
  chargeLabel: string;
  amountInr: string;
  explanation: string;
  simpleExplanation?: string;
  category?: string;
  confident: boolean;
}

export type IdentificationStatus =
  | "identified"
  | "needs_verification"
  | "not_found"
  | "unregistered_hospital"
  | "unreadable_image"
  | "incomplete"
  | "temporary_failure";

export interface IdentificationResult {
  status: IdentificationStatus;
  hospitalName?: string;
  billNumber?: string;
  patientNamePreview?: string;
  billDate?: string;
  message?: string;
}

export type VerificationState = "verified" | "invalid" | "expired" | "locked";

export interface VerificationResult {
  state: VerificationState;
  attemptsRemaining: number;
  message: string;
}

export type BillState =
  | "verified"
  | "discrepancy"
  | "incomplete"
  | "not_found"
  | "hospital_unregistered"
  | "expired_access";

export interface HospitalBill {
  hospitalName: string;
  billNumber: string;
  patientName: string;
  totalAmountInr: number;
  insuranceCoveredInr: number;
  paidAmountInr: number;
  patientPayableInr: number;
  admissionDate: string;
  dischargeDate: string;
  billDate: string;
  dueDate: string;
  state: BillState;
  discrepancyNotice?: string;
  items: BillLineItem[];
  isDemo: boolean;
}

export interface BillExplanation {
  heading: string;
  summaryText: string;
  simplifiedSummaryText: string;
  breakdownSections: {
    title: string;
    description: string;
    simpleDescription: string;
  }[];
  sourceLabel: string; // Must match exact required label: "Generated from hospital-provided bill information."
  isAiGenerated: boolean;
  disclaimer: string;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: string;
  isRefusal?: boolean;
}

export type CallbackWindow = "now" | "morning" | "afternoon" | "evening";

export type TicketStatus = "New" | "Callback scheduled" | "Contacted" | "Resolved";

export type AnalysisSource = "real" | "demo";

export interface BillAnalysisResult {
  source: AnalysisSource;
  hospitalName: string | null;
  billNumber: string | null;
  items: BillLineItem[];
  totalInr: string | null;
  language: Lang;
  warnings: string[];
}

export type BillLookupStatus = "found" | "not_found" | "connection_error";

export interface BillLookupResponse {
  status: BillLookupStatus;
  result?: BillAnalysisResult;
  message?: string;
}

export interface SupportTicket {
  ticketId: string;
  referenceId: string;
  patientName: string;
  contactNumber: string;
  hospitalId: string;
  hospitalName: string;
  billNumber: string;
  patientNote: string;
  preferredLanguage: Lang;
  preferredCallbackTime: CallbackWindow;
  consentVerified: boolean;
  status: TicketStatus;
  createdAt: string;
  staffNotes?: string[];
  isDemo: boolean;
}
