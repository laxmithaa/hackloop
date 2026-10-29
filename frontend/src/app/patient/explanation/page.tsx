"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import DemoNotice from "@/components/DemoNotice";
import AudioPlayer from "@/components/AudioPlayer";
import { useLanguage } from "@/lib/context/LanguageContext";
import {
  Sparkles,
  ArrowLeft,
  MessageSquare,
  PhoneCall,
  Volume2,
  ToggleLeft,
  ToggleRight,
  ShieldAlert,
  Info,
  CheckCircle2,
  FileText,
  RefreshCw,
  Globe,
} from "lucide-react";
import { getMockExplanation } from "@/lib/services/mockData";
import type { Lang } from "@/lib/types/billing";

export default function ExplanationPage() {
  const router = useRouter();
  const { t, lang, setLang, currentBill } = useLanguage();

  const [isSimplified, setIsSimplified] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [isUnavailable, setIsUnavailable] = useState(false);

  const explanation = getMockExplanation(currentBill, lang);

  // Build the complete voice narration transcript
  const narrationText = isSimplified
    ? `${explanation.heading}. ${explanation.simplifiedSummaryText} ${explanation.breakdownSections
        .map((s) => `${s.title}: ${s.simpleDescription}`)
        .join(". ")}`
    : `${explanation.heading}. ${explanation.summaryText} ${explanation.breakdownSections
        .map((s) => `${s.title}: ${s.description}`)
        .join(". ")}`;

  const handleRetry = () => {
    setIsLoading(true);
    setIsUnavailable(false);
    setTimeout(() => {
      setIsLoading(false);
    }, 600);
  };

  return (
    <div className="min-h-screen flex flex-col bg-[#f8fafc]">
      <DemoNotice />
      <Navbar />

      <main className="flex-1 max-w-4xl mx-auto w-full px-4 sm:px-6 py-8 md:py-12">
        {/* Step Indicator & Back Navigation */}
        <div className="mb-6 flex items-center justify-between">
          <button
            type="button"
            onClick={() => router.push("/patient/bill")}
            className="inline-flex items-center gap-1.5 text-xs sm:text-sm font-bold text-slate-600 hover:text-slate-900 transition-colors touch-target"
          >
            <ArrowLeft className="w-4 h-4" />
            <span>{t.explanation.backToBillBtn}</span>
          </button>

          <span className="text-xs font-bold uppercase tracking-wider text-blue-700">
            {lang === "hi"
              ? "चरण 5 का 5 · सरल व्याख्या"
              : lang === "kn"
              ? "ಹಂತ 5 / 5 · ಸರಳ ವಿವರಣೆ"
              : "Step 5 of 5 · Plain Explanation"}
          </span>
        </div>

        {/* Main Card */}
        <div className="bg-white rounded-3xl border border-slate-200/80 shadow-sm p-6 sm:p-10 space-y-8">
          {/* Top Bar: Title & Language Selector */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-slate-200">
            <div>
              <div className="flex items-center gap-2 mb-2">
                <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-extrabold bg-blue-50 text-blue-800 border border-blue-200">
                  <Sparkles className="w-3.5 h-3.5 text-blue-600" />
                  <span>{explanation.isAiGenerated ? t.explanation.aiBadge : t.explanation.templateBadge}</span>
                </span>
                <span className="text-xs text-slate-500 font-mono">
                  {currentBill.billNumber}
                </span>
              </div>
              <h1 className="text-2xl sm:text-3xl font-black text-slate-900 tracking-tight">
                {explanation.heading}
              </h1>
              <p className="text-xs sm:text-sm text-slate-500 mt-0.5">
                {currentBill.hospitalName} · Patient: {currentBill.patientName}
              </p>
            </div>

            {/* In-page Language Selector */}
            <div className="flex items-center gap-2 bg-slate-100 p-1.5 rounded-2xl border border-slate-200 self-start sm:self-auto">
              <Globe className="w-4 h-4 text-slate-500 ml-1" />
              {(["en", "hi", "kn"] as Lang[]).map((code) => (
                <button
                  key={code}
                  type="button"
                  onClick={() => setLang(code)}
                  className={`px-3 py-1.5 rounded-xl text-xs font-bold transition-all ${
                    lang === code
                      ? "bg-blue-700 text-white shadow-sm"
                      : "text-slate-600 hover:text-slate-900"
                  }`}
                >
                  {code === "en" ? "English" : code === "hi" ? "हिंदी" : "ಕನ್ನಡ"}
                </button>
              ))}
            </div>
          </div>

          {/* ── REQUIRED EXACT INFORMATION LABEL ── */}
          <div
            role="note"
            className="p-4 rounded-2xl bg-blue-50 border border-blue-200 text-blue-950 text-xs sm:text-sm flex items-start gap-3"
          >
            <Info className="w-5 h-5 text-blue-700 flex-shrink-0 mt-0.5" />
            <div className="space-y-1">
              <div className="font-extrabold tracking-wide text-blue-900">
                Generated from hospital-provided bill information.
              </div>
              <p className="text-blue-800 text-xs leading-relaxed">
                {explanation.disclaimer}
              </p>
            </div>
          </div>

          {/* ── Phase 10: Simplify Explanation Control ── */}
          <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div>
              <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                <span>{t.explanation.simplifyToggle}</span>
                {isSimplified && (
                  <span className="text-xs bg-emerald-100 text-emerald-800 font-bold px-2 py-0.5 rounded-full">
                    Active
                  </span>
                )}
              </h3>
              <p className="text-xs text-slate-600 mt-0.5">
                {isSimplified
                  ? t.explanation.simplifyActive
                  : lang === "hi"
                  ? "यदि आप और भी सरल, बोलचाल के शब्दों में विवरण चाहते हैं तो इसे चालू करें"
                  : lang === "kn"
                  ? "ಇನ್ನಷ್ಟು ಸರಳ ದೈನಂದಿನ ಮಾತುಗಳಲ್ಲಿ ವಿವರಣೆ ಪಡೆಯಲು ಇದನ್ನು ಆನ್ ಮಾಡಿ"
                  : "Switch to a shorter, 5th-grade reading level version with zero jargon"}
              </p>
            </div>

            <button
              type="button"
              onClick={() => setIsSimplified(!isSimplified)}
              aria-pressed={isSimplified}
              className={`inline-flex items-center gap-2 px-4 py-2 rounded-xl text-xs sm:text-sm font-bold border transition-all touch-target ${
                isSimplified
                  ? "bg-emerald-700 text-white border-emerald-700 shadow-sm"
                  : "bg-white text-slate-700 border-slate-300 hover:bg-slate-100"
              }`}
            >
              {isSimplified ? (
                <>
                  <ToggleRight className="w-5 h-5 text-emerald-300" />
                  <span>Showing Simpler Version</span>
                </>
              ) : (
                <>
                  <ToggleLeft className="w-5 h-5 text-slate-400" />
                  <span>Make Explanation Simpler</span>
                </>
              )}
            </button>
          </div>

          {/* ── Audio Narrator Player (Web Speech TTS) ── */}
          <AudioPlayer
            textToRead={narrationText}
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

          {/* Loading State simulation */}
          {isLoading ? (
            <div className="py-12 text-center space-y-3">
              <RefreshCw className="w-8 h-8 text-blue-700 animate-spin mx-auto" />
              <p className="text-sm font-bold text-slate-600">Generating plain-language explanation…</p>
            </div>
          ) : isUnavailable ? (
            /* Explanation Unavailable State */
            <div className="bg-red-50 border border-red-200 rounded-2xl p-6 text-center space-y-3">
              <ShieldAlert className="w-8 h-8 text-red-600 mx-auto" />
              <h3 className="text-base font-bold text-red-950">Explanation Temporarily Unavailable</h3>
              <p className="text-xs sm:text-sm text-red-800 max-w-md mx-auto">
                We could not generate the explanation at this moment. You can retry or view your raw bill summary.
              </p>
              <div className="pt-2 flex justify-center gap-3">
                <button
                  type="button"
                  onClick={handleRetry}
                  className="px-4 py-2 bg-red-700 text-white font-bold rounded-xl text-xs"
                >
                  {t.explanation.retryBtn}
                </button>
                <Link
                  href="/patient/bill"
                  className="px-4 py-2 bg-white border border-red-300 text-red-900 font-bold rounded-xl text-xs"
                >
                  {t.explanation.backToBillBtn}
                </Link>
              </div>
            </div>
          ) : (
            /* ── Main Explanation Text Content ── */
            <div className="space-y-6">
              {/* Overall Summary Box */}
              <div className="p-5 sm:p-6 rounded-2xl bg-slate-50 border border-slate-200">
                <h2 className="text-sm font-bold uppercase tracking-wider text-slate-500 mb-2">
                  {lang === "hi"
                    ? "मुख्य वित्तीय निष्कर्ष"
                    : lang === "kn"
                    ? "ಮುಖ್ಯ ಹಣಕಾಸು ಸಾರಾಂಶ"
                    : "Overall Summary"}
                </h2>
                <p className="text-base sm:text-lg text-slate-800 leading-relaxed font-medium">
                  {isSimplified ? explanation.simplifiedSummaryText : explanation.summaryText}
                </p>
              </div>

              {/* Itemized Line-by-Line Meanings */}
              <div>
                <h2 className="text-sm font-bold uppercase tracking-wider text-slate-500 mb-3">
                  {lang === "hi"
                    ? "हर शुल्क का सरल अर्थ"
                    : lang === "kn"
                    ? "ಪ್ರತಿ ಶುಲ್ಕದ ಸರಳ ಅರ್ಥ"
                    : "Breakdown of Every Charge"}
                </h2>

                <div className="space-y-3">
                  {explanation.breakdownSections.map((sec, idx) => (
                    <div
                      key={idx}
                      className="p-4 sm:p-5 rounded-2xl border border-slate-200 bg-white space-y-1.5"
                    >
                      <div className="flex items-center justify-between">
                        <h3 className="font-extrabold text-slate-900 text-base">
                          {sec.title}
                        </h3>
                        <span className="text-xs font-mono font-bold text-slate-700">
                          Item #{idx + 1}
                        </span>
                      </div>
                      <p className="text-sm sm:text-base text-slate-700 leading-relaxed">
                        {isSimplified ? sec.simpleDescription : sec.description}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* ── Bottom Action Links ── */}
          <div className="pt-6 border-t border-slate-200 flex flex-col sm:flex-row items-center justify-between gap-4">
            <Link
              href="/patient/questions"
              className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-6 py-3.5 bg-blue-700 hover:bg-blue-800 active:bg-blue-900 text-white font-extrabold rounded-2xl text-sm shadow-sm transition-all touch-target"
            >
              <MessageSquare className="w-4 h-4" />
              <span>{t.explanation.askFollowUpBtn}</span>
            </Link>

            <div className="flex items-center gap-3 w-full sm:w-auto">
              <Link
                href="/caregiver"
                className="flex-1 sm:flex-initial inline-flex items-center justify-center px-4 py-3 bg-slate-100 hover:bg-slate-200 text-slate-800 font-bold rounded-2xl text-xs sm:text-sm transition-colors touch-target"
              >
                Caregiver Summary
              </Link>

              <Link
                href="/patient/help"
                className="flex-1 sm:flex-initial inline-flex items-center justify-center gap-1.5 px-4 py-3 bg-teal-50 hover:bg-teal-100 border border-teal-200 text-teal-900 font-bold rounded-2xl text-xs sm:text-sm transition-colors touch-target"
              >
                <PhoneCall className="w-4 h-4 text-teal-700" />
                <span>{t.explanation.requestSupportBtn}</span>
              </Link>
            </div>
          </div>
        </div>
      </main>

      <Footer />
    </div>
  );
}
