// File: layout.tsx
// Path: var-ified-xi/frontend/app/layout.tsx

import type { Metadata } from "next";
import { Oswald, JetBrains_Mono, Inter } from "next/font/google";
import "./globals.css";

const oswald = Oswald({
  subsets: ["latin"],
  weight: ["500", "600", "700"],
  variable: "--font-oswald",
});

const jbMono = JetBrains_Mono({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  variable: "--font-jbmono",
});

const inter = Inter({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  variable: "--font-inter",
});

export const metadata: Metadata = {
  title: "VAR-ified XI — your FPL week, decided",
  description:
    "An FPL engine that predicts every player's points and solves for the best transfer to make this week — under the real rules. Reviewed weekly.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${oswald.variable} ${jbMono.variable} ${inter.variable}`}>
      <body className="min-h-screen bg-pitch-night font-body text-ink-200 antialiased">
        {children}
      </body>
    </html>
  );
}
