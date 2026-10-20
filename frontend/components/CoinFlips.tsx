// File: CoinFlips.tsx
// Path: var-ified-xi/frontend/components/CoinFlips.tsx
//
// The start/bench calls this week that are too close to call. Between
// near-equal players the higher projection only wins about 52-57% of the
// time, so these are the ones worth a last look after the final refresh
// before the deadline, when the press conferences are in.

import type { Player } from "@/lib/types";
import { coinFlips, pct } from "@/lib/odds";
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
    <div className="rounded-[2px] border border-gold/30 bg-gold/[0.05] p-3.5">
      <p className="label text-gold">
        <Term explain="A bench player and a starter he could replace, each with a 40-60% chance of outscoring the other (ties left out). Over thousands of past calls, the higher projection won only 52% of the time when the two were within half a point. Make these calls last, after the final refresh before the deadline, when the press conferences and team news are in.">
          Coin-flip calls this week
        </Term>
      </p>
      <ul className="mt-2 space-y-1.5">
        {flips.map((f) => (
          <li key={f.sub.player_id} className="flex flex-wrap items-baseline gap-x-2 gap-y-0.5 font-mono text-sm">
            <span className="text-ink-100">{f.starter.name}</span>
            <span className="text-[11px] text-ink-500">starting, {f.starter.predicted_points.toFixed(1)}</span>
            <span className="text-ink-500">or</span>
            <span className="text-ink-100">{f.sub.name}</span>
            <span className="text-[11px] text-ink-500">bench, {f.sub.predicted_points.toFixed(1)}</span>
            <span className="text-[11px] text-gold">
              {pct(1 - f.p)} / {pct(f.p)}
            </span>
          </li>
        ))}
      </ul>
      <p className="mt-2 font-body text-xs text-ink-300">
        Too close to call on the numbers. Check the last refresh before the deadline: a
        rotation or injury hint settles it.
      </p>
    </div>
  );
}
