"use client";

/**
 * src/lib/context/LanguageContext.tsx
 *
 * Global context managing language, accessibility text sizing, and current bill state.
 */

import React, { createContext, useContext, useState, useEffect } from "react";
import { translations, type Lang, type TranslationDictionary } from "../i18n/translations";
import type { HospitalBill } from "../types/billing";
import { MOCK_VERIFIED_BILL } from "../services/mockData";

interface LanguageContextType {
  lang: Lang;
  setLang: (lang: Lang) => void;
  t: TranslationDictionary;
  isLargeText: boolean;
  toggleLargeText: () => void;
  hasConsented: boolean;
  setHasConsented: (val: boolean) => void;
  currentBill: HospitalBill;
  setCurrentBill: (bill: HospitalBill) => void;
}

const LanguageContext = createContext<LanguageContextType | undefined>(undefined);

export function LanguageProvider({ children }: { children: React.ReactNode }) {
  const [lang, setLangState] = useState<Lang>("en");
  const [isLargeText, setIsLargeText] = useState(false);
  const [hasConsented, setHasConsented] = useState(false);
  const [currentBill, setCurrentBill] = useState<HospitalBill>(MOCK_VERIFIED_BILL);

  const setLang = (newLang: Lang) => {
    setLangState(newLang);
    if (typeof document !== "undefined") {
      document.documentElement.lang = newLang;
    }
  };

  const toggleLargeText = () => {
    setIsLargeText((prev) => {
      const next = !prev;
      if (typeof document !== "undefined") {
        if (next) {
          document.body.classList.add("large-text");
        } else {
          document.body.classList.remove("large-text");
        }
      }
      return next;
    });
  };

  const t = translations[lang];

  return (
    <LanguageContext.Provider
      value={{
        lang,
        setLang,
        t,
        isLargeText,
        toggleLargeText,
        hasConsented,
        setHasConsented,
        currentBill,
        setCurrentBill,
      }}
    >
      {children}
    </LanguageContext.Provider>
  );
}

export function useLanguage() {
  const context = useContext(LanguageContext);
  if (!context) {
    throw new Error("useLanguage must be used within a LanguageProvider");
  }
  return context;
}
