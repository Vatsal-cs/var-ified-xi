// File: ThisWeek.tsx
// Path: var-ified-xi/frontend/components/ThisWeek.tsx
//
// The one thing you came here for: the decision to make before this week's
// deadline. Everything below it on the page is supporting detail.

import type { LineupCheck, OptimizedTeam, PickCheck, Player, PlannedWeek } from "@/lib/types";
import { kitFor } from "@/lib/teams";
import { Term } from "./ui";
import CaptainOdds from "./CaptainOdds";
import TeamNews from "./TeamNews";

function named(team: OptimizedTeam, id: number | null): Player | undefined {
  if (id == null) return undefined;
  return [...team.starting_xi, ...team.bench].find((p) => p.player_id === id);
}

function CaptainLine({ team }: { team: OptimizedTeam }) {
  const cap = named(team, team.captain_id);
  const vice = named(team, team.vice_captain_id);
  if (!cap) return null;
  const override = team.captain_override;
  const modelCap = override ? named(team, override.model_captain_id) : undefined;
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
      {override && modelCap && modelCap.player_id !== cap.player_id && (
        <span className="font-mono text-[11px] text-ink-500">
          your call &middot; the model had {modelCap.name} (
          {modelCap.predicted_points.toFixed(1)} vs {cap.predicted_points.toFixed(1)} pts)
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
      className={`relative flex-1 overflow-hidden rounded-[3px] border p-3.5 ${
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
        className={`mt-1.5 font-display text-[26px] leading-[1.05] ${
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

function TransferRows({ week, checks = [] }: { week: PlannedWeek; checks?: PickCheck[] }) {
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
      {week.transfers_in
        .map((inn) => checks.find((c) => c.player_id === inn.player_id && c.transfer))
        .filter((c): c is PickCheck => !!c)
        .map((c) => (
          <li key={`check-${c.player_id}`} className="font-mono text-[11px] text-warn">
            Worth a second look: {c.name} &mdash; {c.flags.join("; ")}
          </li>
        ))}
    </ul>
  );
}

const CHIP_LABEL: Record<string, string> = { wildcard: "Wildcard", freehit: "Free Hit" };

/** Your chip team against the model's view of the same 15: whether it would
 *  still change a player (free until the deadline) or the lineup. */
function LockedCheck({ check, chip }: { check?: LineupCheck | null; chip: string }) {
  if (!check) return null;
  const changes = check.suggested_changes ?? [];
  if (changes.length > 0) {
    return (
      <div className="rounded-[2px] border border-warn/40 bg-warn/[0.06] p-3.5">
        <p className="label text-warn">The model would still change this</p>
        <ul className="mt-2 space-y-1.5">
          {changes.map((c) => (
            <li
              key={c.out_id}
              className="flex flex-wrap items-center gap-x-2 gap-y-0.5 font-mono text-sm"
            >
              <span className="text-risk line-through decoration-risk/40">{c.out}</span>
              <span aria-hidden className="text-ink-500">
                &rarr;
              </span>
              <span className="font-medium text-pts">{c.in}</span>
              <span className="text-[11px] text-ink-500">
                £{c.in_cost_m.toFixed(1)}m · {c.out_points.toFixed(1)} &rarr;{" "}
                {c.in_points.toFixed(1)} pts this week
              </span>
            </li>
          ))}
        </ul>
        <p className="mt-2 font-body text-xs text-ink-300">
          +{check.suggested_gain.toFixed(1)} points over the planning window. Free while
          your {chip} is active, until the deadline; after that it costs a transfer.
        </p>
      </div>
    );
  }
  if (!check.model_agrees) {
    return (
      <div className="rounded-[2px] border border-warn/40 bg-warn/[0.06] p-3.5">
        <p className="label text-warn">The model would line it up differently</p>
        <p className="mt-1.5 font-body text-sm text-ink-200">
          {check.model_would_start.length > 0 && (
            <>
              Start <span className="text-pts">{check.model_would_start.join(", ")}</span>
              {check.model_would_bench.length > 0 && (
                <>
                  {" "}
                  over <span className="text-risk">{check.model_would_bench.join(", ")}</span>
                </>
              )}
              .{" "}
            </>
          )}
          Captain {check.model_captain}, vice {check.model_vice_captain}.
        </p>
        <p className="mt-1 font-mono text-[11px] text-ink-500">
          {check.points_model.toFixed(1)} pts its way vs {check.points_yours.toFixed(1)} yours
        </p>
      </div>
    );
  }
  return (
    <p className="font-body text-[15px] text-ink-200">
      The model agrees: same XI, same armband, and nothing in the market worth changing for.
      Changes stay free until the deadline if the news turns.
    </p>
  );
}

export default function ThisWeek({ team }: { team: OptimizedTeam }) {
  const plan = team.transfer_plan;
  const week = plan?.weeks[0];
  const hit = plan?.hit_recommendation ?? null;
  const chip =
    team.active_chip && team.active_chip.gameweek === team.gameweek
      ? CHIP_LABEL[team.active_chip.chip] ?? team.active_chip.chip
      : null;

  // Headline
  const headline = chip
    ? `${chip} played`
    : team.mode !== "transfer_plan"
      ? "Your optimal squad"
      : !week || week.transfers_out.length === 0
      ? "Hold this week"
      : week.transfers_out.length === 1
      ? "Make this transfer"
      : `Make these ${week.transfers_out.length} transfers`;

  return (
    <div id="week" className="panel-lead scroll-mt-32 p-6 sm:p-9">
      <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
        <p className="font-mono text-[10px] uppercase tracking-[0.28em] text-gold">
          Gameweek {team.gameweek} &middot; before the deadline
        </p>
        {team.team && (
          <p className="font-mono text-[11px] text-ink-400">
            {team.team.name} &middot;{" "}
            {chip ? (
              <span className="text-gold">{chip} active &middot; unlimited free transfers</span>
            ) : (
              <>
                {team.team.free_transfers} free transfer
                {team.team.free_transfers === 1 ? "" : "s"}
              </>
            )}{" "}
            &middot; &pound;{team.team.bank_m.toFixed(1)}m bank
          </p>
        )}
      </div>

      <h1 className="mt-3 font-display text-[44px] leading-[1] tracking-[-0.02em] text-ink-100 sm:text-[60px]">
        {headline}
      </h1>

      <div className="mt-5 space-y-4">
        {chip && week ? (
          <>
            <p className="prose-note">
              Your team for Gameweek {team.gameweek}, as you set it in the FPL app. FPL keeps
              a {chip}&apos;s transfers private until the deadline, so this comes from your
              own entry rather than FPL&apos;s public data, and every refresh re-checks it
              against the latest projections and team news.
            </p>
            <LockedCheck check={team.lineup_check} chip={chip} />
            <CaptainLine team={team} />
            {team.captain_odds && <CaptainOdds odds={team.captain_odds} />}
            <TeamNews news={team.team_news} />
            <p className="border-t border-line pt-3 font-mono text-xs text-ink-400">
              Projected GW{team.gameweek} score for your XI:{" "}
              <span className="text-pts">{week.predicted_points.toFixed(1)} pts</span>
            </p>
          </>
        ) : team.mode === "transfer_plan" && week ? (
          <>
            <TransferRows week={week} checks={team.pick_checks} />

            {/* Is a points hit worth it this week? */}
            <div
              className={`rounded-[2px] border p-3.5 ${
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
            {team.captain_odds && (
              <CaptainOdds odds={team.captain_odds} />
            )}
            <TeamNews news={team.team_news} />

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
