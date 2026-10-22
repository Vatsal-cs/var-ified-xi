// File: page.tsx
// Path: var-ified-xi/frontend/app/plan/page.tsx
//
// Beyond this week: the multi-week transfer plan and when to play each chip.

import type { Metadata } from "next";
import { getTeamData } from "@/lib/getTeamData";
import PageShell, { NoData } from "@/components/PageShell";
import TransfersPanel from "@/components/TransfersPanel";
import ChipAdvice from "@/components/ChipAdvice";
import WildcardPanel from "@/components/WildcardPanel";
import { PageIntro, Section } from "@/components/ui";

export const metadata: Metadata = { title: "Plan & chips — VAR-ified XI" };

export default function PlanPage() {
  const team = getTeamData();
  if (!team) return <NoData />;
  const weeks = team.transfer_plan?.weeks ?? [];
  const later = weeks.slice(1);
  const moves = later.reduce((n, w) => n + w.transfers_out.length, 0);
  const hits = later.reduce((n, w) => n + w.hit_cost, 0);
  const expiry = team.chip_expiry;
  const first = later[0]?.gameweek;
  const lastGw = later[later.length - 1]?.gameweek;

  return (
    <PageShell team={team}>
      <PageIntro
        kicker={first && lastGw ? `Gameweeks ${first}–${lastGw}` : `Gameweek ${team.gameweek}`}
        title="The plan"
        sub={`The moves after this week's, and the best week for every chip${
          expiry ? ` before they expire at GW${expiry.deadline_gw}` : ""
        }.`}
        figures={[
          { label: "Planned transfers", value: moves },
          { label: "Points hits", value: hits > 0 ? `−${hits}` : "None", tone: hits > 0 ? "text-risk" : undefined },
          ...(expiry
            ? [
                { label: "Chips left", value: expiry.chips_left.length },
                { label: "Chip deadline", value: `GW${expiry.deadline_gw}` },
              ]
            : []),
        ]}
      />

      {team.mode === "transfer_plan" && later.length > 0 && (
        <Section
          id="outlook"
          title={`The next ${later.length} gameweeks`}
          lede="The solver plans this far ahead so it never sells a player it would only have to buy back."
        >
          <TransfersPanel weeks={weeks} />
        </Section>
      )}

      {/* Wildcard / Triple Captain / Bench Boost / Free Hit — named the
          moment a double or blank gameweek is close enough to act on,
          and explicit about "watching, nothing yet" otherwise. */}
      <Section id="chips" title="When to play a chip">
        <ChipAdvice
          advice={team.chip_advice}
          watch={team.chip_watch}
          expiry={team.chip_expiry}
          plan={team.chip_plan}
          horizonGws={team.horizon_gws}
        />
        {team.wildcard_option && (
          <div className="mt-8">
            <WildcardPanel option={team.wildcard_option} />
          </div>
        )}
      </Section>
    </PageShell>
  );
}
