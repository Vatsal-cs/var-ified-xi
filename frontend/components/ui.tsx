// File: ui.tsx
// Path: var-ified-xi/frontend/components/ui.tsx
//
// Small shared building blocks so every section looks and explains itself the
// same way: a titled section with a plain-language subtitle, a hoverable
// jargon term, an inline explainer note, and a stat tile.

import type { ReactNode } from "react";

/** A page section with a heading and a one-line plain description. */
export function Section({
  id,
  eyebrow,
  title,
  lede,
  children,
}: {
  id?: string;
  eyebrow?: string;
  title: string;
  lede?: string;
  children: ReactNode;
}) {
  return (
    <section id={id} aria-labelledby={id ? `${id}-h` : undefined} className="scroll-mt-32">
      {eyebrow && (
        <p className="eyebrow-rule mb-4">
          <span className="font-mono text-[10px] font-medium uppercase tracking-[0.28em] text-gold">
            {eyebrow}
          </span>
        </p>
      )}
      <h2
        id={id ? `${id}-h` : undefined}
        className="max-w-3xl font-display text-[38px] leading-[1.05] tracking-[-0.015em] text-ink-100 sm:text-[52px]"
      >
        {title}
      </h2>
      {lede && <p className="mt-3 max-w-[58ch] prose-note">{lede}</p>}
      <div className="mt-8">{children}</div>
    </section>
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
  tone?: "default" | "accent";
}) {
  return (
    <div className="panel transition-colors duration-200 hover:border-line-strong p-4">
      <p className="label">{label}</p>
      <p className={`mt-1.5 stat ${tone === "accent" ? "text-pts" : ""}`}>{value}</p>
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
