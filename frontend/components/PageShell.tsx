// File: PageShell.tsx
// Path: var-ified-xi/frontend/components/PageShell.tsx
//
// What every page shares: the sticky header with the page nav, the content
// column and the footer. The site used to be one long scroll with in-page
// anchors; each part now has its own page, and the nav only lists the pages
// this run has something for (fresh-squad mode has no league, for one).

import type { OptimizedTeam } from "@/lib/types";
import SiteHeader, { type NavPage } from "./SiteHeader";

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
      {/* The ground: a floodlit pitch at night (or in daylight) laid out in
          perspective below a horizon, its mown bands narrowing into the
          distance. Fixed, so the page scrolls over it like a camera pan. */}
      <div aria-hidden className="pointer-events-none fixed inset-0 z-0 overflow-hidden [perspective-origin:50%_0%] [perspective:900px]">
        <div
          className="absolute left-1/2 top-[52vh] h-[80vh] w-[260vw] origin-top"
          style={{
            transform: "translateX(-50%) rotateX(62deg)",
            backgroundImage:
              "repeating-linear-gradient(180deg, var(--turf-a) 0 9vh, var(--turf-b) 9vh 18vh)",
          }}
        >
          <svg className="absolute inset-0 h-full w-full" viewBox="0 0 1000 400" preserveAspectRatio="none" fill="none">
            <g stroke="var(--pitch-line)" strokeWidth="3" vectorEffect="non-scaling-stroke">
              <line x1="500" y1="0" x2="500" y2="400" vectorEffect="non-scaling-stroke" />
              <ellipse cx="500" cy="120" rx="46" ry="70" vectorEffect="non-scaling-stroke" />
              <line x1="0" y1="2" x2="1000" y2="2" vectorEffect="non-scaling-stroke" />
            </g>
          </svg>
        </div>
        {/* Haze where the pitch meets the dark, and the edges falling off */}
        <div className="absolute inset-x-0 top-[44vh] h-[22vh] bg-[linear-gradient(180deg,rgb(var(--c-base))_0%,rgb(var(--c-base)/0.6)_45%,transparent_100%)]" />
        <div className="absolute inset-0 bg-[radial-gradient(120%_80%_at_50%_100%,transparent_40%,rgb(var(--c-base)/0.85)_100%)]" />
      </div>
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
