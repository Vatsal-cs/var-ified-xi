// File: CoinFlips.tsx
// Path: var-ified-xi/frontend/components/CoinFlips.tsx
//
// The start/bench calls this week that are too close to call. Between
// near-equal players the higher projection only wins about 52-57% of the
// time, so these are the ones worth a last look after the final refresh
// before the deadline, when the press conferences are in.

import type { Player } from "@/lib/types";
import { coinFlips, pct } from "@/lib/odds";
import Shirt from "./Shirt";
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
      <ul className="space-y-5">
        {flips.map((f) => (
          <li key={f.sub.player_id}>
            <div className="grid grid-cols-[40px_1fr_40px] items-center gap-3">
              <Shirt
                team={f.starter.team}
                number={f.starter.predicted_points.toFixed(1)}
                uid={`flip-s-${f.sub.player_id}-${f.starter.player_id}`}
                goalkeeper={f.starter.position === "GK"}
                className="h-10 w-10"
              />
              <div>
                <div className="flex justify-between text-[13px]">
                  <span className="font-medium text-ink-100">{f.starter.name}</span>
                  <span className="font-medium text-ink-100">{f.sub.name}</span>
                </div>
                <div className="mt-1 flex h-2 overflow-hidden rounded-full" aria-hidden>
                  <span className="bg-ink-100" style={{ width: `${(1 - f.p) * 100}%` }} />
                  <span className="bg-violet" style={{ width: `${f.p * 100}%` }} />
                </div>
                <div className="mt-1 flex justify-between text-[12px] tabular-nums text-ink-400">
                  <span>starts &middot; {pct(1 - f.p)}</span>
                  <span>
                    {pct(f.p)} &middot; <span className="text-violet">bench</span>
                  </span>
                </div>
              </div>
              <Shirt
                team={f.sub.team}
                number={f.sub.predicted_points.toFixed(1)}
                uid={`flip-b-${f.sub.player_id}-${f.starter.player_id}`}
                goalkeeper={f.sub.position === "GK"}
                className="h-10 w-10"
              />
            </div>
          </li>
        ))}
      </ul>
      <p className="mt-4 text-[12.5px] leading-relaxed text-ink-500">
        <Term explain="A bench player and a starter he could replace, each with a 40-60% chance of outscoring the other (ties left out). Over thousands of past calls, the higher projection won only 52% of the time when the two were within half a point.">
          Too close to call
        </Term>{" "}
        on the numbers. Check the last refresh before the deadline: a rotation or injury hint settles it.
      </p>
    </div>
  );
}
