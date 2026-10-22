// File: page.tsx
// Path: var-ified-xi/frontend/app/league/page.tsx
//
// Who you're actually racing, and what they own.

import type { Metadata } from "next";
import { getTeamData } from "@/lib/getTeamData";
import PageShell, { NoData } from "@/components/PageShell";
import LeagueView from "@/components/LeagueView";
import { PageIntro } from "@/components/ui";

export const metadata: Metadata = { title: "League — VAR-ified XI" };

const ordinal = (n: number) => {
  const s = ["th", "st", "nd", "rd"];
  const v = n % 100;
  return `${n}${s[(v - 20) % 10] || s[v] || s[0]}`;
};

export default function LeaguePage() {
  const team = getTeamData();
  if (!team) return <NoData />;
  const league = team.league;
  if (!league) {
    return (
      <PageShell team={team}>
        <PageIntro title="Your league" sub="No mini-league was read on this run." />
      </PageShell>
    );
  }
  const table = league.chips_spent;
  const you = table.find((r) => r.is_you);
  const leader = table[0];
  const above = you ? table.find((r) => r.rank === you.rank - 1) : undefined;
  const players = [...team.starting_xi, ...team.bench];

  return (
    <PageShell team={team}>
      <PageIntro
        kicker={league.league_name}
        title={league.your_rank ? `${ordinal(league.your_rank)} of ${league.league_size}` : league.league_name}
        sub={
          league.rivals_ahead > 0
            ? `Points you and a rival both score cancel out. What moves you up is what the ${league.rivals_ahead} managers ahead of you don't own.`
            : "You lead. What the chasers don't own is their way past you."
        }
        figures={[
          ...(you && leader && leader.entry !== you.entry
            ? [{ label: "Behind the leader", value: leader.total - you.total, tone: "text-risk" }]
            : []),
          ...(you && above ? [{ label: `Behind ${ordinal(above.rank)}`, value: above.total - you.total }] : []),
          { label: "Managers ahead", value: league.rivals_ahead },
          { label: "Read after", value: `GW${league.gameweek_read}` },
        ]}
      />
      <LeagueView league={league} players={players} />
    </PageShell>
  );
}
