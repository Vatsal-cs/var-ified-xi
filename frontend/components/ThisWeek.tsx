// File: ThisWeek.tsx
// Path: var-ified-xi/frontend/components/ThisWeek.tsx
//
// The one thing you came here for: the decision to make before this week's
// deadline, said in a sentence and drawn as a shirt swap on the kit-room rail.
// No card around it — it's the page's headline. <ThisWeekNotes> holds the
// smaller calls that go with it: the armband, close calls and team news.

import type { LineupCheck, OptimizedTeam, PickCheck, Player, PlannedWeek, TransferMove } from "@/lib/types";
import Crest from "@/components/Crest";
import Shirt, { Hanger } from "@/components/Shirt";
import { Figures, Term } from "./ui";
import CaptainOdds from "./CaptainOdds";
import TeamNews from "./TeamNews";
import CoinFlips from "./CoinFlips";
import { CountUp } from "./motion";
import { pct } from "@/lib/odds";

const CHIP_LABEL: Record<string, string> = { wildcard: "Wildcard", freehit: "Free Hit" };

function named(team: OptimizedTeam, id: number | null): Player | undefined {
  if (id == null) return undefined;
  return [...team.starting_xi, ...team.bench].find((p) => p.player_id === id);
}

function activeChip(team: OptimizedTeam): string | null {
  return team.active_chip && team.active_chip.gameweek === team.gameweek
    ? CHIP_LABEL[team.active_chip.chip] ?? team.active_chip.chip
    : null;
}

const and = (names: string[]) =>
  names.length <= 1 ? names.join("") : `${names.slice(0, -1).join(", ")} and ${names[names.length - 1]}`;

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
      <Hanger className="relative z-[1] -mb-1.5 w-[72px] sm:w-[88px]" />
      <Shirt
        team={move?.team}
        number={(move?.predicted_points ?? 0).toFixed(1)}
        uid={uid}
        className="h-[104px] w-[104px] drop-shadow-[0_12px_14px_rgba(0,0,0,0.22)] sm:h-[132px] sm:w-[132px]"
      />
      <p className="mt-2 flex items-center justify-center gap-1.5 text-[16px] font-semibold tracking-[-0.01em] text-ink-100 sm:text-[17px]">
        <Crest team={move?.team} className="h-[18px] w-[18px] flex-none" />
        <span className={isOut ? "line-through decoration-risk decoration-2" : ""}>{move?.name ?? "—"}</span>
      </p>
      <p className="text-[12.5px] text-ink-400">
        {isOut ? "Out" : "In"} &middot; {price != null ? `£${price.toFixed(1)}m` : "—"}
      </p>
    </div>
  );
}

/** The transfers as shirts on a rail: no box, just the rail and its hangers. */
function SwapRail({ week }: { week: PlannedWeek }) {
  return (
    <div className="space-y-6">
      {week.transfers_out.map((out, i) => {
        const inn = week.transfers_in[i];
        return (
          <div key={out.player_id} className="relative grid max-w-[520px] grid-cols-[1fr_44px_1fr] items-end pt-1">
            <span aria-hidden className="absolute inset-x-3 top-1 h-[3px] rounded-full bg-ink-500/45" />
            <SwapShirt move={out} tone="out" uid={`out-${out.player_id}`} />
            <span
              aria-hidden
              className="mb-14 animate-pop self-center justify-self-center text-[22px] text-ink-400"
              style={{ animationDelay: "1.5s" }}
            >
              &rarr;
            </span>
            <SwapShirt move={inn} tone="in" uid={`in-${inn?.player_id ?? i}`} />
          </div>
        );
      })}
    </div>
  );
}

