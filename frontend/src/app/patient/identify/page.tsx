"use client";

import React, { useState, useRef } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import DemoNotice from "@/components/DemoNotice";
import StatusBadge from "@/components/StatusBadge";
import { useLanguage } from "@/lib/context/LanguageContext";
import {
  UploadCloud,
  FileText,
  Camera,
  Search,
  CheckCircle2,
  AlertTriangle,
  AlertCircle,
  XCircle,
  HelpCircle,
  ArrowRight,
  RefreshCw,
  PhoneCall,
  X,
  File,
  Wifi,
  KeyRound,
} from "lucide-react";
import { z } from "zod";
import { getMockBill, MOCK_VERIFIED_BILL, MOCK_DISCREPANCY_BILL, MOCK_INCOMPLETE_BILL } from "@/lib/services/mockData";
import { lookupBillByNumber } from "@/lib/services/billingService";
import type { IdentificationStatus } from "@/lib/types/billing";

// Zod validation schema for bill number
const billNumberSchema = z
  .string()
  .min(3, "Bill number must be at least 3 characters")
  .max(30, "Bill number cannot exceed 30 characters")
  .regex(/^[A-Za-z0-9\-_ ]+$/, "Bill number can only contain letters, numbers, spaces, and hyphens");

export default function IdentifyPage() {
  const router = useRouter();
  const { t, lang, setCurrentBill } = useLanguage();

  const [activeTab, setActiveTab] = useState<"upload" | "number">("number");
  const [billNumber, setBillNumber] = useState("BILL-2026-001");
  const [inputError, setInputError] = useState<string | null>(null);

  // Upload state
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [filePreview, setFilePreview] = useState<string | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const cameraInputRef = useRef<HTMLInputElement>(null);

  // Result state
  const [resultStatus, setResultStatus] = useState<IdentificationStatus | null>(null);
  const [resultDetails, setResultDetails] = useState<{
    hospitalName?: string;
    billNumber?: string;
    patientPreview?: string;
    date?: string;
  }>({});

  // ── Handle Bill Number Submission ─────────────────────────────────────────
  const handleNumberSubmit = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    setInputError(null);

    const validation = billNumberSchema.safeParse(billNumber);
    if (!validation.success) {
      setInputError(validation.error.errors[0].message);
      return;
    }

    setIsProcessing(true);
    setResultStatus(null);

    setTimeout(async () => {
      setIsProcessing(false);
      const clean = billNumber.trim().toUpperCase();

      if (clean === "UNREG-770" || clean.includes("UNREG")) {
        setResultStatus("unregistered_hospital");
      } else if (clean === "NOTFOUND-99" || clean.includes("NOTFOUND")) {
        setResultStatus("not_found");
      } else if (clean === "INCOMPLETE-01" || clean === "INC-2026-104") {
        setResultStatus("incomplete");
        setCurrentBill(MOCK_INCOMPLETE_BILL);
        setResultDetails({
          hospitalName: MOCK_INCOMPLETE_BILL.hospitalName,
          billNumber: MOCK_INCOMPLETE_BILL.billNumber,
          date: MOCK_INCOMPLETE_BILL.billDate,
        });
      } else if (clean === "TEMPFAIL-500" || clean.includes("FAIL")) {
        setResultStatus("temporary_failure");
      } else if (clean === "VERIFY-REQ" || clean === "BILL-2026-001") {
        // Demands access code verification
        setResultStatus("needs_verification");
        setCurrentBill(MOCK_VERIFIED_BILL);
        setResultDetails({
          hospitalName: MOCK_VERIFIED_BILL.hospitalName,
          billNumber: MOCK_VERIFIED_BILL.billNumber,
          patientPreview: "Ramesh S. (Demo)",
          date: MOCK_VERIFIED_BILL.billDate,
        });
      } else if (clean === "DISC-2026-902") {
        setResultStatus("identified");
        setCurrentBill(MOCK_DISCREPANCY_BILL);
        setResultDetails({
          hospitalName: MOCK_DISCREPANCY_BILL.hospitalName,
          billNumber: MOCK_DISCREPANCY_BILL.billNumber,
          patientPreview: "Ananya P. (Demo)",
          date: MOCK_DISCREPANCY_BILL.billDate,
        });
      } else {
        // Real lookup: the backend verifies the access code and returns the
        // hospital's recorded amounts, read from PostgreSQL.
        const response = await lookupBillByNumber(billNumber, lang);
        if (response.status === "found" && response.result) {
          const analysis = response.result;
          const rupees = (id: string) =>
            Number.parseFloat(analysis.items.find((i) => i.id === id)?.amountInr || "0") || 0;

          setCurrentBill({
            hospitalName: analysis.hospitalName || "",
            billNumber: analysis.billNumber || clean,
            patientName: "",
            totalAmountInr: rupees("billTotalAfterDiscounts"),
            insuranceCoveredInr: rupees("insurancePaidOrCredited"),
            paidAmountInr: rupees("patientPayments"),
            patientPayableInr: rupees("printedAmountDue"),
            admissionDate: "",
            dischargeDate: "",
            billDate: analysis.billDate || "",
            dueDate: analysis.dueDate || "",
            state: "verified",
            items: analysis.items,
            isDemo: false,
          });
          setResultStatus("needs_verification");
          setResultDetails({
            hospitalName: analysis.hospitalName || undefined,
            billNumber: analysis.billNumber || clean,
            date: analysis.billDate || undefined,
          });
        } else {
          setResultStatus("not_found");
        }
      }
    }, 100);
  };

  // ── Handle File Upload ────────────────────────────────────────────────────
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploadError(null);

    // Validate size (max 10MB)
    if (file.size > 10 * 1024 * 1024) {
      setUploadError(
        lang === "hi"
          ? "फ़ाइल 10 MB से बड़ी है। कृपया एक छोटी फ़ाइल चुनें।"
          : lang === "kn"
          ? "ಫೈಲ್ 10 MB ಗಿಂತ ದೊಡ್ಡದಾಗಿದೆ. ದಯವಿಟ್ಟು ಚಿಕ್ಕ ಫೈಲ್ ಆಯ್ಕೆಮಾಡಿ."
          : "File exceeds 10 MB limit. Please select a smaller image."
      );
      return;
    }

    // Validate type
    const validTypes = ["image/jpeg", "image/png", "application/pdf"];
    if (!validTypes.includes(file.type)) {
      setUploadError(
        lang === "hi"
          ? "अमान्य फ़ाइल प्रकार। कृपया केवल JPG, PNG या PDF अपलोड करें।"
          : lang === "kn"
          ? "ಅಮಾನ್ಯ ಫೈಲ್ ಮಾದರಿ. ದಯವಿಟ್ಟು JPG, PNG ಅಥವಾ PDF ಮಾತ್ರ ಅಪ್‌ಲೋಡ್ ಮಾಡಿ."
          : "Invalid file format. Please upload a JPG, PNG, or PDF file."
      );
      return;
    }

    setSelectedFile(file);
    if (file.type.startsWith("image/")) {
      setFilePreview(URL.createObjectURL(file));
    } else {
      setFilePreview(null);
    }
  };

  const handleUploadSubmit = () => {
    if (!selectedFile) return;

    setIsProcessing(true);
    setResultStatus(null);

    // Simulate OCR scanning
    setTimeout(() => {
      setIsProcessing(false);
      // If filename includes "blurry" or "dark", show unreadable
      if (selectedFile.name.toLowerCase().includes("blurry") || selectedFile.name.toLowerCase().includes("dark")) {
        setResultStatus("unreadable_image");
      } else {
        setResultStatus("needs_verification");
        setCurrentBill(MOCK_VERIFIED_BILL);
        setResultDetails({
          hospitalName: "Sunrise Community Hospital",
          billNumber: "BILL-2026-001",
          patientPreview: "Ramesh S. (Demo)",
          date: "2026-10-24",
        });
      }
    }, 1200);
  };

  const handleRemoveFile = () => {
    setSelectedFile(null);
    setFilePreview(null);
    setUploadError(null);
    if (fileInputRef.current) fileInputRef.current.value = "";
    if (cameraInputRef.current) cameraInputRef.current.value = "";
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
              ? "चरण 2 का 5 · बिल की पहचान"
              : lang === "kn"
              ? "ಹಂತ 2 / 5 · ಬಿಲ್ ಗುರುತಿಸುವಿಕೆ"
              : "Step 2 of 5 · Bill Identification"}
          </span>
          <span className="text-blue-700">Healthcare Bill Navigator</span>
        </div>

        <div className="bg-white rounded-3xl border border-slate-200/80 shadow-sm p-6 sm:p-10">
          {/* Header */}
          <div className="mb-8">
            <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
              {t.identify.title}
            </h1>
            <p className="text-sm sm:text-base text-slate-600 mt-1.5 leading-relaxed">
              {t.identify.subtitle}
            </p>
          </div>

          {/* Option Selector Tabs */}
          <div className="grid grid-cols-2 gap-3 p-1.5 bg-slate-100 rounded-2xl mb-8">
            <button
              type="button"
              onClick={() => {
                setActiveTab("number");
                setResultStatus(null);
              }}
              className={`py-3 px-4 rounded-xl text-sm font-bold flex items-center justify-center gap-2 transition-all touch-target ${
                activeTab === "number"
                  ? "bg-white text-blue-700 shadow-sm"
                  : "text-slate-600 hover:text-slate-900"
              }`}
            >
              <Search className="w-4 h-4" />
              <span>{t.identify.tabNumber}</span>
            </button>

            <button
              type="button"
              onClick={() => {
                setActiveTab("upload");
                setResultStatus(null);
              }}
              className={`py-3 px-4 rounded-xl text-sm font-bold flex items-center justify-center gap-2 transition-all touch-target ${
                activeTab === "upload"
                  ? "bg-white text-blue-700 shadow-sm"
                  : "text-slate-600 hover:text-slate-900"
              }`}
            >
              <UploadCloud className="w-4 h-4" />
              <span>{t.identify.tabUpload}</span>
            </button>
          </div>

          {/* ── TAB 1: Enter Bill Number (Low-Bandwidth Friendly) ── */}
          {activeTab === "number" && (
            <div className="space-y-6">
              {/* Low network badge */}
              <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs font-bold">
                <Wifi className="w-3.5 h-3.5" />
                <span>{t.identify.lowBandwidthBadge}</span>
              </div>

              <form onSubmit={handleNumberSubmit} className="space-y-4">
                <div>
                  <label htmlFor="billNumberInput" className="block text-sm font-bold text-slate-900 mb-1">
                    {t.identify.numberInputLabel}
                  </label>
                  <p className="text-xs text-slate-500 mb-2">
                    {t.identify.numberInstructions}
                  </p>
                  <input
                    id="billNumberInput"
                    type="text"
                    value={billNumber}
                    onChange={(e) => {
                      setBillNumber(e.target.value);
                      if (inputError) setInputError(null);
                    }}
                    placeholder={t.identify.numberPlaceholder}
                    className={`w-full px-4 py-3.5 rounded-xl border text-base font-semibold text-slate-900 bg-white placeholder-slate-400 focus-visible:ring-4 focus-visible:ring-blue-600/20 touch-target ${
                      inputError ? "border-red-500 bg-red-50/50" : "border-slate-300"
                    }`}
                  />
                  {inputError && (
                    <p className="mt-1.5 text-xs font-semibold text-red-600 flex items-center gap-1">
                      <XCircle className="w-3.5 h-3.5" />
                      <span>{inputError}</span>
                    </p>
                  )}
                </div>

                <button
                  type="submit"
                  disabled={isProcessing}
                  className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-8 py-3.5 bg-blue-700 hover:bg-blue-800 active:bg-blue-900 disabled:opacity-60 text-white font-extrabold rounded-xl text-base shadow-sm transition-all touch-target"
                >
                  {isProcessing ? (
                    <>
                      <RefreshCw className="w-4 h-4 animate-spin" />
                      <span>{t.common.loading}</span>
                    </>
                  ) : (
                    <>
                      <Search className="w-4 h-4" />
                      <span>{t.identify.numberSubmit}</span>
                    </>
                  )}
                </button>
              </form>

              {/* Quick Presets for Evaluators / Patients to test all states */}
              <div className="pt-4 border-t border-slate-100">
                <span className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">
                  {t.identify.presetExamplesLabel}
                </span>
                <div className="flex flex-wrap gap-2 text-xs">
                  {[
                    { label: "Verified Record", code: "BILL-2026-001" },
                    { label: "Verification Required", code: "VERIFY-REQ" },
                    { label: "Amount Discrepancy", code: "DISC-2026-902" },
                    { label: "Incomplete Bill", code: "INC-2026-104" },
                    { label: "Bill Not Found", code: "NOTFOUND-99" },
                    { label: "Hospital Unregistered", code: "UNREG-770" },
                    { label: "Temporary Failure", code: "TEMPFAIL-500" },
                  ].map((p) => (
                    <button
                      key={p.code}
                      type="button"
                      onClick={() => {
                        setBillNumber(p.code);
                        setInputError(null);
                      }}
                      className="px-2.5 py-1.5 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold border border-slate-200 transition-colors"
                    >
                      {p.label} (<span className="font-mono">{p.code}</span>)
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* ── TAB 2: Upload Bill Photo ── */}
          {activeTab === "upload" && (
            <div className="space-y-6">
              <input
                ref={fileInputRef}
                type="file"
                accept="image/jpeg,image/png,application/pdf"
                onChange={handleFileChange}
                className="hidden"
                id="file-upload-input"
              />
              <input
                ref={cameraInputRef}
                type="file"
                accept="image/*"
                capture="environment"
                onChange={handleFileChange}
                className="hidden"
                id="camera-upload-input"
              />

              {!selectedFile ? (
                /* Empty Upload Dropzone */
                <div
                  onDragOver={(e) => e.preventDefault()}
                  onDrop={(e) => {
                    e.preventDefault();
                    if (e.dataTransfer.files?.[0]) {
                      const file = e.dataTransfer.files[0];
                      setSelectedFile(file);
                      if (file.type.startsWith("image/")) setFilePreview(URL.createObjectURL(file));
                    }
                  }}
                  className="border-2 border-dashed border-slate-300 rounded-3xl p-8 text-center bg-slate-50/60 hover:bg-slate-50 transition-colors"
                >
                  <div className="w-14 h-14 rounded-2xl bg-blue-50 text-blue-700 flex items-center justify-center mx-auto mb-4">
                    <UploadCloud className="w-8 h-8" />
                  </div>
                  <h3 className="text-base font-bold text-slate-900 mb-1">
                    {t.identify.uploadDragDrop}
                  </h3>
                  <p className="text-xs text-slate-500 mb-6">
                    {t.identify.uploadLimits}
                  </p>

                  <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
                    <button
                      type="button"
                      onClick={() => fileInputRef.current?.click()}
                      className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-6 py-3 bg-blue-700 hover:bg-blue-800 text-white font-bold rounded-xl text-sm shadow-sm transition-colors touch-target"
                    >
                      <File className="w-4 h-4" />
                      <span>{t.identify.uploadBrowse}</span>
                    </button>

                    <button
                      type="button"
                      onClick={() => cameraInputRef.current?.click()}
                      className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-6 py-3 bg-white border border-slate-300 hover:bg-slate-100 text-slate-700 font-bold rounded-xl text-sm transition-colors touch-target"
                    >
                      <Camera className="w-4 h-4 text-slate-600" />
                      <span>{t.identify.uploadCamera}</span>
                    </button>
                  </div>
                </div>
              ) : (
                /* Selected File Preview */
                <div className="border border-slate-200 rounded-2xl p-5 bg-slate-50 space-y-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-xl bg-blue-100 text-blue-700 flex items-center justify-center flex-shrink-0">
                        <FileText className="w-5 h-5" />
                      </div>
                      <div>
                        <div className="text-sm font-bold text-slate-900 truncate max-w-xs sm:max-w-md">
                          {selectedFile.name}
                        </div>
                        <div className="text-xs text-slate-500">
                          {(selectedFile.size / 1024).toFixed(1)} KB · {selectedFile.type || "Document"}
                        </div>
                      </div>
                    </div>

                    <button
                      type="button"
                      onClick={handleRemoveFile}
                      className="p-2 text-slate-400 hover:text-slate-600 rounded-lg hover:bg-slate-200 transition-colors"
                      aria-label={t.identify.uploadRemove}
                    >
                      <X className="w-5 h-5" />
                    </button>
                  </div>

                  {/* Image Thumbnail Preview */}
                  {filePreview && (
                    <div className="relative rounded-xl overflow-hidden border border-slate-200 bg-white max-h-56 flex items-center justify-center p-2">
                      {/* eslint-disable-next-line @next/next/no-img-element */}
                      <img
                        src={filePreview}
                        alt="Bill Preview"
                        className="max-h-52 object-contain rounded-lg"
                      />
                    </div>
                  )}

                  <div className="flex flex-wrap items-center gap-3 pt-2">
                    <button
                      type="button"
                      onClick={handleUploadSubmit}
                      disabled={isProcessing}
                      className="inline-flex items-center gap-2 px-6 py-3 bg-blue-700 hover:bg-blue-800 disabled:opacity-60 text-white font-bold rounded-xl text-sm shadow-sm transition-colors touch-target"
                    >
                      {isProcessing ? (
                        <>
                          <RefreshCw className="w-4 h-4 animate-spin" />
                          <span>{t.identify.uploadingProgress}</span>
                        </>
                      ) : (
                        <>
                          <Search className="w-4 h-4" />
                          <span>{t.identify.uploadSubmit}</span>
                        </>
                      )}
                    </button>

                    <button
                      type="button"
                      onClick={() => fileInputRef.current?.click()}
                      className="px-4 py-3 text-slate-600 hover:text-slate-800 text-sm font-semibold rounded-xl hover:bg-slate-200 transition-colors"
                    >
                      {t.identify.uploadReplace}
                    </button>
                  </div>
                </div>
              )}

              {uploadError && (
                <div
                  role="alert"
                  className="p-3 bg-red-50 border border-red-200 text-red-800 text-sm rounded-xl flex items-center gap-2"
                >
                  <XCircle className="w-4 h-4 text-red-600 flex-shrink-0" />
                  <span>{uploadError}</span>
                </div>
              )}
            </div>
          )}

          {/* ── IDENTIFICATION RESULT STATES ── */}
          {resultStatus && (
            <div className="mt-8 pt-8 border-t border-slate-200 animate-fade-up">
              {/* 1. Information Identified */}
              {resultStatus === "identified" && (
                <div className="bg-emerald-50 border border-emerald-200 rounded-2xl p-6 sm:p-8 space-y-4">
                  <div className="flex items-center gap-3">
                    <CheckCircle2 className="w-7 h-7 text-emerald-700 flex-shrink-0" />
                    <div>
                      <h3 className="text-lg font-bold text-emerald-950">
                        {t.identify.states.identifiedTitle}
                      </h3>
                      <p className="text-sm text-emerald-800 mt-0.5">
                        {t.identify.states.identifiedDesc}
                      </p>
                    </div>
                  </div>

                  {/* Summary Card (Note: Financial amounts NOT shown on identification screen) */}
                  <div className="bg-white rounded-xl p-4 border border-emerald-200/80 text-sm space-y-1.5">
                    <div className="flex justify-between">
                      <span className="text-slate-500">Hospital:</span>
                      <span className="font-bold text-slate-900">{resultDetails.hospitalName}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-500">Bill Number:</span>
                      <span className="font-mono font-bold text-slate-900">{resultDetails.billNumber}</span>
                    </div>
                    {resultDetails.patientPreview && (
                      <div className="flex justify-between">
                        <span className="text-slate-500">Patient:</span>
                        <span className="font-semibold text-slate-900">{resultDetails.patientPreview}</span>
                      </div>
                    )}
                    {resultDetails.date && (
                      <div className="flex justify-between">
                        <span className="text-slate-500">Bill Date:</span>
                        <span className="text-slate-700">{resultDetails.date}</span>
                      </div>
                    )}
                  </div>

                  <button
                    type="button"
                    onClick={() => router.push("/patient/bill")}
                    className="inline-flex items-center gap-2 px-6 py-3.5 bg-emerald-700 hover:bg-emerald-800 text-white font-extrabold rounded-xl text-base shadow-sm transition-colors touch-target"
                  >
                    <span>{t.identify.states.proceedBtn}</span>
                    <ArrowRight className="w-5 h-5" />
                  </button>
                </div>
              )}

              {/* 2. Additional Verification Required */}
              {resultStatus === "needs_verification" && (
                <div className="bg-blue-50 border border-blue-200 rounded-2xl p-6 sm:p-8 space-y-4">
                  <div className="flex items-center gap-3">
                    <KeyRound className="w-7 h-7 text-blue-700 flex-shrink-0" />
                    <div>
                      <h3 className="text-lg font-bold text-blue-950">
                        {t.identify.states.needsVerificationTitle}
                      </h3>
                      <p className="text-sm text-blue-800 mt-0.5">
                        {t.identify.states.needsVerificationDesc}
                      </p>
                    </div>
                  </div>

                  <div className="bg-white rounded-xl p-4 border border-blue-200 text-sm space-y-1">
                    <div className="flex justify-between">
                      <span className="text-slate-500">Hospital:</span>
                      <span className="font-bold text-slate-900">{resultDetails.hospitalName}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-500">Bill Number:</span>
                      <span className="font-mono font-bold text-slate-900">{resultDetails.billNumber}</span>
                    </div>
                  </div>

                  <button
                    type="button"
                    onClick={() => router.push("/patient/verify")}
                    className="inline-flex items-center gap-2 px-6 py-3.5 bg-blue-700 hover:bg-blue-800 text-white font-extrabold rounded-xl text-base shadow-sm transition-colors touch-target"
                  >
                    <KeyRound className="w-5 h-5" />
                    <span>{t.identify.states.verifyBtn}</span>
                  </button>
                </div>
              )}

              {/* 3. Bill Not Found */}
              {resultStatus === "not_found" && (
                <div className="bg-amber-50 border border-amber-200 rounded-2xl p-6 space-y-3">
                  <div className="flex items-center gap-3">
                    <AlertTriangle className="w-6 h-6 text-amber-700 flex-shrink-0" />
                    <h3 className="text-lg font-bold text-amber-950">
                      {t.identify.states.notFoundTitle}
                    </h3>
                  </div>
                  <p className="text-sm text-amber-900 leading-relaxed">
                    {t.identify.states.notFoundDesc}
                  </p>
                  <div className="pt-2 flex flex-wrap gap-3">
                    <button
                      type="button"
                      onClick={() => setBillNumber("BILL-2026-001")}
                      className="px-4 py-2 bg-amber-700 hover:bg-amber-800 text-white font-bold rounded-xl text-sm"
                    >
                      Use Demo Bill (BILL-2026-001)
                    </button>
                    <button
                      type="button"
                      onClick={() => setActiveTab("upload")}
                      className="px-4 py-2 bg-white border border-amber-300 text-amber-900 font-bold rounded-xl text-sm"
                    >
                      {t.identify.tabUpload}
                    </button>
                  </div>
                </div>
              )}

              {/* 4. Hospital Not Registered */}
              {resultStatus === "unregistered_hospital" && (
                <div className="bg-slate-100 border border-slate-300 rounded-2xl p-6 space-y-3">
                  <div className="flex items-center gap-3">
                    <AlertCircle className="w-6 h-6 text-slate-700 flex-shrink-0" />
                    <h3 className="text-lg font-bold text-slate-900">
                      {t.identify.states.unregisteredTitle}
                    </h3>
                  </div>
                  <p className="text-sm text-slate-700 leading-relaxed">
                    {t.identify.states.unregisteredDesc}
                  </p>
                  <Link
                    href="/patient/help"
                    className="inline-flex items-center gap-2 px-5 py-2.5 bg-teal-700 text-white font-bold rounded-xl text-sm mt-2"
                  >
                    <PhoneCall className="w-4 h-4" />
                    <span>{t.nav.seekHelpBtn}</span>
                  </Link>
                </div>
              )}

              {/* 5. Unreadable Image */}
              {resultStatus === "unreadable_image" && (
                <div className="bg-red-50 border border-red-200 rounded-2xl p-6 space-y-3">
                  <div className="flex items-center gap-3">
                    <XCircle className="w-6 h-6 text-red-700 flex-shrink-0" />
                    <h3 className="text-lg font-bold text-red-950">
                      {t.identify.states.unreadableTitle}
                    </h3>
                  </div>
                  <p className="text-sm text-red-900 leading-relaxed">
                    {t.identify.states.unreadableDesc}
                  </p>
                  <div className="pt-2 flex flex-wrap gap-3">
                    <button
                      type="button"
                      onClick={() => fileInputRef.current?.click()}
                      className="px-4 py-2 bg-red-700 text-white font-bold rounded-xl text-sm"
                    >
                      Upload Clearer Photo
                    </button>
                    <button
                      type="button"
                      onClick={() => setActiveTab("number")}
                      className="px-4 py-2 bg-white border border-red-300 text-red-900 font-bold rounded-xl text-sm"
                    >
                      Enter Bill Number Instead
                    </button>
                  </div>
                </div>
              )}

              {/* 6. Incomplete Identification */}
              {resultStatus === "incomplete" && (
                <div className="bg-amber-50 border border-amber-200 rounded-2xl p-6 space-y-3">
                  <div className="flex items-center gap-3">
                    <AlertTriangle className="w-6 h-6 text-amber-700 flex-shrink-0" />
                    <h3 className="text-lg font-bold text-amber-950">
                      {t.identify.states.incompleteTitle}
                    </h3>
                  </div>
                  <p className="text-sm text-amber-900 leading-relaxed">
                    {t.identify.states.incompleteDesc}
                  </p>
                  <div className="pt-2 flex gap-3">
                    <button
                      type="button"
                      onClick={() => router.push("/patient/bill")}
                      className="px-5 py-2.5 bg-amber-700 text-white font-bold rounded-xl text-sm"
                    >
                      View Available Details Anyway
                    </button>
                    <Link
                      href="/patient/help"
                      className="px-5 py-2.5 bg-white border border-amber-300 text-amber-900 font-bold rounded-xl text-sm"
                    >
                      {t.nav.seekHelpBtn}
                    </Link>
                  </div>
                </div>
              )}

              {/* 7. Temporary Failure */}
              {resultStatus === "temporary_failure" && (
                <div className="bg-slate-100 border border-slate-300 rounded-2xl p-6 space-y-3">
                  <div className="flex items-center gap-3">
                    <RefreshCw className="w-6 h-6 text-slate-700 flex-shrink-0" />
                    <h3 className="text-lg font-bold text-slate-900">
                      {t.identify.states.temporaryFailureTitle}
                    </h3>
                  </div>
                  <p className="text-sm text-slate-700 leading-relaxed">
                    {t.identify.states.temporaryFailureDesc}
                  </p>
                  <button
                    type="button"
                    onClick={() => handleNumberSubmit()}
                    className="inline-flex items-center gap-2 px-5 py-2.5 bg-blue-700 text-white font-bold rounded-xl text-sm mt-2"
                  >
                    <RefreshCw className="w-4 h-4" />
                    <span>{t.common.retryBtn}</span>
                  </button>
                </div>
              )}
            </div>
          )}
        </div>
      </main>

      <Footer />
    </div>
  );
}
