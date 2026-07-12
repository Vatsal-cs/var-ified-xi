// File: BudgetGauge.tsx
// Path: var-ified-xi/frontend/components/BudgetGauge.tsx

export default function BudgetGauge({
  used,
  total,
  points,
  formation,
}: {
  used: number;
  total: number;
  points: number;
  formation: string;
}) {
  const pct = Math.min(100, (used / total) * 100);
  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
      <div className="rounded-lg border border-pitch-line bg-pitch-panel p-4">
        <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-ink-500">Budget deployed</p>
        <p className="mt-1 font-mono text-2xl text-ink-100">
          &pound;{used.toFixed(1)}m <span className="text-sm text-ink-500">/ &pound;{total.toFixed(1)}m</span>
        </p>
        <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-pitch-line">
          <div className="h-full rounded-full bg-var-green" style={{ width: `${pct}%` }} />
        </div>
      </div>
      <div className="rounded-lg border border-pitch-line bg-pitch-panel p-4">
        <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-ink-500">Predicted GW points</p>
        <p className="mt-1 font-mono text-2xl text-var-green">{points.toFixed(2)}</p>
        <p className="mt-2 font-mono text-[10px] text-ink-500">Starting XI + captain multiplier</p>
      </div>
      <div className="rounded-lg border border-pitch-line bg-pitch-panel p-4">
        <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-ink-500">Formation</p>
        <p className="mt-1 font-mono text-2xl text-ink-100">{formation}</p>
        <p className="mt-2 font-mono text-[10px] text-ink-500">Chosen by the solver, not preset</p>
      </div>
    </div>
  );
}
