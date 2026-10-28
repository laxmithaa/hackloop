"use client";

import React, { useState } from "react";
import Link from "next/link";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import DemoNotice from "@/components/DemoNotice";
import { useLanguage } from "@/lib/context/LanguageContext";
import {
  PhoneCall,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Clock,
  ArrowRight,
  ShieldCheck,
  RefreshCw,
  FileText,
  User,
  Phone,
} from "lucide-react";
import { z } from "zod";
import type { Lang, CallbackWindow } from "@/lib/types/billing";

const supportFormSchema = z.object({
  patientName: z.string().min(2, "Please enter your name"),
  contactNumber: z
    .string()
    .min(8, "Please enter a valid phone number")
    .regex(/^[0-9+\- ]+$/, "Phone number can only contain digits, plus, and spaces"),
  billNumber: z.string().min(3, "Please provide the bill number"),
  preferredLang: z.enum(["en", "hi", "kn"]),
  preferredCallback: z.enum(["now", "morning", "afternoon", "evening"]),
  reason: z.string().min(8, "Please briefly explain the issue or question (at least 8 characters)"),
  consentGiven: z.literal(true, {
    errorMap: () => ({ message: "You must provide consent for a worker to call you" }),
  }),
});

export default function HumanSupportPage() {
  const { t, lang, currentBill } = useLanguage();

  const [patientName, setPatientName] = useState(currentBill.patientName.replace(" (Demo)", ""));
  const [contactNumber, setContactNumber] = useState("+91 98765 43210");
  const [billNumber, setBillNumber] = useState(currentBill.billNumber);
  const [preferredLang, setPreferredLang] = useState<Lang>(lang);
  const [preferredCallback, setPreferredCallback] = useState<CallbackWindow>("now");
  const [reason, setReason] = useState("I need clarification on the consultation fee and insurance deduction.");
  const [consentGiven, setConsentGiven] = useState(false);

  const [errors, setErrors] = useState<Record<string, string>>({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);
  const [referenceId, setReferenceId] = useState<string | null>(null);
  const [submissionFailed, setSubmissionFailed] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setErrors({});
    setSubmissionFailed(false);

    const result = supportFormSchema.safeParse({
      patientName,
      contactNumber,
      billNumber,
      preferredLang,
      preferredCallback,
      reason,
      consentGiven,
    });

    if (!result.success) {
      const fieldErrors: Record<string, string> = {};
      result.error.errors.forEach((err) => {
        if (err.path[0]) {
          fieldErrors[err.path[0].toString()] = err.message;
        }
      });
      setErrors(fieldErrors);
      return;
    }

    setIsSubmitting(true);

    setTimeout(() => {
      setIsSubmitting(false);
      // Generate clean demonstration reference ID
      const newRef = `REF-2026-${Math.floor(1000 + Math.random() * 9000)}`;
      setReferenceId(newRef);
      setIsSuccess(true);
    }, 800);
  };

  return (
    <div className="min-h-screen flex flex-col bg-[#f8fafc]">
      <DemoNotice />
      <Navbar />

      <main className="flex-1 max-w-2xl mx-auto w-full px-4 sm:px-6 py-8 md:py-12">
        <div className="bg-white rounded-3xl border border-slate-200/80 shadow-sm p-6 sm:p-10 space-y-6">
          {/* Header */}
          <div className="flex items-start gap-4 pb-6 border-b border-slate-200">
            <div className="w-12 h-12 rounded-2xl bg-teal-50 text-teal-700 flex items-center justify-center flex-shrink-0 mt-0.5">
              <PhoneCall className="w-6 h-6" />
            </div>
            <div>
              <h1 className="text-2xl sm:text-3xl font-black text-slate-900 tracking-tight">
                {t.help.title}
              </h1>
              <p className="text-xs sm:text-sm text-slate-600 mt-1 leading-relaxed">
                {t.help.subtitle}
              </p>
            </div>
          </div>

          {/* ── State: Submission Successful ── */}
          {isSuccess && referenceId ? (
            <div
              role="status"
              className="bg-emerald-50 border-2 border-emerald-300 rounded-2xl p-6 sm:p-8 space-y-4 animate-fade-up"
            >
              <div className="flex items-center gap-3">
                <CheckCircle2 className="w-8 h-8 text-emerald-700 flex-shrink-0" />
                <div>
                  <h2 className="text-xl font-extrabold text-emerald-950">
                    {t.help.successTitle}
                  </h2>
                  <p className="text-xs sm:text-sm text-emerald-800 mt-0.5">
                    {t.help.successMessage}
                  </p>
                </div>
              </div>

              {/* Reference ID Badge */}
              <div className="p-4 bg-white rounded-xl border border-emerald-200 text-center space-y-1">
                <span className="text-xs font-bold uppercase tracking-wider text-slate-500">
                  {t.help.successReference}
                </span>
                <div className="text-2xl font-black font-mono text-emerald-800">
                  {referenceId}
                </div>
                <div className="text-xs text-slate-500">
                  Bill #{billNumber} · Callback: {preferredCallback.toUpperCase()}
                </div>
              </div>

              {/* Demo Warning */}
              <div className="p-3 bg-amber-50 border border-amber-200 text-amber-900 text-xs font-semibold rounded-xl text-center">
                {t.help.demoNote}
              </div>

              <div className="pt-2 flex flex-col sm:flex-row gap-3">
                <Link
                  href="/support"
                  className="inline-flex items-center justify-center gap-2 px-5 py-3 bg-teal-700 hover:bg-teal-800 text-white font-bold rounded-xl text-sm transition-colors touch-target"
                >
                  <span>View in Support Worker Dashboard</span>
                  <ArrowRight className="w-4 h-4" />
                </Link>

                <button
                  type="button"
                  onClick={() => {
                    setIsSuccess(false);
                    setReferenceId(null);
                  }}
                  className="px-5 py-3 bg-white border border-slate-300 hover:bg-slate-50 text-slate-700 font-bold rounded-xl text-sm transition-colors touch-target"
                >
                  Submit Another Request
                </button>
              </div>
            </div>
          ) : (
            /* ── Support Request Form ── */
            <form onSubmit={handleSubmit} className="space-y-5">
              {submissionFailed && (
                <div
                  role="alert"
                  className="p-3.5 bg-red-50 border border-red-200 text-red-900 rounded-xl text-sm flex items-center gap-2"
                >
                  <XCircle className="w-5 h-5 text-red-600 flex-shrink-0" />
                  <span>{t.help.errorMessage}</span>
                </div>
              )}

              {/* Patient Name */}
              <div>
                <label htmlFor="patientName" className="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-1">
                  {t.help.patientNameLabel} *
                </label>
                <div className="relative">
                  <User className="w-4 h-4 text-slate-400 absolute left-3.5 top-3.5" />
                  <input
                    id="patientName"
                    type="text"
                    value={patientName}
                    onChange={(e) => setPatientName(e.target.value)}
                    className="w-full pl-10 pr-4 py-3 rounded-xl border border-slate-300 text-sm font-semibold text-slate-900 focus-visible:ring-4 focus-visible:ring-blue-600/20"
                  />
                </div>
                {errors.patientName && (
                  <p className="text-xs text-red-600 font-bold mt-1">{errors.patientName}</p>
                )}
              </div>

              {/* Phone Number */}
              <div>
                <label htmlFor="contactNumber" className="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-1">
                  {t.help.contactLabel} *
                </label>
                <div className="relative">
                  <Phone className="w-4 h-4 text-slate-400 absolute left-3.5 top-3.5" />
                  <input
                    id="contactNumber"
                    type="tel"
                    value={contactNumber}
                    onChange={(e) => setContactNumber(e.target.value)}
                    className="w-full pl-10 pr-4 py-3 rounded-xl border border-slate-300 text-sm font-semibold text-slate-900 focus-visible:ring-4 focus-visible:ring-blue-600/20"
                  />
                </div>
                {errors.contactNumber && (
                  <p className="text-xs text-red-600 font-bold mt-1">{errors.contactNumber}</p>
                )}
              </div>

              {/* Bill Number */}
              <div>
                <label htmlFor="billNumberField" className="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-1">
                  {t.help.billNumberLabel} *
                </label>
                <div className="relative">
                  <FileText className="w-4 h-4 text-slate-400 absolute left-3.5 top-3.5" />
                  <input
                    id="billNumberField"
                    type="text"
                    value={billNumber}
                    onChange={(e) => setBillNumber(e.target.value)}
                    className="w-full pl-10 pr-4 py-3 rounded-xl border border-slate-300 text-sm font-mono font-bold text-slate-900 focus-visible:ring-4 focus-visible:ring-blue-600/20 uppercase"
                  />
                </div>
                {errors.billNumber && (
                  <p className="text-xs text-red-600 font-bold mt-1">{errors.billNumber}</p>
                )}
              </div>

              {/* Preferred Language Radio */}
              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-1.5">
                  {t.help.langPrefLabel} *
                </label>
                <div className="grid grid-cols-3 gap-2">
                  {[
                    { code: "en", label: "English" },
                    { code: "hi", label: "हिंदी" },
                    { code: "kn", label: "ಕನ್ನಡ" },
                  ].map((item) => (
                    <button
                      key={item.code}
                      type="button"
                      onClick={() => setPreferredLang(item.code as Lang)}
                      className={`py-2.5 rounded-xl border text-xs sm:text-sm font-bold text-center transition-colors ${
                        preferredLang === item.code
                          ? "bg-teal-700 text-white border-teal-700 shadow-sm"
                          : "bg-slate-50 text-slate-700 border-slate-300 hover:bg-slate-100"
                      }`}
                    >
                      {item.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* Preferred Callback Time */}
              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-1.5">
                  {t.help.callbackTimeLabel} *
                </label>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs sm:text-sm">
                  {[
                    { val: "now", label: t.help.callbackNow },
                    { val: "morning", label: t.help.callbackMorning },
                    { val: "afternoon", label: t.help.callbackAfternoon },
                    { val: "evening", label: t.help.callbackEvening },
                  ].map((opt) => (
                    <button
                      key={opt.val}
                      type="button"
                      onClick={() => setPreferredCallback(opt.val as CallbackWindow)}
                      className={`p-3 rounded-xl border text-left font-semibold transition-colors flex items-center justify-between ${
                        preferredCallback === opt.val
                          ? "bg-blue-50 text-blue-900 border-blue-500 font-bold"
                          : "bg-slate-50 text-slate-700 border-slate-300 hover:bg-slate-100"
                      }`}
                    >
                      <span>{opt.label}</span>
                      {preferredCallback === opt.val && (
                        <CheckCircle2 className="w-4 h-4 text-blue-700 flex-shrink-0" />
                      )}
                    </button>
                  ))}
                </div>
              </div>

              {/* Reason for Requesting Assistance */}
              <div>
                <label htmlFor="reasonField" className="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-1">
                  {t.help.reasonLabel} *
                </label>
                <textarea
                  id="reasonField"
                  rows={3}
                  value={reason}
                  onChange={(e) => setReason(e.target.value)}
                  placeholder={t.help.reasonPlaceholder}
                  className="w-full p-3 rounded-xl border border-slate-300 text-sm text-slate-900 placeholder-slate-400 focus-visible:ring-4 focus-visible:ring-blue-600/20"
                />
                {errors.reason && (
                  <p className="text-xs text-red-600 font-bold mt-1">{errors.reason}</p>
                )}
              </div>

              {/* Explicit Consent Checkbox */}
              <div className="pt-2">
                <label className="flex items-start gap-3 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={consentGiven}
                    onChange={(e) => setConsentGiven(e.target.checked)}
                    className="w-5 h-5 rounded border-slate-300 text-teal-700 focus:ring-teal-600 mt-0.5"
                  />
                  <span className="text-xs sm:text-sm text-slate-700 leading-relaxed font-medium">
                    {t.help.consentCheckboxLabel}
                  </span>
                </label>
                {errors.consentGiven && (
                  <p className="text-xs text-red-600 font-bold mt-1 pl-8">
                    {errors.consentGiven}
                  </p>
                )}
              </div>

              {/* Submit Button */}
              <div className="pt-4 border-t border-slate-100">
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="w-full inline-flex items-center justify-center gap-2 py-4 px-6 bg-teal-700 hover:bg-teal-800 active:bg-teal-900 disabled:opacity-50 text-white font-extrabold rounded-2xl text-base shadow-sm transition-all touch-target focus-visible:ring-4 focus-visible:ring-teal-700/30"
                >
                  {isSubmitting ? (
                    <>
                      <RefreshCw className="w-5 h-5 animate-spin" />
                      <span>{t.help.submitting}</span>
                    </>
                  ) : (
                    <>
                      <PhoneCall className="w-5 h-5" />
                      <span>{t.help.submitBtn}</span>
                    </>
                  )}
                </button>
              </div>

              <p className="text-center text-xs text-slate-400 italic">
                {t.help.demoNote}
              </p>
            </form>
          )}
        </div>
      </main>

      <Footer />
    </div>
  );
}
