// File: SiteHeader.tsx
// Path: var-ified-xi/frontend/components/SiteHeader.tsx

import type { OptimizedTeam } from "@/lib/types";

function timeAgo(iso: string) {
  const then = new Date(iso).getTime();
  const mins = Math.max(0, Math.round((Date.now() - then) / 60000));
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.round(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.round(hrs / 24)}d ago`;
}

export default function SiteHeader({ team }: { team: OptimizedTeam }) {
  const modeLabel =
    team.mode === "transfer_plan" ? "Transfer plan" : "Fresh squad";

  return (
    <header className="sticky top-0 z-40 border-b border-pitch-line bg-pitch-night/85 backdrop-blur">
      <div className="mx-auto flex max-w-5xl items-center justify-between gap-4 px-5 py-3.5">
        <a href="#top" className="flex items-baseline gap-2">
          <span className="font-display text-lg font-bold tracking-tight text-ink-100">
            VAR&#8209;ified <span className="text-var-green">XI</span>
          </span>
        </a>

        <div className="flex items-center gap-4 font-mono text-[11px] text-ink-400">
          <span className="hidden rounded border border-pitch-line px-2 py-1 text-ink-300 sm:inline">
            {modeLabel}
          </span>
          <span>
            GW <span className="text-ink-100">{team.gameweek ?? "—"}</span>
          </span>
          <span className="hidden items-center gap-1.5 sm:flex">
            <span className="h-1.5 w-1.5 animate-pulseDot rounded-full bg-var-green" />
            updated {timeAgo(team.generated_at)}
          </span>
        </div>
      </div>
    </header>
  );
}
