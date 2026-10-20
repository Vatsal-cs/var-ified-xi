// File: page.tsx
// Path: var-ified-xi/frontend/app/page.tsx
//
// This week: the decision that's due, and the team it produces.

import { getTeamData, deriveFormation } from "@/lib/getTeamData";
import PageShell, { NoData } from "@/components/PageShell";
import ThisWeek from "@/components/ThisWeek";
import PitchView from "@/components/PitchView";
import BenchStrip from "@/components/BenchStrip";
import SquadStats from "@/components/SquadStats";
import { Section } from "@/components/ui";
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

  return (
    <PageShell team={team}>
      {/* The decision that's due */}
      <ThisWeek team={team} />

      {/* The squad it produces */}
      <Section
        id="squad"
        eyebrow="The squad"
        title={
          chipTeam
            ? `Your ${chipTeam} team`
            : isPlan
            ? "Your team after these moves"
            : "The starting XI"
        }
        lede={
          chipTeam
            ? "Your XI and bench order as you set them. Tap any player for their projection and upcoming fixtures."
            : isPlan
            ? "How the pitch looks once this week's transfers are made. Tap any player for their projection and upcoming fixtures."
            : "The 15 the solver picked, and the 11 it starts. Tap any player for detail."
        }
      >
        <div className="grid gap-6 lg:grid-cols-[1fr_360px]">
          <div className="space-y-6">
            <SquadStats
              used={team.budget_used_m}
              total={team.budget_total_m}
              points={team.predicted_total_points}
              formation={formation}
              horizonGws={team.horizon_gws}
              valueLabel={isPlan ? "Squad value" : "Budget used"}
            />
            <BenchStrip
              bench={team.bench}
              startingXi={team.starting_xi}
              scale={team.odds_calibration?.pair_logit_scale ?? 1}
            />
          </div>
          <PitchView startingXi={team.starting_xi} coinFlipIds={flipIds} />
        </div>
      </Section>
    </PageShell>
  );
}
