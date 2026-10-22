// File: TransfersPanel.tsx
// Path: var-ified-xi/frontend/components/TransfersPanel.tsx
//
// The weeks AFTER the one that's due, as a rail of the kit room: under each
// gameweek hangs the shirt the plan signs that week, with who it replaces.
// The immediate decision lives in <ThisWeek>; this is the plan it belongs to —
// the reason the solver looks several gameweeks ahead instead of one.

import type { PlannedWeek } from "@/lib/types";
import Crest from "./Crest";
import Shirt, { Hanger } from "./Shirt";

export default function TransfersPanel({ weeks }: { weeks: PlannedWeek[] }) {
  const rest = weeks.slice(1);
  if (rest.length === 0) return null;

  return (
    <div>
      <div className="relative -mx-4 overflow-x-auto px-4 [scrollbar-width:none] sm:mx-0 sm:px-0 [&::-webkit-scrollbar]:hidden">
        <ol className="relative flex min-w-max snap-x sm:min-w-0">
          <span aria-hidden className="absolute inset-x-2 top-[7px] h-[3px] rounded-full bg-ink-500/45" />
          {rest.map((week, w) => {
            const moves = week.transfers_out.map((o, i) => ({ out: o, in: week.transfers_in[i] }));
            const small = moves.length > 1;
            return (
              <li
                key={week.gameweek}
                className="flex w-[150px] flex-none snap-start flex-col items-center px-2 text-center sm:w-auto sm:flex-1"
              >
                <div className="flex min-h-[150px] items-start justify-center gap-1">
                  {moves.length === 0 ? (
                    <div className="flex flex-col items-center">
                      <Hanger className="w-14" />
                      <p className="mt-6 text-[13px] text-ink-400">Roll the transfer</p>
                    </div>
                  ) : (
                    moves.map(({ out, in: inn }, i) => (
                      <div
                        key={out.player_id}
                        className="shirt-hang flex animate-hang flex-col items-center"
                        style={{ animationDelay: `${0.2 + w * 0.1 + i * 0.05}s` }}
                      >
                        <Hanger className={`relative z-[1] -mb-1 ${small ? "w-10" : "w-14"}`} />
                        <Shirt
                          team={inn?.team}
                          number={(inn?.predicted_points ?? 0).toFixed(1)}
                          uid={`plan-${week.gameweek}-${inn?.player_id ?? out.player_id}`}
                          className={`drop-shadow-[0_6px_8px_rgba(0,0,0,0.22)] ${small ? "h-14 w-14" : "h-[78px] w-[78px]"}`}
                        />
                        <span className="-mt-1 max-w-[120px] truncate rounded-md bg-plate px-2 py-px text-[12px] font-semibold text-plate-text">
                          {inn?.name ?? "—"}
                        </span>
                        <span className="mt-1.5 flex max-w-[130px] items-center gap-1 text-[12px] text-ink-400">
                          for
                          <Crest team={out.team} className="h-3.5 w-3.5 flex-none opacity-60 grayscale" />
                          <span className="truncate line-through decoration-risk/60">{out.name}</span>
                        </span>
                      </div>
                    ))
                  )}
                </div>
                <div className="mt-3 w-full border-t border-line pt-2.5">
                  <p className="text-[13px] font-semibold text-ink-100">GW{week.gameweek}</p>
                  <p className="text-[12px] tabular-nums text-ink-400">
                    {week.predicted_points.toFixed(1)} pts
                    {week.hits > 0 && <span className="ml-1 font-semibold text-risk">&minus;{week.hit_cost}</span>}
                  </p>
                </div>
              </li>
            );
          })}
        </ol>
      </div>
      <p className="mt-4 text-[12.5px] text-ink-500">
        Provisional. These weeks assume today&apos;s form and prices and are re-solved from scratch every run —
        act only on the gameweek that&apos;s due.
      </p>
    </div>
  );
}
