// File: TransfersPanel.tsx
// Path: var-ified-xi/frontend/components/TransfersPanel.tsx
//
// The weeks AFTER the one that's due. The immediate decision lives in
// <ThisWeek>; this is the plan it belongs to — the reason the solver looks
// several gameweeks ahead instead of one. Each week's move is a small shirt
// swap: the shirt going out faded, the one coming in.

import type { PlannedWeek, TransferMove } from "@/lib/types";
import Shirt from "./Shirt";

function Kit({ move, out, uid }: { move?: TransferMove; out?: boolean; uid: string }) {
  return (
    <span className={`flex min-w-0 items-center gap-1.5 ${out ? "opacity-55" : ""}`}>
      <Shirt
        team={move?.team}
        number={(move?.predicted_points ?? 0).toFixed(1)}
        uid={uid}
        className={`h-9 w-9 flex-none ${out ? "grayscale" : "drop-shadow-[0_3px_3px_rgba(0,0,0,0.2)]"}`}
      />
      <span className="min-w-0">
        <span
          className={`block truncate text-[13.5px] font-medium ${
            out ? "text-ink-300 line-through decoration-risk/60" : "text-ink-100"
          }`}
        >
          {move?.name ?? "—"}
        </span>
        <span className="block truncate text-[11.5px] text-ink-400">{move?.team}</span>
      </span>
    </span>
  );
}

export default function TransfersPanel({ weeks }: { weeks: PlannedWeek[] }) {
  const rest = weeks.slice(1);
  if (rest.length === 0) return null;

  return (
    <div className="panel overflow-hidden">
      <ul className="divide-y divide-line">
        {rest.map((week, w) => {
          const moves = week.transfers_out.map((o, i) => ({ out: o, in: week.transfers_in[i] }));
          return (
            <li
              key={week.gameweek}
              className="grid animate-rise grid-cols-[52px_1fr_auto] items-center gap-x-3 px-4 py-3"
              style={{ animationDelay: `${w * 0.06}s` }}
            >
              <span className="text-[12px] font-semibold tabular-nums text-ink-400">GW{week.gameweek}</span>
              <div className="min-w-0 space-y-2">
                {moves.length === 0 ? (
                  <span className="text-[13.5px] text-ink-400">Roll the transfer</span>
                ) : (
                  moves.map(({ out, in: inn }) => (
                    <div key={out.player_id} className="grid max-w-[460px] grid-cols-[1fr_18px_1fr] items-center gap-2">
                      <Kit move={out} out uid={`plan-out-${week.gameweek}-${out.player_id}`} />
                      <span aria-hidden className="text-center text-ink-500">
                        &rarr;
                      </span>
                      <Kit move={inn} uid={`plan-in-${week.gameweek}-${inn?.player_id ?? out.player_id}`} />
                    </div>
                  ))
                )}
              </div>
              <span className="text-right text-[12px] tabular-nums text-ink-400">
                {week.hits > 0 && <span className="mr-2 font-semibold text-risk">&minus;{week.hit_cost}</span>}
                <span className="font-semibold text-ink-100">{week.predicted_points.toFixed(1)}</span> pts
              </span>
            </li>
          );
        })}
      </ul>
      <p className="border-t border-line px-4 py-2.5 text-xs text-ink-500">
        Provisional. These weeks assume today&apos;s form and prices, and are re-solved from scratch every
        run — act only on the gameweek that&apos;s due.
      </p>
    </div>
  );
}
