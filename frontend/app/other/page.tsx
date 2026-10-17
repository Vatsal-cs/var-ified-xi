// File: page.tsx
// Path: var-ified-xi/frontend/app/other/page.tsx
//
// Games FPL doesn't show: cup, European and international.

import type { Metadata } from "next";
import { getTeamData } from "@/lib/getTeamData";
import PageShell, { NoData } from "@/components/PageShell";
import OtherMatches from "@/components/OtherMatches";
import { Section } from "@/components/ui";

export const metadata: Metadata = { title: "Other games — VAR-ified XI" };

export default function OtherPage() {
  const team = getTeamData();
  if (!team) return <NoData />;

  return (
    <PageShell team={team}>
      <Section
        id="other"
        eyebrow="Beyond the Premier League"
        title="Midweek and international games"
        lede="FPL only shows Premier League matches. These are the other games your players' clubs and countries play before the end of the planning window: a midweek tie means rotation risk, a long international trip means tired legs."
      >
        {team.other_matches ? (
          <OtherMatches view={team.other_matches} />
        ) : (
          <p className="prose-note">No cup, European or international games were read on this run.</p>
        )}
      </Section>
    </PageShell>
  );
}
