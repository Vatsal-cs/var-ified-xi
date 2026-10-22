// File: page.tsx
// Path: var-ified-xi/frontend/app/how/page.tsx
//
// How the answer was produced, and the questions it tends to raise.

import type { Metadata } from "next";
import { getTeamData } from "@/lib/getTeamData";
import PageShell, { NoData } from "@/components/PageShell";
import PipelineExplainer from "@/components/PipelineExplainer";
import Glossary from "@/components/Glossary";
import { PageIntro, Section } from "@/components/ui";

export const metadata: Metadata = { title: "How it works — VAR-ified XI" };

export default function HowPage() {
  const team = getTeamData();
  if (!team) return <NoData />;

  return (
    <PageShell team={team}>
      <PageIntro
        kicker="Under the hood"
        title="How it works"
        sub="Five stages, run in order before every deadline. Open any stage for the real mechanics."
        figures={[
          { label: "Training rows", value: "~87k" },
          { label: "Planned ahead", value: `${team.horizon_gws} GWs` },
          { label: "Models averaged", value: 5 },
          { label: "Running cost", value: "$0" },
        ]}
      />
      <PipelineExplainer />

      <Section id="faq" title="Questions you might have">
        <Glossary />
      </Section>
    </PageShell>
  );
}
