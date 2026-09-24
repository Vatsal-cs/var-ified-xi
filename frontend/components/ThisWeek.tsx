// File: ThisWeek.tsx
// Path: var-ified-xi/frontend/components/ThisWeek.tsx
//
// The one thing you came here for: the decision to make before this week's
// deadline. Everything below it on the page is supporting detail.

import type { OptimizedTeam, Player, PlannedWeek } from "@/lib/types";
import { kitFor } from "@/lib/teams";
import { Term } from "./ui";

function named(team: OptimizedTeam, id: number | null): Player | undefined {
  if (id == null) return undefined;
  return [...team.starting_xi, ...team.bench].find((p) => p.player_id === id);
}

function CaptainLine({ team }: { team: OptimizedTeam }) {
  const cap = named(team, team.captain_id);
  const vice = named(team, team.vice_captain_id);
  if (!cap) return null;
  return (
    <div className="flex flex-wrap items-center gap-x-6 gap-y-1 font-body text-sm text-ink-300">
      <span>
        <span className="label mr-2">Captain&nbsp;</span>
        <span className="font-mono text-ink-100">{cap.name}</span>
        <span className="ml-1.5 text-ink-500">({cap.team})</span>
      </span>
      {vice && (
        <span>
          <span className="label mr-2">Vice&nbsp;</span>
          <span className="font-mono text-ink-200">{vice.name}</span>
        </span>
      )}
    </div>
  );
}

/** One side of a swap, wearing the club's colour so the move reads at a
 *  glance rather than as two names in a row. */
function SwapCard({
  name,
  team,
  sub,
  tone,
}: {
  name: string;
  team?: string;
  sub: string;
  tone: "out" | "in";
}) {
  const kit = kitFor(team);
  const isOut = tone === "out";
  return (
    <div
      className={`relative flex-1 overflow-hidden rounded-xl border p-3.5 ${
        isOut
          ? "border-risk/25 bg-risk/[0.06]"
          : "border-pts/30 bg-pts/[0.07]"
      }`}
    >
      <span
        className="absolute inset-y-0 left-0 w-1"
        style={{ background: kit.shirt }}
        aria-hidden
      />
      <p className={`label ${isOut ? "text-risk/80" : "text-pts/80"}`}>
        {isOut ? "Out" : "In"}
      </p>
      <p
        className={`mt-1 font-display text-lg font-bold leading-tight ${
          isOut ? "text-ink-300 line-through decoration-risk/50" : "text-ink-100"
        }`}
      >
        {name}
      </p>
      <p className="mt-0.5 font-mono text-[11px] text-ink-400">
        {kit.abbr} &middot; {sub}
      </p>
    </div>
  );
}

function TransferRows({ week }: { week: PlannedWeek }) {
  if (week.transfers_out.length === 0) {
    return (
      <p className="font-body text-[15px] text-ink-200">
        No transfer. Bank your free transfer for next week.
      </p>
    );
  }
  return (
    <ul className="space-y-3">
      {week.transfers_out.map((out, i) => {
        const inn = week.transfers_in[i];
        return (
          <li key={out.player_id} className="flex items-stretch gap-2.5">
            <SwapCard
              name={out.name}
              team={out.team}
              sub={`£${out.sell_price_m?.toFixed(1) ?? "—"}m`}
              tone="out"
            />
            <span
              aria-hidden
              className="flex w-7 flex-none items-center justify-center font-display text-xl text-ink-500"
            >
              &rarr;
            </span>
            <SwapCard
              name={inn?.name ?? "—"}
              team={inn?.team}
              sub={`£${inn?.cost_m?.toFixed(1) ?? "—"}m · ${
                inn?.predicted_points.toFixed(1) ?? "—"
              } pts proj.`}
              tone="in"
            />
          </li>
        );
      })}
    </ul>
  );
}

