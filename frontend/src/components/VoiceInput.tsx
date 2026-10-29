"use client";

import React, { useState, useEffect, useRef } from "react";
import { Mic, MicOff, Check, Edit3, AlertCircle, RefreshCw } from "lucide-react";
import type { Lang } from "@/lib/types/billing";

interface Props {
  lang: Lang;
  onConfirmText: (text: string) => void;
  labels: {
    voiceBtnStart: string;
    voiceBtnStop: string;
    voiceListening: string;
    voiceReviewLabel: string;
    voiceEditHint: string;
    voiceConfirmBtn: string;
    voiceUnavailable: string;
  };
}

export default function VoiceInput({ lang, onConfirmText, labels }: Props) {
  const [isRecording, setIsRecording] = useState(false);
  const [isSupported, setIsSupported] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [recognizedText, setRecognizedText] = useState("");
  const [editableText, setEditableText] = useState("");

  const recognitionRef = useRef<any>(null);

  useEffect(() => {
    const SpeechRecognition =
      (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;

    if (!SpeechRecognition) {
      setIsSupported(false);
      return;
    }

    try {
      const recognition = new SpeechRecognition();
      recognition.continuous = false;
      recognition.interimResults = true;
      recognition.lang = lang === "hi" ? "hi-IN" : lang === "kn" ? "kn-IN" : "en-IN";

      recognition.onstart = () => {
        setIsRecording(true);
        setErrorMessage(null);
      };

      recognition.onresult = (event: any) => {
        let transcript = "";
        for (let i = event.resultIndex; i < event.results.length; ++i) {
          transcript += event.results[i][0].transcript;
        }
        setRecognizedText(transcript);
        setEditableText(transcript);
      };

      recognition.onerror = (event: any) => {
        setIsRecording(false);
        if (event.error === "not-allowed") {
          setErrorMessage(
            lang === "hi"
              ? "माइक्रोफ़ोन अनुमति अस्वीकृत है। कृपया ब्राउज़र सेटिंग में अनुमति दें।"
              : lang === "kn"
              ? "ಮೈಕ್ರೊಫೋನ್ ಅನುಮತಿ ನಿರಾಕರಿಸಲಾಗಿದೆ. ದಯವಿಟ್ಟು ಅನುಮತಿ ನೀಡಿ."
              : "Microphone permission was denied. Please allow microphone access in your browser settings."
          );
        } else if (event.error === "no-speech") {
          setErrorMessage(
            lang === "hi"
              ? "कोई आवाज़ नहीं सुनी गई। कृपया दोबारा कोशिश करें।"
              : lang === "kn"
              ? "ಯಾವುದೇ ಧ್ವನಿ ಕೇಳಲಿಲ್ಲ. ದಯವಿಟ್ಟು ಮತ್ತೆ ಪ್ರಯತ್ನಿಸಿ."
              : "No speech detected. Please press the microphone and speak clearly."
          );
        } else {
          setErrorMessage(
            lang === "hi"
              ? `आवाज़ पहचान त्रुटि: ${event.error}`
              : lang === "kn"
              ? `ಧ್ವನಿ ದೋಷ: ${event.error}`
              : `Speech recognition error: ${event.error}`
          );
        }
      };

      recognition.onend = () => {
        setIsRecording(false);
      };

      recognitionRef.current = recognition;
    } catch (err) {
      setIsSupported(false);
    }

    return () => {
      if (recognitionRef.current) {
        try {
          recognitionRef.current.abort();
        } catch (e) {}
      }
    };
  }, [lang]);

  const handleStart = () => {
    if (!isSupported || !recognitionRef.current) return;
    setErrorMessage(null);
    setRecognizedText("");
    setEditableText("");
    try {
      recognitionRef.current.lang = lang === "hi" ? "hi-IN" : lang === "kn" ? "kn-IN" : "en-IN";
      recognitionRef.current.start();
    } catch (err) {
      // If already started, stop then restart
      try {
        recognitionRef.current.stop();
        setTimeout(() => recognitionRef.current.start(), 200);
      } catch (e) {}
    }
  };

  const handleStop = () => {
    if (recognitionRef.current && isRecording) {
      try {
        recognitionRef.current.stop();
      } catch (e) {}
    }
    setIsRecording(false);
  };

  const handleConfirm = () => {
    if (editableText.trim()) {
      onConfirmText(editableText.trim());
      setRecognizedText("");
      setEditableText("");
    }
  };

  if (!isSupported) {
    return (
      <div className="text-xs text-slate-500 bg-slate-100 p-2.5 rounded-lg border border-slate-200 flex items-center gap-2">
        <AlertCircle className="w-4 h-4 text-slate-500 flex-shrink-0" />
        <span>{labels.voiceUnavailable}</span>
      </div>
    );
  }

  return (
    <div className="w-full bg-slate-50 border border-slate-200 rounded-xl p-4 my-2">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <span className="text-xs font-bold uppercase tracking-wider text-slate-500 bg-slate-200 px-2 py-0.5 rounded">
            {lang === "hi" ? "आवाज़ इनपुट" : lang === "kn" ? "ಧ್ವನಿ ಇನ್‌ಪುಟ್" : "Voice Input"} (
            {lang === "hi" ? "हिंदी" : lang === "kn" ? "ಕನ್ನಡ" : "English"})
          </span>
          {isRecording && (
            <span className="inline-flex items-center gap-1.5 text-xs font-bold text-red-600 animate-pulse">
              <span className="w-2.5 h-2.5 rounded-full bg-red-600" />
              {labels.voiceListening}
            </span>
          )}
        </div>

        <div>
          {!isRecording ? (
            <button
              type="button"
              onClick={handleStart}
              className="inline-flex items-center gap-2 px-4 py-2 bg-teal-700 hover:bg-teal-800 active:bg-teal-900 text-white font-bold rounded-lg text-sm shadow-sm transition-colors touch-target focus-visible:ring-2 focus-visible:ring-teal-700"
              aria-label={labels.voiceBtnStart}
            >
              <Mic className="w-4 h-4" />
              <span>{labels.voiceBtnStart}</span>
            </button>
          ) : (
            <button
              type="button"
              onClick={handleStop}
              className="inline-flex items-center gap-2 px-4 py-2 bg-red-600 hover:bg-red-700 text-white font-bold rounded-lg text-sm shadow-sm animate-pulse touch-target"
              aria-label={labels.voiceBtnStop}
            >
              <MicOff className="w-4 h-4" />
              <span>{labels.voiceBtnStop}</span>
            </button>
          )}
        </div>
      </div>

      {errorMessage && (
        <div
          role="alert"
          className="mt-3 p-3 bg-red-50 border border-red-200 text-red-800 text-xs rounded-lg flex items-center gap-2"
        >
          <AlertCircle className="w-4 h-4 text-red-600 flex-shrink-0" />
          <span>{errorMessage}</span>
        </div>
      )}

      {/* Review & Edit Transcript Box */}
      {(recognizedText || editableText) && (
        <div className="mt-4 pt-3 border-t border-slate-200">
          <label htmlFor="voice-edit-transcript" className="block text-xs font-bold text-slate-700 mb-1 flex items-center gap-1.5">
            <Edit3 className="w-3.5 h-3.5 text-slate-500" />
            <span>{labels.voiceReviewLabel}</span>
          </label>
          <p className="text-xs text-slate-500 mb-2">{labels.voiceEditHint}</p>
          <textarea
            id="voice-edit-transcript"
            value={editableText}
            onChange={(e) => setEditableText(e.target.value)}
            rows={2}
            className="w-full p-2.5 bg-white border border-slate-300 rounded-lg text-sm text-slate-900 focus-visible:ring-2 focus-visible:ring-blue-600"
          />
          <div className="mt-2 flex justify-end gap-2">
            <button
              type="button"
              onClick={() => {
                setRecognizedText("");
                setEditableText("");
              }}
              className="px-3 py-1.5 text-xs text-slate-600 hover:bg-slate-200 rounded-lg font-semibold"
            >
              Clear
            </button>
            <button
              type="button"
              onClick={handleConfirm}
              disabled={!editableText.trim()}
              className="inline-flex items-center gap-1.5 px-4 py-2 bg-blue-700 hover:bg-blue-800 disabled:opacity-50 text-white font-bold text-xs rounded-lg shadow-sm"
            >
              <Check className="w-3.5 h-3.5" />
              <span>{labels.voiceConfirmBtn}</span>
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
