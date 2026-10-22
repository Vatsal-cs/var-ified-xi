// File: ui.tsx
// Path: var-ified-xi/frontend/components/ui.tsx
//
// Small shared building blocks so every section looks and explains itself the
// same way: a titled section with a plain-language subtitle, a hoverable
// jargon term, an inline explainer note, and a stat tile.

import { Reveal } from "./motion";
import type { ReactNode } from "react";

/** A page section with a heading and a one-line plain description. */
export type Tone = "gold" | "violet" | "sky" | "pts" | "coral";

const TONE_TEXT: Record<Tone, string> = {
  gold: "text-gold", violet: "text-violet", sky: "text-sky", pts: "text-pts", coral: "text-coral",
};

export function Section({
  id,
  eyebrow,
  title,
  lede,
  children,
  tone = "gold",
}: {
  id?: string;
  eyebrow?: string;
  title: string;
  lede?: string;
  children: ReactNode;
  /** The section's accent: the colour of its eyebrow. */
  tone?: Tone;
}) {
  return (
    <Reveal>
      <section id={id} aria-labelledby={id ? `${id}-h` : undefined} className="scroll-mt-32">
        {eyebrow && <p className={`label mb-2 ${TONE_TEXT[tone]}`}>{eyebrow}</p>}
        <h2
          id={id ? `${id}-h` : undefined}
          className="max-w-3xl text-[26px] font-semibold leading-tight tracking-[-0.025em] text-ink-100 sm:text-[32px]"
        >
          {title}
        </h2>
        {lede && <p className="mt-2 max-w-[62ch] prose-note">{lede}</p>}
        <div className="mt-6">{children}</div>
      </section>
    </Reveal>
  );
}

/** A jargon term with a plain-language tooltip on hover / focus. */
export function Term({ children, explain }: { children: ReactNode; explain: string }) {
  return (
    <abbr title={explain} className="term no-underline">
      {children}
    </abbr>
  );
}

/** A boxed aside for a concept worth spelling out where it's first used. */
export function InfoNote({ title, children }: { title?: string; children: ReactNode }) {
  return (
    <div className="callout">
      {title && (
        <p className="label mb-1">
          {title}
        </p>
      )}
      <p className="font-body text-sm leading-relaxed text-ink-300">{children}</p>
    </div>
  );
}

/** A single labelled number. */
export function Stat({
  label,
  value,
  sub,
  tone = "default",
}: {
  label: ReactNode;
  value: ReactNode;
  sub?: ReactNode;
  tone?: "default" | "accent" | Tone;
}) {
  const t: Tone | null = tone === "accent" ? "pts" : tone === "default" ? null : tone;
  return (
    <div className="border-t border-line pt-3">
      <p className="label">{label}</p>
      <p className={`mt-1.5 stat ${t ? TONE_TEXT[t] : ""}`}>{value}</p>
      {sub && <p className="mt-1.5 text-xs text-ink-400">{sub}</p>}
    </div>
  );
}

/** Position pill (GK / DEF / MID / FWD). */
export function PosPill({ pos }: { pos: string }) {
  const tone: Record<string, string> = {
    GK: "text-warn border-warn/30",
    DEF: "text-sky border-sky/30",
    MID: "text-pts border-pts/30",
    FWD: "text-risk border-risk/30",
  };
  return (
    <span
      className={`inline-flex h-5 min-w-[2.4rem] items-center justify-center rounded-md border px-1 text-[10.5px] font-semibold ${
        tone[pos] ?? "text-ink-300 border-line"
      }`}
    >
      {pos}
    </span>
  );
}
