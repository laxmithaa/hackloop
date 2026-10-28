"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import DemoNotice from "@/components/DemoNotice";
import { useLanguage } from "@/lib/context/LanguageContext";
import {
  KeyRound,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  RefreshCw,
  PhoneCall,
  ArrowRight,
  ShieldAlert,
} from "lucide-react";
import { z } from "zod";

const accessCodeSchema = z
  .string()
  .min(4, "Access code must be at least 4 characters")
  .max(12, "Access code cannot exceed 12 characters");

export default function AccessCodePage() {
  const router = useRouter();
  const { t, lang, currentBill } = useLanguage();

  const [code, setCode] = useState("HBN-4921");
  const [attempts, setAttempts] = useState(3);
  const [isVerifying, setIsVerifying] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isExpired, setIsExpired] = useState(false);
  const [isLocked, setIsLocked] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (isLocked) return;

    setErrorMessage(null);
    setIsExpired(false);

    const validation = accessCodeSchema.safeParse(code.trim());
    if (!validation.success) {
      setErrorMessage(validation.error.errors[0].message);
      return;
    }

    setIsVerifying(true);

    setTimeout(() => {
      setIsVerifying(false);
      const clean = code.trim().toUpperCase();

      if (clean === "EXPIRED" || clean === "EXP-000") {
        setIsExpired(true);
      } else if (clean === "HBN-4921" || clean === "7492" || clean === "PASS123") {
        // Success
        router.push("/patient/bill");
      } else {
        const nextAttempts = attempts - 1;
        setAttempts(nextAttempts);

        if (nextAttempts <= 0) {
          setIsLocked(true);
          setErrorMessage(t.verify.lockedError);
        } else {
          setErrorMessage(t.verify.invalidError);
        }
      }
    }, 600);
  };

  return (
    <div className="min-h-screen flex flex-col bg-[#f8fafc]">
      <DemoNotice />
      <Navbar />

      <main className="flex-1 max-w-xl mx-auto w-full px-4 sm:px-6 py-8 md:py-14">
        {/* Step Indicator */}
        <div className="mb-6 flex items-center justify-between text-xs font-bold uppercase tracking-wider text-slate-500">
          <span>
            {lang === "hi"
              ? "चरण 3 का 5 · एक्सेस कोड सत्यापन"
              : lang === "kn"
              ? "ಹಂತ 3 / 5 · ಪ್ರವೇಶ ಕೋಡ್ ದೃಢೀಕರಣ"
              : "Step 3 of 5 · Access Code"}
          </span>
          <span className="text-blue-700">Healthcare Bill Navigator</span>
        </div>

        <div className="bg-white rounded-3xl border border-slate-200/80 shadow-sm p-6 sm:p-10">
          <div className="flex items-center gap-3.5 mb-6">
            <div className="w-12 h-12 rounded-2xl bg-blue-50 text-blue-700 flex items-center justify-center flex-shrink-0">
              <KeyRound className="w-6 h-6" aria-hidden="true" />
            </div>
            <div>
              <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">
                {t.verify.title}
              </h1>
              <p className="text-xs sm:text-sm text-slate-600 mt-0.5">
                {t.verify.subtitle}
              </p>
            </div>
          </div>

          {/* Target Bill Info Header */}
          <div className="mb-6 p-4 rounded-xl bg-slate-50 border border-slate-200 text-xs sm:text-sm flex justify-between items-center">
            <div>
              <span className="text-slate-500 block">
                {lang === "hi" ? "अस्पताल" : lang === "kn" ? "ಆಸ್ಪತ್ರೆ" : "Hospital"}:
              </span>
              <span className="font-bold text-slate-900">{currentBill.hospitalName}</span>
            </div>
            <div className="text-right">
              <span className="text-slate-500 block">
                {lang === "hi" ? "बिल संख्या" : lang === "kn" ? "ಬಿಲ್ ಸಂಖ್ಯೆ" : "Bill #"}:
              </span>
              <span className="font-mono font-bold text-blue-700">{currentBill.billNumber}</span>
            </div>
          </div>

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label htmlFor="accessCodeInput" className="block text-sm font-bold text-slate-900 mb-1">
                {t.verify.inputLabel}
              </label>
              <p className="text-xs text-slate-500 mb-2">
                {t.verify.helperText}
              </p>
              <input
                id="accessCodeInput"
                type="text"
                disabled={isLocked || isVerifying}
                value={code}
                onChange={(e) => {
                  setCode(e.target.value);
                  if (errorMessage) setErrorMessage(null);
                }}
                placeholder={t.verify.placeholder}
                className="w-full px-4 py-3.5 rounded-xl border border-slate-300 text-lg font-mono font-bold tracking-wider text-slate-900 bg-white placeholder-slate-400 focus-visible:ring-4 focus-visible:ring-blue-600/20 touch-target uppercase"
                maxLength={12}
                autoComplete="off"
              />
            </div>

            {/* Attempts Remaining Display */}
            {!isLocked && (
              <div className="text-xs font-semibold text-slate-600 flex items-center justify-between">
                <span>
                  {attempts} {t.verify.attemptsRemaining}
                </span>
                <span className="text-slate-400">Security protection active</span>
              </div>
            )}

            {/* Error States */}
            {errorMessage && (
              <div
                role="alert"
                className="p-3.5 bg-red-50 border border-red-200 rounded-xl text-red-900 text-sm flex items-start gap-2.5 animate-fade-up"
              >
                <XCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
                <div>
                  <span className="font-bold block">Verification Error</span>
                  <span>{errorMessage}</span>
                </div>
              </div>
            )}

            {/* Expired State */}
            {isExpired && (
              <div
                role="alert"
                className="p-3.5 bg-amber-50 border border-amber-200 rounded-xl text-amber-900 text-sm flex items-start gap-2.5 animate-fade-up"
              >
                <AlertTriangle className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
                <div>
                  <span className="font-bold block">Access Code Expired</span>
                  <span>{t.verify.expiredError}</span>
                </div>
              </div>
            )}

            {/* Locked State */}
            {isLocked && (
              <div
                role="alert"
                className="p-4 bg-slate-900 text-white rounded-xl text-sm space-y-3 animate-fade-up"
              >
                <div className="flex items-center gap-2 text-red-400 font-bold">
                  <ShieldAlert className="w-5 h-5" />
                  <span>Temporary Security Lockout</span>
                </div>
                <p className="text-xs text-slate-300 leading-relaxed">
                  Too many incorrect attempts have been entered. To protect confidential medical records, automated entry has been temporarily paused.
                </p>
                <Link
                  href="/patient/help"
                  className="inline-flex items-center gap-2 px-4 py-2 bg-teal-600 hover:bg-teal-500 text-white rounded-lg text-xs font-bold"
                >
                  <PhoneCall className="w-4 h-4" />
                  <span>Request Support Worker Callback</span>
                </Link>
              </div>
            )}

            {/* Submit Button */}
            {!isLocked && (
              <button
                type="submit"
                disabled={isVerifying || !code.trim()}
                className="w-full inline-flex items-center justify-center gap-2 py-4 px-6 bg-blue-700 hover:bg-blue-800 active:bg-blue-900 disabled:opacity-50 text-white font-extrabold rounded-2xl text-base shadow-sm transition-all touch-target focus-visible:ring-4 focus-visible:ring-blue-600/30"
              >
                {isVerifying ? (
                  <>
                    <RefreshCw className="w-5 h-5 animate-spin" />
                    <span>{t.verify.verifying}</span>
                  </>
                ) : (
                  <>
                    <span>{t.verify.submitBtn}</span>
                    <ArrowRight className="w-5 h-5" />
                  </>
                )}
              </button>
            )}
          </form>

          {/* Demo Hint & Help */}
          <div className="mt-8 pt-6 border-t border-slate-100 space-y-3">
            <p className="text-xs text-slate-500 italic">
              {t.verify.demoHint}
            </p>

            <div className="p-3 bg-teal-50/70 border border-teal-200 rounded-xl text-xs text-teal-900 flex items-center justify-between">
              <span>{t.verify.nextStepHelp}</span>
              <Link
                href="/patient/help"
                className="font-bold underline hover:text-teal-950 whitespace-nowrap ml-2"
              >
                {t.nav.seekHelpBtn}
              </Link>
            </div>
          </div>
        </div>
      </main>

      <Footer />
    </div>
  );
}
