'use client';
import { createContext, useContext, useEffect, useState } from 'react';
import { Language, TranslationKey, translate } from '@/lib/translations';

type Consent = 'undecided' | 'accepted' | 'declined';
type Identification = 'none' | 'sample';
type Verification = { status: 'not-started' } | { status: 'pending'; expiresAt: number; attempts: number } | { status: 'verified'; expiresAt: number } | { status: 'locked' } | { status: 'expired' };
type Context = {
 language: Language; setLanguage: (language: Language) => void; t: (key: TranslationKey) => string;
 consent: Consent; chooseConsent: (value: Consent) => void; identification: Identification;
 verification: Verification; startSample: () => void; submitCode: (code: string) => void; restart: () => void;
};
const AppContext = createContext<Context | null>(null);
export function AppProvider({ children }: { children: React.ReactNode }) {
 const [language, setLanguage] = useState<Language>('en');
 const [consent, setConsent] = useState<Consent>('undecided');
 const [identification, setIdentification] = useState<Identification>('none');
 const [verification, setVerification] = useState<Verification>({ status: 'not-started' });
 function restart() { setConsent('undecided'); setIdentification('none'); setVerification({ status: 'not-started' }); }
 function chooseConsent(value: Consent) { setConsent(value); if (value !== 'accepted') { setIdentification('none'); setVerification({ status: 'not-started' }); } }
 function startSample() { setIdentification('sample'); setVerification({ status: 'pending', expiresAt: Date.now() + 5 * 60_000, attempts: 3 }); }
 function submitCode(code: string) { setVerification(current => {
  if (current.status !== 'pending') return current;
  if (Date.now() >= current.expiresAt) return { status: 'expired' };
  if (code === '1234') return { status: 'verified', expiresAt: current.expiresAt };
  return current.attempts <= 1 ? { status: 'locked' } : { ...current, attempts: current.attempts - 1 };
 }); }
 useEffect(() => {
  if (verification.status !== 'pending' && verification.status !== 'verified') return;
  const timer = window.setTimeout(() => setVerification(current => (current.status === 'pending' || current.status === 'verified') && Date.now() >= current.expiresAt ? { status: 'expired' } : current), Math.max(0, verification.expiresAt - Date.now()));
  return () => window.clearTimeout(timer);
 }, [verification]);
 useEffect(() => { document.documentElement.lang = language; return () => { if ('speechSynthesis' in window) window.speechSynthesis.cancel(); }; }, [language]);
 return <AppContext.Provider value={{ language, setLanguage, t: key => translate(language, key), consent, chooseConsent, identification, verification, startSample, submitCode, restart }}>{children}</AppContext.Provider>;
}
export function useApp() { const context = useContext(AppContext); if (!context) throw new Error('Missing AppProvider'); return context; }
