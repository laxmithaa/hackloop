"use client";

import React, { useState } from "react";
import Link from "next/link";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import DemoNotice from "@/components/DemoNotice";
import VoiceInput from "@/components/VoiceInput";
import { useLanguage } from "@/lib/context/LanguageContext";
import {
  MessageSquare,
  Send,
  HelpCircle,
  PhoneCall,
  ArrowLeft,
  AlertCircle,
  RefreshCw,
  CheckCircle2,
  ShieldAlert,
} from "lucide-react";
import type { ChatMessage } from "@/lib/types/billing";

export default function QuestionsPage() {
  const { t, lang, currentBill } = useLanguage();

  const [questionInput, setQuestionInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: "msg-0",
      role: "assistant",
      content:
        lang === "hi"
          ? `नमस्ते! मैं आपके ${currentBill.hospitalName} बिल (कुल राशि: ₹ ${currentBill.totalAmountInr.toLocaleString("en-IN")}) के बारे में सहायता कर सकता हूँ। किसी भी शुल्क या टेस्ट के बारे में पूछें।`
          : lang === "kn"
          ? `ನಮಸ್ಕಾರ! ನಾನು ನಿಮ್ಮ ${currentBill.hospitalName} ಬಿಲ್ (ಒಟ್ಟು ಮೊತ್ತ: ₹ ${currentBill.totalAmountInr.toLocaleString("en-IN")}) ಬಗ್ಗೆ ಸಹಾಯ ಮಾಡಬಲ್ಲೆ. ಯಾವುದೇ ಶುಲ್ಕದ ಬಗ್ಗೆ ಕೇಳಿ.`
          : `Hello! I can help clarify charges on your ${currentBill.hospitalName} statement (Total: ₹ ${currentBill.totalAmountInr.toLocaleString("en-IN")}). Ask about any test, doctor fee, or payment term.`,
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    },
  ]);

  const handleAsk = (query: string) => {
    if (!query.trim() || isLoading) return;

    const userMsg: ChatMessage = {
      id: `usr-${Date.now()}`,
      role: "user",
      content: query.trim(),
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    };

    setMessages((prev) => [...prev, userMsg]);
    setQuestionInput("");
    setIsLoading(true);

    // Simulate smart contextual response & medical boundary enforcement
    setTimeout(() => {
      setIsLoading(false);
      const lower = query.toLowerCase();

      // Check if question asks for medical advice / diagnosis (refusal requirement)
      if (
        lower.includes("cancer") ||
        lower.includes("tumor") ||
        lower.includes("cure") ||
        lower.includes("disease") ||
        lower.includes("medicine dose") ||
        lower.includes("treatment work") ||
        lower.includes("symptom")
      ) {
        setMessages((prev) => [
          ...prev,
          {
            id: `asst-${Date.now()}`,
            role: "assistant",
            content:
              lang === "hi"
                ? "चिकित्सीय अस्वीकरण: मैं केवल अस्पताल के बिल, शुल्कों और वित्तीय नियमों की व्याख्या कर सकता हूँ। किसी बीमारी के निदान, इलाज या दवा की खुराक के लिए कृपया अपने डॉक्टर या अस्पताल स्टाफ़ से संपर्क करें।"
                : lang === "kn"
                ? "ವೈದ್ಯಕೀಯ ಮಿತಿ: ನಾನು ಕೇವಲ ಆಸ್ಪತ್ರೆ ಬಿಲ್ ಶುಲ್ಕಗಳು ಮತ್ತು ಹಣಕಾಸಿನ ನಿಯಮಗಳನ್ನು ಮಾತ್ರ ವಿವರಿಸಬಲ್ಲೆ. ಚಿಕಿತ್ಸೆ, ರೋಗನಿರ್ಣಯ ಅಥವಾ ಔಷಧಿಗಳ ಪ್ರಮಾಣಕ್ಕಾಗಿ ದಯವಿಟ್ಟು ನಿಮ್ಮ ವೈದ್ಯರನ್ನು ಸಂಪರ್ಕಿಸಿ."
                : "Medical Scope Notice: I can only explain hospital billing terms, insurance deductions, and financial charges. For questions about your medical condition, diagnosis, or treatment decisions, please consult your doctor directly.",
            timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
            isRefusal: true,
          },
        ]);
        return;
      }

      // Contextual billing answers
      let reply = "";
      if (lower.includes("consultation") || lower.includes("कंसल्टेशन") || lower.includes("ಕನ್ಸಲ್ಟೇಶನ್")) {
        reply =
          lang === "hi"
            ? "कंसल्टेशन फ़ीस (₹ 800) अस्पताल में आपके उपस्थित डॉक्टर द्वारा आपकी जांच करने, रिपोर्ट देखने और चिकित्सीय सलाह देने का आधिकारिक शुल्क है।"
            : lang === "kn"
            ? "ಕನ್ಸಲ್ಟೇಶನ್ ಶುಲ್ಕ (₹ 800) ಎಂದರೆ ವೈದ್ಯರು ನಿಮ್ಮನ್ನು ತಪಾಸಣೆ ಮಾಡಿ, ವರದಿಗಳನ್ನು ನೋಡಿ ನೀಡಿದ ವೈದ್ಯಕೀಯ ಸಲಹೆಯ ಅಧಿಕೃತ ಶುಲ್ಕವಾಗಿದೆ."
            : "The Consultation Fee (₹ 800) is the doctor's fee for reviewing your symptoms, evaluating diagnostic reports, and managing your hospital care plan.";
      } else if (lower.includes("x-ray") || lower.includes("एक्स-रे") || lower.includes("ಎಕ್ಸ್‌ರೇ")) {
        reply =
          lang === "hi"
            ? "चेस्ट एक्स-रे (₹ 1,200) एक रेडियोलॉजी जांच है जिसमें फेफड़ों और हृदय की स्पष्ट तस्वीर ली जाती है। यह शुल्क इमेजिंग उपकरण और रेडियोलॉजिस्ट की रिपोर्टिंग दोनों को शामिल करता है।"
            : lang === "kn"
            ? "ಎದೆಯ ಎಕ್ಸ್‌ರೇ (₹ 1,200) ಎನ್ನುವುದು ಶ್ವಾಸಕೋಶ ಮತ್ತು ಹೃದಯದ ಸ್ಥಿತಿಯನ್ನು ಪರೀಕ್ಷಿಸಲು ತೆಗೆದ ಚಿತ್ರ ಸ್ಕ್ಯಾನ್ ಆಗಿದೆ."
            : "The Chest X-Ray (₹ 1,200) is a standard imaging scan taken to verify lung clarity and rule out infection. It covers both the radiologic technician and specialist doctor's report.";
      } else if (lower.includes("installment") || lower.includes("किस्त") || lower.includes("ಕಂತು")) {
        reply =
          lang === "hi"
            ? "हाँ, अधिकांश अस्पताल मरीज़ के देय हिस्से (₹ 800) के लिए 3 से 6 महीने की ब्याज-मुक्त किस्त योजना प्रदान करते हैं। आप अस्पताल के वित्तीय सलाहकार या हमारे सहायता कार्यकर्ता से बात कर सकते हैं।"
            : lang === "kn"
            ? "ಹೌದು, ಆಸ್ಪತ್ರೆಯು ರೋಗಿ ಪಾವತಿಸಬೇಕಾದ ಮೊತ್ತಕ್ಕೆ ಕಂತುಗಳ ಸೌಲಭ್ಯವನ್ನು ನೀಡುತ್ತದೆ. ಆಸ್ಪತ್ರೆ ಸಹಾಯಕರನ್ನು ಸಂಪರ್ಕಿಸಲು ಕೆಳಗಿನ ಲಿಂಕ್ ಬಳಸಿ."
            : "Yes, most registered hospitals allow patients to split their payable share into monthly installments. You can submit a callback request using the Human Support button below to set up an installment arrangement.";
      } else {
        reply =
          lang === "hi"
            ? `आपके बिल नंबर ${currentBill.billNumber} के अनुसार, कुल अस्पताल शुल्क ₹ ${currentBill.totalAmountInr.toLocaleString("en-IN")} है, जिसमें से ₹ ${currentBill.insuranceCoveredInr.toLocaleString("en-IN")} बीमा द्वारा घटाए गए हैं। अधिक जानकारी के लिए अस्पताल बिलिंग डेस्क से संपर्क किया जा सकता है।`
            : lang === "kn"
            ? `ನಿಮ್ಮ ಬಿಲ್ ಸಂಖ್ಯೆ ${currentBill.billNumber} ಪ್ರಕಾರ ಒಟ್ಟು ಶುಲ್ಕ ₹ ${currentBill.totalAmountInr.toLocaleString("en-IN")}. ಇದರಲ್ಲಿ ₹ ${currentBill.insuranceCoveredInr.toLocaleString("en-IN")} ವಿಮೆಯಿಂದ ಕಡಿತವಾಗಿದೆ.`
            : `According to record #${currentBill.billNumber}, your gross charges total ₹ ${currentBill.totalAmountInr.toLocaleString("en-IN")} with ₹ ${currentBill.insuranceCoveredInr.toLocaleString("en-IN")} covered by insurance. If this item requires revision, you may request a billing clerk callback below.`;
      }

      setMessages((prev) => [
        ...prev,
        {
          id: `asst-${Date.now()}`,
          role: "assistant",
          content: reply,
          timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        },
      ]);
    }, 700);
  };

  return (
    <div className="min-h-screen flex flex-col bg-[#f8fafc]">
      <DemoNotice />
      <Navbar />

      <main className="flex-1 max-w-4xl mx-auto w-full px-4 sm:px-6 py-8 md:py-12">
        {/* Navigation Breadcrumb */}
        <div className="mb-6 flex items-center justify-between">
          <Link
            href="/patient/explanation"
            className="inline-flex items-center gap-1.5 text-xs sm:text-sm font-bold text-slate-600 hover:text-slate-900 transition-colors touch-target"
          >
            <ArrowLeft className="w-4 h-4" />
            <span>Back to Explanation</span>
          </Link>

          <span className="text-xs font-bold uppercase tracking-wider text-slate-500">
            Bill Q&A Assistant
          </span>
        </div>

        <div className="bg-white rounded-3xl border border-slate-200/80 shadow-sm p-6 sm:p-10 space-y-6">
          {/* Header */}
          <div className="border-b border-slate-200 pb-5">
            <h1 className="text-2xl sm:text-3xl font-black text-slate-900 tracking-tight flex items-center gap-2.5">
              <MessageSquare className="w-7 h-7 text-blue-700" />
              <span>{t.questions.title}</span>
            </h1>
            <p className="text-sm text-slate-600 mt-1">
              {t.questions.subtitle}
            </p>
          </div>

          {/* Scope Refusal Reminder */}
          <div className="p-3 bg-amber-50 border border-amber-200 rounded-xl text-xs text-amber-900 flex items-start gap-2">
            <ShieldAlert className="w-4 h-4 text-amber-700 flex-shrink-0 mt-0.5" />
            <span>{t.questions.refusalNotice}</span>
          </div>

          {/* Example Questions (Clickable chips) */}
          <div>
            <span className="block text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">
              {t.questions.examplesLabel}
            </span>
            <div className="flex flex-wrap gap-2">
              {[t.questions.sample1, t.questions.sample2, t.questions.sample3].map((sample, idx) => (
                <button
                  key={idx}
                  type="button"
                  onClick={() => handleAsk(sample)}
                  className="px-3.5 py-2 bg-slate-100 hover:bg-blue-50 hover:text-blue-700 hover:border-blue-200 border border-slate-200 rounded-xl text-xs font-semibold text-slate-800 transition-all text-left"
                >
                  &ldquo;{sample}&rdquo;
                </button>
              ))}
            </div>
          </div>

          {/* ── Conversation History Display ── */}
          <div
            role="log"
            aria-label="Question and Answer History"
            className="border border-slate-200 rounded-2xl p-4 sm:p-6 bg-slate-50/70 min-h-[300px] max-h-[500px] overflow-y-auto space-y-4"
          >
            {messages.length === 0 && (
              <p className="text-center text-slate-400 text-sm py-12">
                {t.questions.emptyHistory}
              </p>
            )}

            {messages.map((msg) => (
              <div
                key={msg.id}
                className={`flex flex-col ${msg.role === "user" ? "items-end" : "items-start"}`}
              >
                <div
                  className={`max-w-[85%] rounded-2xl p-4 text-sm sm:text-base leading-relaxed ${
                    msg.role === "user"
                      ? "bg-blue-700 text-white font-medium rounded-br-sm"
                      : msg.isRefusal
                      ? "bg-amber-100 text-amber-950 border border-amber-300 font-medium rounded-bl-sm"
                      : "bg-white text-slate-900 border border-slate-200 shadow-sm rounded-bl-sm font-normal"
                  }`}
                >
                  <div className="text-xs font-bold opacity-70 mb-1 flex items-center justify-between gap-4">
                    <span>{msg.role === "user" ? "You asked:" : "Billing Explanation:"}</span>
                    <span>{msg.timestamp}</span>
                  </div>
                  <p>{msg.content}</p>
                </div>
              </div>
            ))}

            {isLoading && (
              <div className="flex items-center gap-2 text-slate-500 text-xs font-bold p-3 bg-white rounded-xl border border-slate-200 w-fit">
                <RefreshCw className="w-4 h-4 animate-spin text-blue-700" />
                <span>Checking hospital billing guidelines…</span>
              </div>
            )}
          </div>

          {/* ── Phase 11: Voice-First Input Component ── */}
          <VoiceInput
            lang={lang}
            onConfirmText={(spoken) => handleAsk(spoken)}
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

          {/* ── Standard Text Input Alternative (Never mandatory to speak) ── */}
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleAsk(questionInput);
            }}
            className="flex flex-col sm:flex-row gap-3 pt-2"
          >
            <div className="flex-1">
              <label htmlFor="question-input-field" className="sr-only">
                {t.questions.inputLabel}
              </label>
              <input
                id="question-input-field"
                type="text"
                value={questionInput}
                onChange={(e) => setQuestionInput(e.target.value)}
                placeholder={t.questions.placeholder}
                disabled={isLoading}
                className="w-full px-4 py-3.5 rounded-xl border border-slate-300 text-sm sm:text-base text-slate-900 bg-white placeholder-slate-400 focus-visible:ring-4 focus-visible:ring-blue-600/20 touch-target"
              />
            </div>
            <button
              type="submit"
              disabled={isLoading || !questionInput.trim()}
              className="inline-flex items-center justify-center gap-2 px-6 py-3.5 bg-blue-700 hover:bg-blue-800 disabled:opacity-50 text-white font-extrabold rounded-xl text-sm shadow-sm transition-all touch-target"
            >
              <span>{t.questions.submitBtn}</span>
              <Send className="w-4 h-4" />
            </button>
          </form>

          {/* Human Support Option Notice */}
          <div className="pt-4 border-t border-slate-100 flex flex-col sm:flex-row items-center justify-between gap-3 text-xs text-slate-500">
            <span>
              Unsure if a charge is wrong? A hospital patient advocate can investigate.
            </span>
            <Link
              href="/patient/help"
              className="font-bold text-teal-800 hover:text-teal-900 inline-flex items-center gap-1.5 whitespace-nowrap"
            >
              <PhoneCall className="w-3.5 h-3.5" />
              <span>{t.nav.seekHelpBtn}</span>
            </Link>
          </div>
        </div>
      </main>

      <Footer />
    </div>
  );
}
