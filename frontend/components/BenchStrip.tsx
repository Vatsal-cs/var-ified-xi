// File: BenchStrip.tsx
// Path: var-ified-xi/frontend/components/BenchStrip.tsx

import type { Player } from "@/lib/types";
import { PosPill } from "./ui";

export default function BenchStrip({ bench }: { bench: Player[] }) {
  return (
    <div className="card p-4">
      <p className="label mb-3">Bench — substitution order</p>
      <ol className="grid grid-cols-2 gap-2.5 sm:grid-cols-4">
        {bench.map((p, i) => (
          <li
            key={p.player_id}
            className="flex items-center gap-2.5 rounded-lg border border-pitch-line bg-pitch-panel2/60 p-2.5"
          >
            <span className="font-mono text-[10px] text-ink-500">{i + 1}</span>
            <div className="min-w-0">
              <p className="flex items-center gap-1.5">
                <PosPill pos={p.position} />
              </p>
              <p className="mt-1 truncate font-mono text-xs text-ink-100">{p.name}</p>
              <p className="font-mono text-[10px] text-ink-400">
                {p.predicted_points.toFixed(1)} pts
              </p>
            </div>
          </li>
        ))}
      </ol>
    </div>
  );
}
