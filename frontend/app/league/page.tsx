// File: page.tsx
// Path: var-ified-xi/frontend/app/league/page.tsx
//
// Who you're actually racing, and what they own.

import type { Metadata } from "next";
import { getTeamData } from "@/lib/getTeamData";
import PageShell, { NoData } from "@/components/PageShell";
import LeagueView from "@/components/LeagueView";
import { Section } from "@/components/ui";

export const metadata: Metadata = { title: "League — VAR-ified XI" };

export default function LeaguePage() {
  const team = getTeamData();
  if (!team) return <NoData />;

  return (
    <PageShell team={team}>
      <Section
        id="league"
        eyebrow="Your league"
        title="What the managers ahead of you own"
        lede="Points you and a rival both score cancel out. What moves you past them is the players they don't have — and what quietly costs you is the ones they all have and you don't."
      >
        {team.league ? (
          <LeagueView league={team.league} />
        ) : (
          <p className="prose-note">No mini-league was read on this run.</p>
        )}
      </Section>
    </PageShell>
  );
}
