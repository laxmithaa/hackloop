"use client";

import React from "react";
import Link from "next/link";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import DemoNotice from "@/components/DemoNotice";
import { useLanguage } from "@/lib/context/LanguageContext";
import {
  Users,
  Calendar,
  HelpCircle,
  CheckCircle2,
  PhoneCall,
  ArrowRight,
  ShieldCheck,
  FileText,
  AlertCircle,
  ArrowLeft,
  DollarSign,
  HeartHandshake,
} from "lucide-react";

export default function CaregiverSummaryPage() {
  const { t, lang, currentBill } = useLanguage();

  return (
    <div className="min-h-screen flex flex-col bg-[#f8fafc]">
      <DemoNotice />
      <Navbar />

      <main className="flex-1 max-w-4xl mx-auto w-full px-4 sm:px-6 py-8 md:py-12">
        {/* Navigation Breadcrumb */}
        <div className="mb-6 flex items-center justify-between">
          <Link
            href="/patient/bill"
            className="inline-flex items-center gap-1.5 text-xs sm:text-sm font-bold text-slate-600 hover:text-slate-900 transition-colors touch-target"
          >
            <ArrowLeft className="w-4 h-4" />
            <span>{t.caregiver.returnToPatientBtn}</span>
          </Link>

          <span className="text-xs font-bold uppercase tracking-wider text-teal-800 bg-teal-50 px-2.5 py-1 rounded-full border border-teal-200">
            Caregiver & Family Portal
          </span>
        </div>

        <div className="bg-white rounded-3xl border border-slate-200/80 shadow-sm p-6 sm:p-10 space-y-8">
          {/* Main Required Heading */}
          <div className="pb-6 border-b border-slate-200">
            <div className="flex items-center gap-2 mb-2 text-teal-700">
              <HeartHandshake className="w-6 h-6" />
              <span className="text-xs font-bold uppercase tracking-wider">
                Authorized Caregiver Summary
              </span>
            </div>
            <h1 className="text-3xl sm:text-4xl font-black text-slate-900 tracking-tight">
              {t.caregiver.title}
            </h1>
            <p className="text-sm sm:text-base text-slate-600 mt-1 leading-relaxed">
              {t.caregiver.subtitle}
            </p>
          </div>

          {/* 1. Main Bill Details (Essential Numbers) */}
          <section aria-labelledby="caregiver-summary-heading">
            <h2 id="caregiver-summary-heading" className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-3 flex items-center gap-1.5">
              <FileText className="w-4 h-4 text-blue-700" />
              <span>{t.caregiver.billSummaryTitle}</span>
            </h2>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200">
                <span className="text-xs font-bold text-slate-500 block mb-1">
                  Hospital & Bill Number
                </span>
                <div className="font-extrabold text-slate-900 text-sm">
                  {currentBill.hospitalName}
                </div>
                <div className="font-mono text-xs text-blue-700 mt-0.5">
                  #{currentBill.billNumber}
                </div>
              </div>

              <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200">
                <span className="text-xs font-bold text-slate-500 block mb-1">
                  Total Bill Amount
                </span>
                <div className="font-black font-mono text-xl text-slate-900">
                  ₹ {currentBill.totalAmountInr.toLocaleString("en-IN")}
                </div>
                <div className="text-xs text-emerald-700 font-semibold mt-0.5">
                  ₹ {currentBill.insuranceCoveredInr.toLocaleString("en-IN")} paid by insurance
                </div>
              </div>

              <div className="p-4 rounded-2xl bg-teal-50 border border-teal-200">
                <span className="text-xs font-bold text-teal-800 block mb-1">
                  Patient Payable Share
                </span>
                <div className="font-black font-mono text-xl text-teal-950">
                  ₹ {currentBill.patientPayableInr.toLocaleString("en-IN")}
                </div>
                <div className="text-xs text-teal-800 font-semibold mt-0.5">
                  Due by: {currentBill.dueDate}
                </div>
              </div>
            </div>
          </section>

          {/* 2. Important Financial Terms Decoded */}
          <section aria-labelledby="caregiver-terms-heading">
            <h2 id="caregiver-terms-heading" className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-3">
              {t.caregiver.financialTermsTitle}
            </h2>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs sm:text-sm">
              <div className="p-4 rounded-2xl border border-slate-200 bg-white space-y-1">
                <span className="font-extrabold text-slate-900 block">
                  1. Co-Payment (सह-भुगतान)
                </span>
                <p className="text-slate-600 leading-relaxed">
                  A fixed percentage or amount that the patient pays out-of-pocket for each hospital service, while the insurance scheme covers the remainder.
                </p>
              </div>

              <div className="p-4 rounded-2xl border border-slate-200 bg-white space-y-1">
                <span className="font-extrabold text-slate-900 block">
                  2. Room Rent Sub-Limit
                </span>
                <p className="text-slate-600 leading-relaxed">
                  The maximum daily room rent your insurance policy will cover. If a higher room category is chosen, proportionate extra deductions apply.
                </p>
              </div>

              <div className="p-4 rounded-2xl border border-slate-200 bg-white space-y-1">
                <span className="font-extrabold text-slate-900 block">
                  3. Consumables (उपभोग्य वस्तुएं)
                </span>
                <p className="text-slate-600 leading-relaxed">
                  Syringes, surgical gloves, and sanitizers often not reimbursed by standard insurance policies and billed to patient share.
                </p>
              </div>
            </div>
          </section>

          {/* 3. Deadlines & Critical Dates */}
          <section aria-labelledby="caregiver-dates-heading" className="p-5 rounded-2xl bg-slate-50 border border-slate-200">
            <h2 id="caregiver-dates-heading" className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-2 flex items-center gap-1.5">
              <Calendar className="w-4 h-4 text-slate-600" />
              <span>{t.caregiver.importantDatesTitle}</span>
            </h2>
            <ul className="space-y-2 text-xs sm:text-sm text-slate-700">
              <li className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-blue-600" />
                <span>
                  <strong>Discharge Date:</strong> {currentBill.dischargeDate} — All pharmacy medicines and original reports must be collected.
                </span>
              </li>
              <li className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-amber-600" />
                <span>
                  <strong>Payment Due Date:</strong> {currentBill.dueDate} — Final settlement deadline before accounts escalation.
                </span>
              </li>
              <li className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-emerald-600" />
                <span>
                  <strong>Insurance Claim Window:</strong> Submit post-hospitalization bills within 30 days of discharge.
                </span>
              </li>
            </ul>
          </section>

          {/* 4. Questions to Ask Hospital Billing Desk */}
          <section aria-labelledby="caregiver-questions-heading">
            <h2 id="caregiver-questions-heading" className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-3 flex items-center gap-1.5">
              <HelpCircle className="w-4 h-4 text-blue-700" />
              <span>{t.caregiver.clarificationQuestionsTitle}</span>
            </h2>

            <div className="space-y-2.5 text-xs sm:text-sm">
              {[
                "1. Has the final insurance settlement letter (TPA approval) been applied to this bill?",
                "2. Were generic medicine alternatives used for pharmacy items, or brand name medicines?",
                "3. Can the hospital provide an itemized tax breakdown of surgical consumables?",
                "4. Does the hospital offer an interest-free payment plan for the patient payable share?",
              ].map((q, idx) => (
                <div key={idx} className="p-3 rounded-xl bg-slate-50 border border-slate-200 text-slate-800 font-medium">
                  {q}
                </div>
              ))}
            </div>
          </section>

          {/* 5. Suggested Next Steps */}
          <section aria-labelledby="caregiver-nextsteps-heading">
            <h2 id="caregiver-nextsteps-heading" className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-3">
              {t.caregiver.nextStepsTitle}
            </h2>

            <div className="space-y-3">
              <div className="p-4 rounded-2xl bg-emerald-50/70 border border-emerald-200 flex items-start gap-3">
                <CheckCircle2 className="w-5 h-5 text-emerald-700 flex-shrink-0 mt-0.5" />
                <p className="text-xs sm:text-sm text-emerald-950 font-medium">
                  {t.caregiver.nextStep1}
                </p>
              </div>

              <div className="p-4 rounded-2xl bg-emerald-50/70 border border-emerald-200 flex items-start gap-3">
                <CheckCircle2 className="w-5 h-5 text-emerald-700 flex-shrink-0 mt-0.5" />
                <p className="text-xs sm:text-sm text-emerald-950 font-medium">
                  {t.caregiver.nextStep2}
                </p>
              </div>

              <div className="p-4 rounded-2xl bg-emerald-50/70 border border-emerald-200 flex items-start gap-3">
                <CheckCircle2 className="w-5 h-5 text-emerald-700 flex-shrink-0 mt-0.5" />
                <p className="text-xs sm:text-sm text-emerald-950 font-medium">
                  {t.caregiver.nextStep3}
                </p>
              </div>
            </div>
          </section>

          {/* Action Footer */}
          <div className="pt-6 border-t border-slate-200 flex flex-col sm:flex-row items-center justify-between gap-4">
            <Link
              href="/patient/help"
              className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-6 py-3.5 bg-teal-700 hover:bg-teal-800 text-white font-extrabold rounded-2xl text-sm shadow-sm transition-colors touch-target"
            >
              <PhoneCall className="w-4 h-4" />
              <span>{t.caregiver.requestSupportBtn}</span>
            </Link>

            <Link
              href="/patient/bill"
              className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-6 py-3.5 bg-slate-100 hover:bg-slate-200 text-slate-800 font-bold rounded-2xl text-sm transition-colors touch-target"
            >
              <ArrowLeft className="w-4 h-4" />
              <span>{t.caregiver.returnToPatientBtn}</span>
            </Link>
          </div>
        </div>
      </main>

      <Footer />
    </div>
  );
}
