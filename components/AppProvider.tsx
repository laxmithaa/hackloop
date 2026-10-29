'use client';
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';
import { Language, TranslationKey, translate } from '@/lib/translations';
import {
  createSession,
  fetchVerifiedBill,
  grantConsent,
  identifyByBillNumber,
  identifyByPhoto,
  isAbortError,
  isApiError,
  verifyAccessCode,
  withdrawConsent,
  type IdentificationResult,
  type VerificationResult,
  type VerifiedBill,
} from '@/lib/api';
import { describeApiError, type ApiFailure } from '@/lib/apiErrors';

type Consent = 'undecided' | 'accepted' | 'declined';
type VerificationStatus = 'not-started' | 'pending' | 'verified' | 'locked' | 'expired';
type BillState =
  | { status: 'idle' | 'loading' | 'ready' }
  | { status: 'error'; failure: ApiFailure };

type Context = {
  language: Language;
  setLanguage: (language: Language) => void;
  t: (key: TranslationKey) => string;
  consent: Consent;
  consentBusy: boolean;
  consentFailure: ApiFailure | null;
  chooseConsent: (value: 'accepted' | 'declined') => Promise<void>;
  sessionId: string | null;
  identification: IdentificationResult | null;
  identifying: boolean;
  identificationFailure: ApiFailure | null;
  identifyFromPhoto: (file: File) => Promise<void>;
  identifyFromNumber: (billNumber: string, hospitalIdentifier: string) => Promise<void>;
  clearIdentification: () => void;
  cancelIdentification: () => void;
  verification: VerificationStatus;
  verificationDetail: VerificationResult | null;
  verificationFailure: ApiFailure | null;
  verifying: boolean;
  verifyCode: (code: string) => Promise<boolean>;
  bill: VerifiedBill | null;
  billState: BillState;
  loadBill: () => Promise<void>;
  restart: () => void;
};

const AppContext = createContext<Context | null>(null);

const NO_SESSION_FAILURE: ApiFailure = {
  code: 'session_missing',
  status: 0,
  key: 'sessionMissing',
  message: 'No active session.',
};

