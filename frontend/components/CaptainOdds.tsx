// File: CaptainOdds.tsx
// Path: var-ified-xi/frontend/components/CaptainOdds.tsx
//
// The armband as head-to-heads: the captain, then the XI's next three best
// projections, each with how often he'd outscore the captain this week and
// his chance of a 10+ week. Head-to-heads are recalibrated on two past
// seasons (backend research/2026-10-distributions); the 10+ chance and the
// likely range needed no correction.

import type { CaptainOdds as Odds } from "@/lib/types";
import { pct } from "@/lib/odds";
import { Term } from "./ui";

export default function CaptainOdds({ odds }: { odds: Odds[] }) {
  if (odds.length < 2) return null;
  const [cap, ...others] = odds;

  return (
    <div className="rounded-[2px] border border-line bg-surface-raised/50 p-3.5">
      <p className="label">
        <Term explain="Each player's full points distribution, built from how players projected like him actually scored over two past seasons. 'Beats' is how often he'd outscore the captain, ties left out.">
          The armband, head to head
        </Term>
      </p>
      <p className="mt-2 font-mono text-[12px] text-ink-200">
        <span className="text-gold">{cap.name} (C)</span>
        <span className="text-ink-400">
          {" "}
          &middot; likely {cap.p10}&ndash;{cap.p90} &middot; 10+ {pct(cap.p_haul)} &middot; doubled{" "}
          {cap.p10 * 2}&ndash;{cap.p90 * 2}
        </span>
      </p>
      <ul className="mt-3 max-w-md space-y-2.5">
        {others.map((o) => {
          const b = o.beats_captain ?? 0;
          return (
            <li key={o.player_id}>
              <div className="flex items-baseline justify-between gap-3 font-mono">
                <span className="truncate text-[12px] text-ink-100">{o.name}</span>
                <span className="flex-none text-[11px] tabular-nums text-ink-300">
                  beats {cap.name} {pct(b)}
                </span>
              </div>
              <span className="relative mt-1 block h-1.5 rounded-full bg-line" aria-hidden>
                <span className="absolute inset-y-[-2px] left-1/2 w-px bg-ink-400" />
                <span className="block h-full rounded-full bg-pts/55" style={{ width: `${b * 100}%` }} />
              </span>
            </li>
          );
        })}
      </ul>
      <p className="mt-2.5 font-body text-xs leading-relaxed text-ink-400">
        Left of the centre line, {cap.name} is the better bet. Nobody here is a sure thing in a
        single week; the armband goes to the highest projection because that wins over a season.
      </p>
    </div>
  );
}
