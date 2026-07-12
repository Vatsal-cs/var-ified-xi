// File: layout.tsx
// Path: var-ified-xi/frontend/app/layout.tsx

import type { Metadata } from "next";
import { Oswald, JetBrains_Mono, Inter } from "next/font/google";
import "./globals.css";

const oswald = Oswald({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  variable: "--font-oswald",
});

const jbMono = JetBrains_Mono({
  subsets: ["latin"],
  weight: ["400", "500", "700"],
  variable: "--font-jbmono",
});

const inter = Inter({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  variable: "--font-inter",
});

export const metadata: Metadata = {
  title: "VAR-ified XI",
  description: "Machine-checked. Math-approved. Your optimal FPL squad, reviewed.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${oswald.variable} ${jbMono.variable} ${inter.variable}`}>
      <body className="bg-pitch-night text-ink-100 font-body antialiased">{children}</body>
    </html>
  );
}
