// File: page.tsx
// Path: var-ified-xi/frontend/app/page.tsx

import { getTeamData, deriveFormation } from "@/lib/getTeamData";
import SiteHeader from "@/components/SiteHeader";
import ThisWeek from "@/components/ThisWeek";
import PitchView from "@/components/PitchView";
import BenchStrip from "@/components/BenchStrip";
import SquadStats from "@/components/SquadStats";
import TransfersPanel from "@/components/TransfersPanel";
import PipelineExplainer from "@/components/PipelineExplainer";
import Glossary from "@/components/Glossary";
import { Section } from "@/components/ui";

export default function Home() {
  const team = getTeamData();

  if (!team) {
    return (
      <main className="mx-auto flex min-h-screen max-w-lg flex-col items-center justify-center gap-3 px-6 text-center">
        <p className="font-mono text-[11px] uppercase tracking-[0.24em] text-var-amber">
          No data yet
        </p>
        <h1 className="font-display text-2xl font-bold tracking-tight text-ink-100">
          Run the engine to generate a plan
        </h1>
        <p className="prose-note">
          From <code className="rounded bg-pitch-panel px-1.5 py-0.5 font-mono text-var-green">backend/</code>,
          run <code className="rounded bg-pitch-panel px-1.5 py-0.5 font-mono text-var-green">python main.py --team-id YOUR_ID</code>.
          It writes <code className="rounded bg-pitch-panel px-1.5 py-0.5 font-mono text-var-green">optimized_team.json</code> straight
          into this app&apos;s <code className="rounded bg-pitch-panel px-1.5 py-0.5 font-mono text-var-green">public/</code> folder.
        </p>
      </main>
    );
  }

  const formation = deriveFormation(team.starting_xi);
  const isPlan = team.mode === "transfer_plan";

  return (
    <div id="top">
      <SiteHeader team={team} />

      <main className="mx-auto max-w-5xl space-y-14 px-5 py-10 pb-28 sm:space-y-16">
        {/* The decision that's due */}
        <ThisWeek team={team} />

        {/* The squad it produces */}
        <Section
          id="squad"
          eyebrow="The squad"
          title={isPlan ? "Your team after these moves" : "The starting XI"}
          lede={
            isPlan
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
              <BenchStrip bench={team.bench} />
            </div>
            <PitchView startingXi={team.starting_xi} />
          </div>
        </Section>

        {/* The multi-week plan (transfer mode only, and only if there's more than week 1) */}
        {isPlan && team.transfer_plan && team.transfer_plan.weeks.length > 1 && (
          <Section
            id="outlook"
            eyebrow="The plan"
            title={`The next ${team.transfer_plan.weeks.length} gameweeks`}
            lede="The run of moves this week's decision belongs to. The solver looks this far ahead so it doesn't sell a player it would only have to buy back."
          >
            <TransfersPanel weeks={team.transfer_plan.weeks} />
          </Section>
        )}

        {/* How the answer was produced */}
        <Section
          id="how"
          eyebrow="Under the hood"
          title="How this was decided"
          lede="Five stages, run in order, every time the engine runs. Expand any stage for the real mechanics."
        >
          <PipelineExplainer />
        </Section>

        {/* Questions */}
        <Section
          id="faq"
          eyebrow="Good to know"
          title="Questions you might have"
          lede="Straight answers to what this page tends to raise."
        >
          <Glossary />
        </Section>

        <footer className="border-t border-pitch-line pt-8 text-center font-mono text-[11px] text-ink-500">
          VAR-ified XI — built on the free FPL API. Not affiliated with the Premier
          League or Fantasy Premier League. Projections are estimates, not
          guarantees.
        </footer>
      </main>
    </div>
  );
}
