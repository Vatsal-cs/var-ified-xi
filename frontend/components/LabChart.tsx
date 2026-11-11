// File: LabChart.tsx
// Path: var-ified-xi/frontend/components/LabChart.tsx
//
// Every tested change on one scale: points gained or lost against the model
// at the time, a dot for the estimate and a line for its 95% interval, so a
// line crossing zero reads as "the test can't tell" at a glance. Grouped by
// verdict; each row opens to the question, the seasons and the commits.
// Colour carries the verdict with the marker's shape as a second channel
// (filled dot, diamond, open ring), and every group is named in words.

import type { ReactNode } from "react";
import { LAB_TESTS, gap, commitDate, type LabTest, type Proof, type Verdict } from "@/lib/lab";

// The scale, wide enough for every interval.
const MIN = -300;
const MAX = 250;
const TICKS = [-300, -200, -100, 0, 100, 200];
const x = (v: number) => ((v - MIN) / (MAX - MIN)) * 100;

const GROUPS: { verdict: Verdict; name: string; blurb: string }[] = [
  {
    verdict: "shipped",
    name: "Shipped",
    blurb: "Better on the tuning seasons, then ahead on two seasons it never saw.",
  },
  {
    verdict: "worse",
    name: "Worse",
    blurb: "The whole interval below zero, and behind in both seasons.",
  },
  {
    verdict: "none",
    name: "No detectable effect",
    blurb: "The interval crosses zero: the test can't tell, so the model stays as it is.",
  },
];

const COLOUR: Record<Verdict, string> = {
  shipped: "rgb(var(--c-lab-good))",
  worse: "rgb(var(--c-lab-bad))",
  none: "rgb(var(--c-lab-none))",
};

/** −37, +92, 0: signed, with a real minus. */
export function signed(v: number): string {
  const r = Math.round(v);
  return r > 0 ? `+${r}` : r < 0 ? `−${Math.abs(r)}` : "0";
}

/** The verdict's marker: a filled dot, a diamond or an open ring, each with a
 *  ring of the page colour so it stands clear of its line. */
export function Marker({ verdict, className = "" }: { verdict: Verdict; className?: string }) {
  const colour = COLOUR[verdict];
  const halo = "0 0 0 2px rgb(var(--c-base))";
  if (verdict === "worse")
    return (
      <span
        aria-hidden
        className={`block h-[9px] w-[9px] rotate-45 rounded-[1px] ${className}`}
        style={{ background: colour, boxShadow: halo }}
      />
    );
  if (verdict === "none")
    return (
      <span
        aria-hidden
        className={`block h-[10px] w-[10px] rounded-full border-2 bg-[rgb(var(--c-base))] ${className}`}
        style={{ borderColor: colour, boxShadow: halo }}
      />
    );
  return (
    <span aria-hidden className={`block h-[10px] w-[10px] rounded-full ${className}`} style={{ background: colour, boxShadow: halo }} />
  );
}

/** The gridlines and the zero line, drawn into every row so they run
 *  unbroken down the chart. */
function Grid() {
  return (
    <>
      {TICKS.map((t) => (
        <span
          key={t}
          aria-hidden
          className={`absolute inset-y-0 w-px ${t === 0 ? "bg-ink-300" : "bg-[var(--c-line)]"}`}
          style={{ left: `${x(t)}%` }}
        />
      ))}
    </>
  );
}

function Plot({ t }: { t: LabTest }) {
  return (
    <div aria-hidden className="relative min-h-[28px] self-stretch [grid-area:plot]">
      <Grid />
      <span
        className="absolute top-1/2 h-[2px] -translate-y-1/2 rounded-full"
        style={{ left: `${x(t.lo)}%`, width: `${x(t.hi) - x(t.lo)}%`, background: COLOUR[t.verdict] }}
      />
      <span className="absolute top-1/2 -translate-x-1/2 -translate-y-1/2" style={{ left: `${x(t.est)}%` }}>
        <Marker verdict={t.verdict} />
      </span>
    </div>
  );
}

/** The scale's numbers, over the plot column. */
function Axis() {
  return (
    <div className="grid gap-x-4 grid-cols-[minmax(0,1fr)_4.75rem] md:grid-cols-[17rem_minmax(0,1fr)_7.5rem_1rem] [grid-template-areas:'plot_value'] md:[grid-template-areas:'label_plot_value_toggle']">
      <div className="relative h-6 [grid-area:plot]">
        {TICKS.map((t, i) => (
          <span
            key={t}
            // The outermost number crowds its neighbour on a phone.
            className={`absolute bottom-1 text-[11.5px] tabular-nums text-ink-400 ${i === 0 ? "hidden md:block" : ""}`}
            style={{ left: `${x(t)}%`, transform: i === 0 ? "none" : "translateX(-50%)" }}
          >
            {signed(t)}
          </span>
        ))}
      </div>
    </div>
  );
}

