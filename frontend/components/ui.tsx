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
const TONE_DOT: Record<Tone, string> = {
  gold: "bg-gold", violet: "bg-violet", sky: "bg-sky", pts: "bg-pts", coral: "bg-coral",
};
const TONE_RULE: Record<Tone, string> = {
  gold: "from-gold/60", violet: "from-violet/60", sky: "from-sky/60", pts: "from-pts/60", coral: "from-coral/60",
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
  /** The section's accent: its eyebrow, dot and rule. */
  tone?: Tone;
}) {
  return (
    <Reveal>
    <section id={id} aria-labelledby={id ? `${id}-h` : undefined} className="scroll-mt-32">
      {eyebrow && (
        <p className="mb-4 flex items-center gap-3">
          <span aria-hidden className={`h-1.5 w-1.5 rounded-full ${TONE_DOT[tone]} shadow-[0_0_10px_currentColor] ${TONE_TEXT[tone]}`} />
          <span className={`font-mono text-[10px] font-medium uppercase tracking-[0.28em] ${TONE_TEXT[tone]}`}>
            {eyebrow}
          </span>
          <span aria-hidden className={`h-px flex-1 bg-gradient-to-r ${TONE_RULE[tone]} to-transparent`} />
        </p>
      )}
      <h2
        id={id ? `${id}-h` : undefined}
        className="max-w-3xl font-display text-[38px] leading-[1.05] tracking-[-0.015em] text-gradient-gold sm:text-[52px]"
      >
        {title}
      </h2>
      {lede && <p className="mt-3 max-w-[58ch] prose-note">{lede}</p>}
      <div className="mt-8">{children}</div>
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
    <div className="rounded-[2px] border border-line bg-surface-raised/60 p-4">
      {title && (
        <p className="mb-1 font-mono text-[11px] uppercase tracking-[0.16em] text-ink-400">
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
    <div className="panel group relative overflow-hidden p-4 transition-all duration-300 hover:-translate-y-0.5 hover:border-line-strong">
      {t && <span aria-hidden className={`absolute inset-x-0 top-0 h-[2px] ${TONE_DOT[t]} opacity-80`} />}
      {t && (
        <span
          aria-hidden
          className={`pointer-events-none absolute -right-8 -top-8 h-24 w-24 rounded-full ${TONE_DOT[t]} opacity-[0.07] blur-2xl transition-opacity duration-300 group-hover:opacity-[0.16]`}
        />
      )}
      <p className="label">{label}</p>
      <p className={`mt-1.5 stat ${t ? TONE_TEXT[t] : ""}`}>{value}</p>
      {sub && <p className="mt-1.5 font-body text-xs text-ink-400">{sub}</p>}
    </div>
  );
}

/** Position pill (GK / DEF / MID / FWD). */
export function PosPill({ pos }: { pos: string }) {
  const tone: Record<string, string> = {
    GK: "text-amber-300/90 border-warn/30",
    DEF: "text-sky-300/90 border-sky-400/30",
    MID: "text-pts border-pts/30",
    FWD: "text-risk border-risk/30",
  };
  return (
    <span
      className={`inline-flex h-5 min-w-[2.4rem] items-center justify-center rounded border px-1 font-mono text-[10px] font-medium ${
        tone[pos] ?? "text-ink-300 border-line"
      }`}
    >
      {pos}
    </span>
  );
}
