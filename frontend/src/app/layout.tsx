import type { Metadata } from "next";
import "./globals.css";
import { LanguageProvider } from "@/lib/context/LanguageContext";

export const metadata: Metadata = {
  title: "Healthcare Bill Navigator — Your hospital bill, explained simply",
  description:
    "Plain-language, accessible medical bill explainer for patients, rural communities, and caregivers. Available in English, Hindi, and Kannada.",
  icons: {
    icon: "data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'><rect width='32' height='32' rx='6' fill='%231d4ed8'/><path d='M14 8h4v6h6v4h-6v6h-4v-6H8v-4h6V8z' fill='white'/></svg>",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=Noto+Sans+Devanagari:wght@400;600;700&family=Noto+Sans+Kannada:wght@400;600;700&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="antialiased min-h-screen flex flex-col bg-[#f8fafc] text-[#0f172a]">
        <LanguageProvider>
          {children}
        </LanguageProvider>
      </body>
    </html>
  );
}