/** Your chip team against the model's view of the same 15. */
function LockedCheck({ check, chip }: { check?: LineupCheck | null; chip: string }) {
  if (!check) return null;
  const changes = check.suggested_changes ?? [];
  if (changes.length > 0) {
    return (
      <div className="callout border-warn">
        <p className="text-[14px] font-semibold text-warn">The model would still change this</p>
        <ul className="mt-1.5 space-y-1">
          {changes.map((c) => (
            <li key={c.out_id} className="flex flex-wrap items-center gap-x-2 text-sm">
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
        <p className="mt-1.5 text-[13px] text-ink-300">
          +{check.suggested_gain.toFixed(1)} points over the planning window. Free while your {chip} is
          active, until the deadline; after that it costs a transfer.
        </p>
      </div>
    );
  }
  if (!check.model_agrees) {
    return (
      <div className="callout border-warn">
        <p className="text-[14px] font-semibold text-warn">The model would line it up differently</p>
        <p className="mt-1 text-sm text-ink-200">
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
          Captain {check.model_captain}, vice {check.model_vice_captain}. {check.points_model.toFixed(1)} pts
          its way vs {check.points_yours.toFixed(1)} yours.
        </p>
      </div>
    );
  }
  return null;
}

/** The headline and its one-sentence case. */
function decision(team: OptimizedTeam, week?: PlannedWeek): { headline: string; lede: string } {
  const chip = activeChip(team);
  const hit = team.transfer_plan?.hit_recommendation;
  if (chip) {
    const agrees = team.lineup_check?.model_agrees && !(team.lineup_check?.suggested_changes ?? []).length;
    return {
      headline: `${chip} played.`,
      lede: `Your team for Gameweek ${team.gameweek}, as you set it in the FPL app. FPL keeps a ${chip}'s transfers private until the deadline, so this is your own entry, re-checked against the latest projections every refresh.${
        agrees ? " The model agrees with every choice." : ""
      }`,
    };
  }
  if (team.mode !== "transfer_plan" || !week) {
    return {
      headline: "Your optimal squad.",
      lede: "Built from scratch under every FPL rule — £100m budget, 2/5/5/3 squad, max 3 per club. Use it for Gameweek 1, a Wildcard or a fresh start.",
    };
  }
  const outs = week.transfers_out;
  const ins = week.transfers_in;
  const extra = hit?.worth_it ? ` Also worth a −${hit.hit_cost}: ${hit.verdict}` : " Nothing beyond it is worth a −4.";
  if (outs.length === 0) {
    return {
      headline: "Hold this week.",
      lede: `No move beats rolling the free transfer to next week.${hit?.worth_it ? extra : ""}`,
    };
  }
  if (outs.length === 1) {
    const out = outs[0];
    const inn = ins[0];
    const diff = (out.sell_price_m ?? 0) - (inn?.cost_m ?? 0);
    const money =
      diff > 0.05
        ? `, and costs £${diff.toFixed(1)}m less than ${out.name} sells for`
        : diff < -0.05
          ? `, for £${(-diff).toFixed(1)}m more than ${out.name} sells for`
          : "";
    const covered = week.hits > 0 ? ` It costs a −${week.hit_cost}, and the model says that's worth it.` : extra;
    return {
      headline: `Sell ${out.name}. Buy ${inn?.name ?? "—"}.`,
      lede: `${inn?.name} is projected ${inn?.predicted_points.toFixed(1)} points this week${money}.${covered}`,
    };
  }
  return {
    headline: outs.length === 2 ? `Sell ${and(outs.map((o) => o.name))}.` : `Make ${outs.length} changes.`,
    lede: `In come ${and(ins.map((i) => i.name))}.${week.hits > 0 ? ` That's a −${week.hit_cost}, and the model says it's worth it.` : extra}`,
  };
}

/** The headline block: the decision, its case, the swap and the numbers. */
export default function ThisWeek({ team }: { team: OptimizedTeam }) {
  const week = team.transfer_plan?.weeks[0];
  const chip = activeChip(team);
  const { headline, lede } = decision(team, week);
  const checks = (week?.transfers_in ?? [])
    .map((inn) => team.pick_checks?.find((c) => c.player_id === inn.player_id && c.transfer))
    .filter((c): c is PickCheck => !!c);
  const hit = team.transfer_plan?.hit_recommendation;
  const league = team.league;

  const numbers: { label: string; value: React.ReactNode }[] =
    team.mode === "transfer_plan" && week
      ? [
          { label: "Projected", value: <><CountUp value={week.predicted_points} /><small className="ml-1 font-body text-[14px] font-medium text-ink-400">pts</small></> },
          { label: "Free transfers", value: chip ? "∞" : team.team?.free_transfers ?? "—" },
          { label: "Bank", value: `£${(team.team?.bank_m ?? 0).toFixed(1)}m` },
          league?.your_rank
            ? { label: "League", value: <>{league.your_rank}<small className="ml-1 font-body text-[14px] font-medium text-ink-400">of {league.league_size}</small></> }
            : { label: "Horizon", value: `${team.horizon_gws} GWs` },
        ]
      : [
          { label: "Projected", value: <><CountUp value={team.predicted_total_points} /><small className="ml-1 font-body text-[14px] font-medium text-ink-400">pts</small></> },
          { label: "Budget", value: `£${team.budget_used_m.toFixed(1)}m` },
          { label: "Horizon", value: `${team.horizon_gws} GWs` },
        ];

  return (
    <section id="week" className="scroll-mt-32">
      <p className="animate-rise text-[13px] text-ink-400">
        <span className="font-semibold text-gold">Gameweek {team.gameweek}</span>
        {team.team && (
          <>
            {" "}
            &middot; {team.team.name} &middot;{" "}
            {chip ? `${chip} active` : `${team.team.free_transfers} free transfer${team.team.free_transfers === 1 ? "" : "s"}`}{" "}
            &middot; &pound;{team.team.bank_m.toFixed(1)}m in the bank
          </>
        )}
      </p>
      <h1
        className="mt-2 animate-rise text-[38px] font-semibold leading-[1.02] tracking-[-0.035em] text-ink-100 sm:text-[52px]"
        style={{ animationDelay: "0.05s" }}
      >
        {/* One sentence per line: "Sell Semenyo." / "Buy Rogers." */}
        {headline.split(/(?<=\.) /).map((line, i) => (
          <span key={i} className="block">
            {line}
          </span>
        ))}
      </h1>
      <p className="mt-3 max-w-[46ch] animate-rise text-[16px] leading-relaxed text-ink-300" style={{ animationDelay: "0.1s" }}>
        {lede}
      </p>
      {checks.map((c) => (
        <p key={c.player_id} className="mt-2 max-w-[52ch] text-[13.5px] text-warn">
          Worth a second look: {c.name} &mdash; {c.flags.join("; ")}
        </p>
      ))}

      {chip ? (
        <div className="mt-6">
          <LockedCheck check={team.lineup_check} chip={chip} />
        </div>
      ) : (
        week &&
        week.transfers_out.length > 0 && (
          <div className="mt-8">
            <SwapRail week={week} />
          </div>
        )
      )}

      {hit?.worth_it && !chip && (
        <div className="callout mt-6 border-warn">
          <p className="text-[14px] font-semibold text-warn">
            <Term explain="FPL charges 4 points for each transfer beyond your free ones. Only worth it if the extra points clearly beat that cost.">
              Also take the &minus;{hit.hit_cost}
            </Term>
          </p>
          <ul className="mt-1.5 space-y-1">
            {hit.extra_transfers_out.map((out, i) => {
              const inn = hit.extra_transfers_in[i];
              return (
                <li key={out.player_id} className="flex flex-wrap items-center gap-x-2 text-sm">
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
        </div>
      )}

      <Figures items={numbers} className="mt-8" />
    </section>
  );
}

/** The captain in his shirt, armband on, and his week in numbers. */
function Captain({ team }: { team: OptimizedTeam }) {
  const cap = named(team, team.captain_id);
  const vice = named(team, team.vice_captain_id);
  if (!cap) return null;
  const override = team.captain_override;
  const modelCap = override ? named(team, override.model_captain_id) : undefined;
  const haul = team.captain_odds?.find((o) => o.player_id === cap.player_id)?.p_haul;
  return (
    <div>
      <div className="flex items-center gap-4">
        <Shirt
          team={cap.team}
          number={cap.predicted_points.toFixed(1)}
          uid={`cap-${cap.player_id}`}
          goalkeeper={cap.position === "GK"}
          captain
          armbandDelay={2.2}
          className="h-[88px] w-[88px] flex-none drop-shadow-[0_8px_10px_rgba(0,0,0,0.25)]"
        />
        <div className="min-w-0">
          <p className="text-[22px] font-semibold leading-tight tracking-[-0.02em] text-ink-100">{cap.name}</p>
          <p className="mt-0.5 text-[13px] leading-snug text-ink-400">
            {cap.team}
            {haul != null && <> &middot; {pct(haul)} chance of 10+</>}
          </p>
          {vice && <p className="text-[13px] text-ink-400">Vice-captain {vice.name}</p>}
        </div>
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

/** The armband: the captain in his shirt and who could outscore him. Sits
 *  under the decision, beside the pitch. */
export function Armband({ team }: { team: OptimizedTeam }) {
  const players = [...team.starting_xi, ...team.bench];
  return (
    <section aria-label="The armband" className="border-t border-line pt-7">
      <h2 className="mb-4 text-[15px] font-semibold text-ink-100">The armband</h2>
      <div className="grid gap-6 sm:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)] sm:gap-8">
        <Captain team={team} />
        {team.captain_odds && <CaptainOdds odds={team.captain_odds} players={players} />}
      </div>
    </section>
  );
}

/** The smaller calls that go with the decision, side by side under it. */
export function ThisWeekNotes({ team }: { team: OptimizedTeam }) {
  const scale = team.odds_calibration?.pair_logit_scale ?? 1;
  return (
    <section aria-label="This week's smaller calls" className="grid gap-10 border-t border-line pt-8 md:grid-cols-2 md:gap-0">
      <div className="md:pr-10">
        <h2 className="mb-4 text-[15px] font-semibold text-ink-100">Close calls</h2>
        <CoinFlips xi={team.starting_xi} bench={team.bench} scale={scale} />
      </div>
      <div className="md:border-l md:border-line md:pl-10">
        <h2 className="mb-4 text-[15px] font-semibold text-ink-100">Team news</h2>
        <TeamNews news={team.team_news} />
      </div>
    </section>
  );
}
