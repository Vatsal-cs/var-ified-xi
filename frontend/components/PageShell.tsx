// File: PageShell.tsx
// Path: var-ified-xi/frontend/components/PageShell.tsx
//
// What every page shares: the sticky header with the page nav, the content
// column and the footer. The site used to be one long scroll with in-page
// anchors; each part now has its own page, and the nav only lists the pages
// this run has something for (fresh-squad mode has no league, for one).

import type { OptimizedTeam } from "@/lib/types";
import SiteHeader, { type NavPage } from "./SiteHeader";

/** A bank of floodlights high in a corner, throwing its beam across the
 *  ground. Lit at night; in daylight the lamps are off and there's no beam. */
function Floodlight({ side }: { side: "left" | "right" }) {
  const left = side === "left";
  return (
    <div className={`absolute top-[11vh] hidden lg:block ${left ? "left-[2.5vw]" : "right-[2.5vw]"}`}>
      <div
        className="absolute top-4 h-[85vh] w-[44vw]"
        style={{
          [left ? "left" : "right"]: "10px",
          background: "linear-gradient(180deg, var(--beam), transparent 78%)",
          clipPath: left ? "polygon(0 0, 7% 0, 100% 100%, 38% 100%)" : "polygon(93% 0, 100% 0, 62% 100%, 0 100%)",
        }}
      />
      <div
        className="relative grid grid-cols-4 gap-[3px] rounded-[3px] bg-[var(--lamp-frame)] p-[4px]"
        style={{ transform: `rotate(${left ? 9 : -9}deg)` }}
      >
        {Array.from({ length: 12 }, (_, i) => (
          <span key={i} className="h-[7px] w-[7px] rounded-full bg-[var(--lamp)] shadow-[var(--lamp-glow)]" />
        ))}
      </div>
    </div>
  );
}

/** The ground behind every page: a stadium. Floodlights in the top corners,
 *  their light in the sky over the stand, and the pitch laid out in
 *  perspective below the horizon, its mown bands widening towards you. Fixed,
 *  so the page scrolls over it like a camera pan. */
function Stadium() {
  return (
    <div aria-hidden className="pointer-events-none fixed inset-0 z-0 overflow-hidden">
      {/* The sky over the stand, lit from below */}
      <div className="absolute inset-0 bg-[radial-gradient(90%_42%_at_50%_30%,var(--sky-glow),transparent_72%)]" />
      <Floodlight side="left" />
      <Floodlight side="right" />
      {/* The pitch */}
      <div className="absolute inset-x-0 bottom-0 top-[13vh] [perspective-origin:50%_0%] [perspective:700px] lg:top-[30vh]">
        <div
          className="absolute left-1/2 top-0 h-[700px] w-[400vw] origin-top"
          style={{
            transform: "translateX(-50%) rotateX(64deg)",
            backgroundImage: "repeating-linear-gradient(180deg, var(--turf-a) 0 56px, var(--turf-b) 56px 112px)",
          }}
        >
        </div>
      </div>
      {/* Mist where the pitch meets the stand, and the corners falling into shadow */}
      <div className="absolute inset-x-0 top-[6vh] h-[16vh] bg-[linear-gradient(180deg,transparent,var(--mist)_50%,transparent)] lg:top-[22vh] lg:h-[18vh]" />
      <div className="absolute inset-0 bg-[radial-gradient(140%_95%_at_50%_42%,transparent_55%,rgb(var(--c-base)/0.85)_100%)]" />
    </div>
  );
}

export function pagesFor(team: OptimizedTeam): NavPage[] {
  const pages: NavPage[] = [
    { href: "/", label: "This week" },
    { href: "/plan", label: "Plan & chips" },
  ];
  if (team.league) pages.push({ href: "/league", label: "League" });
  if (team.other_matches) pages.push({ href: "/other", label: "Other games" });
  pages.push({ href: "/how", label: "How it works" });
  return pages;
}

export default function PageShell({
  team,
  children,
}: {
  team: OptimizedTeam;
  children: React.ReactNode;
}) {
  return (
    <div id="top" className="relative overflow-x-clip">
      <SiteHeader team={team} pages={pagesFor(team)} />
      <Stadium />
      <main className="relative mx-auto max-w-6xl space-y-14 px-4 py-8 pb-24 sm:space-y-20 sm:px-6 sm:py-12">
        {children}
        <footer className="border-t border-line pt-8 text-center text-[12.5px] text-ink-500">
          VAR-ified XI — built on the free FPL API. Not affiliated with the Premier
          League or Fantasy Premier League. Projections are estimates, not
          guarantees.
        </footer>
      </main>
    </div>
  );
}

export function NoData() {
  return (
    <main className="mx-auto flex min-h-screen max-w-lg flex-col items-center justify-center gap-3 px-6 text-center">
      <p className="label text-warn">No data yet</p>
      <h1 className="text-2xl font-semibold tracking-tight text-ink-100">
        Run the engine to generate a plan
      </h1>
      <p className="prose-note">
        From <code className="rounded-md bg-surface px-1.5 py-0.5 font-mono text-pts">backend/</code>,
        run{" "}
        <code className="rounded-md bg-surface px-1.5 py-0.5 font-mono text-pts">
          python main.py --team-id YOUR_ID
        </code>
        . It writes{" "}
        <code className="rounded-md bg-surface px-1.5 py-0.5 font-mono text-pts">optimized_team.json</code>{" "}
        straight into this app&apos;s{" "}
        <code className="rounded-md bg-surface px-1.5 py-0.5 font-mono text-pts">public/</code> folder.
      </p>
    </main>
  );
}
