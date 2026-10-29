"use client";

import React from "react";
import Link from "next/link";
import { useLanguage } from "@/lib/context/LanguageContext";
import { ShieldCheck, PhoneCall, HelpCircle, FileText } from "lucide-react";

export default function Footer() {
  const { t, lang } = useLanguage();

  return (
    <footer className="mt-auto bg-slate-900 text-slate-300 border-t border-slate-800">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10 sm:py-14">
        {/* Top Disclaimer Banner */}
        <div className="bg-slate-800/80 border border-slate-700/80 rounded-2xl p-5 mb-8 flex flex-col sm:flex-row items-start sm:items-center gap-4">
          <div className="w-10 h-10 rounded-xl bg-blue-500/10 text-blue-400 flex items-center justify-center flex-shrink-0">
            <ShieldCheck className="w-6 h-6" aria-hidden="true" />
          </div>
          <div className="text-xs sm:text-sm text-slate-300 leading-relaxed">
            <span className="font-bold text-white block mb-0.5">
              {lang === "hi"
                ? "महत्वपूर्ण सूचना"
                : lang === "kn"
                ? "ಮುಖ್ಯ ಸೂಚನೆ"
                : "Important Informational Notice"}
            </span>
            {t.common.officialNotice}
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-8 mb-8 text-sm">
          {/* Col 1: Brand & Purpose */}
          <div className="md:col-span-2 space-y-3">
            <div className="text-lg font-black text-white flex items-center gap-2">
              <span className="w-3 h-3 rounded-full bg-teal-400" />
              Healthcare Bill Navigator
            </div>
            <p className="text-slate-400 text-xs sm:text-sm leading-relaxed max-w-md">
              {t.common.appTagline}. {t.common.privacyNotice}
            </p>
          </div>

          {/* Col 2: Navigation */}
          <div>
            <h4 className="text-xs font-bold uppercase tracking-wider text-white mb-3">
              {lang === "hi" ? "त्वरित लिंक" : lang === "kn" ? "ಮುಖ್ಯ ಲಿಂಕ್‌ಗಳು" : "Navigation"}
            </h4>
            <ul className="space-y-2 text-xs sm:text-sm">
              <li>
                <Link href="/" className="hover:text-white transition-colors">
                  {t.nav.welcome}
                </Link>
              </li>
              <li>
                <Link href="/patient" className="hover:text-white transition-colors">
                  {t.nav.patientFlow}
                </Link>
              </li>
              <li>
                <Link href="/caregiver" className="hover:text-white transition-colors">
                  {t.nav.caregiver}
                </Link>
              </li>
              <li>
                <Link href="/support" className="hover:text-white transition-colors">
                  {t.nav.support}
                </Link>
              </li>
            </ul>
          </div>

          {/* Col 3: Assistance */}
          <div>
            <h4 className="text-xs font-bold uppercase tracking-wider text-white mb-3">
              {t.common.seekHumanHelp}
            </h4>
            <p className="text-xs text-slate-400 mb-3">
              {lang === "hi"
                ? "क्या आपके पास अपने बिल के बारे में प्रश्न हैं?"
                : lang === "kn"
                ? "ನಿಮ್ಮ ಬಿಲ್ ಬಗ್ಗೆ ಯಾವುದೇ ಪ್ರಶ್ನೆಗಳಿವೆಯೇ?"
                : "Have questions about disputed charges or need a payment plan?"}
            </p>
            <Link
              href="/patient/help"
              className="inline-flex items-center gap-2 px-3 py-2 bg-teal-600 hover:bg-teal-500 text-white rounded-lg text-xs font-bold transition-colors"
            >
              <PhoneCall className="w-3.5 h-3.5" />
              <span>{t.nav.seekHelpBtn}</span>
            </Link>
          </div>
        </div>

        {/* Bottom Bar */}
        <div className="pt-6 border-t border-slate-800 text-xs text-slate-500 flex flex-col sm:flex-row items-center justify-between gap-3">
          <div>
            © {new Date().getFullYear()} Healthcare Bill Navigator · English, Hindi & Kannada Support.
          </div>
        </div>
      </div>
    </footer>
  );
}
