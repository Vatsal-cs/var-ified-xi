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
      {/* Chalk markings behind the top of the page: a centre circle and the
          halfway line, drawn faintly enough to read as the ground underfoot. */}
      <div aria-hidden className="pointer-events-none absolute inset-x-0 top-0 h-[820px] overflow-hidden">
        <svg
          viewBox="0 0 800 800"
          fill="none"
          className="absolute -right-[260px] top-[-120px] h-[640px] w-[640px] sm:-right-[160px] sm:h-[800px] sm:w-[800px]"
        >
          <circle cx="400" cy="400" r="330" stroke="var(--pitch-line)" strokeWidth="2.5" />
          <circle cx="400" cy="400" r="7" fill="var(--pitch-line)" />
        </svg>
        <span className="absolute inset-x-0 top-[200px] h-[2.5px] bg-[var(--pitch-line)] sm:top-[280px]" />
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
