import "@testing-library/jest-dom";
import { vi } from "vitest";

// Mock matchMedia
Object.defineProperty(window, "matchMedia", {
  writable: true,
  value: vi.fn().mockImplementation((query) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
});

// Mock SpeechSynthesis
const mockVoices = [
  { name: "Google US English", lang: "en-US", default: true, localService: true, voiceURI: "Google US English" },
  { name: "Google Hindi", lang: "hi-IN", default: false, localService: true, voiceURI: "Google Hindi" },
  { name: "Google Kannada", lang: "kn-IN", default: false, localService: true, voiceURI: "Google Kannada" },
];

Object.defineProperty(window, "speechSynthesis", {
  writable: true,
  value: {
    speak: vi.fn(),
    cancel: vi.fn(),
    pause: vi.fn(),
    resume: vi.fn(),
    getVoices: vi.fn().mockReturnValue(mockVoices),
    speaking: false,
    paused: false,
    onvoiceschanged: null,
  },
});

// Mock SpeechSynthesisUtterance
(globalThis as any).SpeechSynthesisUtterance = class {
  text: string;
  lang: string = "en-US";
  rate: number = 1;
  voice: any = null;
  onstart: any = null;
  onend: any = null;
  onerror: any = null;
  constructor(text: string) {
    this.text = text;
  }
};

// Mock SpeechRecognition
(window as any).SpeechRecognition = class {
  continuous: boolean = false;
  interimResults: boolean = true;
  lang: string = "en-IN";
  onstart: any = null;
  onresult: any = null;
  onerror: any = null;
  onend: any = null;
  start = vi.fn();
  stop = vi.fn();
  abort = vi.fn();
};

// Mock URL.createObjectURL
if (typeof window !== "undefined") {
  window.URL.createObjectURL = vi.fn().mockReturnValue("blob:mock-preview-url");
}

// Mock next/navigation
vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: vi.fn(),
    replace: vi.fn(),
    back: vi.fn(),
    forward: vi.fn(),
    refresh: vi.fn(),
    prefetch: vi.fn(),
  }),
  usePathname: () => "/",
  useSearchParams: () => new URLSearchParams(),
}));
