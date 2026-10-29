/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          50: "#eff6ff",
          100: "#dbeafe",
          200: "#bfdbfe",
          500: "#3b82f6",
          600: "#2563eb",
          700: "#1d4ed8",
          800: "#1e40af",
          900: "#1e3a8a",
        },
        tealAccent: {
          50: "#f0fdfa",
          100: "#ccfbf1",
          500: "#14b8a6",
          700: "#0f766e",
          800: "#115e59",
        },
        surface: {
          light: "#ffffff",
          subtle: "#f8fafc",
          raised: "#f1f5f9",
          border: "#e2e8f0",
        },
      },
      fontFamily: {
        sans: [
          "var(--font-jakarta)",
          "-apple-system",
          "BlinkMacSystemFont",
          "Segoe UI",
          "Roboto",
          "Noto Sans Devanagari",
          "Noto Sans Kannada",
          "sans-serif",
        ],
      },
      fontSize: {
        "fluid-lg": "clamp(1.125rem, 1rem + 0.5vw, 1.35rem)",
        "fluid-xl": "clamp(1.35rem, 1.15rem + 0.8vw, 1.75rem)",
        "fluid-2xl": "clamp(1.75rem, 1.4rem + 1.2vw, 2.25rem)",
      },
    },
  },
  plugins: [],
};
