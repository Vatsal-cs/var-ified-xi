// File: TransfersPanel.tsx
// Path: var-ified-xi/frontend/components/TransfersPanel.tsx
//
// The weeks AFTER the one that's due. The immediate decision lives in
// <ThisWeek>; this is the plan it belongs to — the reason the solver looks
// several gameweeks ahead instead of one.

import type { PlannedWeek } from "@/lib/types";

export default function TransfersPanel({ weeks }: { weeks: PlannedWeek[] }) {
  const rest = weeks.slice(1);
  if (rest.length === 0) return null;

  return (
    <div className="card overflow-hidden">
      <ul className="divide-y divide-pitch-line">
        {rest.map((week) => {
          const moves = week.transfers_out.map((o, i) => ({
            out: o,
            in: week.transfers_in[i],
          }));
          return (
            <li
              key={week.gameweek}
              className="flex flex-wrap items-center gap-x-6 gap-y-1.5 px-4 py-3"
            >
              <span className="w-14 shrink-0 font-mono text-xs text-ink-400">
                GW{week.gameweek}
              </span>
              <div className="min-w-0 flex-1 font-mono text-sm">
                {moves.length === 0 ? (
                  <span className="text-ink-500">roll transfer</span>
                ) : (
                  moves.map(({ out, in: inn }, i) => (
                    <span key={out.player_id} className="mr-3 inline-block">
                      {i > 0 && <span className="mr-3 text-ink-600">·</span>}
                      <span className="text-var-crimson line-through decoration-var-crimson/40">
                        {out.name}
                      </span>{" "}
                      <span aria-hidden className="text-ink-500">
                        &rarr;
                      </span>{" "}
                      <span className="text-var-green">{inn?.name ?? "—"}</span>
                    </span>
                  ))
                )}
              </div>
              {week.hits > 0 && (
                <span className="font-mono text-xs text-var-crimson">
                  &minus;{week.hit_cost}
                </span>
              )}
              <span className="font-mono text-xs text-ink-400">
                {week.predicted_points.toFixed(1)} pts
              </span>
            </li>
          );
        })}
      </ul>
      <p className="border-t border-pitch-line px-4 py-2.5 font-body text-xs text-ink-500">
        Provisional. These weeks assume today&apos;s form and prices, and are
        re-solved from scratch every run — act only on the gameweek that&apos;s due.
      </p>
    </div>
  );
}
