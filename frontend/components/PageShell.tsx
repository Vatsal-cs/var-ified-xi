// File: PageShell.tsx
// Path: var-ified-xi/frontend/components/PageShell.tsx
//
// What every page shares: the sticky header with the page nav, the content
// column and the footer. The site used to be one long scroll with in-page
// anchors; each part now has its own page, and the nav only lists the pages
// this run has something for (fresh-squad mode has no league, for one).

import type { OptimizedTeam } from "@/lib/types";
import SiteHeader, { type NavPage } from "./SiteHeader";
import Chalkboard from "./Chalkboard";

// How brightly each of the twelve lamps burns: never all quite the same.
const LAMPS = [1, 1, 0.9, 1, 0.95, 1, 1, 0.85, 1, 0.92, 1, 1];

/** A bank of floodlights high in a corner, just under the header whatever the
 *  screen (it measures itself into --header-h), sized to the screen too.
 *  Twelve lamps on a frame turned down and in towards the pitch, the air
 *  round them catching the light, and a beam with dust in it falling across
 *  the ground; a mast below where there's room beside the page. Lit at night;
 *  in daylight the lamps are off and there's no beam (globals.css). */
function Floodlight({ side }: { side: "left" | "right" }) {
  const left = side === "left";
  return (
    <div
      className="absolute w-[clamp(28px,3.6vw,58px)]"
      style={{ top: "calc(var(--header-h) + clamp(4px, 1vw, 16px))", [side]: "clamp(10px, 2.4vw, 46px)" }}
    >
      <div
        className="floodlight-beam absolute left-[calc(50%-110vh)] top-1/2 h-[110vh] w-[220vh] origin-top"
        style={{ transform: `rotate(calc(var(--beam-turn) * ${left ? -1 : 1}))` }}
      />
      <div className="floodlight-bloom absolute left-1/2 top-1/2 aspect-square w-[360%] -translate-x-1/2 -translate-y-1/2" />
      <div className="absolute left-1/2 top-[70%] hidden h-[42vh] w-[3px] -translate-x-1/2 bg-gradient-to-b from-[var(--mast)] to-transparent xl:block" />
      <div
        className="relative grid grid-cols-4 gap-[2px] rounded-[3px] p-[3px] shadow-[0_4px_10px_rgba(0,0,0,0.45),inset_0_1px_0_rgba(255,255,255,0.14)]"
        style={{
          background: "var(--lamp-frame)",
          transform: `perspective(260px) rotateX(16deg) rotateY(${left ? 26 : -26}deg)`,
        }}
      >
        {LAMPS.map((burn, i) => (
          <span key={i} className="floodlight-lamp aspect-square rounded-full" style={{ opacity: burn }} />
        ))}
      </div>
    </div>
  );
}

/** A length on the stadium's pitch, in metres at the scale of its far side
 *  (--stadium-m, globals.css, which grows with the screen). */
const metres = (n: number) => `calc(${n} * var(--stadium-m))`;

/** The pitch below the horizon, laid flat and seen from high in the main
 *  stand: touchlines, halfway line, centre circle, both boxes and their arcs,
 *  mown across its width so the stripes run away towards the far side, and
 *  the perimeter boards lit behind the far touchline. Drawn upright here; the
 *  plane it lies on is tipped back in perspective (Stadium). */
function StadiumPitch() {
  const end = (side: "left" | "right") => {
    const at = side === "left" ? "left-0 border-l-0" : "right-0 border-r-0";
    return (
      <>
        <div className={`absolute top-1/2 -translate-y-1/2 border-2 border-[var(--stadium-line)] ${at}`} style={{ width: metres(16.5), height: metres(40.3) }} />
        <div className={`absolute top-1/2 -translate-y-1/2 border-2 border-[var(--stadium-line)] ${at}`} style={{ width: metres(5.5), height: metres(18.3) }} />
        {/* The arc of the D: the circle round the spot, beyond the box */}
        <div
          className="absolute top-1/2 -translate-y-1/2 rounded-full border-2 border-[var(--stadium-line)]"
          style={{
            [side]: metres(11 - 9.15),
            width: metres(18.3),
            height: metres(18.3),
            clipPath: side === "left" ? "inset(0 0 0 80%)" : "inset(0 80% 0 0)",
          }}
        />
        <div
          className="absolute top-1/2 h-[5px] w-[5px] -translate-y-1/2 rounded-full bg-[var(--stadium-line)]"
          style={{ [side]: metres(11) }}
        />
      </>
    );
  };
  return (
    <div
      className="absolute left-1/2 -translate-x-1/2 border-2 border-[var(--stadium-line)]"
      style={{
        top: metres(4),
        width: metres(105),
        height: metres(68),
        backgroundImage: "repeating-linear-gradient(90deg, var(--turf-b) 0 5.5556%, var(--turf-a) 5.5556% 11.1111%)",
      }}
    >
      <div
        className="absolute left-1/2 -translate-x-1/2 bg-[linear-gradient(90deg,transparent,var(--boards)_12%,var(--boards)_88%,transparent)]"
        style={{ top: metres(-3.2), width: metres(118), height: metres(1) }}
      />
      <div className="absolute inset-y-0 left-1/2 w-[2px] -translate-x-1/2 bg-[var(--stadium-line)]" />
      <div
        className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-[var(--stadium-line)]"
        style={{ width: metres(18.3), height: metres(18.3) }}
      />
      <div className="absolute left-1/2 top-1/2 h-[5px] w-[5px] -translate-x-1/2 -translate-y-1/2 rounded-full bg-[var(--stadium-line)]" />
      {end("left")}
      {end("right")}
    </div>
  );
}

/** The ground behind the top of every page: a stadium at night, the wide shot
 *  from the main stand. Floodlights in the top corners, their light in the
 *  sky over the far stand, and the pitch laid out in perspective below the
 *  horizon. It scrolls away with the first screen and fades into the page
 *  below it; pinned to the screen, its floodlights sat on top of whatever
 *  scrolled past. */
function Stadium() {
  return (
    <div aria-hidden className="depth-far pointer-events-none absolute inset-x-0 top-0 z-0 h-[100svh] overflow-hidden">
      {/* The sky over the stand, lit from below */}
      <div className="absolute inset-0 bg-[radial-gradient(90%_36%_at_50%_10%,var(--sky-glow),transparent_72%)]" />
      <Floodlight side="left" />
      <Floodlight side="right" />
      {/* The ground: the pitch on a wider plane of grass, tipped back. Its far
          side sits just under the header, level with the floodlights, so the
          page reads as standing on it rather than a line running through it. */}
      <div
        className="absolute inset-x-0 bottom-0 [perspective-origin:50%_0%] [perspective:700px]"
        style={{ top: "calc(var(--header-h) + 2.5vh)" }}
      >
        <div
          className="depth-turf absolute left-1/2 top-0 h-[1400px] w-[400vw] origin-top bg-[var(--turf-a)]"
          style={{ transform: "translateX(-50%) rotateX(64deg)" }}
        >
          <StadiumPitch />
        </div>
      </div>
      {/* Mist where the pitch meets the stand, and the corners falling into shadow */}
      <div
        className="absolute inset-x-0 h-[14vh] bg-[linear-gradient(180deg,transparent,var(--mist)_50%,transparent)]"
        style={{ top: "calc(var(--header-h) + 2.5vh - 7vh)" }}
      />
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
      <Chalkboard team={team} />
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
