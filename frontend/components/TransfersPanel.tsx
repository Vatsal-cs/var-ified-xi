// File: TransfersPanel.tsx
// Path: var-ified-xi/frontend/components/TransfersPanel.tsx
//
// Shows the planned transfers gameweek by gameweek. The immediate gameweek is
// the decision you have to make before the deadline; the rest is the plan it
// belongs to, which is the whole reason the solver looks several weeks ahead.

import type { PlannedWeek, TeamInfo } from "@/lib/types";

function MoveRow({ week }: { week: PlannedWeek }) {
  const pairs = week.transfers_out.map((out, i) => ({
    out,
    in: week.transfers_in[i],
  }));

  if (pairs.length === 0) {
    return (
      <p className="font-mono text-xs text-ink-500">
        Hold — bank the free transfer.
      </p>
    );
  }

  return (
    <ul className="space-y-2">
      {pairs.map(({ out, in: inn }) => (
        <li key={out.player_id} className="flex flex-wrap items-center gap-2 font-mono text-xs">
          <span className="text-var-crimson line-through decoration-var-crimson/50">
            {out.name}
          </span>
          <span className="text-ink-500" aria-label="replaced by">
            &rarr;
          </span>
          <span className="text-var-green">{inn?.name ?? "—"}</span>
          {inn && (
            <span className="text-ink-500">
              &pound;{inn.cost_m?.toFixed(1)}m &middot; {inn.predicted_points.toFixed(1)} xP
            </span>
          )}
        </li>
      ))}
    </ul>
  );
}

export default function TransfersPanel({
  weeks,
  team,
}: {
  weeks: PlannedWeek[];
  team?: TeamInfo;
}) {
  if (weeks.length === 0) return null;

  const [immediate, ...rest] = weeks;

  return (
    <section aria-labelledby="transfers-heading">
      <h2
        id="transfers-heading"
        className="mb-1 font-display text-2xl uppercase tracking-tight text-ink-100"
      >
        The transfer decision
      </h2>
      <p className="mb-6 max-w-2xl font-body text-sm text-ink-300">
        Planned across the next {weeks.length} gameweeks at once, under the real
        transfer economy: one free transfer a week, up to five banked, and{" "}
        <span className="text-var-crimson">&minus;4</span> for every extra.
      </p>

      {team && (
        <dl className="mb-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
          {[
            { label: "Team", value: team.name },
            { label: "In the bank", value: `£${team.bank_m.toFixed(1)}m` },
            { label: "Free transfers", value: String(team.free_transfers) },
            {
              label: "Chips left",
              value: team.chips_available.length
                ? team.chips_available.join(", ")
                : "none",
            },
          ].map((stat) => (
            <div
              key={stat.label}
              className="rounded-md border border-pitch-line bg-pitch-panel p-3"
            >
              <dt className="font-mono text-[10px] uppercase tracking-[0.2em] text-ink-500">
                {stat.label}
              </dt>
              <dd className="mt-1 truncate font-mono text-sm text-ink-100">{stat.value}</dd>
            </div>
          ))}
        </dl>
      )}

      {/* The decision that's actually due */}
      <div className="rounded-lg border border-var-green/40 bg-pitch-panel p-5">
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
          <span className="font-mono text-[11px] uppercase tracking-[0.25em] text-var-green">
            Gameweek {immediate.gameweek} &middot; on the field
          </span>
          <span className="font-mono text-xs text-ink-500">
            {immediate.free_transfers} FT available
            {immediate.hits > 0 && (
              <span className="text-var-crimson">
                {" "}&middot; taking a &minus;{immediate.hit_cost}
              </span>
            )}
          </span>
        </div>
        <MoveRow week={immediate} />
        <p className="mt-4 border-t border-pitch-line pt-3 font-mono text-xs text-ink-500">
          Projected after transfer costs:{" "}
          <span className="text-var-green">{immediate.predicted_points.toFixed(1)} pts</span>
        </p>
      </div>

      {/* The rest of the plan */}
      {rest.length > 0 && (
        <div className="mt-4 divide-y divide-pitch-line rounded-lg border border-pitch-line bg-pitch-panel">
          {rest.map((week) => (
            <div key={week.gameweek} className="flex flex-wrap gap-x-6 gap-y-2 px-5 py-3">
              <span className="w-16 shrink-0 font-mono text-xs text-ink-500">
                GW{week.gameweek}
              </span>
              <div className="min-w-0 flex-1">
                <MoveRow week={week} />
              </div>
              <span className="font-mono text-xs text-ink-500">
                {week.predicted_points.toFixed(1)} pts
              </span>
            </div>
          ))}
        </div>
      )}

      <p className="mt-3 font-mono text-[11px] text-ink-500">
        Later weeks are provisional — they assume today&apos;s form and prices, and get
        re-solved every run.
      </p>
    </section>
  );
}
