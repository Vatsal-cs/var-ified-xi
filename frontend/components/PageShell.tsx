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

/** The ground behind the top of every page: a stadium. Floodlights in the top
 *  corners, their light in the sky over the stand, and the pitch laid out in
 *  perspective below the horizon, its mown bands widening towards you. It
 *  scrolls away with the first screen and fades into the page below it; pinned
 *  to the screen, its floodlights sat on top of whatever scrolled past. */
function Stadium() {
  return (
    <div aria-hidden className="depth-far pointer-events-none absolute inset-x-0 top-0 z-0 h-[100svh] overflow-hidden">
      {/* The sky over the stand, lit from below */}
      <div className="absolute inset-0 bg-[radial-gradient(90%_42%_at_50%_30%,var(--sky-glow),transparent_72%)]" />
      <Floodlight side="left" />
      <Floodlight side="right" />
      {/* The pitch */}
      <div className="absolute inset-x-0 bottom-0 top-[13vh] [perspective-origin:50%_0%] [perspective:700px] lg:top-[30vh]">
        <div
          className="depth-turf absolute left-1/2 top-0 h-[700px] w-[400vw] origin-top"
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
      {/* No edge where the stadium ends */}
      <div className="absolute inset-x-0 bottom-0 h-[35%] bg-gradient-to-b from-transparent to-base" />
    </div>
  );
}

/** Below the stadium the page itself is the pitch at night: faint mown bands
 *  the length of the page, fading in where the stadium fades out. */
function PageTurf() {
  return (
    <div
      aria-hidden
      className="pointer-events-none absolute inset-0 z-0 bg-[repeating-linear-gradient(180deg,var(--page-turf-a)_0_150px,var(--page-turf-b)_150px_300px)] [mask-image:linear-gradient(180deg,transparent_65vh,#000_110vh)]"
    />
  );
}

// Chalk tactics, drawn in the turf's own shorthand: O for one of ours, X for
// one of theirs, a line for the ball and an arrow for a run.
const ring = (x: number, y: number, r = 12) => `M${x + r} ${y} A${r} ${r} 0 1 1 ${x - r} ${y} A${r} ${r} 0 1 1 ${x + r} ${y}`;
const cross = (x: number, y: number, s = 10) => `M${x - s} ${y - s} L${x + s} ${y + s} M${x + s} ${y - s} L${x - s} ${y + s}`;
/** An arrowhead at (x, y) for a line arriving in direction (dx, dy). */
function head(x: number, y: number, dx: number, dy: number, size = 15) {
  const len = Math.hypot(dx, dy);
  const [ux, uy] = [-dx / len, -dy / len];
  const barb = (a: number) =>
    `M${x} ${y} l${((ux * Math.cos(a) - uy * Math.sin(a)) * size).toFixed(1)} ${((ux * Math.sin(a) + uy * Math.cos(a)) * size).toFixed(1)}`;
  return `${barb(0.5)} ${barb(-0.5)}`;
}

const PLAYS: string[][] = [
  // The one-two: pass, run, and the ball played back into the run
  [
    ring(40, 215), ring(205, 140), cross(118, 170),
    `M54 208 L190 147 ${head(190, 147, 136, -61)}`,
    `M48 200 C70 120 110 70 175 48 ${head(175, 48, 65, -22)}`,
    `M200 126 L180 62 ${head(180, 62, -20, -64)}`,
  ],
  // The overlap: round the outside of the man on the ball
  [
    ring(70, 210), ring(150, 150), cross(205, 190), cross(108, 92),
    `M80 198 C170 210 235 120 190 40 ${head(190, 40, -45, -80)}`,
    `M150 136 L180 60 ${head(180, 60, 30, -76)}`,
  ],
  // Beat one, shoot
  [
    "M70 30 H190 M70 30 V12 M190 30 V12 M70 12 H190", "M40 30 V95 H220 V30",
    ring(150, 215), cross(110, 160),
    `M140 202 C120 180 160 165 135 140 ${head(135, 140, -25, -25)}`,
    `M135 140 L108 40 ${head(108, 40, -27, -100)}`,
  ],
];

// Where they're chalked up, by share of the page's height.
const BOARD: { play: number; top: string; side: "left" | "right"; at: string; turn: number; flip?: boolean }[] = [
  { play: 0, top: "15%", side: "left", at: "-1%", turn: -10 },
  { play: 1, top: "33%", side: "right", at: "0%", turn: 8 },
  { play: 2, top: "52%", side: "left", at: "2%", turn: 5 },
  { play: 0, top: "71%", side: "right", at: "2%", turn: -6, flip: true },
];

/** Old tactics in chalk on the turf, faint and behind everything, drawn in
 *  as you scroll past them (globals.css .chalk-draw). */
function Tactics() {
  return (
    <div aria-hidden className="pointer-events-none absolute inset-0 z-0 hidden overflow-clip md:block">
      {BOARD.map((b, i) => (
        <svg
          key={i}
          viewBox="0 0 260 260"
          className="chalk-draw absolute w-[min(24vw,320px)]"
          style={{ top: b.top, [b.side]: b.at, transform: `rotate(${b.turn}deg)${b.flip ? " scaleX(-1)" : ""}` }}
        >
          <defs>
            {/* Chalk never goes on quite straight */}
            <filter id={`chalk-${i}`}>
              <feTurbulence type="fractalNoise" baseFrequency="0.8" numOctaves="1" seed={i + 3} />
              <feDisplacementMap in="SourceGraphic" scale="3" />
            </filter>
          </defs>
          <g
            fill="none"
            stroke="var(--doodle)"
            strokeWidth="2.6"
            strokeLinecap="round"
            strokeLinejoin="round"
            filter={`url(#chalk-${i})`}
          >
            {PLAYS[b.play].map((d) => (
              <path key={d} d={d} pathLength={1} />
            ))}
          </g>
        </svg>
      ))}
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
      <PageTurf />
      <Tactics />
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
