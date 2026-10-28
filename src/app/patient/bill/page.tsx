"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import DemoNotice from "@/components/DemoNotice";
import StatusBadge from "@/components/StatusBadge";
import { useLanguage } from "@/lib/context/LanguageContext";
import {
  FileText,
  Building2,
  Calendar,
  AlertTriangle,
  CheckCircle2,
  HelpCircle,
  ArrowRight,
  MessageSquare,
  PhoneCall,
  ShieldCheck,
  ChevronRight,
  Info,
  DollarSign,
  Receipt,
  User,
} from "lucide-react";
import { MOCK_VERIFIED_BILL, MOCK_DISCREPANCY_BILL, MOCK_INCOMPLETE_BILL } from "@/lib/services/mockData";

export default function BillInformationPage() {
  const router = useRouter();
  const { t, lang, currentBill, setCurrentBill } = useLanguage();
  const [selectedPreset, setSelectedPreset] = useState<string>("verified");

  const formatCurrency = (amount: number) => {
    return `₹ ${amount.toLocaleString("en-IN")}`;
  };

  const handlePresetSwitch = (preset: "verified" | "discrepancy" | "incomplete") => {
    setSelectedPreset(preset);
    if (preset === "verified") setCurrentBill(MOCK_VERIFIED_BILL);
    if (preset === "discrepancy") setCurrentBill(MOCK_DISCREPANCY_BILL);
    if (preset === "incomplete") setCurrentBill(MOCK_INCOMPLETE_BILL);
  };

  return (
    <div className="min-h-screen flex flex-col bg-[#f8fafc]">
      <DemoNotice />
      <Navbar />

      <main className="flex-1 max-w-4xl mx-auto w-full px-4 sm:px-6 py-8 md:py-12">
        {/* Step Indicator */}
        <div className="mb-6 flex items-center justify-between text-xs font-bold uppercase tracking-wider text-slate-500">
          <span>
            {lang === "hi"
              ? "चरण 4 का 5 · बिल सारांश"
              : lang === "kn"
              ? "ಹಂತ 4 / 5 · ಬಿಲ್ ಸಾರಾಂಶ"
              : "Step 4 of 5 · Bill Summary"}
          </span>
          <span className="text-blue-700">Healthcare Bill Navigator</span>
        </div>

        {/* Top Control Bar: Demo State Switcher */}
        <div className="mb-6 p-3 bg-white rounded-2xl border border-slate-200 flex flex-wrap items-center justify-between gap-3 text-xs">
          <span className="font-bold text-slate-600 flex items-center gap-1.5">
            <Info className="w-4 h-4 text-blue-600" />
            <span>Test Bill Status:</span>
          </span>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={() => handlePresetSwitch("verified")}
              className={`px-3 py-1.5 rounded-lg font-bold transition-colors ${
                selectedPreset === "verified"
                  ? "bg-blue-700 text-white shadow-sm"
                  : "bg-slate-100 hover:bg-slate-200 text-slate-700"
              }`}
            >
              Verified Bill (Normal)
            </button>
            <button
              type="button"
              onClick={() => handlePresetSwitch("discrepancy")}
              className={`px-3 py-1.5 rounded-lg font-bold transition-colors ${
                selectedPreset === "discrepancy"
                  ? "bg-amber-600 text-white shadow-sm"
                  : "bg-slate-100 hover:bg-slate-200 text-slate-700"
              }`}
            >
              Discrepancy Detected
            </button>
            <button
              type="button"
              onClick={() => handlePresetSwitch("incomplete")}
              className={`px-3 py-1.5 rounded-lg font-bold transition-colors ${
                selectedPreset === "incomplete"
                  ? "bg-slate-800 text-white shadow-sm"
                  : "bg-slate-100 hover:bg-slate-200 text-slate-700"
              }`}
            >
              Incomplete Data
            </button>
          </div>
        </div>

        {/* Main Content Card */}
        <div className="bg-white rounded-3xl border border-slate-200/80 shadow-sm p-6 sm:p-10 space-y-8">
          {/* Header & Verification Status */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-slate-200">
            <div>
              <div className="flex items-center gap-2 mb-2">
                {currentBill.state === "verified" && (
                  <StatusBadge variant="success" label={t.bill.verifiedBadge} />
                )}
                {currentBill.state === "discrepancy" && (
                  <StatusBadge variant="warning" label={t.bill.discrepancyBadge} />
                )}
                {currentBill.state === "incomplete" && (
                  <StatusBadge variant="neutral" label={t.bill.incompleteBadge} />
                )}
              </div>
              <h1 className="text-2xl sm:text-3xl font-black text-slate-900 tracking-tight">
                {currentBill.hospitalName}
              </h1>
              <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs sm:text-sm text-slate-500 mt-1 font-medium">
                <span>
                  {t.bill.billNumberLabel}: <strong className="text-slate-900 font-mono">{currentBill.billNumber}</strong>
                </span>
                <span>•</span>
                <span>
                  {t.bill.patientNameLabel}: <strong className="text-slate-900">{currentBill.patientName}</strong>
                </span>
              </div>
            </div>

            {/* Quick Action: Explain Button */}
            <button
              type="button"
              onClick={() => router.push("/patient/explanation")}
              className="inline-flex items-center justify-center gap-2 px-6 py-3.5 bg-blue-700 hover:bg-blue-800 active:bg-blue-900 text-white font-extrabold rounded-2xl text-base shadow-sm transition-all touch-target focus-visible:ring-4 focus-visible:ring-blue-600/30 whitespace-nowrap"
            >
              <span>{t.bill.explainCtaBtn}</span>
              <ArrowRight className="w-5 h-5" />
            </button>
          </div>

          {/* Amount Discrepancy Banner if present */}
          {currentBill.state === "discrepancy" && currentBill.discrepancyNotice && (
            <div
              role="alert"
              className="bg-amber-50 border-2 border-amber-300 rounded-2xl p-5 sm:p-6 text-amber-950 flex items-start gap-4 animate-fade-up"
            >
              <AlertTriangle className="w-6 h-6 text-amber-700 flex-shrink-0 mt-0.5" />
              <div>
                <h2 className="text-base font-extrabold text-amber-950 mb-1">
                  {t.bill.discrepancyAlertTitle}
                </h2>
                <p className="text-sm text-amber-900 leading-relaxed">
                  {currentBill.discrepancyNotice}
                </p>
                <div className="mt-3 flex gap-3">
                  <Link
                    href="/patient/help"
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-amber-700 hover:bg-amber-800 text-white text-xs font-bold rounded-lg"
                  >
                    <PhoneCall className="w-3.5 h-3.5" />
                    <span>Dispute this charge with hospital</span>
                  </Link>
                </div>
              </div>
            </div>
          )}

          {/* Incomplete Notice if present */}
          {currentBill.state === "incomplete" && currentBill.discrepancyNotice && (
            <div
              role="alert"
              className="bg-slate-100 border border-slate-300 rounded-2xl p-5 text-slate-800 flex items-start gap-3"
            >
              <Info className="w-5 h-5 text-slate-600 flex-shrink-0 mt-0.5" />
              <div className="text-sm">
                <span className="font-bold block mb-0.5">Incomplete Bill Notice:</span>
                <span>{currentBill.discrepancyNotice}</span>
              </div>
            </div>
          )}

          {/* ── Financial Summary Grid (4 Clear Distinctions) ── */}
          <div>
            <h2 className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-3">
              {lang === "hi"
                ? "वित्तीय सारांश (Financial Overview)"
                : lang === "kn"
                ? "ಹಣಕಾಸು ಸಾರಾಂಶ"
                : "Financial Overview"}
            </h2>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              {/* 1. Total Bill */}
              <div className="p-4 sm:p-5 rounded-2xl bg-slate-50 border border-slate-200">
                <span className="text-xs font-bold text-slate-500 uppercase tracking-wider block mb-1">
                  {t.bill.totalAmountLabel}
                </span>
                <div className="text-2xl sm:text-3xl font-black text-slate-900 font-mono">
                  {formatCurrency(currentBill.totalAmountInr)}
                </div>
                <span className="text-xs text-slate-500 mt-1 block">
                  Total hospital fees before deductions
                </span>
              </div>

              {/* 2. Insurance Covered */}
              <div className="p-4 sm:p-5 rounded-2xl bg-emerald-50/70 border border-emerald-200">
                <span className="text-xs font-bold text-emerald-800 uppercase tracking-wider block mb-1">
                  {t.bill.insuranceLabel}
                </span>
                <div className="text-2xl sm:text-3xl font-black text-emerald-900 font-mono">
                  - {formatCurrency(currentBill.insuranceCoveredInr)}
                </div>
                <span className="text-xs text-emerald-800 mt-1 block">
                  Paid directly by insurer / scheme
                </span>
              </div>

              {/* 3. Already Paid */}
              <div className="p-4 sm:p-5 rounded-2xl bg-blue-50/70 border border-blue-200">
                <span className="text-xs font-bold text-blue-800 uppercase tracking-wider block mb-1">
                  {t.bill.paidLabel}
                </span>
                <div className="text-2xl sm:text-3xl font-black text-blue-900 font-mono">
                  - {formatCurrency(currentBill.paidAmountInr)}
                </div>
                <span className="text-xs text-blue-800 mt-1 block">
                  Advance / previous deposits
                </span>
              </div>

              {/* 4. Patient Payable Amount (Highlighted Primary) */}
              <div className="p-4 sm:p-5 rounded-2xl bg-slate-900 text-white shadow-md border border-slate-800">
                <span className="text-xs font-bold text-blue-300 uppercase tracking-wider block mb-1">
                  {t.bill.patientPayableLabel}
                </span>
                <div className="text-2xl sm:text-3xl font-black text-white font-mono">
                  {formatCurrency(currentBill.patientPayableInr)}
                </div>
                <span className="text-xs text-slate-300 mt-1 block font-medium">
                  Net balance due from patient
                </span>
              </div>
            </div>
          </div>

          {/* ── Relevant Dates ── */}
          <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-2 flex items-center gap-1.5">
              <Calendar className="w-4 h-4 text-slate-600" />
              <span>
                {lang === "hi"
                  ? "महत्वपूर्ण तिथियां"
                  : lang === "kn"
                  ? "ಮುಖ್ಯ ದಿನಾಂಕಗಳು"
                  : "Relevant Hospital Dates"}
              </span>
            </h3>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs sm:text-sm">
              <div>
                <span className="text-slate-500 block">{t.bill.admissionLabel}:</span>
                <span className="font-bold text-slate-900">{currentBill.admissionDate}</span>
              </div>
              <div>
                <span className="text-slate-500 block">{t.bill.dischargeLabel}:</span>
                <span className="font-bold text-slate-900">{currentBill.dischargeDate}</span>
              </div>
              <div>
                <span className="text-slate-500 block">{t.bill.billDateLabel}:</span>
                <span className="font-bold text-slate-900">{currentBill.billDate}</span>
              </div>
              <div>
                <span className="text-slate-500 block">{t.bill.dueDateLabel}:</span>
                <span className="font-bold text-blue-700">{currentBill.dueDate}</span>
              </div>
            </div>
          </div>

          {/* ── Itemized Breakdown (Simple, readable cards) ── */}
          <div>
            <div className="flex items-center justify-between mb-4">
              <div>
                <h2 className="text-lg font-extrabold text-slate-900">
                  {t.bill.lineItemsTitle}
                </h2>
                <p className="text-xs text-slate-500">
                  {t.bill.lineItemsSubtitle}
                </p>
              </div>
              <span className="text-xs font-bold text-slate-500 bg-slate-100 px-2.5 py-1 rounded-full">
                {currentBill.items.length} items
              </span>
            </div>

            <div className="space-y-3">
              {currentBill.items.map((item, idx) => (
                <div
                  key={item.id}
                  className="p-4 rounded-2xl border border-slate-200 hover:border-slate-300 transition-colors bg-white flex flex-col sm:flex-row sm:items-center justify-between gap-3"
                >
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-bold text-slate-400">#{idx + 1}</span>
                      <h3 className="font-extrabold text-slate-900 text-sm sm:text-base">
                        {item.chargeLabel}
                      </h3>
                      {item.category && (
                        <span className="text-xs font-semibold px-2 py-0.5 rounded bg-slate-100 text-slate-600">
                          {item.category}
                        </span>
                      )}
                    </div>
                    <p className="text-xs sm:text-sm text-slate-600 leading-relaxed">
                      {item.explanation}
                    </p>
                  </div>

                  <div className="text-right sm:flex-shrink-0">
                    <div className="text-base sm:text-lg font-black text-slate-900 font-mono">
                      ₹ {parseFloat(item.amountInr).toLocaleString("en-IN")}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* ── Action Toolbar ── */}
          <div className="pt-6 border-t border-slate-200 flex flex-col sm:flex-row items-center justify-between gap-4">
            <button
              type="button"
              onClick={() => router.push("/patient/explanation")}
              className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-8 py-4 bg-blue-700 hover:bg-blue-800 active:bg-blue-900 text-white font-extrabold rounded-2xl text-base shadow-sm transition-all touch-target"
            >
              <span>{t.bill.explainCtaBtn}</span>
              <ArrowRight className="w-5 h-5" />
            </button>

            <div className="flex items-center gap-3 w-full sm:w-auto">
              <Link
                href="/patient/questions"
                className="flex-1 sm:flex-initial inline-flex items-center justify-center gap-2 px-5 py-3.5 bg-slate-100 hover:bg-slate-200 text-slate-800 font-bold rounded-2xl text-sm transition-colors touch-target"
              >
                <MessageSquare className="w-4 h-4 text-blue-700" />
                <span>{t.bill.askQuestionBtn}</span>
              </Link>

              <Link
                href="/patient/help"
                className="flex-1 sm:flex-initial inline-flex items-center justify-center gap-2 px-5 py-3.5 bg-teal-50 hover:bg-teal-100 text-teal-800 font-bold rounded-2xl text-sm border border-teal-200 transition-colors touch-target"
              >
                <PhoneCall className="w-4 h-4 text-teal-700" />
                <span>{t.bill.needHelpBtn}</span>
              </Link>
            </div>
          </div>
        </div>
      </main>

      <Footer />
    </div>
  );
}
