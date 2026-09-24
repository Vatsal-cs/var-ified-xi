// File: layout.tsx
// Path: var-ified-xi/frontend/app/layout.tsx

import type { Metadata } from "next";
import { Bricolage_Grotesque, JetBrains_Mono, Inter } from "next/font/google";
import "./globals.css";

// Bricolage carries the personality: a contemporary grotesque with real
// character in its wider weights, so headings feel designed rather than set.
const display = Bricolage_Grotesque({
  subsets: ["latin"],
  weight: ["600", "700", "800"],
  variable: "--font-display",
});

// Inter does the reading. It is deliberately neutral — the display face is
// doing the talking, and body copy here is often dense explanation.
const body = Inter({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  variable: "--font-body",
});

// Every number on this site is a measurement, and measurements line up.
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
