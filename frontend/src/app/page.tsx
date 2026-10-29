"use client";

import React, { useState, useRef } from "react";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import DemoNotice from "@/components/DemoNotice";
import StatusBadge, { BadgeVariant } from "@/components/StatusBadge";
import AudioPlayer from "@/components/AudioPlayer";
import VoiceInput from "@/components/VoiceInput";
import { useLanguage } from "@/lib/context/LanguageContext";
import {
  FileText,
  Volume2,
  PhoneCall,
  ArrowRight,
  ShieldCheck,
  CheckCircle2,
  Users,
  Search,
  KeyRound,
  Sparkles,
  ToggleLeft,
  ToggleRight,
  MessageSquare,
  Send,
  UploadCloud,
  Camera,
  XCircle,
  AlertTriangle,
  RefreshCw,
  File,
  Wifi,
  Calendar,
  Lock,
  Eye,
  FileQuestion,
  HelpCircle,
  User,
  Phone,
  Clock,
  Plus,
  HeartHandshake,
  Info,
  ShieldAlert,
  ChevronDown,
  X,
} from "lucide-react";
import { z } from "zod";
import {
  getMockBill,
  getMockExplanation,
  MOCK_VERIFIED_BILL,
  MOCK_DISCREPANCY_BILL,
  MOCK_INCOMPLETE_BILL,
  INITIAL_SUPPORT_TICKETS,
} from "@/lib/services/mockData";
import type {
  Lang,
  HospitalBill,
  IdentificationStatus,
  ChatMessage,
  CallbackWindow,
  SupportTicket,
  TicketStatus,
} from "@/lib/types/billing";

// Zod schemas
const billNumberSchema = z
  .string()
  .min(3, "Bill number must be at least 3 characters")
  .max(30, "Bill number cannot exceed 30 characters");

const supportFormSchema = z.object({
  patientName: z.string().min(2, "Please enter your name"),
  contactNumber: z.string().min(8, "Please enter a valid phone number"),
  billNumber: z.string().min(3, "Please provide the bill number"),
  reason: z.string().min(8, "Please describe your question or dispute (min 8 characters)"),
  consentGiven: z.literal(true, {
    errorMap: () => ({ message: "You must provide consent for a worker to call you" }),
  }),
});

