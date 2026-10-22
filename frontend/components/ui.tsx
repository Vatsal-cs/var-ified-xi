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
        {eyebrow && <p className={`kicker mb-2 ${TONE_TEXT[tone]}`}>{eyebrow}</p>}
        <h2
          id={id ? `${id}-h` : undefined}
          className="headline max-w-3xl text-[34px] sm:text-[42px]"
        >
          {title}
        </h2>
        {lede && <p className="mt-2 max-w-[60ch] text-[15px] leading-relaxed text-ink-300">{lede}</p>}
        <div className="mt-6">{children}</div>
      </section>
    </Reveal>
  );
}

/** The top of a page: what it is in a few words, one sentence, and its key
 *  numbers in a ruled row. Every page opens the same way. */
export function PageIntro({
  kicker,
  title,
  sub,
  figures = [],
}: {
  kicker?: ReactNode;
  title: string;
  sub?: ReactNode;
  figures?: { label: string; value: ReactNode; tone?: string }[];
}) {
  return (
    <header className="animate-rise">
      {kicker && <p className="kicker">{kicker}</p>}
      <h1 className="headline mt-3 text-[54px] sm:text-[84px]">
        {title}
      </h1>
      {sub && <p className="mt-4 max-w-[56ch] text-[17px] leading-relaxed text-ink-300">{sub}</p>}
      {figures.length > 0 && <Figures items={figures} className="mt-7" />}
    </header>
  );
}

/** Numbers in one ruled row (two by two on a phone): label over figure,
 *  divided by hairlines. No tiles. */
export function Figures({
  items,
  className = "",
}: {
  items: { label: string; value: ReactNode; tone?: string }[];
  className?: string;
}) {
  return (
    <dl className={`grid grid-cols-2 gap-y-5 border-t border-line pt-5 sm:flex ${className}`}>
      {items.map((n, i) => (
        <div
          key={n.label}
          className={`sm:pr-6 lg:pr-7 ${i % 2 === 1 ? "border-l border-line pl-5" : ""} ${
            i > 0 ? "sm:border-l sm:border-line sm:pl-6 lg:pl-7" : ""
          }`}
        >
          <dt className="whitespace-nowrap text-[12.5px] text-ink-400">{n.label}</dt>
          <dd className={`mt-1 whitespace-nowrap font-display text-[38px] font-extrabold leading-none tabular-nums ${n.tone ?? "text-ink-100"}`}>
            {n.value}
          </dd>
        </div>
      ))}
    </dl>
  );
}

/** A chip, drawn like the round tokens in the FPL app. */
const CHIP_STYLE: Record<string, { short: string; name: string; bg: string; fg: string }> = {
  "3xc": { short: "TC", name: "Triple Captain", bg: "#E3A93C", fg: "#2A1A00" },
  bboost: { short: "BB", name: "Bench Boost", bg: "#2E9D6A", fg: "#FFFFFF" },
  freehit: { short: "FH", name: "Free Hit", bg: "#7A5CD6", fg: "#FFFFFF" },
  wildcard: { short: "WC", name: "Wildcard", bg: "#D2553E", fg: "#FFFFFF" },
};

export function chipName(chip: string): string {
  return CHIP_STYLE[chip]?.name ?? chip;
}

export function ChipToken({ chip, size = 28, className = "" }: { chip: string; size?: number; className?: string }) {
  const c = CHIP_STYLE[chip] ?? { short: chip.slice(0, 2).toUpperCase(), name: chip, bg: "#777", fg: "#fff" };
  return (
    <span
      title={c.name}
      className={`inline-grid flex-none place-items-center rounded-full font-kit font-bold leading-none shadow-[inset_0_-2px_0_rgba(0,0,0,0.18)] ${className}`}
      style={{ width: size, height: size, background: c.bg, color: c.fg, fontSize: Math.round(size * 0.42) }}
    >
      {c.short}
    </span>
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
