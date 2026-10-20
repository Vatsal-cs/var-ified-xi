// File: SquadStats.tsx
// Path: var-ified-xi/frontend/components/SquadStats.tsx

import { Stat, Term } from "./ui";

export default function SquadStats({
  used,
  total,
  points,
  formation,
  horizonGws,
  valueLabel = "Budget used",
}: {
  used: number;
  total: number;
  points: number;
  formation: string;
  horizonGws: number;
  valueLabel?: string;
}) {
  const pct = Math.min(100, (used / total) * 100);
  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
      <div className="panel group relative overflow-hidden p-4 transition-all duration-300 hover:-translate-y-0.5 hover:border-line-strong">
        <span aria-hidden className="absolute inset-x-0 top-0 h-[2px] bg-sky opacity-80" />
        <span aria-hidden className="pointer-events-none absolute -right-8 -top-8 h-24 w-24 rounded-full bg-sky opacity-[0.07] blur-2xl transition-opacity duration-300 group-hover:opacity-[0.16]" />
        <p className="label">{valueLabel}</p>
        <p className="mt-1.5 stat text-sky">
          &pound;{used.toFixed(1)}
          <span className="text-sm text-ink-500">m</span>
        </p>
        <div className="mt-2 h-1 w-full overflow-hidden rounded-full bg-line">
          <div
            className="h-full origin-left animate-grow rounded-full bg-gradient-to-r from-sky/60 to-sky"
            style={{ width: `${pct}%` }}
          />
        </div>
      </div>

      <Stat
        label={
          <Term explain="Expected points for the starting XI plus the captain's doubled score, in the coming gameweek only.">
            Proj. GW points
          </Term>
        }
        value={points.toFixed(1)}
        tone="accent"
        sub="XI + captain"
      />

      <Stat label="Formation" value={formation} tone="violet" sub="chosen by the solver" />

      <Stat
        label={
          <Term explain="The solver judges players over this many upcoming gameweeks, with later weeks discounted, so it doesn't chase one good fixture into a hard run.">
            Horizon
          </Term>
        }
        value={`${horizonGws} GWs`}
        tone="gold"
        sub="look-ahead window"
      />
    </div>
  );
}