export function AppProvider({ children }: { children: React.ReactNode }) {
  const [language, setLanguage] = useState<Language>('en');
  const [consent, setConsent] = useState<Consent>('undecided');
  const [consentBusy, setConsentBusy] = useState(false);
  const [consentFailure, setConsentFailure] = useState<ApiFailure | null>(null);
  const [sessionId, setSessionIdState] = useState<string | null>(null);
  const [identification, setIdentification] = useState<IdentificationResult | null>(null);
  const [identifying, setIdentifying] = useState(false);
  const [identificationFailure, setIdentificationFailure] = useState<ApiFailure | null>(null);
  const [verification, setVerification] = useState<VerificationStatus>('not-started');
  const [verificationDetail, setVerificationDetail] = useState<VerificationResult | null>(null);
  const [verificationFailure, setVerificationFailure] = useState<ApiFailure | null>(null);
  const [verifying, setVerifying] = useState(false);
  const [bill, setBill] = useState<VerifiedBill | null>(null);
  const [billState, setBillState] = useState<BillState>({ status: 'idle' });

  const sessionRef = useRef<string | null>(null);
  const requestRef = useRef<AbortController | null>(null);
  const identifyingRef = useRef(false);

  /** State updates and the ref must move together so async actions never use a stale id. */
  const setSessionId = useCallback((id: string | null) => {
    sessionRef.current = id;
    setSessionIdState(id);
  }, []);

  const clearVerificationAndBill = useCallback(() => {
    setVerification('not-started');
    setVerificationDetail(null);
    setVerificationFailure(null);
    setBill(null);
    setBillState({ status: 'idle' });
  }, []);

  const clearIdentification = useCallback(() => {
    setIdentification(null);
    setIdentificationFailure(null);
    clearVerificationAndBill();
  }, [clearVerificationAndBill]);

  const cancelIdentification = useCallback(() => {
    requestRef.current?.abort();
    requestRef.current = null;
    identifyingRef.current = false;
    setIdentifying(false);
  }, []);

  const resetJourneyState = useCallback(() => {
    requestRef.current?.abort();
    requestRef.current = null;
    identifyingRef.current = false;
    setIdentification(null);
    setIdentificationFailure(null);
    setIdentifying(false);
    clearVerificationAndBill();
  }, [clearVerificationAndBill]);

  const restart = useCallback(() => {
    const id = sessionRef.current;
    resetJourneyState();
    setSessionId(null);
    setConsent('undecided');
    setConsentFailure(null);
    setConsentBusy(false);
    if (id) void withdrawConsent(id).catch(() => undefined);
  }, [resetJourneyState, setSessionId]);

  const handleSessionFailure = useCallback(
    (error: unknown) => {
      if (
        isApiError(error) &&
        (error.code === 'session_not_found' || error.code === 'session_expired')
      ) {
        setSessionId(null);
      }
    },
    [setSessionId],
  );

  const chooseConsent = useCallback(
    async (value: 'accepted' | 'declined') => {
      setConsentBusy(true);
      setConsentFailure(null);

      if (value === 'declined') {
        const id = sessionRef.current;
        resetJourneyState();
        setSessionId(null);
        setConsent('declined');
        if (id) {
          try {
            await withdrawConsent(id);
          } catch {
            setConsentFailure({
              code: 'consent_withdraw_failed',
              status: 0,
              key: 'consentWithdrawFailed',
              message: 'Withdrawal could not be confirmed with the service.',
            });
          }
        }
        setConsentBusy(false);
        return;
      }

      try {
        const hadSession = Boolean(sessionRef.current);
        let id = sessionRef.current;
        if (!id) {
          const created = await createSession();
          id = created.sessionId;
          setSessionId(id);
        }
        try {
          await grantConsent(id);
        } catch (error) {
          // A backend restart drops in-memory sessions; create a fresh one and
          // record consent again instead of pretending consent was accepted.
          if (
            isApiError(error) &&
            (error.code === 'session_not_found' || error.code === 'session_expired')
          ) {
            const created = await createSession();
            id = created.sessionId;
            setSessionId(id);
            await grantConsent(id);
          } else {
            throw error;
          }
        }
        // A brand-new session cannot own the previous session's identification.
        if (!hadSession) {
          setIdentification(null);
          clearVerificationAndBill();
        }
        setConsent('accepted');
      } catch (error) {
        setConsentFailure(describeApiError(error));
      } finally {
        setConsentBusy(false);
      }
    },
    [clearVerificationAndBill, resetJourneyState, setSessionId],
  );

  const beginIdentification = useCallback(() => {
    const session = sessionRef.current;
    if (!session) {
      setIdentificationFailure(NO_SESSION_FAILURE);
      return null;
    }
    // A second click in the same tick must not start a second upload.
    if (identifyingRef.current) return null;
    identifyingRef.current = true;
    requestRef.current?.abort();
    const controller = new AbortController();
    requestRef.current = controller;
    setIdentifying(true);
    setIdentification(null);
    setIdentificationFailure(null);
    clearVerificationAndBill();
    return { session, controller };
  }, [clearVerificationAndBill]);

  const finishIdentification = useCallback(
    (result: IdentificationResult) => {
      setIdentification(result);
      if (result.status === 'access_code_required') setVerification('pending');
    },
    [],
  );

  const identifyFromPhoto = useCallback(
    async (file: File) => {
      const started = beginIdentification();
      if (!started) return;
      try {
        const result = await identifyByPhoto(started.session, file, started.controller.signal);
        if (started.controller.signal.aborted) return;
        finishIdentification(result);
      } catch (error) {
        if (isAbortError(error) || started.controller.signal.aborted) return;
        handleSessionFailure(error);
        setIdentificationFailure(describeApiError(error));
      } finally {
        identifyingRef.current = false;
        if (requestRef.current === started.controller) {
          requestRef.current = null;
          setIdentifying(false);
        }
      }
    },
    [beginIdentification, finishIdentification, handleSessionFailure],
  );

  const identifyFromNumber = useCallback(
    async (billNumber: string, hospitalIdentifier: string) => {
      const started = beginIdentification();
      if (!started) return;
      try {
        const result = await identifyByBillNumber(
          started.session,
          billNumber,
          hospitalIdentifier || undefined,
          started.controller.signal,
        );
        if (started.controller.signal.aborted) return;
        finishIdentification(result);
      } catch (error) {
        if (isAbortError(error) || started.controller.signal.aborted) return;
        handleSessionFailure(error);
        setIdentificationFailure(describeApiError(error));
      } finally {
        identifyingRef.current = false;
        if (requestRef.current === started.controller) {
          requestRef.current = null;
          setIdentifying(false);
        }
      }
    },
    [beginIdentification, finishIdentification, handleSessionFailure],
  );

  const verifyCode = useCallback(
    async (code: string): Promise<boolean> => {
      const session = sessionRef.current;
      if (!session) {
        setVerificationFailure(NO_SESSION_FAILURE);
        return false;
      }
      if (!identification || identification.status !== 'access_code_required') {
        setVerificationFailure({
          code: 'identification_missing',
          status: 0,
          key: 'identificationMissing',
          message: 'No identified bill in this session.',
        });
        return false;
      }

      setVerifying(true);
      setVerificationFailure(null);
      try {
        const detail = await verifyAccessCode(identification.identification_id, session, code);
        setVerificationDetail(detail);
        setVerification('verified');
        return true;
      } catch (error) {
        setVerificationFailure(describeApiError(error));
        if (isApiError(error)) {
          switch (error.code) {
            case 'verification_locked':
              setVerification('locked');
              break;
            case 'verification_challenge_expired':
            case 'identification_not_found':
              setVerification('expired');
              break;
            case 'session_not_found':
            case 'session_expired':
              setSessionId(null);
              setVerification('expired');
              break;
            default:
              break;
          }
        }
        return false;
      } finally {
        setVerifying(false);
      }
    },
    [identification, setSessionId],
  );

  const loadBill = useCallback(async () => {
    const session = sessionRef.current;
    if (!session) {
      setBillState({ status: 'error', failure: NO_SESSION_FAILURE });
      return;
    }
    if (!identification) {
      setBillState({
        status: 'error',
        failure: {
          code: 'identification_missing',
          status: 0,
          key: 'identificationMissing',
          message: 'No identified bill in this session.',
        },
      });
      return;
    }

    setBillState({ status: 'loading' });
    try {
      const data = await fetchVerifiedBill(identification.identification_id, session);
      setBill(data);
      setBillState({ status: 'ready' });
    } catch (error) {
      const failure = describeApiError(error);
      if (
        isApiError(error) &&
        (error.code === 'verification_required' ||
          error.code === 'verification_challenge_expired' ||
          error.code === 'identification_not_found')
      ) {
        setVerification('expired');
      }
      if (
        isApiError(error) &&
        (error.code === 'session_not_found' || error.code === 'session_expired')
      ) {
        setSessionId(null);
        setVerification('expired');
      }
      setBillState({ status: 'error', failure });
    }
  }, [identification, setSessionId]);

  const t = useCallback(
    (key: TranslationKey) => translate(language, key),
    [language],
  );

  useEffect(() => {
    document.documentElement.lang = language;
    return () => {
      if ('speechSynthesis' in window) window.speechSynthesis.cancel();
    };
  }, [language]);

  useEffect(
    () => () => {
      requestRef.current?.abort();
    },
    [],
  );

  const value = useMemo<Context>(
    () => ({
      language,
      setLanguage,
      t,
      consent,
      consentBusy,
      consentFailure,
      chooseConsent,
      sessionId,
      identification,
      identifying,
      identificationFailure,
      identifyFromPhoto,
      identifyFromNumber,
      clearIdentification,
      cancelIdentification,
      verification,
      verificationDetail,
      verificationFailure,
      verifying,
      verifyCode,
      bill,
      billState,
      loadBill,
      restart,
    }),
    [
      language,
      t,
      consent,
      consentBusy,
      consentFailure,
      chooseConsent,
      sessionId,
      identification,
      identifying,
      identificationFailure,
      identifyFromPhoto,
      identifyFromNumber,
      clearIdentification,
      cancelIdentification,
      verification,
      verificationDetail,
      verificationFailure,
      verifying,
      verifyCode,
      bill,
      billState,
      loadBill,
      restart,
    ],
  );

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
}

export function useApp() {
  const context = useContext(AppContext);
  if (!context) throw new Error('Missing AppProvider');
  return context;
}
