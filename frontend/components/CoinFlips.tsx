// File: CoinFlips.tsx
// Path: var-ified-xi/frontend/components/CoinFlips.tsx
//
// The start/bench calls this week that are too close to call. Between
// near-equal players the higher projection only wins about 52-57% of the
// time, so these are the ones worth a last look after the final refresh
// before the deadline, when the press conferences are in.

import type { Player } from "@/lib/types";
import { coinFlips, pct } from "@/lib/odds";
import Crest from "./Crest";
import { Term } from "./ui";

export default function CoinFlips({
  xi,
  bench,
  scale = 1,
}: {
  xi: Player[];
  bench: Player[];
  scale?: number;
}) {
  const flips = coinFlips(xi, bench, scale);
  if (flips.length === 0) return null;
  return (
    <div className="rounded-xl border border-violet/30 bg-violet/[0.06] p-4">
      <p className="label flex items-center gap-2 text-violet">
        <span
          aria-hidden
          className="inline-flex h-4 w-4 animate-coin items-center justify-center rounded-full border border-violet/70 bg-violet/15 text-[8px] text-violet [transform-style:preserve-3d]"
        >
          ½
        </span>
        <Term explain="A bench player and a starter he could replace, each with a 40-60% chance of outscoring the other (ties left out). Over thousands of past calls, the higher projection won only 52% of the time when the two were within half a point. Make these calls last, after the final refresh before the deadline, when the press conferences and team news are in.">
          Coin-flip calls this week
        </Term>
      </p>
      <ul className="mt-2 space-y-1.5">
        {flips.map((f) => (
          <li key={f.sub.player_id} className="flex flex-wrap items-center gap-x-2 gap-y-0.5 text-sm">
            <Crest team={f.starter.team} className="h-4 w-4 flex-none" />
            <span className="font-medium text-ink-100">{f.starter.name}</span>
            <span className="text-[12px] text-ink-400">starting, {f.starter.predicted_points.toFixed(1)}</span>
            <span className="text-ink-500">or</span>
            <Crest team={f.sub.team} className="h-4 w-4 flex-none" />
            <span className="font-medium text-ink-100">{f.sub.name}</span>
            <span className="text-[12px] text-ink-400">bench, {f.sub.predicted_points.toFixed(1)}</span>
            <span className="text-[12px] font-semibold tabular-nums text-violet">
              {pct(1 - f.p)} / {pct(f.p)}
            </span>
          </li>
        ))}
      </ul>
      <p className="mt-2 text-xs text-ink-300">
        Too close to call on the numbers. Check the last refresh before the deadline: a
        rotation or injury hint settles it.
      </p>
    </div>
  );
}
