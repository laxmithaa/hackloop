"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import DemoNotice from "@/components/DemoNotice";
import { useLanguage } from "@/lib/context/LanguageContext";
import {
  ShieldCheck,
  CheckCircle2,
  XCircle,
  HelpCircle,
  ArrowRight,
  PhoneCall,
  Lock,
  Eye,
  FileQuestion,
  RotateCcw,
} from "lucide-react";

export default function ConsentPage() {
  const router = useRouter();
  const { t, lang, setHasConsented } = useLanguage();
  const [declined, setDeclined] = useState(false);

  const handleAgree = () => {
    setHasConsented(true);
    router.push("/patient/identify");
  };

  const handleDecline = () => {
    setHasConsented(false);
    setDeclined(true);
  };

  const handleReconsider = () => {
    setDeclined(false);
  };

  return (
    <div className="min-h-screen flex flex-col bg-[#f8fafc]">
      <DemoNotice />
      <Navbar />

      <main className="flex-1 max-w-3xl mx-auto w-full px-4 sm:px-6 py-8 md:py-12">
        {/* Step Indicator */}
        <div className="mb-6 flex items-center justify-between text-xs font-bold uppercase tracking-wider text-slate-500">
          <span>
            {lang === "hi"
              ? "चरण 1 का 5 · गोपनीयता व सहमति"
              : lang === "kn"
              ? "ಹಂತ 1 / 5 · ಗೌಪ್ಯತೆ ಮತ್ತು ಒಪ್ಪಿಗೆ"
              : "Step 1 of 5 · Privacy & Consent"}
          </span>
          <span className="text-blue-700">Healthcare Bill Navigator</span>
        </div>

        <div className="bg-white rounded-3xl border border-slate-200/80 shadow-sm p-6 sm:p-10">
          {/* Header */}
          <div className="flex items-start gap-4 mb-8">
            <div className="w-12 h-12 rounded-2xl bg-blue-50 text-blue-700 flex items-center justify-center flex-shrink-0 mt-1">
              <ShieldCheck className="w-7 h-7" aria-hidden="true" />
            </div>
            <div>
              <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
                {t.consent.title}
              </h1>
              <p className="text-sm sm:text-base text-slate-600 mt-1.5 leading-relaxed">
                {t.consent.subtitle}
              </p>
            </div>
          </div>

          {/* If user declined, show informative limitation message */}
          {declined ? (
            <div
              role="region"
              aria-live="polite"
              className="bg-amber-50 border border-amber-200 rounded-2xl p-6 sm:p-8 space-y-4 animate-fade-up"
            >
              <div className="flex items-center gap-3">
                <XCircle className="w-6 h-6 text-amber-700 flex-shrink-0" />
                <h2 className="text-lg font-bold text-amber-950">
                  {t.consent.declinedNoticeTitle}
                </h2>
              </div>
              <p className="text-sm text-amber-900 leading-relaxed">
                {t.consent.declinedNoticeMsg}
              </p>
              <div className="pt-2 flex flex-col sm:flex-row gap-3">
                <button
                  type="button"
                  onClick={handleReconsider}
                  className="inline-flex items-center justify-center gap-2 px-5 py-3 bg-blue-700 hover:bg-blue-800 text-white font-bold rounded-xl text-sm transition-colors touch-target"
                >
                  <RotateCcw className="w-4 h-4" />
                  <span>{t.consent.reconsiderBtn}</span>
                </button>
                <Link
                  href="/patient/help"
                  className="inline-flex items-center justify-center gap-2 px-5 py-3 bg-white border border-slate-300 hover:bg-slate-50 text-slate-800 font-bold rounded-xl text-sm transition-colors touch-target"
                >
                  <PhoneCall className="w-4 h-4 text-teal-700" />
                  <span>{t.nav.seekHelpBtn}</span>
                </Link>
              </div>
            </div>
          ) : (
            /* Plain-Language Consent Points */
            <div className="space-y-6">
              {/* Point 1 */}
              <div className="p-4 sm:p-5 rounded-2xl bg-slate-50 border border-slate-200">
                <h2 className="text-base font-bold text-slate-900 flex items-center gap-2 mb-1.5">
                  <Eye className="w-4 h-4 text-blue-700 flex-shrink-0" />
                  <span>{t.consent.whatUsedTitle}</span>
                </h2>
                <p className="text-sm text-slate-600 leading-relaxed pl-6">
                  {t.consent.whatUsedText}
                </p>
              </div>

              {/* Point 2 */}
              <div className="p-4 sm:p-5 rounded-2xl bg-slate-50 border border-slate-200">
                <h2 className="text-base font-bold text-slate-900 flex items-center gap-2 mb-1.5">
                  <FileQuestion className="w-4 h-4 text-blue-700 flex-shrink-0" />
                  <span>{t.consent.whyNeededTitle}</span>
                </h2>
                <p className="text-sm text-slate-600 leading-relaxed pl-6">
                  {t.consent.whyNeededText}
                </p>
              </div>

              {/* Point 3 */}
              <div className="p-4 sm:p-5 rounded-2xl bg-slate-50 border border-slate-200">
                <h2 className="text-base font-bold text-slate-900 flex items-center gap-2 mb-1.5">
                  <Lock className="w-4 h-4 text-blue-700 flex-shrink-0" />
                  <span>{t.consent.howUsedTitle}</span>
                </h2>
                <p className="text-sm text-slate-600 leading-relaxed pl-6">
                  {t.consent.howUsedText}
                </p>
              </div>

              {/* Point 4 */}
              <div className="p-4 sm:p-5 rounded-2xl bg-slate-50 border border-slate-200">
                <h2 className="text-base font-bold text-slate-900 flex items-center gap-2 mb-1.5">
                  <CheckCircle2 className="w-4 h-4 text-blue-700 flex-shrink-0" />
                  <span>{t.consent.agreeMeaningTitle}</span>
                </h2>
                <p className="text-sm text-slate-600 leading-relaxed pl-6">
                  {t.consent.agreeMeaningText}
                </p>
              </div>

              {/* Point 5 */}
              <div className="p-4 sm:p-5 rounded-2xl bg-slate-50 border border-slate-200">
                <h2 className="text-base font-bold text-slate-900 flex items-center gap-2 mb-1.5">
                  <HelpCircle className="w-4 h-4 text-slate-600 flex-shrink-0" />
                  <span>{t.consent.declineTitle}</span>
                </h2>
                <p className="text-sm text-slate-600 leading-relaxed pl-6">
                  {t.consent.declineText}
                </p>
              </div>

              {/* Agree and Decline Controls */}
              <div className="pt-6 border-t border-slate-200 flex flex-col sm:flex-row items-center gap-4">
                <button
                  type="button"
                  onClick={handleAgree}
                  className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-8 py-4 bg-blue-700 hover:bg-blue-800 active:bg-blue-900 text-white font-extrabold rounded-2xl text-base shadow-sm hover:shadow transition-all touch-target focus-visible:ring-4 focus-visible:ring-blue-600/30"
                >
                  <span>{t.consent.agreeBtn}</span>
                  <ArrowRight className="w-5 h-5" />
                </button>

                <button
                  type="button"
                  onClick={handleDecline}
                  className="w-full sm:w-auto inline-flex items-center justify-center px-6 py-4 bg-slate-100 hover:bg-slate-200 active:bg-slate-300 text-slate-700 font-bold rounded-2xl text-base transition-colors touch-target"
                >
                  <span>{t.consent.declineBtn}</span>
                </button>
              </div>
            </div>
          )}
        </div>
      </main>

      <Footer />
    </div>
  );
}
