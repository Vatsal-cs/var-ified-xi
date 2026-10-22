// File: ThisWeek.tsx
// Path: var-ified-xi/frontend/components/ThisWeek.tsx
//
// The one thing you came here for: the decision to make before this week's
// deadline. A transfer is drawn as a shirt swap on the kit-room rail — the
// old shirt taken down, the new one hung up. The other pages are supporting
// detail.

import type { LineupCheck, OptimizedTeam, PickCheck, Player, PlannedWeek, TransferMove } from "@/lib/types";
import Crest from "@/components/Crest";
import Shirt, { Hanger } from "@/components/Shirt";
import { Term } from "./ui";
import CaptainOdds from "./CaptainOdds";
import TeamNews from "./TeamNews";
import CoinFlips from "./CoinFlips";
import { CountUp } from "./motion";
import { pct } from "@/lib/odds";

function named(team: OptimizedTeam, id: number | null): Player | undefined {
  if (id == null) return undefined;
  return [...team.starting_xi, ...team.bench].find((p) => p.player_id === id);
}

/** The captain, with his crest and armband, the vice, and — when you overrode
 *  the model — what it would have picked. */
function CaptainCard({ team }: { team: OptimizedTeam }) {
  const cap = named(team, team.captain_id);
  const vice = named(team, team.vice_captain_id);
  if (!cap) return null;
  const override = team.captain_override;
  const modelCap = override ? named(team, override.model_captain_id) : undefined;
  const haul = team.captain_odds?.find((o) => o.player_id === cap.player_id)?.p_haul;
  return (
    <div className="border-t border-line pt-5">
      <div className="flex items-center gap-3">
        <Crest team={cap.team} className="h-10 w-10 flex-none" />
        <div className="min-w-0">
          <p className="text-[19px] font-semibold tracking-[-0.02em] text-ink-100">{cap.name}</p>
          <p className="text-[13px] text-ink-400">
            Captain &middot; {cap.predicted_points.toFixed(1)} pts
            {haul != null && <> &middot; {pct(haul)} chance of 10+</>}
            {vice && <> &middot; vice {vice.name}</>}
          </p>
        </div>
        <span
          aria-hidden
          className="ml-auto grid h-8 w-8 flex-none -rotate-[8deg] animate-pop place-items-center rounded-lg bg-[#E3A93C] text-[14px] font-extrabold text-[#2A1A00]"
          style={{ animationDelay: "2.1s" }}
        >
          C
        </span>
      </div>
      {override && modelCap && modelCap.player_id !== cap.player_id && (
        <p className="mt-2 text-[12.5px] text-ink-400">
          Your call &middot; the model had {modelCap.name} ({modelCap.predicted_points.toFixed(1)} vs{" "}
          {cap.predicted_points.toFixed(1)} pts)
        </p>
      )}
    </div>
  );
}

/** One shirt on the swap rail. */
function SwapShirt({ move, tone, uid }: { move?: TransferMove; tone: "out" | "in"; uid: string }) {
  const isOut = tone === "out";
  const price = isOut ? move?.sell_price_m : move?.cost_m;
  return (
    <div
      className={`shirt-hang flex flex-col items-center text-center ${
        isOut ? "-translate-x-1.5 -rotate-[7deg] opacity-50 grayscale animate-outgo" : "animate-income"
      }`}
      style={{ animationDelay: isOut ? "0.5s" : "0.9s" }}
    >
      <Hanger className="relative z-[1] -mb-1.5 w-[70px] sm:w-[84px]" />
      <Shirt
        team={move?.team}
        number={(move?.predicted_points ?? 0).toFixed(1)}
        uid={uid}
        className="h-24 w-24 drop-shadow-[0_10px_12px_rgba(0,0,0,0.22)] sm:h-[118px] sm:w-[118px]"
      />
      <p className="mt-2 flex items-center justify-center gap-1.5 text-[16px] font-semibold tracking-[-0.01em] text-ink-100 sm:text-[17px]">
        <Crest team={move?.team} className="h-[18px] w-[18px] flex-none" />
        <span className={isOut ? "line-through decoration-risk decoration-2" : ""}>{move?.name ?? "—"}</span>
      </p>
      <p className="text-[12.5px] text-ink-400">
        {price != null ? `£${price.toFixed(1)}m` : "—"}
        {!isOut && move && <> &middot; {move.predicted_points.toFixed(1)} pts</>}
      </p>
      <span
        className={`mt-1.5 rounded-full px-2 py-px text-[10.5px] font-bold tracking-[0.12em] text-white ${
          isOut ? "bg-risk" : "bg-pts"
        }`}
      >
        {isOut ? "OUT" : "IN"}
      </span>
    </div>
  );
}

