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
import { Section } from "@/components/ui";

export const metadata: Metadata = { title: "Plan & chips — VAR-ified XI" };

export default function PlanPage() {
  const team = getTeamData();
  if (!team) return <NoData />;
  const weeks = team.transfer_plan?.weeks ?? [];

  return (
    <PageShell team={team}>
      {team.mode === "transfer_plan" && weeks.length > 1 && (
        <Section
          id="outlook"
          tone="violet"
          eyebrow="The plan"
          title={`The next ${weeks.length} gameweeks`}
          lede="The run of moves this week's decision belongs to. The solver looks this far ahead so it doesn't sell a player it would only have to buy back."
        >
          <TransfersPanel weeks={weeks} />
        </Section>
      )}

      {/* Wildcard / Triple Captain / Bench Boost / Free Hit — named the
          moment a double or blank gameweek is close enough to act on,
          and explicit about "watching, nothing yet" otherwise. */}
      <Section
        id="chips"
        tone="gold"
        eyebrow="Chip watch"
        title="When to play a chip"
        lede="Chips come in two half-season sets, and an unplayed chip is lost at its deadline. This tracks the deadline, values the best week in sight, and watches the fixture calendar for doubles and blanks."
      >
        <ChipAdvice
          advice={team.chip_advice}
          watch={team.chip_watch}
          expiry={team.chip_expiry}
          plan={team.chip_plan}
          horizonGws={team.horizon_gws}
        />
        {team.wildcard_option && (
          <div className="mt-4">
            <WildcardPanel option={team.wildcard_option} />
          </div>
        )}
      </Section>
    </PageShell>
  );
}
