// File: page.tsx
// Path: var-ified-xi/frontend/app/how/page.tsx
//
// How the answer was produced, and the questions it tends to raise.

import type { Metadata } from "next";
import { getTeamData } from "@/lib/getTeamData";
import PageShell, { NoData } from "@/components/PageShell";
import PipelineExplainer from "@/components/PipelineExplainer";
import Glossary from "@/components/Glossary";
import { Section } from "@/components/ui";

export const metadata: Metadata = { title: "How it works — VAR-ified XI" };

export default function HowPage() {
  const team = getTeamData();
  if (!team) return <NoData />;

  return (
    <PageShell team={team}>
      <Section
        id="how"
        tone="sky"
        eyebrow="Under the hood"
        title="How this was decided"
        lede="Five stages, run in order, every time the engine runs. Expand any stage for the real mechanics."
      >
        <PipelineExplainer />
      </Section>

      <Section
        id="faq"
        tone="violet"
        eyebrow="Good to know"
        title="Questions you might have"
        lede="Straight answers to what this page tends to raise."
      >
        <Glossary />
      </Section>
    </PageShell>
  );
}
