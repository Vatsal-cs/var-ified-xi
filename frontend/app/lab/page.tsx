// File: page.tsx
// Path: var-ified-xi/frontend/app/lab/page.tsx
//
// The lab: every study run on the model, the ones that failed included, with
// the rule each had to pass and when its plan was committed (lib/lab.ts).

import type { Metadata } from "next";
import { getTeamData } from "@/lib/getTeamData";
import PageShell, { NoData } from "@/components/PageShell";
import LabChart, { Marker, ProofLine } from "@/components/LabChart";
import { PageIntro, Section } from "@/components/ui";
import { BENCH_FIXES, LAB_CHECKS, LAB_TESTS, studyCount } from "@/lib/lab";

export const metadata: Metadata = {
  title: "The lab — VAR-ified XI",
  description:
    "Every change to the model had to win real points, by more than the noise, on a rule written down before the first result. Every test so far, including the ones that failed.",
};

const STEPS: { title: string; body: string }[] = [
  {
    title: "Replay real seasons",
    body: "Each week the model trains only on what was known before that deadline, picks a team and is scored on what actually happened, autosubs and captain fallback included. Points, not accuracy: you field 15 of ~600 players, so a lower average error can still pick a worse team.",
  },
  {
    title: "Five seeds, one interval",
    body: "Changing nothing but the random seed moved a two-season replay from 4,443 to 4,618 points, with accuracy identical to three decimals. So every comparison runs on five seeds, week against week, with a 95% interval from a block bootstrap.",
  },
  {
    title: "Three verdicts, written down first",
    body: "Better: the interval above zero and ahead in both seasons. Worse: below zero and behind in both. Anything else is no detectable effect, which means the test can't tell, not that the idea is wrong.",
  },
  {
    title: "Then seasons it never saw",
    body: "A change that comes out better runs once on 2022-23 and 2023-24, held back from all tuning, and ships only if it stays ahead in both.",
  },
];

export default function LabPage() {
  const team = getTeamData();
  if (!team) return <NoData />;
  const { studies, planFirst } = studyCount();
  const count = (v: string) => LAB_TESTS.filter((t) => t.verdict === v).length;

  return (
    <PageShell team={team}>
      <PageIntro
        kicker="Research lab"
        title="The lab"
        sub="Nothing here ships because it sounds smart. A change has to score more real points than the model it would replace, by more than the noise, on a rule written down before the first result. This is every test so far, including the ones that failed."
        figures={[
          { label: "Studies", value: studies },
          { label: "Shipped", value: count("shipped") },
          { label: "Clearly worse", value: count("worse") },
          { label: "Plan committed first", value: `${planFirst} of ${studies}` },
        ]}
      />

      <Section id="rules" eyebrow="The rules" title="How a change gets in">
        <ol className="grid gap-x-10 gap-y-6 border-t border-line pt-6 sm:grid-cols-2">
          {STEPS.map((s, i) => (
            <li key={s.title} className="flex gap-4">
              <span className="font-display text-[26px] font-extrabold leading-none text-gold">{i + 1}</span>
              <div>
                <p className="font-semibold text-ink-100">{s.title}</p>
                <p className="mt-1 text-[15px] leading-relaxed text-ink-300">{s.body}</p>
              </div>
            </li>
          ))}
        </ol>
      </Section>

      <Section
        id="tests"
        eyebrow="Every tested change"
        title={`${LAB_TESTS.length} changes, one scale`}
        lede="Points gained or lost against the model at the time, over two replayed seasons. The marker is the best estimate and the line its 95% interval: a line crossing zero means the test can't tell. Open a row for the question, the seasons and when its plan was committed."
      >
        <LabChart />
        <p className="callout mt-8 max-w-[68ch] text-[14px] leading-relaxed text-ink-300">
          About the dates. Each study&rsquo;s plan and result are separate files, and the history shows when each went in.
          For {planFirst} of {studies} studies the plan is there first. For the other {studies - planFirst} they went in
          together, so for those the order rests on my word.
        </p>
      </Section>

      <Section
        id="checks"
        eyebrow="Measured another way"
        title="Questions that weren't a points race"
        lede="Some questions are about whether the numbers are honest, not whether a change wins points. Same rule: the bar was set before the result."
      >
        <ul className="divide-y divide-line border-y border-line">
          {LAB_CHECKS.map((q) => (
            <li key={q.title} className="grid gap-x-8 gap-y-1.5 py-4 md:grid-cols-[17rem_minmax(0,1fr)]">
              <div>
                <p className="font-semibold leading-snug text-ink-100">{q.title}</p>
                <p className="mt-1 text-[13px] font-medium text-ink-400">{q.outcome}</p>
              </div>
              <div className="max-w-[68ch] text-[14.5px] leading-relaxed text-ink-300">
                <p>{q.result}</p>
                <p className="mt-1.5 text-[13px] text-ink-400">
                  <ProofLine proof={q.proof} />
                </p>
              </div>
            </li>
          ))}
        </ul>
      </Section>

      <Section
        id="bench"
        eyebrow="Before any of this"
        title="Fixing the test bench first"
        lede="None of the results above mean anything if the replay isn't playing the real game. An audit found it wasn't. Each fix came with the direction it should move the totals, so a fix that moved them the wrong way would point at a bug in the fix."
      >
        <div className="border-t border-line">
          <div className="hidden grid-cols-[minmax(0,1.2fr)_minmax(0,1fr)_minmax(0,1fr)] gap-x-6 border-b border-line py-2 text-[12.5px] text-ink-400 md:grid">
            <span>Fix</span>
            <span>Should move totals</span>
            <span>Measured</span>
          </div>
          <ul className="divide-y divide-line border-b border-line">
            {BENCH_FIXES.map((f) => (
              <li key={f.fix} className="grid gap-x-6 gap-y-1 py-3.5 text-[14.5px] md:grid-cols-[minmax(0,1.2fr)_minmax(0,1fr)_minmax(0,1fr)]">
                <span className="font-semibold text-ink-100">{f.fix}</span>
                <span className="text-ink-300">
                  <span className="text-ink-400 md:hidden">Should move totals: </span>
                  {f.expected}
                </span>
                <span className="flex items-start gap-2 text-ink-200">
                  <Marker verdict="shipped" className="mt-[6px] flex-none" />
                  <span>
                    <span className="text-ink-400 md:hidden">Measured: </span>
                    {f.measured}
                  </span>
                </span>
              </li>
            ))}
          </ul>
        </div>
        <div className="mt-8 grid gap-x-10 gap-y-6 md:grid-cols-2">
          <div>
            <p className="font-semibold text-ink-100">A benchmark too good to be true</p>
            <p className="mt-1 text-[15px] leading-relaxed text-ink-300">
              FPL&rsquo;s own archived expected points built squads scoring about 99 a week, two thirds of perfect
              hindsight, which no forecast made before a deadline can do. They&rsquo;re recorded after lineups are
              known. The comparison was dropped instead of left in looking authoritative.
            </p>
          </div>
          <div>
            <p className="font-semibold text-ink-100">A headline, retracted</p>
            <p className="mt-1 text-[15px] leading-relaxed text-ink-300">
              The project&rsquo;s old best result, +299 points from a stricter rule on &minus;4 hits, was measured on the
              broken simulator. On the fixed one it came to &minus;1 [&minus;92, +97]: no detectable effect.
            </p>
          </div>
        </div>
      </Section>
    </PageShell>
  );
}