export default function CombinedSinglePageApp() {
  const { t, lang, setLang, currentBill, setCurrentBill } = useLanguage();

  // Top-level View Mode: 'patient' | 'caregiver' | 'support'
  const [activeView, setActiveView] = useState<"patient" | "caregiver" | "support">("patient");

  // ── 1. Consent State ──
  const [consentGranted, setConsentGranted] = useState(false);
  const [consentDeclined, setConsentDeclined] = useState(false);

  // ── 2. Identification State ──
  const [idTab, setIdTab] = useState<"number" | "upload">("number");
  const [billNumberInput, setBillNumberInput] = useState("BILL-2026-001");
  const [idError, setIdError] = useState<string | null>(null);
  const [isSearchingBill, setIsSearchingBill] = useState(false);
  const [idResultStatus, setIdResultStatus] = useState<IdentificationStatus | null>(null);

  // Upload state
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);
  const [uploadPreview, setUploadPreview] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const cameraInputRef = useRef<HTMLInputElement>(null);

  // ── 3. Access Code Verification State ──
  const [accessCode, setAccessCode] = useState("HBN-4921");
  const [verifyAttempts, setVerifyAttempts] = useState(3);
  const [isVerifyingCode, setIsVerifyingCode] = useState(false);
  const [codeVerified, setCodeVerified] = useState(false);
  const [verifyError, setVerifyError] = useState<string | null>(null);
  const [codeExpired, setCodeExpired] = useState(false);
  const [codeLocked, setCodeLocked] = useState(false);

  // ── 4. Explanation State ──
  const [isSimplified, setIsSimplified] = useState(false);
  const explanation = getMockExplanation(currentBill, lang);

  // ── 5. Follow-Up Questions State ──
  const [questionText, setQuestionText] = useState("");
  const [isAnswering, setIsAnswering] = useState(false);
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([
    {
      id: "init-1",
      role: "assistant",
      content:
        lang === "hi"
          ? `नमस्ते! मैं आपके ${currentBill.hospitalName} बिल (कुल राशि: ₹ ${currentBill.totalAmountInr.toLocaleString("en-IN")}) के शुल्कों को समझने में मदद कर सकता हूँ।`
          : lang === "kn"
          ? `ನಮಸ್ಕಾರ! ನಾನು ನಿಮ್ಮ ${currentBill.hospitalName} ಬಿಲ್ (ಒಟ್ಟು ಮೊತ್ತ: ₹ ${currentBill.totalAmountInr.toLocaleString("en-IN")}) ಶುಲ್ಕಗಳನ್ನು ವಿವರಿಸಬಲ್ಲೆ.`
          : `Hello! I am ready to explain charges, medical tests, and insurance coverage on your ${currentBill.hospitalName} bill.`,
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    },
  ]);

  // ── 6. Human Support State ──
  const [supportName, setSupportName] = useState(currentBill.patientName.replace(" (Demo)", ""));
  const [supportPhone, setSupportPhone] = useState("+91 98765 43210");
  const [supportCallback, setSupportCallback] = useState<CallbackWindow>("now");
  const [supportReason, setSupportReason] = useState("Clarification needed on doctor consultation and medicine charges.");
  const [supportConsent, setSupportConsent] = useState(false);
  const [supportErrors, setSupportErrors] = useState<Record<string, string>>({});
  const [supportSubmitting, setSupportSubmitting] = useState(false);
  const [supportRefId, setSupportRefId] = useState<string | null>(null);

  // ── 7. Support Worker Dashboard State ──
  const [tickets, setTickets] = useState<SupportTicket[]>(INITIAL_SUPPORT_TICKETS);
  const [selectedTicketId, setSelectedTicketId] = useState<string>(INITIAL_SUPPORT_TICKETS[0].ticketId);
  const [ticketSearch, setTicketSearch] = useState("");
  const [ticketFilter, setTicketFilter] = useState("All");
  const [staffNoteInput, setStaffNoteInput] = useState("");

  const activeTicket = tickets.find((t) => t.ticketId === selectedTicketId) || tickets[0];

  // ── Handlers ──

  // Bill Identification Submit
  const handleFindBill = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    setIdError(null);

    const val = billNumberSchema.safeParse(billNumberInput);
    if (!val.success) {
      setIdError(val.error.errors[0].message);
      return;
    }

    setIsSearchingBill(true);
    setIdResultStatus(null);

    setTimeout(() => {
      setIsSearchingBill(false);
      const clean = billNumberInput.trim().toUpperCase();

      if (clean === "UNREG-770" || clean.includes("UNREG")) {
        setIdResultStatus("unregistered_hospital");
      } else if (clean === "NOTFOUND-99" || clean.includes("NOTFOUND")) {
        setIdResultStatus("not_found");
      } else if (clean === "INC-2026-104" || clean.includes("INC")) {
        setIdResultStatus("incomplete");
        setCurrentBill(MOCK_INCOMPLETE_BILL);
      } else if (clean === "DISC-2026-902" || clean.includes("DISC")) {
        setIdResultStatus("identified");
        setCurrentBill(MOCK_DISCREPANCY_BILL);
      } else if (clean === "VERIFY-REQ" || clean === "BILL-2026-001") {
        setIdResultStatus("needs_verification");
        setCurrentBill(MOCK_VERIFIED_BILL);
      } else {
        const found = getMockBill(billNumberInput);
        if (found) {
          setIdResultStatus("identified");
          setCurrentBill(found);
        } else {
          setIdResultStatus("not_found");
        }
      }
    }, 500);
  };

  // Upload Handler
  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploadedFile(file);
    if (file.type.startsWith("image/")) {
      setUploadPreview(URL.createObjectURL(file));
    }
  };

  const handleScanUpload = () => {
    if (!uploadedFile) return;
    setIsSearchingBill(true);
    setTimeout(() => {
      setIsSearchingBill(false);
      if (uploadedFile.name.toLowerCase().includes("blurry")) {
        setIdResultStatus("unreadable_image");
      } else {
        setIdResultStatus("needs_verification");
        setCurrentBill(MOCK_VERIFIED_BILL);
      }
    }, 800);
  };

  // Access Code Verification
  const handleVerifyCode = (e: React.FormEvent) => {
    e.preventDefault();
    if (codeLocked) return;

    setVerifyError(null);
    setCodeExpired(false);
    setIsVerifyingCode(true);

    setTimeout(() => {
      setIsVerifyingCode(false);
      const clean = accessCode.trim().toUpperCase();
      if (clean === "EXPIRED") {
        setCodeExpired(true);
      } else if (clean === "HBN-4921" || clean === "7492" || clean === "PASS123") {
        setCodeVerified(true);
        // Scroll to bill summary
        document.getElementById("section-bill-summary")?.scrollIntoView({ behavior: "smooth" });
      } else {
        const next = verifyAttempts - 1;
        setVerifyAttempts(next);
        if (next <= 0) {
          setCodeLocked(true);
          setVerifyError(t.verify.lockedError);
        } else {
          setVerifyError(t.verify.invalidError);
        }
      }
    }, 500);
  };

  // Q&A Handler
  const handleAskQuestion = (text: string) => {
    if (!text.trim() || isAnswering) return;

    const userMsg: ChatMessage = {
      id: `usr-${Date.now()}`,
      role: "user",
      content: text.trim(),
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    };

    setChatMessages((prev) => [...prev, userMsg]);
    setQuestionText("");
    setIsAnswering(true);

    setTimeout(() => {
      setIsAnswering(false);
      const lower = text.toLowerCase();

      if (
        lower.includes("cancer") ||
        lower.includes("tumor") ||
        lower.includes("cure") ||
        lower.includes("treatment work") ||
        lower.includes("dosage")
      ) {
        setChatMessages((prev) => [
          ...prev,
          {
            id: `asst-${Date.now()}`,
            role: "assistant",
            content:
              lang === "hi"
                ? "चिकित्सीय सीमा: मैं केवल अस्पताल के बिल, वित्तीय शुल्कों और बीमा नियमों को समझा सकता हूँ। अपनी बीमारी के इलाज या दवा की सही खुराक के लिए कृपया अपने डॉक्टर से परामर्श करें।"
                : lang === "kn"
                ? "ವೈದ್ಯಕೀಯ ಮಿತಿ: ನಾನು ಬಿಲ್ಲಿಂಗ್ ಮತ್ತು ಹಣಕಾಸಿನ ಶುಲ್ಕಗಳನ್ನು ಮಾತ್ರ ವಿವರಿಸಬಲ್ಲೆ. ಚಿಕಿತ್ಸೆ ಅಥವಾ ರೋಗನಿರ್ಣಯಕ್ಕಾಗಿ ನಿಮ್ಮ ವೈದ್ಯರನ್ನು ಸಂಪರ್ಕಿಸಿ."
                : "Medical Scope Notice: I can only explain hospital billing terms and charges. For clinical diagnosis, medicine doses, or treatment choices, please consult your doctor.",
            timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
            isRefusal: true,
          },
        ]);
        return;
      }

      let answer = "";
      if (lower.includes("consultation") || lower.includes("कंसल्टेशन") || lower.includes("ಕನ್ಸಲ್ಟೇಶನ್")) {
        answer =
          lang === "hi"
            ? "कंसल्टेशन फ़ीस (₹ 800) डॉक्टर द्वारा जांच करने, स्वास्थ्य सलाह देने और अस्पताल में आपकी देखभाल की योजना बनाने का शुल्क है।"
            : lang === "kn"
            ? "ಕನ್ಸಲ್ಟೇಶನ್ ಶುಲ್ಕ (₹ 800) ಎಂದರೆ ವೈದ್ಯರು ನಿಮ್ಮನ್ನು ತಪಾಸಣೆ ಮಾಡಿ ನೀಡಿದ ವೈದ್ಯಕೀಯ ಸಲಹೆಯ ಅಧಿಕೃತ ಶುಲ್ಕವಾಗಿದೆ."
            : "The Consultation Fee (₹ 800) covers your attending physician's clinical examination, vital checks, and in-hospital care management.";
      } else if (lower.includes("x-ray") || lower.includes("एक्स-रे") || lower.includes("ಎಕ್ಸ್‌ರೇ")) {
        answer =
          lang === "hi"
            ? "चेस्ट एक्स-रे (₹ 1,200) फेफड़ों और सीने की जांच के लिए इमेजिंग स्कैन है। इसमें रेडियोग्राफर और विशेषज्ञ रिपोर्टिंग दोनों शामिल हैं।"
            : lang === "kn"
            ? "ಎದೆಯ ಎಕ್ಸ್‌ರೇ (₹ 1,200) ಶ್ವಾಸಕೋಶವನ್ನು ಪರೀಕ್ಷಿಸಲು ತೆಗೆದ ರೇಡಿಯಾಲಜಿ ಸ್ಕ್ಯಾನ್ ಆಗಿದೆ."
            : "The Chest X-Ray (₹ 1,200) is a diagnostic imaging scan of the lungs and chest. It covers the technologist, machine consumables, and radiologist review.";
      } else {
        answer =
          lang === "hi"
            ? `बिल #${currentBill.billNumber} के अनुसार, कुल राशि ₹ ${currentBill.totalAmountInr.toLocaleString("en-IN")} है और बीमा कटौती के बाद देय शेष ₹ ${currentBill.patientPayableInr.toLocaleString("en-IN")} है।`
            : lang === "kn"
            ? `ಬಿಲ್ #${currentBill.billNumber} ಪ್ರಕಾರ ಒಟ್ಟು ಮೊತ್ತ ₹ ${currentBill.totalAmountInr.toLocaleString("en-IN")}. ನೀವು ಪಾವತಿಸಬೇಕಾದ ಉಳಿದ ಹಣ ₹ ${currentBill.patientPayableInr.toLocaleString("en-IN")}.`
            : `Under record #${currentBill.billNumber}, total charges are ₹ ${currentBill.totalAmountInr.toLocaleString("en-IN")}, leaving ₹ ${currentBill.patientPayableInr.toLocaleString("en-IN")} payable after insurance.`;
      }

      setChatMessages((prev) => [
        ...prev,
        {
          id: `asst-${Date.now()}`,
          role: "assistant",
          content: answer,
          timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        },
      ]);
    }, 600);
  };

  // Human Support Form Submit
  const handleSupportSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setSupportErrors({});

    const val = supportFormSchema.safeParse({
      patientName: supportName,
      contactNumber: supportPhone,
      billNumber: currentBill.billNumber,
      reason: supportReason,
      consentGiven: supportConsent,
    });

    if (!val.success) {
      const errMap: Record<string, string> = {};
      val.error.errors.forEach((er) => {
        if (er.path[0]) errMap[er.path[0].toString()] = er.message;
      });
      setSupportErrors(errMap);
      return;
    }

    setSupportSubmitting(true);
    setTimeout(() => {
      setSupportSubmitting(false);
      const generatedRef = `REF-2026-${Math.floor(1000 + Math.random() * 9000)}`;
      setSupportRefId(generatedRef);
    }, 700);
  };

  // Support Worker Status Change
  const handleTicketStatusChange = (newStatus: TicketStatus) => {
    setTickets((prev) =>
      prev.map((t) =>
        t.ticketId === activeTicket.ticketId
          ? {
              ...t,
              status: newStatus,
              staffNotes: [
                ...(t.staffNotes || []),
                `Status changed to "${newStatus}" at ${new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}`,
              ],
            }
          : t
      )
    );
  };

  const handleAddStaffNote = (e: React.FormEvent) => {
    e.preventDefault();
    if (!staffNoteInput.trim()) return;

    setTickets((prev) =>
      prev.map((t) =>
        t.ticketId === activeTicket.ticketId
          ? {
              ...t,
              staffNotes: [
                ...(t.staffNotes || []),
                `${staffNoteInput.trim()} (${new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })})`,
              ],
            }
          : t
      )
    );
    setStaffNoteInput("");
  };

  const getStatusBadge = (st: TicketStatus): BadgeVariant => {
    if (st === "Resolved") return "success";
    if (st === "Callback scheduled") return "warning";
    if (st === "New") return "info";
    return "neutral";
  };

  // Build narration transcript
  const narrationScript = isSimplified
    ? `${explanation.heading}. ${explanation.simplifiedSummaryText} ${explanation.breakdownSections
        .map((s) => `${s.title}: ${s.simpleDescription}`)
        .join(". ")}`
    : `${explanation.heading}. ${explanation.summaryText} ${explanation.breakdownSections
        .map((s) => `${s.title}: ${s.description}`)
        .join(". ")}`;

  return (
    <div className="min-h-screen flex flex-col bg-[#f8fafc]">
      <DemoNotice />

      {/* ── UNIFIED APP NAVIGATION BAR ── */}
      <header className="sticky top-0 z-50 bg-white/95 backdrop-blur-md border-b border-slate-200 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-20">
            {/* Brand Logo */}
            <div className="flex items-center gap-3">
              <div className="w-11 h-11 rounded-xl bg-gradient-to-br from-blue-700 to-teal-700 flex items-center justify-center text-white shadow-md flex-shrink-0">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M12 6v12M6 12h12" />
                </svg>
              </div>
              <div>
                <div className="text-lg sm:text-xl font-extrabold tracking-tight text-slate-900 leading-none">
                  Healthcare <span className="text-blue-700">Bill Navigator</span>
                </div>
                <div className="text-xs text-slate-500 font-medium mt-1 hidden sm:block">
                  {t.nav.tagline}
                </div>
              </div>
            </div>

            {/* Combined View Switcher Tabs (Patient Flow vs Caregiver vs Support Dashboard) */}
            <nav className="inline-flex items-center bg-slate-100 p-1.5 rounded-2xl border border-slate-200">
              <button
                type="button"
                onClick={() => setActiveView("patient")}
                className={`px-3.5 py-2 rounded-xl text-xs sm:text-sm font-bold transition-all ${
                  activeView === "patient"
                    ? "bg-blue-700 text-white shadow-sm"
                    : "text-slate-700 hover:text-slate-900"
                }`}
              >
                {t.nav.patientFlow}
              </button>

              <button
                type="button"
                onClick={() => setActiveView("caregiver")}
                className={`px-3.5 py-2 rounded-xl text-xs sm:text-sm font-bold transition-all ${
                  activeView === "caregiver"
                    ? "bg-blue-700 text-white shadow-sm"
                    : "text-slate-700 hover:text-slate-900"
                }`}
              >
                {t.nav.caregiver}
              </button>

              <button
                type="button"
                onClick={() => setActiveView("support")}
                className={`px-3.5 py-2 rounded-xl text-xs sm:text-sm font-bold transition-all ${
                  activeView === "support"
                    ? "bg-blue-700 text-white shadow-sm"
                    : "text-slate-700 hover:text-slate-900"
                }`}
              >
                {t.nav.support}
              </button>
            </nav>

            {/* Language Switcher */}
            <div className="hidden sm:flex items-center gap-1.5 bg-slate-100 p-1 rounded-xl border border-slate-200">
              {(["en", "hi", "kn"] as Lang[]).map((code) => (
                <button
                  key={code}
                  type="button"
                  onClick={() => setLang(code)}
                  className={`px-2.5 py-1 text-xs font-bold rounded-lg transition-all ${
                    lang === code ? "bg-blue-700 text-white shadow-sm" : "text-slate-600 hover:text-slate-900"
                  }`}
                >
                  {code === "en" ? "EN" : code === "hi" ? "हिंदी" : "ಕನ್ನಡ"}
                </button>
              ))}
            </div>
          </div>
        </div>
      </header>

      {/* ─────────────────────────────────────────────────────────────
          VIEW 1: PATIENT JOURNEY (SEAMLESS ALL-IN-ONE FLOW)
         ───────────────────────────────────────────────────────────── */}
      {activeView === "patient" && (
        <main className="flex-1 max-w-4xl mx-auto w-full px-4 sm:px-6 py-8 md:py-12 space-y-10">
          {/* Welcome Card & Primary Action */}
          <div className="bg-white rounded-3xl border border-slate-200/80 shadow-sm p-6 sm:p-10 text-center">
            <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-blue-50 border border-blue-200 text-blue-800 text-xs font-bold mb-4">
              <span className="w-2 h-2 rounded-full bg-blue-600 animate-pulse" />
              <span>Simple Language · Multilingual · Audio Guidance</span>
            </div>
            <h1 className="text-3xl sm:text-4xl font-black text-slate-900 tracking-tight leading-tight mb-4">
              {t.welcome.title}
            </h1>
            <p className="text-sm sm:text-base text-slate-600 max-w-2xl mx-auto leading-relaxed mb-6">
              {t.welcome.subtitle}
            </p>

            {/* Primary Action Button */}
            <div className="flex flex-col sm:flex-row items-center justify-center gap-4 max-w-md mx-auto mb-8">
              <a
                href="#section-consent"
                className="w-full sm:w-auto inline-flex items-center justify-center gap-3 px-8 py-4 bg-blue-700 hover:bg-blue-800 active:bg-blue-900 text-white font-extrabold rounded-2xl text-lg shadow-md transition-all touch-target"
              >
                <span>{t.welcome.primaryCta}</span>
                <ArrowRight className="w-5 h-5" aria-hidden="true" />
              </a>

              <button
                type="button"
                onClick={() => setActiveView("caregiver")}
                className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-6 py-4 bg-slate-100 hover:bg-slate-200 text-slate-800 font-bold rounded-2xl text-base transition-colors touch-target"
              >
                <Users className="w-5 h-5 text-slate-600" aria-hidden="true" />
                <span>{t.welcome.secondaryCta}</span>
              </button>
            </div>

            {/* Language Selector on Hero */}
            <div className="pt-6 border-t border-slate-100 flex flex-col items-center gap-3 mb-4">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-500">
                {lang === "hi"
                  ? "अपनी पसंदीदा भाषा चुनें:"
                  : lang === "kn"
                  ? "ನಿಮ್ಮ ಆದ್ಯತೆಯ ಭಾಷೆಯನ್ನು ಆಯ್ಕೆಮಾಡಿ:"
                  : "Choose your preferred language:"}
              </span>
              <div className="flex flex-wrap items-center justify-center gap-2">
                {[
                  { code: "en", label: "English" },
                  { code: "hi", label: "हिंदी (Hindi)" },
                  { code: "kn", label: "ಕನ್ನಡ (Kannada)" },
                ].map((item) => (
                  <button
                    key={item.code}
                    type="button"
                    onClick={() => setLang(item.code as any)}
                    className={`px-4 py-2 rounded-xl text-sm font-bold border transition-all touch-target ${
                      lang === item.code
                        ? "bg-blue-700 text-white border-blue-700 shadow-sm"
                        : "bg-slate-50 text-slate-700 border-slate-200 hover:bg-slate-100"
                    }`}
                  >
                    {item.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Quick in-page anchor jump pills */}
            <div className="flex flex-wrap items-center justify-center gap-2 pt-2 border-t border-slate-100 text-xs font-bold">
              <span className="text-slate-400 mr-1">Jump to:</span>
              <a href="#section-consent" className="px-3 py-1.5 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700">1. Consent</a>
              <a href="#section-identify" className="px-3 py-1.5 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700">2. Bill Lookup</a>
              <a href="#section-bill-summary" className="px-3 py-1.5 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700">3. Financial Summary</a>
              <a href="#section-explanation" className="px-3 py-1.5 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700">4. Explanation & Audio</a>
              <a href="#section-questions" className="px-3 py-1.5 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700">5. Voice Q&A</a>
              <a href="#section-help" className="px-3 py-1.5 rounded-xl bg-teal-50 text-teal-800 border border-teal-200">6. Human Support</a>
            </div>

            <p className="text-xs text-slate-500 max-w-xl mx-auto mt-6 leading-relaxed">
              {t.welcome.disclaimer}
            </p>
          </div>

          {/* ── STEP 1: CONSENT SECTION ── */}
          <section id="section-consent" className="bg-white rounded-3xl border border-slate-200/80 shadow-sm p-6 sm:p-10 space-y-6">
            <div className="flex items-center gap-3 pb-4 border-b border-slate-200">
              <div className="w-10 h-10 rounded-xl bg-blue-50 text-blue-700 flex items-center justify-center flex-shrink-0">
                <ShieldCheck className="w-6 h-6" />
              </div>
              <div>
                <h2 className="text-xl font-extrabold text-slate-900">
                  Step 1: {t.consent.title}
                </h2>
                <p className="text-xs text-slate-500">{t.consent.subtitle}</p>
              </div>
            </div>

            {consentDeclined ? (
              <div className="p-5 bg-amber-50 border border-amber-200 rounded-2xl space-y-3">
                <div className="font-bold text-amber-950 flex items-center gap-2">
                  <AlertTriangle className="w-5 h-5 text-amber-700" />
                  <span>{t.consent.declinedNoticeTitle}</span>
                </div>
                <p className="text-xs sm:text-sm text-amber-900">{t.consent.declinedNoticeMsg}</p>
                <button
                  type="button"
                  onClick={() => {
                    setConsentDeclined(false);
                    setConsentGranted(true);
                  }}
                  className="px-4 py-2 bg-blue-700 text-white font-bold rounded-xl text-xs"
                >
                  {t.consent.reconsiderBtn}
                </button>
              </div>
            ) : (
              <div className="space-y-4">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs sm:text-sm">
                  <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200">
                    <strong className="text-slate-900 block mb-1">1. Information Used</strong>
                    <span className="text-slate-600">{t.consent.whatUsedText}</span>
                  </div>
                  <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200">
                    <strong className="text-slate-900 block mb-1">2. Purpose & Need</strong>
                    <span className="text-slate-600">{t.consent.whyNeededText}</span>
                  </div>
                  <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200">
                    <strong className="text-slate-900 block mb-1">3. In-Memory Processing</strong>
                    <span className="text-slate-600">{t.consent.howUsedText}</span>
                  </div>
                  <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200">
                    <strong className="text-slate-900 block mb-1">4. Right to Decline</strong>
                    <span className="text-slate-600">{t.consent.declineText}</span>
                  </div>
                </div>

                <div className="flex flex-wrap items-center gap-3 pt-2">
                  <button
                    type="button"
                    onClick={() => {
                      setConsentGranted(true);
                      setConsentDeclined(false);
                    }}
                    className={`inline-flex items-center gap-2 px-6 py-3 rounded-xl text-sm font-extrabold transition-all ${
                      consentGranted
                        ? "bg-emerald-700 text-white shadow-sm"
                        : "bg-blue-700 hover:bg-blue-800 text-white"
                    }`}
                  >
                    <CheckCircle2 className="w-4 h-4" />
                    <span>{consentGranted ? "Consent Granted ✓" : t.consent.agreeBtn}</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => {
                      setConsentGranted(false);
                      setConsentDeclined(true);
                    }}
                    className="px-4 py-3 rounded-xl text-sm font-bold bg-slate-100 hover:bg-slate-200 text-slate-700"
                  >
                    {t.consent.declineBtn}
                  </button>
                </div>
              </div>
            )}
          </section>

          {/* ── STEP 2: BILL IDENTIFICATION SECTION ── */}
          <section id="section-identify" className="bg-white rounded-3xl border border-slate-200/80 shadow-sm p-6 sm:p-10 space-y-6">
            <div className="flex items-center gap-3 pb-4 border-b border-slate-200">
              <div className="w-10 h-10 rounded-xl bg-blue-50 text-blue-700 flex items-center justify-center flex-shrink-0">
                <Search className="w-6 h-6" />
              </div>
              <div>
                <h2 className="text-xl font-extrabold text-slate-900">
                  Step 2: {t.identify.title}
                </h2>
                <p className="text-xs text-slate-500">{t.identify.subtitle}</p>
              </div>
            </div>

            {/* Tab Switcher */}
            <div className="grid grid-cols-2 gap-2 p-1.5 bg-slate-100 rounded-2xl max-w-md">
              <button
                type="button"
                onClick={() => setIdTab("number")}
                className={`py-2 px-4 rounded-xl text-xs sm:text-sm font-bold ${
                  idTab === "number" ? "bg-white text-blue-700 shadow-sm" : "text-slate-600"
                }`}
              >
                {t.identify.tabNumber}
              </button>
              <button
                type="button"
                onClick={() => setIdTab("upload")}
                className={`py-2 px-4 rounded-xl text-xs sm:text-sm font-bold ${
                  idTab === "upload" ? "bg-white text-blue-700 shadow-sm" : "text-slate-600"
                }`}
              >
                {t.identify.tabUpload}
              </button>
            </div>

            {idTab === "number" ? (
              <form onSubmit={handleFindBill} className="space-y-4">
                <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-50 text-emerald-800 border border-emerald-200 text-xs font-bold">
                  <Wifi className="w-3.5 h-3.5" />
                  <span>{t.identify.lowBandwidthBadge}</span>
                </div>

                <div>
                  <label htmlFor="billNo" className="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-1">
                    {t.identify.numberInputLabel}
                  </label>
                  <div className="flex flex-col sm:flex-row gap-3">
                    <input
                      id="billNo"
                      type="text"
                      value={billNumberInput}
                      onChange={(e) => setBillNumberInput(e.target.value)}
                      placeholder={t.identify.numberPlaceholder}
                      className="flex-1 px-4 py-3 rounded-xl border border-slate-300 text-base font-semibold text-slate-900 uppercase font-mono"
                    />
                    <button
                      type="submit"
                      disabled={isSearchingBill}
                      className="px-6 py-3 bg-blue-700 hover:bg-blue-800 disabled:opacity-60 text-white font-extrabold rounded-xl text-sm inline-flex items-center justify-center gap-2"
                    >
                      {isSearchingBill ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
                      <span>{t.identify.numberSubmit}</span>
                    </button>
                  </div>
                  {idError && <p className="text-xs text-red-600 font-bold mt-1">{idError}</p>}
                </div>

                {/* Quick Testing Presets */}
                <div className="pt-2">
                  <span className="text-xs font-bold text-slate-400 block mb-1.5">
                    {t.identify.presetExamplesLabel}
                  </span>
                  <div className="flex flex-wrap gap-2 text-xs">
                    {[
                      { code: "BILL-2026-001", label: "Normal Record" },
                      { code: "DISC-2026-902", label: "Discrepancy" },
                      { code: "INC-2026-104", label: "Incomplete" },
                      { code: "NOTFOUND-99", label: "Not Found" },
                      { code: "UNREG-770", label: "Unregistered" },
                    ].map((p) => (
                      <button
                        key={p.code}
                        type="button"
                        onClick={() => {
                          setBillNumberInput(p.code);
                          setTimeout(() => handleFindBill(), 50);
                        }}
                        className="px-2.5 py-1 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold"
                      >
                        {p.label} (<span className="font-mono">{p.code}</span>)
                      </button>
                    ))}
                  </div>
                </div>
              </form>
            ) : (
              /* Upload Tab */
              <div className="space-y-4">
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="image/jpeg,image/png,application/pdf"
                  onChange={handleFileUpload}
                  className="hidden"
                />
                {!uploadedFile ? (
                  <div className="border-2 border-dashed border-slate-300 rounded-2xl p-6 text-center bg-slate-50">
                    <UploadCloud className="w-10 h-10 text-blue-700 mx-auto mb-2" />
                    <p className="text-xs text-slate-500 mb-4">{t.identify.uploadLimits}</p>
                    <button
                      type="button"
                      onClick={() => fileInputRef.current?.click()}
                      className="px-5 py-2.5 bg-blue-700 hover:bg-blue-800 text-white font-bold rounded-xl text-xs"
                    >
                      {t.identify.uploadBrowse}
                    </button>
                  </div>
                ) : (
                  <div className="p-4 border border-slate-200 rounded-xl bg-slate-50 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <File className="w-6 h-6 text-blue-700" />
                      <span className="text-xs font-bold text-slate-800">{uploadedFile.name}</span>
                    </div>
                    <button
                      type="button"
                      onClick={handleScanUpload}
                      disabled={isSearchingBill}
                      className="px-4 py-2 bg-blue-700 text-white font-bold text-xs rounded-xl"
                    >
                      {isSearchingBill ? "Scanning…" : t.identify.uploadSubmit}
                    </button>
                  </div>
                )}
              </div>
            )}

            {/* Result States */}
            {idResultStatus && (
              <div className="p-4 rounded-2xl border animate-fade-up bg-slate-50">
                {idResultStatus === "needs_verification" && (
                  <div className="text-xs sm:text-sm text-blue-900 space-y-2">
                    <strong className="block text-blue-950 font-bold">
                      {t.identify.states.needsVerificationTitle}
                    </strong>
                    <p>{t.identify.states.needsVerificationDesc}</p>
                    <a
                      href="#section-verify"
                      className="inline-flex items-center gap-1.5 px-4 py-2 bg-blue-700 text-white font-bold rounded-xl text-xs"
                    >
                      <KeyRound className="w-3.5 h-3.5" />
                      <span>{t.identify.states.verifyBtn}</span>
                    </a>
                  </div>
                )}

                {idResultStatus === "not_found" && (
                  <div className="text-xs sm:text-sm text-amber-900 space-y-1">
                    <strong className="block font-bold">{t.identify.states.notFoundTitle}</strong>
                    <p>{t.identify.states.notFoundDesc}</p>
                  </div>
                )}

                {idResultStatus === "unregistered_hospital" && (
                  <div className="text-xs sm:text-sm text-slate-800 space-y-1">
                    <strong className="block font-bold">{t.identify.states.unregisteredTitle}</strong>
                    <p>{t.identify.states.unregisteredDesc}</p>
                  </div>
                )}
              </div>
            )}
          </section>

          {/* ── STEP 3: ACCESS CODE VERIFICATION ── */}
          <section id="section-verify" className="bg-white rounded-3xl border border-slate-200/80 shadow-sm p-6 sm:p-10 space-y-5">
            <div className="flex items-center gap-3 pb-4 border-b border-slate-200">
              <div className="w-10 h-10 rounded-xl bg-blue-50 text-blue-700 flex items-center justify-center flex-shrink-0">
                <KeyRound className="w-6 h-6" />
              </div>
              <div>
                <h2 className="text-xl font-extrabold text-slate-900">
                  Step 3: {t.verify.title}
                </h2>
                <p className="text-xs text-slate-500">{t.verify.subtitle}</p>
              </div>
            </div>

            {codeVerified ? (
              <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-2xl flex items-center gap-3 text-emerald-900 font-bold text-sm">
                <CheckCircle2 className="w-6 h-6 text-emerald-700 flex-shrink-0" />
                <span>Access Code Verified Official Record Unlocked.</span>
              </div>
            ) : (
              <form onSubmit={handleVerifyCode} className="space-y-4 max-w-md">
                <div>
                  <label htmlFor="accessCode" className="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-1">
                    {t.verify.inputLabel}
                  </label>
                  <p className="text-xs text-slate-500 mb-2">{t.verify.helperText}</p>
                  <div className="flex gap-2">
                    <input
                      id="accessCode"
                      type="text"
                      disabled={codeLocked}
                      value={accessCode}
                      onChange={(e) => setAccessCode(e.target.value)}
                      placeholder="e.g. HBN-4921"
                      className="flex-1 px-4 py-2.5 rounded-xl border border-slate-300 font-mono font-bold uppercase text-slate-900"
                    />
                    <button
                      type="submit"
                      disabled={isVerifyingCode || codeLocked}
                      className="px-5 py-2.5 bg-blue-700 hover:bg-blue-800 disabled:opacity-50 text-white font-bold text-xs rounded-xl"
                    >
                      {isVerifyingCode ? "Verifying…" : t.verify.submitBtn}
                    </button>
                  </div>
                </div>

                {!codeLocked && (
                  <span className="text-xs text-slate-500 block">
                    {verifyAttempts} {t.verify.attemptsRemaining}
                  </span>
                )}

                {verifyError && (
                  <p className="text-xs text-red-600 font-bold flex items-center gap-1">
                    <XCircle className="w-3.5 h-3.5" />
                    <span>{verifyError}</span>
                  </p>
                )}
                {codeExpired && (
                  <p className="text-xs text-amber-700 font-bold">{t.verify.expiredError}</p>
                )}
              </form>
            )}
          </section>

          {/* ── STEP 4: PERMITTED BILL FINANCIAL SUMMARY ── */}
          <section id="section-bill-summary" className="bg-white rounded-3xl border border-slate-200/80 shadow-sm p-6 sm:p-10 space-y-6">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-200">
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <StatusBadge
                    variant={currentBill.state === "verified" ? "success" : currentBill.state === "discrepancy" ? "warning" : "neutral"}
                    label={currentBill.state === "verified" ? t.bill.verifiedBadge : currentBill.state === "discrepancy" ? t.bill.discrepancyBadge : t.bill.incompleteBadge}
                  />
                  <span className="text-xs font-mono text-slate-500">{currentBill.billNumber}</span>
                </div>
                <h2 className="text-2xl font-black text-slate-900">
                  {currentBill.hospitalName}
                </h2>
                <div className="text-xs text-slate-500 font-medium mt-0.5">
                  Patient: <strong className="text-slate-800">{currentBill.patientName}</strong>
                </div>
              </div>
            </div>

            {/* Discrepancy notice banner if present */}
            {currentBill.discrepancyNotice && (
              <div className="p-4 rounded-2xl bg-amber-50 border border-amber-300 text-amber-950 text-xs sm:text-sm flex items-start gap-3">
                <AlertTriangle className="w-5 h-5 text-amber-700 flex-shrink-0 mt-0.5" />
                <div>
                  <span className="font-bold block mb-0.5">{t.bill.discrepancyAlertTitle}</span>
                  <p>{currentBill.discrepancyNotice}</p>
                </div>
              </div>
            )}

            {/* 4 Financial Metric Cards */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
              <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200">
                <span className="text-xs font-bold uppercase tracking-wider text-slate-500 block mb-1">
                  {t.bill.totalAmountLabel}
                </span>
                <div className="text-xl sm:text-2xl font-black font-mono text-slate-900">
                  ₹ {currentBill.totalAmountInr.toLocaleString("en-IN")}
                </div>
              </div>

              <div className="p-4 rounded-2xl bg-emerald-50/70 border border-emerald-200">
                <span className="text-xs font-bold uppercase tracking-wider text-emerald-800 block mb-1">
                  {t.bill.insuranceLabel}
                </span>
                <div className="text-xl sm:text-2xl font-black font-mono text-emerald-900">
                  - ₹ {currentBill.insuranceCoveredInr.toLocaleString("en-IN")}
                </div>
              </div>

              <div className="p-4 rounded-2xl bg-blue-50/70 border border-blue-200">
                <span className="text-xs font-bold uppercase tracking-wider text-blue-800 block mb-1">
                  {t.bill.paidLabel}
                </span>
                <div className="text-xl sm:text-2xl font-black font-mono text-blue-900">
                  - ₹ {currentBill.paidAmountInr.toLocaleString("en-IN")}
                </div>
              </div>

              <div className="p-4 rounded-2xl bg-slate-900 text-white shadow-md">
                <span className="text-xs font-bold uppercase tracking-wider text-blue-300 block mb-1">
                  {t.bill.patientPayableLabel}
                </span>
                <div className="text-xl sm:text-2xl font-black font-mono text-white">
                  ₹ {currentBill.patientPayableInr.toLocaleString("en-IN")}
                </div>
              </div>
            </div>

            {/* Itemized Line Items */}
            <div className="space-y-2 pt-2">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-500 block mb-1">
                {t.bill.lineItemsTitle}
              </span>
              {currentBill.items.map((item, idx) => (
                <div key={item.id} className="p-3.5 rounded-xl border border-slate-200 bg-white flex justify-between items-center text-xs sm:text-sm">
                  <div>
                    <strong className="text-slate-900 font-extrabold">{item.chargeLabel}</strong>
                    <p className="text-slate-600 text-xs mt-0.5">{item.explanation}</p>
                  </div>
                  <div className="font-mono font-bold text-slate-900 text-right whitespace-nowrap ml-4">
                    ₹ {parseFloat(item.amountInr).toLocaleString("en-IN")}
                  </div>
                </div>
              ))}
            </div>
          </section>

          {/* ── STEP 5: VERIFIED EXPLANATION & AUDIO ── */}
          <section id="section-explanation" className="bg-white rounded-3xl border border-slate-200/80 shadow-sm p-6 sm:p-10 space-y-6">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-slate-200">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-blue-50 text-blue-700 flex items-center justify-center flex-shrink-0">
                  <Sparkles className="w-6 h-6" />
                </div>
                <div>
                  <h2 className="text-xl font-extrabold text-slate-900">
                    Step 5: {t.explanation.title}
                  </h2>
                  <p className="text-xs text-slate-500">{t.explanation.subtitle}</p>
                </div>
              </div>

              {/* Simplify Toggle */}
              <button
                type="button"
                onClick={() => setIsSimplified(!isSimplified)}
                className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-xl text-xs font-bold border transition-colors ${
                  isSimplified ? "bg-emerald-700 text-white border-emerald-700" : "bg-slate-50 text-slate-700 border-slate-300"
                }`}
              >
                {isSimplified ? <ToggleRight className="w-4 h-4 text-emerald-300" /> : <ToggleLeft className="w-4 h-4 text-slate-400" />}
                <span>{isSimplified ? "Simpler 5th-Grade Version" : t.explanation.simplifyToggle}</span>
              </button>
            </div>

            {/* REQUIRED EXACT LABEL */}
            <div className="p-3.5 bg-blue-50 border border-blue-200 rounded-xl text-blue-950 text-xs flex items-start gap-2.5">
              <Info className="w-4 h-4 text-blue-700 flex-shrink-0 mt-0.5" />
              <div>
                <strong className="block text-blue-900">
                  Generated from hospital-provided bill information.
                </strong>
                <span>{explanation.disclaimer}</span>
              </div>
            </div>

            {/* Audio Reader */}
            <AudioPlayer
              textToRead={narrationScript}
              lang={lang}
              labels={{
                listenBtn: t.explanation.listenBtn,
                pauseBtn: t.explanation.pauseBtn,
                resumeBtn: t.explanation.resumeBtn,
                stopBtn: t.explanation.stopBtn,
                audioPlaying: t.explanation.audioPlaying,
                audioUnavailable: t.explanation.audioUnavailable,
              }}
            />

            {/* Plain-Language Text Body */}
            <div className="p-5 bg-slate-50 rounded-2xl border border-slate-200 space-y-4">
              <p className="text-sm sm:text-base text-slate-800 leading-relaxed font-medium">
                {isSimplified ? explanation.simplifiedSummaryText : explanation.summaryText}
              </p>

              <div className="space-y-2 pt-2">
                {explanation.breakdownSections.map((sec, i) => (
                  <div key={i} className="p-3 bg-white rounded-xl border border-slate-200 text-xs sm:text-sm">
                    <strong className="text-slate-900 block mb-0.5">{sec.title}</strong>
                    <span className="text-slate-700">{isSimplified ? sec.simpleDescription : sec.description}</span>
                  </div>
                ))}
              </div>
            </div>
          </section>

          {/* ── STEP 6: VOICE-FIRST & TEXT Q&A ── */}
          <section id="section-questions" className="bg-white rounded-3xl border border-slate-200/80 shadow-sm p-6 sm:p-10 space-y-5">
            <div className="flex items-center gap-3 pb-4 border-b border-slate-200">
              <div className="w-10 h-10 rounded-xl bg-blue-50 text-blue-700 flex items-center justify-center flex-shrink-0">
                <MessageSquare className="w-6 h-6" />
              </div>
              <div>
                <h2 className="text-xl font-extrabold text-slate-900">
                  Step 6: {t.questions.title}
                </h2>
                <p className="text-xs text-slate-500">{t.questions.subtitle}</p>
              </div>
            </div>

            {/* Refusal Notice */}
            <div className="p-3 bg-amber-50 border border-amber-200 rounded-xl text-xs text-amber-900 flex items-center gap-2">
              <ShieldAlert className="w-4 h-4 text-amber-700 flex-shrink-0" />
              <span>{t.questions.refusalNotice}</span>
            </div>

            {/* Example Prompts */}
            <div className="flex flex-wrap gap-2 text-xs">
              {[t.questions.sample1, t.questions.sample2, t.questions.sample3].map((s, idx) => (
                <button
                  key={idx}
                  type="button"
                  onClick={() => handleAskQuestion(s)}
                  className="px-3 py-1.5 rounded-xl bg-slate-100 hover:bg-blue-50 text-slate-700 font-semibold border border-slate-200 text-left"
                >
                  &ldquo;{s}&rdquo;
                </button>
              ))}
            </div>

            {/* Chat Log */}
            <div className="border border-slate-200 rounded-2xl p-4 bg-slate-50/70 max-h-80 overflow-y-auto space-y-3">
              {chatMessages.map((m) => (
                <div key={m.id} className={`flex flex-col ${m.role === "user" ? "items-end" : "items-start"}`}>
                  <div
                    className={`max-w-[85%] p-3.5 rounded-2xl text-xs sm:text-sm leading-relaxed ${
                      m.role === "user"
                        ? "bg-blue-700 text-white font-medium"
                        : m.isRefusal
                        ? "bg-amber-100 text-amber-950 border border-amber-300 font-medium"
                        : "bg-white text-slate-900 border border-slate-200"
                    }`}
                  >
                    <p>{m.content}</p>
                  </div>
                </div>
              ))}
            </div>

            {/* Voice Input */}
            <VoiceInput
              lang={lang}
              onConfirmText={(spoken) => handleAskQuestion(spoken)}
              labels={{
                voiceBtnStart: t.questions.voiceBtnStart,
                voiceBtnStop: t.questions.voiceBtnStop,
                voiceListening: t.questions.voiceListening,
                voiceReviewLabel: t.questions.voiceReviewLabel,
                voiceEditHint: t.questions.voiceEditHint,
                voiceConfirmBtn: t.questions.voiceConfirmBtn,
                voiceUnavailable: t.questions.voiceUnavailable,
              }}
            />

            {/* Text Input */}
            <form
              onSubmit={(e) => {
                e.preventDefault();
                handleAskQuestion(questionText);
              }}
              className="flex gap-2"
            >
              <input
                type="text"
                value={questionText}
                onChange={(e) => setQuestionText(e.target.value)}
                placeholder={t.questions.placeholder}
                className="flex-1 px-4 py-2.5 rounded-xl border border-slate-300 text-xs sm:text-sm text-slate-900"
              />
              <button
                type="submit"
                disabled={!questionText.trim()}
                className="px-5 py-2.5 bg-blue-700 hover:bg-blue-800 disabled:opacity-50 text-white font-bold text-xs rounded-xl inline-flex items-center gap-1.5"
              >
                <span>{t.questions.submitBtn}</span>
                <Send className="w-3.5 h-3.5" />
              </button>
            </form>
          </section>

          {/* ── STEP 7: REQUEST HUMAN ASSISTANCE ── */}
          <section id="section-help" className="bg-white rounded-3xl border border-slate-200/80 shadow-sm p-6 sm:p-10 space-y-5">
            <div className="flex items-center gap-3 pb-4 border-b border-slate-200">
              <div className="w-10 h-10 rounded-xl bg-teal-50 text-teal-700 flex items-center justify-center flex-shrink-0">
                <PhoneCall className="w-6 h-6" />
              </div>
              <div>
                <h2 className="text-xl font-extrabold text-slate-900">
                  Step 7: {t.help.title}
                </h2>
                <p className="text-xs text-slate-500">{t.help.subtitle}</p>
              </div>
            </div>

            {supportRefId ? (
              <div className="p-6 bg-emerald-50 border-2 border-emerald-300 rounded-2xl text-center space-y-2 animate-fade-up">
                <CheckCircle2 className="w-8 h-8 text-emerald-700 mx-auto" />
                <h3 className="font-extrabold text-lg text-emerald-950">{t.help.successTitle}</h3>
                <p className="text-xs text-emerald-800">{t.help.successMessage}</p>
                <div className="font-mono font-black text-2xl text-emerald-900 py-1">{supportRefId}</div>
                <p className="text-xs text-amber-800 italic">{t.help.demoNote}</p>
              </div>
            ) : (
              <form onSubmit={handleSupportSubmit} className="space-y-4 max-w-xl">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                  <div>
                    <label className="font-bold text-slate-700 block mb-1">{t.help.patientNameLabel} *</label>
                    <input
                      type="text"
                      value={supportName}
                      onChange={(e) => setSupportName(e.target.value)}
                      className="w-full p-2.5 rounded-xl border border-slate-300 text-sm font-semibold"
                    />
                    {supportErrors.patientName && <p className="text-xs text-red-600 mt-1">{supportErrors.patientName}</p>}
                  </div>

                  <div>
                    <label className="font-bold text-slate-700 block mb-1">{t.help.contactLabel} *</label>
                    <input
                      type="tel"
                      value={supportPhone}
                      onChange={(e) => setSupportPhone(e.target.value)}
                      className="w-full p-2.5 rounded-xl border border-slate-300 text-sm font-semibold"
                    />
                    {supportErrors.contactNumber && <p className="text-xs text-red-600 mt-1">{supportErrors.contactNumber}</p>}
                  </div>
                </div>

                <div>
                  <label className="font-bold text-slate-700 block text-xs mb-1">{t.help.callbackTimeLabel}</label>
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
                    {(["now", "morning", "afternoon", "evening"] as CallbackWindow[]).map((time) => (
                      <button
                        key={time}
                        type="button"
                        onClick={() => setSupportCallback(time)}
                        className={`p-2 rounded-xl border font-bold capitalize transition-colors ${
                          supportCallback === time ? "bg-teal-700 text-white border-teal-700" : "bg-slate-50 text-slate-700 border-slate-300"
                        }`}
                      >
                        {time}
                      </button>
                    ))}
                  </div>
                </div>

                <div>
                  <label className="font-bold text-slate-700 block text-xs mb-1">{t.help.reasonLabel} *</label>
                  <textarea
                    rows={2}
                    value={supportReason}
                    onChange={(e) => setSupportReason(e.target.value)}
                    className="w-full p-2.5 rounded-xl border border-slate-300 text-xs sm:text-sm text-slate-900"
                  />
                  {supportErrors.reason && <p className="text-xs text-red-600 mt-1">{supportErrors.reason}</p>}
                </div>

                <div className="pt-1">
                  <label className="flex items-start gap-2 cursor-pointer text-xs text-slate-700">
                    <input
                      type="checkbox"
                      checked={supportConsent}
                      onChange={(e) => setSupportConsent(e.target.checked)}
                      className="mt-0.5 rounded border-slate-300 text-teal-700"
                    />
                    <span>{t.help.consentCheckboxLabel}</span>
                  </label>
                  {supportErrors.consentGiven && <p className="text-xs text-red-600 mt-1">{supportErrors.consentGiven}</p>}
                </div>

                <button
                  type="submit"
                  disabled={supportSubmitting}
                  className="w-full py-3.5 bg-teal-700 hover:bg-teal-800 disabled:opacity-50 text-white font-extrabold rounded-2xl text-sm"
                >
                  {supportSubmitting ? "Submitting…" : t.help.submitBtn}
                </button>
              </form>
            )}
          </section>
        </main>
      )}

      {/* ─────────────────────────────────────────────────────────────
          VIEW 2: CAREGIVER SUMMARY ("What You Need to Know")
         ───────────────────────────────────────────────────────────── */}
      {activeView === "caregiver" && (
        <main className="flex-1 max-w-4xl mx-auto w-full px-4 sm:px-6 py-8 md:py-12">
          <div className="bg-white rounded-3xl border border-slate-200/80 shadow-sm p-6 sm:p-10 space-y-8">
            <div className="pb-4 border-b border-slate-200">
              <span className="text-xs font-bold uppercase tracking-wider text-teal-700 block mb-1">
                Authorized Caregiver View
              </span>
              <h1 className="text-3xl font-black text-slate-900">{t.caregiver.title}</h1>
              <p className="text-xs sm:text-sm text-slate-600 mt-1">{t.caregiver.subtitle}</p>
            </div>

            {/* Essential Numbers */}
            <div>
              <span className="text-xs font-bold uppercase tracking-wider text-slate-500 block mb-2">
                {t.caregiver.billSummaryTitle}
              </span>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <div className="p-4 rounded-xl bg-slate-50 border border-slate-200">
                  <span className="text-xs text-slate-500 block">Total Hospital Bill</span>
                  <div className="text-xl font-black font-mono">₹ {currentBill.totalAmountInr.toLocaleString("en-IN")}</div>
                </div>
                <div className="p-4 rounded-xl bg-emerald-50 border border-emerald-200">
                  <span className="text-xs text-emerald-800 block">Insurance Paid</span>
                  <div className="text-xl font-black font-mono text-emerald-900">₹ {currentBill.insuranceCoveredInr.toLocaleString("en-IN")}</div>
                </div>
                <div className="p-4 rounded-xl bg-teal-50 border border-teal-200">
                  <span className="text-xs text-teal-800 block">Patient Payable</span>
                  <div className="text-xl font-black font-mono text-teal-950">₹ {currentBill.patientPayableInr.toLocaleString("en-IN")}</div>
                </div>
              </div>
            </div>

            {/* Financial Terms */}
            <div>
              <span className="text-xs font-bold uppercase tracking-wider text-slate-500 block mb-2">
                {t.caregiver.financialTermsTitle}
              </span>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
                <div className="p-3.5 rounded-xl border border-slate-200 bg-white">
                  <strong className="block text-slate-900 mb-1">Co-Payment (सह-भुगतान)</strong>
                  <p className="text-slate-600">Fixed percentage patient pays out-of-pocket for each service.</p>
                </div>
                <div className="p-3.5 rounded-xl border border-slate-200 bg-white">
                  <strong className="block text-slate-900 mb-1">Room Sub-Limit</strong>
                  <p className="text-slate-600">Daily room rent ceiling covered by the insurer.</p>
                </div>
                <div className="p-3.5 rounded-xl border border-slate-200 bg-white">
                  <strong className="block text-slate-900 mb-1">Consumables</strong>
                  <p className="text-slate-600">Surgical gloves and kits often excluded by insurance.</p>
                </div>
              </div>
            </div>

            {/* Next Steps */}
            <div>
              <span className="text-xs font-bold uppercase tracking-wider text-slate-500 block mb-2">
                {t.caregiver.nextStepsTitle}
              </span>
              <ul className="space-y-2 text-xs sm:text-sm text-slate-700">
                <li className="flex items-center gap-2 p-3 bg-emerald-50/70 rounded-xl border border-emerald-200">
                  <CheckCircle2 className="w-4 h-4 text-emerald-700 flex-shrink-0" />
                  <span>{t.caregiver.nextStep1}</span>
                </li>
                <li className="flex items-center gap-2 p-3 bg-emerald-50/70 rounded-xl border border-emerald-200">
                  <CheckCircle2 className="w-4 h-4 text-emerald-700 flex-shrink-0" />
                  <span>{t.caregiver.nextStep2}</span>
                </li>
                <li className="flex items-center gap-2 p-3 bg-emerald-50/70 rounded-xl border border-emerald-200">
                  <CheckCircle2 className="w-4 h-4 text-emerald-700 flex-shrink-0" />
                  <span>{t.caregiver.nextStep3}</span>
                </li>
              </ul>
            </div>
          </div>
        </main>
      )}

      {/* ─────────────────────────────────────────────────────────────
          VIEW 3: SUPPORT WORKER DASHBOARD
         ───────────────────────────────────────────────────────────── */}
      {activeView === "support" && (
        <main className="flex-1 max-w-7xl mx-auto w-full px-4 sm:px-6 lg:px-8 py-8 md:py-12 space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div>
              <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-amber-100 text-amber-900 border border-amber-300">
                {t.supportDashboard.demoBadge}
              </span>
              <h1 className="text-2xl sm:text-3xl font-black text-slate-900 tracking-tight mt-1">
                {t.supportDashboard.title}
              </h1>
              <p className="text-xs sm:text-sm text-slate-600">{t.supportDashboard.subtitle}</p>
            </div>
          </div>

          {/* Search and Filters */}
          <div className="p-3 bg-white rounded-2xl border border-slate-200 flex flex-wrap items-center justify-between gap-3">
            <input
              type="text"
              value={ticketSearch}
              onChange={(e) => setTicketSearch(e.target.value)}
              placeholder={t.supportDashboard.searchPlaceholder}
              className="px-3.5 py-2 rounded-xl border border-slate-300 text-xs sm:text-sm w-full sm:w-80"
            />
            <div className="flex flex-wrap gap-1 text-xs">
              {["All", "New", "Callback scheduled", "Contacted", "Resolved"].map((f) => (
                <button
                  key={f}
                  type="button"
                  onClick={() => setTicketFilter(f)}
                  className={`px-3 py-1.5 rounded-xl font-bold border transition-colors ${
                    ticketFilter === f ? "bg-slate-900 text-white border-slate-900" : "bg-slate-50 text-slate-700 border-slate-200"
                  }`}
                >
                  {f === "All" ? t.supportDashboard.filterAll : f}
                </button>
              ))}
            </div>
          </div>

          {/* Master-Detail 2-Column */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            {/* Ticket List */}
            <div className="lg:col-span-5 space-y-2">
              {tickets
                .filter(
                  (t) =>
                    (ticketFilter === "All" || t.status === ticketFilter) &&
                    (t.patientName.toLowerCase().includes(ticketSearch.toLowerCase()) ||
                      t.billNumber.toLowerCase().includes(ticketSearch.toLowerCase()))
                )
                .map((ticket) => (
                  <div
                    key={ticket.ticketId}
                    onClick={() => setSelectedTicketId(ticket.ticketId)}
                    className={`p-4 rounded-2xl border cursor-pointer transition-all ${
                      activeTicket.ticketId === ticket.ticketId
                        ? "bg-blue-50/80 border-blue-400 ring-2 ring-blue-600/20"
                        : "bg-white border-slate-200 hover:bg-slate-50"
                    }`}
                  >
                    <div className="flex justify-between items-center mb-1">
                      <span className="text-xs font-mono font-bold text-slate-500">{ticket.referenceId}</span>
                      <StatusBadge variant={getStatusBadge(ticket.status)} label={ticket.status} size="sm" />
                    </div>
                    <div className="font-extrabold text-slate-900 text-sm">{ticket.patientName}</div>
                    <p className="text-xs text-slate-600 line-clamp-1 mt-1">{ticket.patientNote}</p>
                  </div>
                ))}
            </div>

            {/* Ticket Details */}
            <div className="lg:col-span-7 bg-white rounded-3xl border border-slate-200 p-6 space-y-4">
              <div className="flex justify-between items-start pb-4 border-b border-slate-200">
                <div>
                  <span className="text-xs font-mono text-slate-500">{activeTicket.referenceId}</span>
                  <h2 className="text-xl font-black text-slate-900">{activeTicket.patientName}</h2>
                  <div className="text-xs text-slate-500 font-mono">Bill #{activeTicket.billNumber}</div>
                </div>
                <div className="flex flex-wrap gap-1">
                  {(["New", "Callback scheduled", "Contacted", "Resolved"] as TicketStatus[]).map((st) => (
                    <button
                      key={st}
                      type="button"
                      onClick={() => handleTicketStatusChange(st)}
                      className={`px-2.5 py-1 rounded-lg text-xs font-bold border ${
                        activeTicket.status === st ? "bg-blue-700 text-white border-blue-700" : "bg-slate-50 text-slate-700 border-slate-200"
                      }`}
                    >
                      {st}
                    </button>
                  ))}
                </div>
              </div>

              <div className="p-3.5 bg-slate-50 rounded-xl text-xs space-y-1">
                <div><strong>Phone:</strong> {activeTicket.contactNumber}</div>
                <div><strong>Callback Window:</strong> {activeTicket.preferredCallbackTime}</div>
                <div><strong>Reason:</strong> &ldquo;{activeTicket.patientNote}&rdquo;</div>
              </div>

              {/* Staff Notes */}
              <div>
                <span className="text-xs font-bold text-slate-500 block mb-1">Staff Notes</span>
                <div className="space-y-1.5 mb-3">
                  {activeTicket.staffNotes?.map((n, i) => (
                    <div key={i} className="text-xs p-2.5 bg-slate-50 border border-slate-200 rounded-lg">{n}</div>
                  ))}
                </div>
                <form onSubmit={handleAddStaffNote} className="flex gap-2">
                  <input
                    type="text"
                    value={staffNoteInput}
                    onChange={(e) => setStaffNoteInput(e.target.value)}
                    placeholder="Add staff note…"
                    className="flex-1 p-2 rounded-lg border border-slate-300 text-xs"
                  />
                  <button type="submit" className="px-3 py-2 bg-blue-700 text-white font-bold text-xs rounded-lg">
                    Add Note
                  </button>
                </form>
              </div>
            </div>
          </div>
        </main>
      )}

      <Footer />
    </div>
  );
}