function TransferRows({ week, checks = [] }: { week: PlannedWeek; checks?: PickCheck[] }) {
  if (week.transfers_out.length === 0) {
    return (
      <p className="text-[15px] text-ink-200">
        No transfer. Bank your free transfer for next week.
      </p>
    );
  }
  const notes = week.transfers_in
    .map((inn) => checks.find((c) => c.player_id === inn.player_id && c.transfer))
    .filter((c): c is PickCheck => !!c);
  return (
    <div className="space-y-3">
      {week.transfers_out.map((out, i) => {
        const inn = week.transfers_in[i];
        return (
          <div
            key={out.player_id}
            className="relative grid grid-cols-[1fr_40px_1fr] items-end overflow-hidden rounded-2xl bg-surface-raised px-3 pb-4 pt-4 sm:grid-cols-[1fr_54px_1fr]"
          >
            <span aria-hidden className="absolute inset-x-5 top-3.5 h-[3px] rounded-full bg-ink-500/40" />
            <SwapShirt move={out} tone="out" uid={`out-${out.player_id}`} />
            <span
              aria-hidden
              className="grid h-9 w-9 animate-pop place-items-center self-center justify-self-center rounded-full border border-line bg-surface text-ink-400"
              style={{ animationDelay: "1.5s" }}
            >
              &rarr;
            </span>
            <SwapShirt move={inn} tone="in" uid={`in-${inn?.player_id ?? i}`} />
          </div>
        );
      })}
      {notes.map((c) => (
        <p key={`check-${c.player_id}`} className="text-[13px] text-warn">
          Worth a second look: {c.name} &mdash; {c.flags.join("; ")}
        </p>
      ))}
    </div>
  );
}

