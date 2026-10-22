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
  if (flips.length === 0) {
    return (
      <p className="text-[14px] leading-relaxed text-ink-300">
        No close start/bench calls this week: every starter is clearly ahead of the bench player who
        could replace him.
      </p>
    );
  }
  return (
    <div>
      <ul className="space-y-3">
        {flips.map((f) => (
          <li key={f.sub.player_id} className="text-[14px]">
            <p className="flex flex-wrap items-center gap-x-1.5">
              <Crest team={f.starter.team} className="h-4 w-4 flex-none" />
              <span className="font-medium text-ink-100">{f.starter.name}</span>
              <span className="text-ink-500">or</span>
              <Crest team={f.sub.team} className="h-4 w-4 flex-none" />
              <span className="font-medium text-ink-100">{f.sub.name}</span>
            </p>
            <p className="mt-0.5 text-[12.5px] text-ink-400">
              starting {f.starter.predicted_points.toFixed(1)} &middot; bench {f.sub.predicted_points.toFixed(1)}{" "}
              &middot;{" "}
              <span className="font-semibold tabular-nums text-violet">
                {pct(1 - f.p)} / {pct(f.p)}
              </span>
            </p>
          </li>
        ))}
      </ul>
      <p className="mt-3 text-[12.5px] leading-relaxed text-ink-500">
        <Term explain="A bench player and a starter he could replace, each with a 40-60% chance of outscoring the other (ties left out). Over thousands of past calls, the higher projection won only 52% of the time when the two were within half a point.">
          Too close to call
        </Term>{" "}
        on the numbers. Check the last refresh before the deadline: a rotation or injury hint settles it.
      </p>
    </div>
  );
}
