// File: ReviewHeader.tsx
// Path: var-ified-xi/frontend/components/ReviewHeader.tsx

import type { OptimizedTeam } from "@/lib/types";

function formatTimestamp(iso: string) {
  const d = new Date(iso);
  return d.toLocaleString("en-GB", {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function ReviewHeader({ team }: { team: OptimizedTeam }) {
  return (
    <header className="sticky top-0 z-30 border-b border-pitch-line bg-pitch-night/90 backdrop-blur">
      <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-3 px-6 py-4">
        <div className="flex items-center gap-3">
          <span className="relative flex h-2.5 w-2.5">
            <span className="absolute inline-flex h-full w-full animate-pulseDot rounded-full bg-var-green" />
          </span>
          <span className="font-mono text-xs uppercase tracking-[0.2em] text-var-green">
            Decision Confirmed
          </span>
        </div>

        <h1 className="order-first w-full font-display text-3xl font-semibold uppercase tracking-tight text-ink-100 sm:order-none sm:w-auto sm:text-2xl">
          VAR-ified <span className="text-var-green">XI</span>
        </h1>

        <div className="flex items-center gap-5 font-mono text-xs text-ink-300">
          <span>
            GW <span className="text-ink-100">{team.gameweek ?? "—"}</span>
          </span>
          <span className="hidden sm:inline">
            REVIEWED {formatTimestamp(team.generated_at).toUpperCase()}
          </span>
        </div>
      </div>
    </header>
  );
}
