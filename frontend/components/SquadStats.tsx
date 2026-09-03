// File: SquadStats.tsx
// Path: var-ified-xi/frontend/components/SquadStats.tsx

import { Stat, Term } from "./ui";

export default function SquadStats({
  used,
  total,
  points,
  formation,
  horizonGws,
}: {
  used: number;
  total: number;
  points: number;
  formation: string;
  horizonGws: number;
}) {
  const pct = Math.min(100, (used / total) * 100);
  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
      <div className="card p-4">
        <p className="label">Budget used</p>
        <p className="mt-1.5 stat">
          &pound;{used.toFixed(1)}
          <span className="text-sm text-ink-500">m</span>
        </p>
        <div className="mt-2 h-1 w-full overflow-hidden rounded-full bg-pitch-line">
          <div className="h-full rounded-full bg-var-green" style={{ width: `${pct}%` }} />
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

      <Stat label="Formation" value={formation} sub="chosen by the solver" />

      <Stat
        label={
          <Term explain="The solver judges players over this many upcoming gameweeks, with later weeks discounted, so it doesn't chase one good fixture into a hard run.">
            Horizon
          </Term>
        }
        value={`${horizonGws} GWs`}
        sub="look-ahead window"
      />
    </div>
  );
}