/** When the plan and the result went into the history, in words. */
export function ProofLine({ proof }: { proof: Proof }): ReactNode {
  // Each commit opens on GitHub, where its date and contents can be checked.
  const hash = (h: string) => (
    <a
      href={`https://github.com/Vatsal-cs/var-ified-xi/commit/${h}`}
      target="_blank"
      rel="noopener noreferrer"
      className="font-mono text-[12.5px] text-ink-300 underline decoration-line-strong underline-offset-2 transition-colors hover:text-ink-100 hover:decoration-ink-300"
    >
      {h}
    </a>
  );
  if (!proof.plan) return null;
  if (!proof.result)
    return (
      <>
        Plan committed {commitDate(proof.plan.at)} ({hash(proof.plan.hash)}), before any result.
      </>
    );
  const after = gap(proof);
  if (!after)
    return (
      <>
        Plan and result committed together, {commitDate(proof.plan.at)} ({hash(proof.plan.hash)}), so the history can&rsquo;t
        show which came first.
      </>
    );
  return (
    <>
      Plan committed {commitDate(proof.plan.at)} ({hash(proof.plan.hash)}), result {after} later ({hash(proof.result.hash)}).
    </>
  );
}

function Row({ t }: { t: LabTest }) {
  return (
    <li>
      <details className="group">
        <summary className="grid cursor-pointer list-none grid-cols-[minmax(0,1fr)_4.75rem] md:grid-cols-[17rem_minmax(0,1fr)_7.5rem_1rem] items-center gap-x-4 gap-y-1 py-2.5 [grid-template-areas:'label_toggle'_'plot_value'] marker:content-none hover:bg-ink-100/[0.03] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ink-300 md:py-0 md:[grid-template-areas:'label_plot_value_toggle'] [&::-webkit-details-marker]:hidden">
          <span className="min-w-0 text-[14.5px] leading-snug text-ink-200 [grid-area:label] md:py-2">
            {t.label}
            {t.note && <span className="ml-1.5 whitespace-nowrap text-[12px] text-ink-400">· {t.note}</span>}
          </span>
          <Plot t={t} />
          <span className="flex flex-col items-end leading-tight [grid-area:value] md:block md:text-right">
            <span className="text-[14.5px] font-semibold tabular-nums text-ink-100">{signed(t.est)}</span>{" "}
            <span className="whitespace-nowrap text-[12px] text-ink-400">
              [{signed(t.lo)}, {signed(t.hi)}]
            </span>
          </span>
          <span aria-hidden className="justify-self-end text-[16px] leading-none text-ink-400 transition-transform [grid-area:toggle] group-open:rotate-45 md:justify-self-center">
            +
          </span>
        </summary>
        <div className="max-w-[68ch] space-y-2 pb-5 pt-2 text-[14.5px] leading-relaxed text-ink-300 md:ml-[calc(17rem+1rem)]">
          <p className="font-semibold text-ink-100">{t.question}</p>
          <p>{t.finding}</p>
          <p className="text-ink-200">
            {signed(t.est)} points [{signed(t.lo)}, {signed(t.hi)}]
            {t.seasons ? (
              <>
                : {signed(t.seasons[0])} in 2024-25, {signed(t.seasons[1])} in 2025-26.
              </>
            ) : (
              <>{t.note ? `, ${t.note}.` : "."}</>
            )}
            {t.heldBack && (
              <>
                {" "}
                Held-back seasons, run once: {signed(t.heldBack[0])} in 2022-23, {signed(t.heldBack[1])} in 2023-24.
              </>
            )}
          </p>
          <p className="text-[13px] text-ink-400">{t.harness}</p>
          <p className="text-[13px] text-ink-400">
            <ProofLine proof={t.proof} />
          </p>
        </div>
      </details>
    </li>
  );
}

export default function LabChart() {
  return (
    <div>
      {/* The key: what each mark means, in words beside it */}
      <ul className="mb-5 flex flex-wrap gap-x-6 gap-y-2 text-[13px] text-ink-300">
        {GROUPS.map((g) => (
          <li key={g.verdict} className="flex items-center gap-2">
            <Marker verdict={g.verdict} />
            {g.name}
          </li>
        ))}
        <li className="flex items-center gap-2">
          <span aria-hidden className="block h-[2px] w-5 rounded-full bg-ink-400" />
          95% interval
        </li>
      </ul>

      <div className="sticky top-[var(--header-h)] z-10 border-b border-line bg-base/95 backdrop-blur-sm">
        <Axis />
      </div>

      {GROUPS.map((g) => {
        const rows = LAB_TESTS.filter((t) => t.verdict === g.verdict).sort((a, b) => b.est - a.est);
        return (
          <section key={g.verdict} aria-label={g.name} className="mt-8 first-of-type:mt-6">
            <div className="mb-2 flex items-baseline gap-3">
              <Marker verdict={g.verdict} className="translate-y-[-1px] self-center" />
              <h3 className="heading">
                {g.name} <span className="text-ink-400">{rows.length}</span>
              </h3>
            </div>
            <p className="mb-3 text-[14px] text-ink-400">{g.blurb}</p>
            <ul className="divide-y divide-line border-y border-line">
              {rows.map((t) => (
                <Row key={t.label} t={t} />
              ))}
            </ul>
          </section>
        );
      })}

      <p className="mt-4 text-[13px] text-ink-400">
        Points over 2024-25 and 2025-26 together, against the model as it ran when each test was made, unless a row says
        otherwise.
      </p>
    </div>
  );
}
