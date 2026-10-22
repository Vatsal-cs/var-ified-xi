// File: page.tsx
// Path: var-ified-xi/frontend/app/page.tsx
//
// This week: the decision that's due, beside the dressing room it produces —
// the XI on the pitch and the bench on its rail.

import { getTeamData, deriveFormation } from "@/lib/getTeamData";
import PageShell, { NoData } from "@/components/PageShell";
import ThisWeek from "@/components/ThisWeek";
import PitchView from "@/components/PitchView";
import BenchStrip from "@/components/BenchStrip";
import { coinFlips } from "@/lib/odds";

export default function Home() {
  const team = getTeamData();
  if (!team) return <NoData />;

  const formation = deriveFormation(team.starting_xi);
  const flipIds = coinFlips(team.starting_xi, team.bench, team.odds_calibration?.pair_logit_scale ?? 1)
    .map((f) => f.starter.player_id);
  const isPlan = team.mode === "transfer_plan";
  const chipTeam =
    team.active_chip && team.active_chip.gameweek === team.gameweek
      ? team.active_chip.chip === "freehit"
        ? "Free Hit"
        : "Wildcard"
      : null;
  const title = chipTeam
    ? `Your ${chipTeam} team`
    : isPlan
      ? "The dressing room"
      : "The starting XI";

  return (
    <PageShell team={team}>
      <div className="grid items-start gap-5 lg:grid-cols-[1fr_1.08fr]">
        {/* The decision that's due */}
        <ThisWeek team={team} />

        {/* The squad it produces */}
        <section
          id="squad"
          aria-label={title}
          className="panel scroll-mt-32 animate-rise p-5 sm:p-6"
          style={{ animationDelay: "0.08s" }}
        >
          <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1">
            <p className="label">
              {title} &middot; {formation}
            </p>
            <p className="text-[12.5px] text-ink-400">
              <span className="font-semibold text-ink-100">{team.predicted_total_points.toFixed(1)}</span> pts
              projected
            </p>
          </div>
          <div className="mt-3">
            <PitchView startingXi={team.starting_xi} coinFlipIds={flipIds} />
          </div>
          <div className="mt-5">
            <BenchStrip
              bench={team.bench}
              startingXi={team.starting_xi}
              scale={team.odds_calibration?.pair_logit_scale ?? 1}
            />
          </div>
          <p className="mt-4 text-center text-[12px] text-ink-500">
            {isPlan ? (
              <>Squad value &pound;{team.budget_used_m.toFixed(1)}m</>
            ) : (
              <>
                Budget used &pound;{team.budget_used_m.toFixed(1)}m of &pound;{team.budget_total_m.toFixed(1)}m
              </>
            )}{" "}
            &middot; planned {team.horizon_gws} gameweeks ahead
          </p>
        </section>
      </div>
    </PageShell>
  );
}
