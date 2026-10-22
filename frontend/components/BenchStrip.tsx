// File: BenchStrip.tsx
// Path: var-ified-xi/frontend/components/BenchStrip.tsx

import type { Player } from "@/lib/types";
import Shirt, { Hanger } from "@/components/Shirt";
import { headToHead, pct, swapTarget } from "@/lib/odds";
import { Term } from "./ui";

/** How the bench player compares with the starter he'd most plausibly
 *  replace — the call the model made, as a head-to-head chance. */
function CloseCall({ player, xi, scale }: { player: Player; xi: Player[]; scale: number }) {
  const target = swapTarget(player, xi);
  if (!target || !player.dist || !target.dist) return null;
  const p = headToHead(player.dist.pmf, target.dist.pmf, scale);
  const flip = p >= 0.4 && p <= 0.6;
  return (
    <p className={`mt-0.5 text-[10.5px] leading-snug ${flip ? "font-semibold text-violet" : "text-ink-500"}`}>
      beats {target.name} {pct(p)}
      {flip && " · coin flip"}
    </p>
  );
}

export default function BenchStrip({
  bench,
  startingXi = [],
  scale = 1,
}: {
  bench: Player[];
  startingXi?: Player[];
  scale?: number;
}) {
  return (
    <div>
      <p className="label mb-2">
        <Term explain="If a starter doesn't play, FPL automatically subs in the first bench player who did — in this order. The reserve keeper can only ever replace the keeper. 'Beats X' is how often he'd outscore the starter he'd most plausibly replace (ties left out); between 40% and 60% the start/bench call is a coin flip.">
          Bench &middot; in substitution order
        </Term>
      </p>
      <div className="relative rounded-2xl bg-surface-raised px-2 pb-3 pt-3.5">
        <span aria-hidden className="absolute inset-x-5 top-3 h-[3px] rounded-full bg-ink-500/40" />
        <ol className="grid grid-cols-4 gap-1">
          {bench.map((p, i) => (
            <li key={p.player_id} className="flex min-w-0 flex-col items-center text-center">
              <span
                className="shirt-hang flex animate-hang flex-col items-center"
                style={{ animationDelay: `${1.2 + i * 0.08}s` }}
              >
                <Hanger className="relative z-[1] -mb-1 w-11" />
                <Shirt
                  team={p.team}
                  number={p.predicted_points.toFixed(1)}
                  uid={`bench-${p.player_id}`}
                  goalkeeper={p.position === "GK"}
                  className="h-[58px] w-[58px] drop-shadow-[0_5px_6px_rgba(0,0,0,0.25)] sm:h-16 sm:w-16"
                />
              </span>
              <span className="-mt-1 max-w-full truncate rounded-md bg-plate px-2 py-px text-[11.5px] font-semibold text-plate-text">
                {p.name}
              </span>
              <span className="mt-0.5 text-[11px] text-ink-400">
                {i + 1}. {p.position}
              </span>
              <CloseCall player={p} xi={startingXi} scale={scale} />
            </li>
          ))}
        </ol>
      </div>
    </div>
  );
}
