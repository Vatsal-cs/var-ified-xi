// File: page.tsx
// Path: var-ified-xi/frontend/app/page.tsx

import { getTeamData, deriveFormation } from "@/lib/getTeamData";
import ReviewHeader from "@/components/ReviewHeader";
import PitchView from "@/components/PitchView";
import BenchStrip from "@/components/BenchStrip";
import BudgetGauge from "@/components/BudgetGauge";
import PipelineExplainer from "@/components/PipelineExplainer";
import Glossary from "@/components/Glossary";

export default function Home() {
  const team = getTeamData();

  if (!team) {
    return (
      <main className="flex min-h-screen flex-col items-center justify-center gap-3 px-6 text-center">
        <p className="font-mono text-xs uppercase tracking-[0.3em] text-var-amber">
          Review Pending
        </p>
        <h1 className="font-display text-2xl uppercase tracking-tight text-ink-100">
          No squad decision found yet
        </h1>
        <p className="max-w-md font-body text-sm text-ink-300">
          Run <code className="rounded bg-pitch-panel px-1.5 py-0.5 font-mono text-var-green">python main.py</code>{" "}
          in <code className="rounded bg-pitch-panel px-1.5 py-0.5 font-mono text-var-green">backend/</code> to
          generate <code className="rounded bg-pitch-panel px-1.5 py-0.5 font-mono text-var-green">optimized_team.json</code>.
          It writes straight into this app&apos;s <code className="rounded bg-pitch-panel px-1.5 py-0.5 font-mono text-var-green">public/</code> folder.
        </p>
      </main>
    );
  }

  const formation = deriveFormation(team.starting_xi);

  return (
    <>
      <ReviewHeader team={team} />
      <main className="mx-auto max-w-6xl px-6 pb-24">
        <section className="grid grid-cols-1 gap-8 py-10 lg:grid-cols-[minmax(0,1fr)_360px]">
          <div>
            <BudgetGauge
              used={team.budget_used_m}
              total={team.budget_total_m}
              points={team.predicted_total_points}
              formation={formation}
            />
            <div className="mt-6">
              <BenchStrip bench={team.bench} />
            </div>
          </div>
          <PitchView startingXi={team.starting_xi} />
        </section>

        <section className="border-t border-pitch-line py-14">
          <PipelineExplainer />
        </section>

        <section className="border-t border-pitch-line py-14">
          <Glossary />
        </section>

        <footer className="border-t border-pitch-line pt-8 text-center">
          <p className="font-mono text-[11px] text-ink-500">
            VAR-ified XI &mdash; built on the free FPL API. Not affiliated with the Premier League or FPL.
          </p>
        </footer>
      </main>
    </>
  );
}
