// File: ChipPlanner.tsx
// Path: var-ified-xi/frontend/components/ChipPlanner.tsx
//
// Every chip you hold placed in its best week up to the chip deadline, planned
// together (one chip a week), from backend chip_planner.py. Two versions —
// with a Wildcard now and without — because the Wildcard changes the squad
// every later chip is played with.

"use client";

import { useState } from "react";
import type { ChipPlan, PlannedChip } from "@/lib/types";
import { ChipToken } from "./ui";

const LABEL: Record<PlannedChip, string> = {
  "3xc": "Triple Captain",
  bboost: "Bench Boost",
  freehit: "Free Hit",
};
const SHORT: Record<PlannedChip, string> = { "3xc": "TC", bboost: "BB", freehit: "FH" };

const WHAT: Record<PlannedChip, string> = {
  "3xc": "one more copy of your captain's score",
  bboost: "your four bench players' scores",
  freehit: "the best one-week XI your budget buys, minus your own",
};

export default function ChipPlanner({ plan }: { plan: ChipPlan }) {
  const keys = plan.scenarios.map((s) => s.key);
  const [key, setKey] = useState(keys.includes("wildcard") ? "wildcard" : keys[0]);
  const sc = plan.scenarios.find((s) => s.key === key) ?? plan.scenarios[0];
  if (!sc) return null;
  const chosen = new Map(sc.plan.map((p) => [`${p.gameweek}:${p.chip}`, p]));

  return (
    <div className="mt-5">
      {plan.scenarios.length > 1 && (
        <div role="tablist" className="mb-4 inline-flex rounded-lg border border-line p-0.5">
          {plan.scenarios.map((s) => (
            <button
              key={s.key}
              role="tab"
              aria-selected={s.key === key}
              onClick={() => setKey(s.key)}
              className={`rounded-md px-3 py-1.5 text-[13px] font-medium transition-colors ${
                s.key === key ? "bg-ink-100 text-[rgb(var(--c-base))]" : "text-ink-400 hover:text-ink-100"
              }`}
            >
              {s.label}
            </button>
          ))}
        </div>
      )}

      {/* Each chip as a token on a ruler of the weeks left before it expires */}
      <div className="-mx-4 overflow-x-auto px-4 [scrollbar-width:none] sm:mx-0 sm:px-0 [&::-webkit-scrollbar]:hidden">
        <div
          className="grid min-w-[460px]"
          style={{ gridTemplateColumns: `repeat(${plan.gameweeks.length}, minmax(0, 1fr))` }}
        >
          {plan.gameweeks.map((gw, i) => {
            const picks = sc.plan.filter((p) => p.gameweek === gw);
            const wk = sc.weeks.find((w) => w.gameweek === gw);
            const last = gw === plan.deadline_gw;
            return (
              <div key={gw} className="flex flex-col items-center">
                <div className="flex h-[76px] flex-col items-center justify-end gap-1 pb-2">
                  {picks.map((p, k) => (
                    <span key={p.chip} className="flex flex-col items-center gap-0.5">
                      <ChipToken
                        chip={p.chip}
                        size={30}
                        className="animate-pop"
                      />
                      <span
                        className="animate-rise text-[11px] font-semibold tabular-nums text-pts"
                        style={{ animationDelay: `${0.3 + k * 0.1}s` }}
                      >
                        +{p.value.toFixed(1)}
                      </span>
                    </span>
                  ))}
                </div>
                <span className={`h-2 w-px ${i === 0 ? "bg-gold" : "bg-line-strong"}`} />
                <span className="w-full border-t border-line-strong" />
                <span
                  className={`mt-1.5 text-[11.5px] tabular-nums ${
                    last ? "font-semibold text-risk" : i === 0 ? "font-semibold text-gold" : "text-ink-400"
                  }`}
                >
                  {gw}
                </span>
                {wk?.fixtures && wk.fixtures.doubles > 0 && <span className="text-[10px] font-semibold text-pts">double</span>}
                {wk?.fixtures && wk.fixtures.blanks > 0 && <span className="text-[10px] font-semibold text-warn">blank</span>}
              </div>
            );
          })}
        </div>
      </div>
      <p className="mt-1 flex justify-between text-[11.5px] text-ink-500">
        <span className="text-gold">Now</span>
        <span className="text-risk">GW{plan.deadline_gw}: unplayed chips are lost</span>
      </p>

      <ul className="mt-5 divide-y divide-line border-y border-line">
        {sc.plan.map((p) => (
          <li key={p.chip} className="flex items-center gap-3 py-3">
            <ChipToken chip={p.chip} size={26} />
            <span className="flex-1 text-[14px] font-medium text-ink-100">
              {LABEL[p.chip]}
              {p.now && <span className="pill ml-2 border-gold/50 py-0.5 text-gold">play this week</span>}
            </span>
            <span className="text-right text-[13px] tabular-nums text-ink-400">
              <span className="font-semibold text-ink-100">GW{p.gameweek}</span>
              {p.player && <> &middot; {p.player}</>} &middot;{" "}
              <span className="font-semibold text-pts">+{p.value.toFixed(1)} pts</span>
              {!p.firm && <span className="text-ink-500"> &middot; rough</span>}
            </span>
          </li>
        ))}
      </ul>
      <p className="mt-2 text-[12.5px] text-ink-500">
        Together +{sc.total.toFixed(1)} projected points.{" "}
        {sc.plan.map((p) => `${SHORT[p.chip]} adds ${WHAT[p.chip]}`).join("; ")}.
      </p>

      <details className="mt-4">
        <summary className="cursor-pointer text-[13px] text-ink-400 hover:text-ink-100">
          Every week, every chip
        </summary>
        <table className="mt-2 w-full tabular-nums text-[11.5px] ">
          <thead>
            <tr className="text-left text-ink-500">
              <th className="py-1.5 font-normal">GW</th>
              {plan.chips.map((c) => (
                <th key={c} className="py-1.5 text-right font-normal">
                  {SHORT[c]}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-line">
            {sc.weeks.map((w) => (
              <tr key={w.gameweek} className={w.firm ? "text-ink-200" : "text-ink-400"}>
                <td className="py-1.5">
                  {w.gameweek}
                  {w.fixtures && w.fixtures.doubles > 0 && <span className="ml-1.5 text-pts">double</span>}
                  {w.fixtures && w.fixtures.blanks > 0 && <span className="ml-1.5 text-warn">blank</span>}
                  {sc.key === "wildcard" && w.gameweek === plan.gameweeks[0] && (
                    <span className="ml-1.5 text-gold">wildcard</span>
                  )}
                </td>
                {plan.chips.map((c) => {
                  const v = c === "3xc" ? w["3xc"] : c === "bboost" ? w.bboost : w.freehit;
                  const pick = chosen.get(`${w.gameweek}:${c}`);
                  return (
                    <td key={c} className="py-1.5 text-right">
                      <span className={pick ? "rounded-lg bg-gold/15 px-1.5 py-0.5 text-gold" : ""}>
                        {v == null ? "—" : v.toFixed(1)}
                      </span>
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
        <p className="mt-2 font-body text-xs leading-relaxed text-ink-400">
          Projected points each chip adds in each week. Up to GW{sc.firm_through_gw} it uses the
          squad the transfer plan builds; later weeks hold that squad, so they&apos;re rough. A
          double or blank gameweek announced later will move these, and the plan updates on the
          next run.
        </p>
      </details>
    </div>
  );
}
