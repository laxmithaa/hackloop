"use client";

import React, { useState, useEffect, useRef } from "react";
import { Volume2, VolumeX, Pause, Play, Square, AlertCircle } from "lucide-react";
import type { Lang } from "@/lib/types/billing";

interface Props {
  textToRead: string;
  lang: Lang;
  title?: string;
  labels: {
    listenBtn: string;
    pauseBtn: string;
    resumeBtn: string;
    stopBtn: string;
    audioPlaying: string;
    audioUnavailable: string;
  };
}

export default function AudioPlayer({ textToRead, lang, title, labels }: Props) {
  const [isPlaying, setIsPlaying] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  const [isSupported, setIsSupported] = useState(true);
  const [selectedVoice, setSelectedVoice] = useState<string>("");
  const [availableVoices, setAvailableVoices] = useState<SpeechSynthesisVoice[]>([]);
  const utteranceRef = useRef<SpeechSynthesisUtterance | null>(null);

  useEffect(() => {
    if (typeof window === "undefined" || !("speechSynthesis" in window)) {
      setIsSupported(false);
      return;
    }

    const updateVoices = () => {
      const voices = window.speechSynthesis.getVoices();
      setAvailableVoices(voices);

      // Match voice for current lang
      const langCode = lang === "hi" ? "hi" : lang === "kn" ? "kn" : "en";
      const matchingVoice = voices.find((v) => v.lang.startsWith(langCode));
      if (matchingVoice) {
        setSelectedVoice(matchingVoice.name);
      }
    };

    updateVoices();
    if (window.speechSynthesis.onvoiceschanged !== undefined) {
      window.speechSynthesis.onvoiceschanged = updateVoices;
    }

    return () => {
      if (typeof window !== "undefined" && "speechSynthesis" in window) {
        window.speechSynthesis.cancel();
      }
    };
  }, [lang]);

  // Cancel speech if text or language changes
  useEffect(() => {
    if (typeof window !== "undefined" && "speechSynthesis" in window) {
      window.speechSynthesis.cancel();
      setIsPlaying(false);
      setIsPaused(false);
    }
  }, [textToRead, lang]);

  const handlePlay = () => {
    if (!isSupported || typeof window === "undefined") return;

    if (isPaused) {
      window.speechSynthesis.resume();
      setIsPaused(false);
      setIsPlaying(true);
      return;
    }

    window.speechSynthesis.cancel();

    const utterance = new SpeechSynthesisUtterance(textToRead);
    utterance.lang = lang === "hi" ? "hi-IN" : lang === "kn" ? "kn-IN" : "en-IN";
    utterance.rate = 0.92; // Slightly measured pace for elderly / clear comprehension

    if (selectedVoice && availableVoices.length > 0) {
      const voice = availableVoices.find((v) => v.name === selectedVoice);
      if (voice) utterance.voice = voice;
    }

    utterance.onstart = () => {
      setIsPlaying(true);
      setIsPaused(false);
    };

    utterance.onend = () => {
      setIsPlaying(false);
      setIsPaused(false);
    };

    utterance.onerror = (e) => {
      if (e.error !== "canceled") {
        setIsPlaying(false);
        setIsPaused(false);
      }
    };

    utteranceRef.current = utterance;
    window.speechSynthesis.speak(utterance);
  };

  const handlePause = () => {
    if (typeof window === "undefined" || !("speechSynthesis" in window)) return;
    if (isPlaying && !isPaused) {
      window.speechSynthesis.pause();
      setIsPaused(true);
    }
  };

  const handleStop = () => {
    if (typeof window === "undefined" || !("speechSynthesis" in window)) return;
    window.speechSynthesis.cancel();
    setIsPlaying(false);
    setIsPaused(false);
  };

  if (!isSupported) {
    return (
      <div
        role="status"
        className="flex items-center gap-2 p-3 bg-slate-50 border border-slate-200 rounded-xl text-slate-700 text-sm"
      >
        <VolumeX className="w-5 h-5 text-slate-500 flex-shrink-0" aria-hidden="true" />
        <span>{labels.audioUnavailable}</span>
      </div>
    );
  }

  return (
    <div
      role="region"
      aria-label="Audio Reader"
      className="p-4 bg-blue-50/70 border border-blue-200 rounded-2xl flex flex-wrap items-center justify-between gap-4"
    >
      <div className="flex items-center gap-3">
        <div
          className={`w-11 h-11 rounded-xl flex items-center justify-center ${
            isPlaying ? "bg-blue-600 text-white animate-pulse" : "bg-blue-100 text-blue-700"
          }`}
          aria-hidden="true"
        >
          <Volume2 className="w-6 h-6" />
        </div>
        <div>
          <h3 className="font-bold text-slate-900 text-base">
            {title || (lang === "hi" ? "ऑडियो विवरण" : lang === "kn" ? "ಧ್ವನಿ ವಿವರಣೆ" : "Audio Narration")}
          </h3>
          <p className="text-xs text-slate-600">
            {isPlaying
              ? isPaused
                ? "Audio Paused"
                : labels.audioPlaying
              : lang === "hi"
              ? "पूरी व्याख्या को स्पष्ट आवाज़ में सुनें"
              : lang === "kn"
              ? "ಸಂಪೂರ್ಣ ವಿವರಣೆಯನ್ನು ಆಲಿಸಿ"
              : "Listen to the explanation read aloud"}
          </p>
        </div>
      </div>

      {/* Control Buttons */}
      <div className="flex items-center gap-2">
        {!isPlaying ? (
          <button
            type="button"
            onClick={handlePlay}
            className="inline-flex items-center gap-2 px-5 py-2.5 bg-blue-600 hover:bg-blue-700 active:bg-blue-800 text-white font-bold rounded-xl shadow-sm transition-all text-sm touch-target focus-visible:ring-2 focus-visible:ring-blue-600 focus-visible:ring-offset-2"
            aria-label={labels.listenBtn}
          >
            <Play className="w-4 h-4 fill-current" aria-hidden="true" />
            <span>{labels.listenBtn}</span>
          </button>
        ) : (
          <>
            {isPaused ? (
              <button
                type="button"
                onClick={handlePlay}
                className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-xl text-sm touch-target"
                aria-label={labels.resumeBtn}
              >
                <Play className="w-4 h-4 fill-current" aria-hidden="true" />
                <span>{labels.resumeBtn}</span>
              </button>
            ) : (
              <button
                type="button"
                onClick={handlePause}
                className="inline-flex items-center gap-2 px-4 py-2 bg-amber-600 hover:bg-amber-700 text-white font-semibold rounded-xl text-sm touch-target"
                aria-label={labels.pauseBtn}
              >
                <Pause className="w-4 h-4" aria-hidden="true" />
                <span>{labels.pauseBtn}</span>
              </button>
            )}

            <button
              type="button"
              onClick={handleStop}
              className="inline-flex items-center gap-2 px-4 py-2 bg-slate-200 hover:bg-slate-300 active:bg-slate-400 text-slate-800 font-semibold rounded-xl text-sm touch-target"
              aria-label={labels.stopBtn}
            >
              <Square className="w-4 h-4 fill-current" aria-hidden="true" />
              <span>{labels.stopBtn}</span>
            </button>
          </>
        )}
      </div>
    </div>
  );
}
