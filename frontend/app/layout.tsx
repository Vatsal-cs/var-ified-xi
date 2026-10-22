// File: layout.tsx
// Path: var-ified-xi/frontend/app/layout.tsx

import type { Metadata } from "next";
import { Barlow_Semi_Condensed, Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

// Clean and modern for everything you read.
const sans = Geist({ subsets: ["latin"], variable: "--font-sans" });

// Tabular figures for the small measurements.
const mono = Geist_Mono({ subsets: ["latin"], variable: "--font-mono" });

// The shirt-number face: condensed, bold, sporty.
const kit = Barlow_Semi_Condensed({
  subsets: ["latin"],
  weight: ["600", "700"],
  variable: "--font-kit",
});

export const metadata: Metadata = {
  title: "VAR-ified XI — your FPL week, decided",
  description:
    "An FPL engine that predicts every player's points and solves for the best transfer to make this week — under the real rules. Reviewed weekly.",
};

// Runs before the first paint, so the page never flashes the wrong theme:
// the visitor's saved choice, otherwise their device's setting.
const THEME_SCRIPT = `(function(){try{var t=localStorage.getItem('vx-theme');if(t!=='light'&&t!=='dark'){t=matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light'}document.documentElement.dataset.theme=t}catch(e){document.documentElement.dataset.theme='light'}})()`;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html
      lang="en"
      suppressHydrationWarning
      className={`${sans.variable} ${mono.variable} ${kit.variable}`}
    >
      <head>
        <script dangerouslySetInnerHTML={{ __html: THEME_SCRIPT }} />
      </head>
      <body className="min-h-screen bg-base font-body text-ink-200 antialiased">{children}</body>
    </html>
  );
}
