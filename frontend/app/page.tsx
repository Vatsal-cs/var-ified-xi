// File: page.tsx
// Path: var-ified-xi/frontend/app/page.tsx
//
// This week: the decision that's due, staged as a shirt swap; then the
// dressing room it produces — the XI on a floodlit pitch, the bench on its
// rail, the armband and the close calls — then the team news.

import { getTeamData, deriveFormation } from "@/lib/getTeamData";
import PageShell, { NoData } from "@/components/PageShell";
import ThisWeek, { Armband, CloseCalls, NewsDesk } from "@/components/ThisWeek";
import PitchView from "@/components/PitchView";
import BenchStrip from "@/components/BenchStrip";
import { coinFlips } from "@/lib/odds";
import { OnView } from "@/components/motion";

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
  const title = chipTeam ? `Your ${chipTeam} team` : isPlan ? "The dressing room" : "The starting XI";

  return (
    <PageShell team={team}>
      {/* The decision that's due */}
      <ThisWeek team={team} />

      {/* The squad it produces */}
      <section id="squad" aria-label={title} className="scroll-mt-32">
        <div className="depth-rise mb-6 flex flex-wrap items-end justify-between gap-x-6 gap-y-2 border-t border-line pt-8">
          <div>
            <p className="kicker">{formation} &middot; {team.predicted_total_points.toFixed(1)} pts projected</p>
            <h2 className="headline mt-2 text-[40px] sm:text-[52px]">{title}</h2>
          </div>
          <p className="max-w-[40ch] text-[14px] text-ink-400">
            {isPlan ? (
              <>Squad value &pound;{team.budget_used_m.toFixed(1)}m</>
            ) : (
              <>
                Budget used &pound;{team.budget_used_m.toFixed(1)}m of &pound;{team.budget_total_m.toFixed(1)}m
              </>
            )}{" "}
            &middot; planned {team.horizon_gws} gameweeks ahead. Tap a shirt for the player&apos;s full projection.
          </p>
        </div>
        <div className="grid items-start gap-12 lg:grid-cols-[1.2fr_1fr] lg:gap-14">
          {/* Each block stands up as it scrolls into view, then plays its animations */}
          <div>
            <OnView className="depth-rise">
              <PitchView startingXi={team.starting_xi} coinFlipIds={flipIds} />
            </OnView>
            <OnView className="depth-rise mt-8">
              <BenchStrip
                bench={team.bench}
                startingXi={team.starting_xi}
                scale={team.odds_calibration?.pair_logit_scale ?? 1}
              />
            </OnView>
          </div>
          <div className="space-y-10">
            <OnView className="depth-rise">
              <Armband team={team} />
            </OnView>
            <OnView className="depth-rise">
              <CloseCalls team={team} />
            </OnView>
          </div>
        </div>
      </section>

      <section className="depth-rise border-t border-line pt-8">
        <NewsDesk team={team} />
      </section>
    </PageShell>
  );
}
