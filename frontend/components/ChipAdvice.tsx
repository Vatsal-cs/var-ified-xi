// File: ChipAdvice.tsx
// Path: var-ified-xi/frontend/components/ChipAdvice.tsx
//
// Surfaces exactly when to play Triple Captain / Bench Boost / Wildcard /
// Free Hit — or, just as importantly, confirms the tool is actively
// watching the fixture calendar for one even when it has nothing to say
// yet. Silence and "checked, nothing found" look identical unless this
// says which one it is.

import type { ChipSuggestion, ChipWatch } from "@/lib/types";

const CHIP_LABEL: Record<ChipSuggestion["chip"], string> = {
  bboost: "Bench Boost",
  "3xc": "Triple Captain",
  freehit: "Free Hit",
  wildcard: "Wildcard",
};

export default function ChipAdvice({
  advice,
  watch,
  horizonGws,
}: {
  advice?: ChipSuggestion[];
  watch?: ChipWatch;
  horizonGws: number;
}) {
  if (advice && advice.length > 0) {
    return (
      <div className="space-y-3">
        {advice.map((a) => (
          <div
            key={`${a.chip}-${a.gameweek}`}
            className="rounded-lg border border-var-amber/40 bg-var-amber/[0.06] p-4"
          >
            <p className="font-mono text-[11px] uppercase tracking-[0.2em] text-var-amber">
              GW{a.gameweek} &middot; {CHIP_LABEL[a.chip]}
            </p>
            <p className="mt-1.5 font-body text-sm text-ink-200">{a.reason}</p>
          </div>
        ))}
      </div>
    );
  }

  // Nothing actionable yet — say so explicitly, and say why, so it never
  // reads as "this feature doesn't work."
  const next = watch?.next_double_gw ?? watch?.next_blank_gw;
  return (
    <div className="card p-4">
      <p className="font-body text-sm text-ink-300">
        {next ? (
          <>
            A gameweek worth a chip is on the calendar (GW{next}), but it&apos;s
            further out than the {horizonGws}-gameweek planning window — too
            early to say who you&apos;d actually own by then. It&apos;ll turn into a
            named suggestion automatically once it&apos;s in range.
          </>
        ) : (
          <>
            Nothing on the fixture calendar yet is worth a chip
            {watch ? ` (checked all published gameweeks through GW${watch.checked_through_gw})` : ""}.
            Double and blank gameweeks come from mid-season fixture reschedules —
            FPL hasn&apos;t confirmed one yet. This re-checks automatically on every
            run, so you&apos;ll see it here the moment one is.
          </>
        )}
      </p>
    </div>
  );
}
