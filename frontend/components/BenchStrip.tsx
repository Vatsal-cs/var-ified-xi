// File: BenchStrip.tsx
// Path: var-ified-xi/frontend/components/BenchStrip.tsx

import type { Player } from "@/lib/types";

export default function BenchStrip({ bench }: { bench: Player[] }) {
  return (
    <div className="rounded-lg border border-pitch-line bg-pitch-panel p-4">
      <p className="mb-3 font-mono text-[11px] uppercase tracking-[0.2em] text-ink-500">
        Bench &mdash; not in match-day XI
      </p>
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {bench.map((p, i) => (
          <div
            key={p.player_id}
            className="flex items-center gap-3 rounded-md border border-pitch-line bg-pitch-panel2 p-2.5"
          >
            <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-pitch-line font-mono text-[10px] text-ink-300">
              {p.position}
            </span>
            <div className="min-w-0">
              <p className="truncate font-mono text-xs text-ink-100">{p.name}</p>
              <p className="font-mono text-[10px] text-ink-500">{p.predicted_points.toFixed(1)} pts</p>
            </div>
            <span className="ml-auto font-mono text-[10px] text-ink-500">{i + 1}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
