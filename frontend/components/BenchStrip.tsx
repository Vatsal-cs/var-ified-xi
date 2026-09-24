// File: BenchStrip.tsx
// Path: var-ified-xi/frontend/components/BenchStrip.tsx

import type { Player } from "@/lib/types";
import { kitFor } from "@/lib/teams";
import { Term } from "./ui";

export default function BenchStrip({ bench }: { bench: Player[] }) {
  return (
    <div className="glass p-4">
      <p className="label mb-3">
        <Term explain="If a starter doesn't play, FPL automatically subs in the first bench player who did — in this order. The reserve keeper can only ever replace the keeper.">
          Bench &mdash; substitution order
        </Term>
      </p>
      <ol className="grid grid-cols-2 gap-2.5 sm:grid-cols-4">
        {bench.map((p, i) => {
          const kit = kitFor(p.team);
          return (
            <li
              key={p.player_id}
              className="group relative flex items-center gap-2.5 overflow-hidden rounded-lg border border-line bg-surface-raised/60 p-2.5 transition-colors hover:border-pts/40"
            >
              {/* Club colour as a spine, so the bench reads at a glance too */}
              <span
                className="absolute inset-y-0 left-0 w-[3px]"
                style={{ background: kit.shirt }}
                aria-hidden
              />
              <span className="ml-0.5 font-mono text-[10px] text-ink-500">{i + 1}</span>
              <div className="min-w-0 flex-1">
                <p className="truncate font-body text-[13px] font-medium text-ink-100">
                  {p.name}
                </p>
                <p className="font-mono text-[10px] text-ink-400">
                  {p.position} &middot; {kit.abbr}
                </p>
                <p className="mt-0.5 font-mono text-[11px] tabular-nums text-pts">
                  {p.predicted_points.toFixed(1)} pts
                </p>
              </div>
            </li>
          );
        })}
      </ol>
    </div>
  );
}
