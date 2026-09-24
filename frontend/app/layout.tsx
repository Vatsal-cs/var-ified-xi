// File: layout.tsx
// Path: var-ified-xi/frontend/app/layout.tsx

import type { Metadata } from "next";
import { Instrument_Serif, Inter_Tight, JetBrains_Mono } from "next/font/google";
import "./globals.css";

// A high-contrast editorial serif. Football's best print — matchday
// programmes, Wisden, Rothmans — was always set in serif, and it is the
// single thing that stops a stats site looking like a dashboard template.
const display = Instrument_Serif({
  subsets: ["latin"],
  weight: ["400"],
  style: ["normal", "italic"],
  variable: "--font-display",
});

// Tighter and more drawn than plain Inter, which keeps captions and running
// copy from reading as default-UI.
const body = Inter_Tight({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  variable: "--font-body",
});

// Every number here is a measurement, and measurements line up.
const mono = JetBrains_Mono({
  subsets: ["latin"],
  weight: ["400", "500", "700"],
  variable: "--font-mono",
});

export const metadata: Metadata = {
  title: "VAR-ified XI — your FPL week, decided",
  description:
    "An FPL engine that predicts every player's points and solves for the best transfer to make this week — under the real rules. Reviewed weekly.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html
      lang="en"
      className={`${display.variable} ${body.variable} ${mono.variable}`}
    >
      <body className="min-h-screen bg-base font-body text-ink-200 antialiased">
        {children}
      </body>
    </html>
  );
}
