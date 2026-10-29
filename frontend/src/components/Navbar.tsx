"use client";

import React, { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useLanguage } from "@/lib/context/LanguageContext";
import { PhoneCall, Type, Globe, Menu, X, ShieldAlert } from "lucide-react";
import type { Lang } from "@/lib/types/billing";

export default function Navbar() {
  const pathname = usePathname();
  const { lang, setLang, t, isLargeText, toggleLargeText } = useLanguage();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const navLinks = [
    { href: "/", label: t.nav.welcome },
    { href: "/patient", label: t.nav.patientFlow },
    { href: "/caregiver", label: t.nav.caregiver },
    { href: "/support", label: t.nav.support },
  ];

  const languages: { code: Lang; label: string }[] = [
    { code: "en", label: "English" },
    { code: "hi", label: "हिंदी" },
    { code: "kn", label: "ಕನ್ನಡ" },
  ];

  const isActive = (href: string) => {
    if (href === "/") return pathname === "/";
    return pathname.startsWith(href);
  };

  return (
    <header className="sticky top-0 z-50 bg-white/95 backdrop-blur-md border-b border-slate-200 shadow-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-20">
          {/* Brand Logo & Title */}
          <Link
            href="/"
            className="flex items-center gap-3 text-slate-900 group focus-visible:ring-2 focus-visible:ring-blue-600 rounded-lg p-1"
          >
            <div className="w-11 h-11 rounded-xl bg-gradient-to-br from-blue-700 to-teal-700 flex items-center justify-center text-white shadow-md shadow-blue-900/10 flex-shrink-0 group-hover:scale-105 transition-transform">
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
          </Link>

          {/* Desktop Navigation Links */}
          <nav className="hidden md:flex items-center gap-1" aria-label="Main Navigation">
            {navLinks.map((item) => {
              const active = isActive(item.href);
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  aria-current={active ? "page" : undefined}
                  className={`px-3.5 py-2 rounded-xl text-sm font-bold transition-all touch-target inline-flex items-center ${
                    active
                      ? "bg-blue-50 text-blue-700 shadow-sm"
                      : "text-slate-600 hover:text-slate-900 hover:bg-slate-100"
                  }`}
                >
                  {item.label}
                </Link>
              );
            })}
          </nav>

          {/* Right Action Controls: Language, Text Size, Seek Help */}
          <div className="hidden lg:flex items-center gap-3">
            {/* Accessibility: Text Size Toggle */}
            <button
              type="button"
              onClick={toggleLargeText}
              aria-label="Toggle larger text size for readability"
              title="Toggle Large Text"
              className={`p-2 rounded-xl border text-xs font-bold flex items-center gap-1.5 transition-colors touch-target ${
                isLargeText
                  ? "bg-blue-700 text-white border-blue-700"
                  : "bg-slate-50 text-slate-700 border-slate-200 hover:bg-slate-100"
              }`}
            >
              <Type className="w-4 h-4" />
              <span>{isLargeText ? "Large: On" : "Text Size"}</span>
            </button>

            {/* Language Selector */}
            <div
              role="group"
              aria-label={t.nav.langSelect}
              className="inline-flex items-center bg-slate-100 p-1 rounded-xl border border-slate-200"
            >
              <Globe className="w-4 h-4 text-slate-500 ml-1.5 mr-1" aria-hidden="true" />
              {languages.map((item) => (
                <button
                  key={item.code}
                  type="button"
                  onClick={() => setLang(item.code)}
                  aria-pressed={lang === item.code}
                  className={`px-2.5 py-1 text-xs font-bold rounded-lg transition-all ${
                    lang === item.code
                      ? "bg-blue-700 text-white shadow-sm"
                      : "text-slate-600 hover:text-slate-900"
                  }`}
                >
                  {item.label}
                </button>
              ))}
            </div>

            {/* Seek Human Help CTA */}
            <Link
              href="/patient/help"
              className="inline-flex items-center gap-2 px-4 py-2.5 bg-teal-700 hover:bg-teal-800 active:bg-teal-900 text-white font-bold rounded-xl text-sm shadow-sm transition-colors touch-target"
            >
              <PhoneCall className="w-4 h-4" />
              <span>{t.nav.seekHelpBtn}</span>
            </Link>
          </div>

          {/* Mobile Menu Button */}
          <div className="flex md:hidden items-center gap-2">
            <button
              type="button"
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="p-2.5 rounded-xl border border-slate-200 text-slate-700 hover:bg-slate-100 touch-target"
              aria-expanded={mobileMenuOpen}
              aria-label="Open mobile navigation menu"
            >
              {mobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
            </button>
          </div>
        </div>
      </div>

      {/* Mobile Menu Dropdown */}
      {mobileMenuOpen && (
        <div className="md:hidden border-t border-slate-200 bg-white px-4 pt-3 pb-6 space-y-4 shadow-lg animate-fade-up">
          <nav className="flex flex-col gap-1">
            {navLinks.map((item) => {
              const active = isActive(item.href);
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  onClick={() => setMobileMenuOpen(false)}
                  className={`px-4 py-3 rounded-xl text-base font-bold ${
                    active ? "bg-blue-50 text-blue-700" : "text-slate-700 hover:bg-slate-50"
                  }`}
                >
                  {item.label}
                </Link>
              );
            })}
          </nav>

          <div className="pt-3 border-t border-slate-100 flex flex-col gap-3">
            {/* Mobile Language Switcher */}
            <div>
              <span className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">
                {t.nav.langSelect}
              </span>
              <div className="grid grid-cols-3 gap-2">
                {languages.map((item) => (
                  <button
                    key={item.code}
                    type="button"
                    onClick={() => {
                      setLang(item.code);
                    }}
                    className={`py-2 text-sm font-bold rounded-xl border text-center ${
                      lang === item.code
                        ? "bg-blue-700 text-white border-blue-700"
                        : "bg-slate-50 text-slate-700 border-slate-200"
                    }`}
                  >
                    {item.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Mobile Text Size */}
            <button
              type="button"
              onClick={toggleLargeText}
              className={`w-full py-2.5 rounded-xl border text-sm font-bold flex items-center justify-center gap-2 ${
                isLargeText
                  ? "bg-blue-700 text-white border-blue-700"
                  : "bg-slate-50 text-slate-700 border-slate-200"
              }`}
            >
              <Type className="w-4 h-4" />
              <span>{isLargeText ? "Large Text Mode: Active" : "Enable Large Text"}</span>
            </button>

            {/* Mobile Help Button */}
            <Link
              href="/patient/help"
              onClick={() => setMobileMenuOpen(false)}
              className="w-full py-3 bg-teal-700 text-white font-bold rounded-xl flex items-center justify-center gap-2 text-base text-center shadow"
            >
              <PhoneCall className="w-5 h-5" />
              <span>{t.nav.seekHelpBtn}</span>
            </Link>
          </div>
        </div>
      )}
    </header>
  );
}