export default function ThisWeek({ team }: { team: OptimizedTeam }) {
  const plan = team.transfer_plan;
  const week = plan?.weeks[0];
  const hit = plan?.hit_recommendation ?? null;

  // Headline
  const headline =
    team.mode !== "transfer_plan"
      ? "Your optimal squad"
      : !week || week.transfers_out.length === 0
      ? "Hold this week"
      : week.transfers_out.length === 1
      ? "Make this transfer"
      : `Make these ${week.transfers_out.length} transfers`;

  return (
    <div id="week" className="glass-brand scroll-mt-32 p-6 sm:p-7">
      <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
        <p className="font-mono text-[11px] uppercase tracking-[0.22em] text-pts">
          Gameweek {team.gameweek} &middot; before the deadline
        </p>
        {team.team && (
          <p className="font-mono text-[11px] text-ink-400">
            {team.team.name} &middot; {team.team.free_transfers} free transfer
            {team.team.free_transfers === 1 ? "" : "s"} &middot;{" "}
            &pound;{team.team.bank_m.toFixed(1)}m bank
          </p>
        )}
      </div>

      <h1 className="mt-2 font-display text-3xl font-bold tracking-tight text-ink-100 sm:text-4xl">
        {headline}
      </h1>

      <div className="mt-5 space-y-4">
        {team.mode === "transfer_plan" && week ? (
          <>
            <TransferRows week={week} />

            {/* Is a points hit worth it this week? */}
            <div
              className={`rounded-lg border p-3.5 ${
                hit?.worth_it
                  ? "border-warn/40 bg-warn/[0.06]"
                  : "border-line bg-surface-raised/50"
              }`}
            >
              <p className="label">
                <Term explain="FPL charges 4 points for each transfer beyond your free ones. Only worth it if the extra points clearly beat that cost.">
                  Points hit
                </Term>{" "}
                — worth it?
              </p>
              {hit?.worth_it ? (
                <>
                  <p className="mt-1.5 font-body text-sm text-warn">
                    Yes — on top of the free transfer(s) above, also take the &minus;
                    {hit.hit_cost}:
                  </p>
                  <ul className="mt-2 space-y-1.5">
                    {hit.extra_transfers_out.map((out, i) => {
                      const inn = hit.extra_transfers_in[i];
                      return (
                        <li
                          key={out.player_id}
                          className="flex flex-wrap items-center gap-x-2 gap-y-0.5 font-mono text-sm"
                        >
                          <span className="text-risk line-through decoration-risk/40">
                            {out.name}
                          </span>
                          <span aria-hidden className="text-ink-500">
                            &rarr;
                          </span>
                          <span className="font-medium text-pts">{inn?.name ?? "—"}</span>
                        </li>
                      );
                    })}
                  </ul>
                  <p className="mt-2 font-body text-xs text-ink-300">{hit.verdict}</p>
                </>
              ) : (
                <p className="mt-1.5 font-body text-sm text-ink-300">
                  No — nothing beyond the free transfer(s) above out-earns its &minus;4.
                  Stop there.
                </p>
              )}
            </div>

            <CaptainLine team={team} />

            <p className="border-t border-line pt-3 font-mono text-xs text-ink-400">
              Projected GW{team.gameweek} score after transfer costs:{" "}
              <span className="text-pts">
                {week.predicted_points.toFixed(1)} pts
              </span>
            </p>
          </>
        ) : (
          <>
            <p className="prose-note">
              Built from scratch under every FPL rule — &pound;100m budget, 2/5/5/3
              squad, max 3 per club. Use this for Gameweek 1, a wildcard, or a
              fresh start.
            </p>
            <CaptainLine team={team} />
            <div className="grid grid-cols-3 gap-3 border-t border-line pt-4">
              <div>
                <p className="label">Proj. points</p>
                <p className="mt-1 font-mono text-xl text-pts">
                  {team.predicted_total_points.toFixed(1)}
                </p>
              </div>
              <div>
                <p className="label">Budget</p>
                <p className="mt-1 font-mono text-xl text-ink-100">
                  &pound;{team.budget_used_m.toFixed(1)}m
                </p>
              </div>
              <div>
                <p className="label">Horizon</p>
                <p className="mt-1 font-mono text-xl text-ink-100">
                  {team.horizon_gws} GWs
                </p>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