/** A row of small numbers under the decision. */
function Figures({ items }: { items: { label: string; value: React.ReactNode; tone?: string }[] }) {
  return (
    <div className="grid grid-cols-2 gap-2.5 sm:grid-cols-4">
      {items.map((it) => (
        <div key={it.label} className="rounded-xl border border-line px-3 py-2.5">
          <p className="label">{it.label}</p>
          <p className={`mt-0.5 font-kit text-[26px] font-bold leading-tight tabular-nums ${it.tone ?? "text-ink-100"}`}>
            {it.value}
          </p>
        </div>
      ))}
    </div>
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
      <div className="rounded-xl border border-warn/40 bg-warn/[0.07] p-4">
        <p className="label text-warn">The model would still change this</p>
        <ul className="mt-2 space-y-1.5">
          {changes.map((c) => (
            <li key={c.out_id} className="flex flex-wrap items-center gap-x-2 gap-y-0.5 text-sm">
              <span className="text-risk line-through decoration-risk/40">{c.out}</span>
              <span aria-hidden className="text-ink-500">
                &rarr;
              </span>
              <span className="font-medium text-pts">{c.in}</span>
              <span className="text-[12px] text-ink-400">
                £{c.in_cost_m.toFixed(1)}m · {c.out_points.toFixed(1)} &rarr; {c.in_points.toFixed(1)} pts this week
              </span>
            </li>
          ))}
        </ul>
        <p className="mt-2 text-xs text-ink-300">
          +{check.suggested_gain.toFixed(1)} points over the planning window. Free while your {chip} is
          active, until the deadline; after that it costs a transfer.
        </p>
      </div>
    );
  }
  if (!check.model_agrees) {
    return (
      <div className="rounded-xl border border-warn/40 bg-warn/[0.07] p-4">
        <p className="label text-warn">The model would line it up differently</p>
        <p className="mt-1.5 text-sm text-ink-200">
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
        <p className="mt-1 text-[12px] text-ink-400">
          {check.points_model.toFixed(1)} pts its way vs {check.points_yours.toFixed(1)} yours
        </p>
      </div>
    );
  }
  return (
    <p className="text-[15px] text-ink-200">
      The model agrees: same XI, same armband, and nothing in the market worth changing for. Changes
      stay free until the deadline if the news turns.
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
  const xiAndBench = [...team.starting_xi, ...team.bench];
  const scale = team.odds_calibration?.pair_logit_scale ?? 1;

  const headline = chip
    ? `${chip} played`
    : team.mode !== "transfer_plan"
      ? "Your optimal squad"
      : !week || week.transfers_out.length === 0
        ? "Hold this week"
        : week.transfers_out.length === 1
          ? "One change this week"
          : `${week.transfers_out.length} changes this week`;

  const league = team.league;
  const figures =
    team.mode === "transfer_plan" && week
      ? [
          { label: "Projected", value: <><CountUp value={week.predicted_points} /><span className="ml-0.5 font-body text-[13px] font-medium text-ink-400">pts</span></> },
          { label: "Free transfers", value: chip ? "∞" : team.team?.free_transfers ?? "—" },
          { label: "Bank", value: `£${(team.team?.bank_m ?? 0).toFixed(1)}m` },
          league?.your_rank
            ? { label: "League", value: <>{league.your_rank}<span className="ml-0.5 font-body text-[13px] font-medium text-ink-400">of {league.league_size}</span></> }
            : { label: "Horizon", value: `${team.horizon_gws} GWs` },
        ]
      : [
          { label: "Projected", value: <><CountUp value={team.predicted_total_points} /><span className="ml-0.5 font-body text-[13px] font-medium text-ink-400">pts</span></>, tone: "text-pts" },
          { label: "Budget", value: `£${team.budget_used_m.toFixed(1)}m` },
          { label: "Horizon", value: `${team.horizon_gws} GWs` },
        ];

  return (
    <section id="week" className="panel-lead scroll-mt-32 animate-rise p-5 sm:p-8">
      <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
        <p className="label text-gold">Gameweek {team.gameweek} &middot; before the deadline</p>
        {team.team && (
          <p className="text-[12.5px] text-ink-400">
            {team.team.name} &middot;{" "}
            {chip ? (
              <span className="text-gold">{chip} active &middot; unlimited free transfers</span>
            ) : (
              <>
                {team.team.free_transfers} free transfer{team.team.free_transfers === 1 ? "" : "s"}
              </>
            )}{" "}
            &middot; &pound;{team.team.bank_m.toFixed(1)}m bank
          </p>
        )}
      </div>

      <h1 className="mt-2 text-[28px] font-semibold leading-tight tracking-[-0.025em] text-ink-100 sm:text-[34px]">
        {headline}
      </h1>

      <div className="mt-5 space-y-5">
        {chip && week ? (
          <>
            <p className="prose-note">
              Your team for Gameweek {team.gameweek}, as you set it in the FPL app. FPL keeps a {chip}
              &apos;s transfers private until the deadline, so this comes from your own entry rather than
              FPL&apos;s public data, and every refresh re-checks it against the latest projections and
              team news.
            </p>
            <LockedCheck check={team.lineup_check} chip={chip} />
            <Figures items={figures} />
          </>
        ) : team.mode === "transfer_plan" && week ? (
          <>
            <TransferRows week={week} checks={team.pick_checks} />
            <Figures items={figures} />

            {/* Is a points hit worth it this week? */}
            <div
              className={`rounded-xl border p-4 ${
                hit?.worth_it ? "border-warn/40 bg-warn/[0.07]" : "border-line bg-surface-raised"
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
                  <p className="mt-1.5 text-sm text-warn">
                    Yes — on top of the free transfer(s) above, also take the &minus;{hit.hit_cost}:
                  </p>
                  <ul className="mt-2 space-y-1.5">
                    {hit.extra_transfers_out.map((out, i) => {
                      const inn = hit.extra_transfers_in[i];
                      return (
                        <li key={out.player_id} className="flex flex-wrap items-center gap-x-2 gap-y-0.5 text-sm">
                          <Crest team={out.team} className="h-4 w-4 flex-none opacity-60 grayscale" />
                          <span className="text-risk line-through decoration-risk/40">{out.name}</span>
                          <span aria-hidden className="text-ink-500">
                            &rarr;
                          </span>
                          <Crest team={inn?.team} className="h-4 w-4 flex-none" />
                          <span className="font-medium text-pts">{inn?.name ?? "—"}</span>
                        </li>
                      );
                    })}
                  </ul>
                  <p className="mt-2 text-xs text-ink-300">{hit.verdict}</p>
                </>
              ) : (
                <p className="mt-1.5 text-sm text-ink-300">
                  No — nothing beyond the free transfer(s) above out-earns its &minus;4. Stop there.
                </p>
              )}
            </div>
          </>
        ) : (
          <>
            <p className="prose-note">
              Built from scratch under every FPL rule — &pound;100m budget, 2/5/5/3 squad, max 3 per
              club. Use this for Gameweek 1, a wildcard, or a fresh start.
            </p>
            <Figures items={figures} />
          </>
        )}

        <CaptainCard team={team} />
        {team.captain_odds && <CaptainOdds odds={team.captain_odds} players={xiAndBench} />}
        <CoinFlips xi={team.starting_xi} bench={team.bench} scale={scale} />
        <TeamNews news={team.team_news} />
      </div>
    </section>
  );
}
