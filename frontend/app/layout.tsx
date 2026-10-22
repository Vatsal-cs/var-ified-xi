// File: layout.tsx
// Path: var-ified-xi/frontend/app/layout.tsx

import type { Metadata } from "next";
import { Barlow_Semi_Condensed, Big_Shoulders, Geist_Mono, Schibsted_Grotesk } from "next/font/google";
import "./globals.css";

// Headlines and big figures: condensed, heavy, stadium signage.
const display = Big_Shoulders({ subsets: ["latin"], weight: ["700", "800", "900"], variable: "--font-display" });

// Everything you read: a newspaper grotesk with some character.
const sans = Schibsted_Grotesk({ subsets: ["latin"], variable: "--font-sans" });

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

// Runs before the first paint, so the page never flashes the wrong theme (the
// visitor's saved choice, otherwise their device's setting), and so blocks
// below the fold start with their animations held until they scroll into view
// (components/motion.tsx). If the app never hydrates, nothing stays held.
const THEME_SCRIPT = `(function(){var d=document.documentElement;try{var t=localStorage.getItem('vx-theme');if(t!=='light'&&t!=='dark'){t=matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light'}d.dataset.theme=t}catch(e){d.dataset.theme='light'}d.classList.add('js-reveal');setTimeout(function(){if(!window.__vxReveal)d.classList.remove('js-reveal')},4000)})()`;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html
      lang="en"
      suppressHydrationWarning
      className={`${display.variable} ${sans.variable} ${mono.variable} ${kit.variable}`}
    >
      <head>
        <script dangerouslySetInnerHTML={{ __html: THEME_SCRIPT }} />
      </head>
      <body className="min-h-screen bg-base font-body text-ink-200 antialiased">{children}</body>
    </html>
  );
}
