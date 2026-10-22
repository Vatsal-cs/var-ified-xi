// File: page.tsx
// Path: var-ified-xi/frontend/app/other/page.tsx
//
// Games FPL doesn't show: cup, European and international.

import type { Metadata } from "next";
import { getTeamData } from "@/lib/getTeamData";
import PageShell, { NoData } from "@/components/PageShell";
import OtherMatches from "@/components/OtherMatches";
import { PageIntro } from "@/components/ui";

export const metadata: Metadata = { title: "Other games — VAR-ified XI" };

export default function OtherPage() {
  const team = getTeamData();
  if (!team) return <NoData />;
  const view = team.other_matches;
  const clubGames = view?.clubs.reduce((n, c) => n + c.matches.length, 0) ?? 0;
  const called = view?.international.length ?? 0;
  const far = view
    ? [...view.clubs.flatMap((c) => c.matches), ...view.international.flatMap((p) => p.matches)].filter((m) => m.far).length
    : 0;

  return (
    <PageShell team={team}>
      <PageIntro
        kicker="Beyond the Premier League"
        title="Other games"
        sub="FPL only shows Premier League matches. These are the cup, European and international games your players face before the end of the planning window."
        figures={
          view
            ? [
                { label: "Club games", value: clubGames },
                { label: "Players on international duty", value: called },
                { label: "Long trips", value: far, tone: far > 0 ? "text-warn" : undefined },
              ]
            : []
        }
      />
      {view ? (
        <OtherMatches view={view} />
      ) : (
        <p className="prose-note">No cup, European or international games were read on this run.</p>
      )}
    </PageShell>
  );
}
