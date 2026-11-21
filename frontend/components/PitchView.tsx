// File: PitchView.tsx
// Path: var-ified-xi/frontend/components/PitchView.tsx
//
// The XI as club shirts on the pitch, the projection as the shirt number.
// The ground is a 3D model: the turf tipped back in real perspective and the
// shirts standing on it, popping up one at a time — keeper first, forwards
// last — with the captain's armband going on once they're all up. It leans
// towards the pointer and can be dragged round (Orbit, motion.tsx). Hover a shirt for a quick
// look; tap it for the full spread and fixture run. The ground is dressed
// for a night match: full markings and goals, mown grass, a shadow from each
// of the four floodlights, the ball on the spot and the LED board behind the
// far goal running the week's numbers.
"use client";

import { useState } from "react";
import type { Player, PointsDist } from "@/lib/types";
import Crest from "@/components/Crest";
import Shirt from "@/components/Shirt";
import { pct } from "@/lib/odds";
import { Orbit } from "@/components/motion";

const ROW_ORDER: Player["position"][] = ["FWD", "MID", "DEF", "GK"];
// Where each line stands on the turf, from the far touchline (0) to the near one (1).
const ROW_Y: Record<Player["position"], number> = { FWD: 0.15, MID: 0.39, DEF: 0.63, GK: 0.87 };

const HANG_ORDER: Player["position"][] = ["GK", "DEF", "MID", "FWD"];

// A pylon in each corner throws a shadow from every player, away from itself:
// the X you see under players at a night match. Those falling towards the
// far end are shorter, foreshortened by the camera. Angles from pointing right.
const SHADOWS = [
  { angle: 26, length: 7.5 },
  { angle: 154, length: 7.5 },
  { angle: -30, length: 5 },
  { angle: -150, length: 5 },
];

// The markings, in the turf's own units: 100 across, 100 from the far end to
// the near one, each unit down being 1.2 across (the turf is 1.2 times taller
// than it is wide), so a circle of radius r is drawn rx r, ry r / 1.2.
const LINES = { left: 3, right: 97, far: 2.5, near: 97.5 };
const CIRCLE_R = 13; // 9.15 m
const SPOT_FROM_LINE = 8.7; // 11 m
const BOX_DEPTH = 13;
const GOAL = { half: 5.05, depth: 1.8 }; // 7.32 m by 2 m
const CORNER_R = 1.4;
const ry = (r: number) => r / 1.2;

/** The arc of the D: the part of the circle round the penalty spot that's
 *  outside the box. */
function penaltyArc(end: "far" | "near") {
  const spot = end === "far" ? LINES.far + SPOT_FROM_LINE : LINES.near - SPOT_FROM_LINE;
  const edge = end === "far" ? LINES.far + BOX_DEPTH : LINES.near - BOX_DEPTH;
  const dx = CIRCLE_R * Math.sqrt(1 - ((edge - spot) / ry(CIRCLE_R)) ** 2);
  const sweep = end === "far" ? 0 : 1;
  return `M${50 - dx} ${edge} A${CIRCLE_R} ${ry(CIRCLE_R)} 0 0 ${sweep} ${50 + dx} ${edge}`;
}

/** A goal behind each goal line: the frame and its net, seen from above. */
function Goal({ end }: { end: "far" | "near" }) {
  const line = end === "far" ? LINES.far : LINES.near;
  const back = end === "far" ? line - GOAL.depth : line + GOAL.depth;
  const [l, r] = [50 - GOAL.half, 50 + GOAL.half];
  const strands = Array.from({ length: 9 }, (_, i) => l + ((r - l) * (i + 1)) / 10);
  return (
    <g>
      <g stroke="var(--chalk)" strokeWidth="0.6" opacity="0.7">
        {strands.map((x) => (
          <line key={x} x1={x} y1={line} x2={x} y2={back} vectorEffect="non-scaling-stroke" />
        ))}
        <line x1={l} y1={(line + back) / 2} x2={r} y2={(line + back) / 2} vectorEffect="non-scaling-stroke" />
      </g>
      <path d={`M${l} ${line} L${l} ${back} L${r} ${back} L${r} ${line}`} vectorEffect="non-scaling-stroke" />
      {/* The posts and crossbar, brighter than the chalk */}
      <line x1={l} y1={line} x2={r} y2={line} stroke="rgba(255,255,255,0.75)" strokeWidth="2.4" vectorEffect="non-scaling-stroke" />
    </g>
  );
}

/** Every line on a real pitch, in chalk. */
function Markings() {
  const { left, right, far, near } = LINES;
  const corner = (x: number, y: number, dx: number, dy: number, sweep: number) =>
    `M${x + dx * CORNER_R} ${y} A${CORNER_R} ${ry(CORNER_R)} 0 0 ${sweep} ${x} ${y + dy * ry(CORNER_R)}`;
  return (
    <svg className="absolute inset-0 h-full w-full" viewBox="0 0 100 100" preserveAspectRatio="none">
      <g fill="none" stroke="var(--chalk)" strokeWidth="1.4">
        <rect x={left} y={far} width={right - left} height={near - far} vectorEffect="non-scaling-stroke" />
        <line x1={left} y1="50" x2={right} y2="50" vectorEffect="non-scaling-stroke" />
        <ellipse cx="50" cy="50" rx={CIRCLE_R} ry={ry(CIRCLE_R)} vectorEffect="non-scaling-stroke" />
        {(["far", "near"] as const).map((end) => {
          const line = end === "far" ? far : near;
          const into = end === "far" ? 1 : -1;
          return (
            <g key={end}>
              <path d={`M25 ${line} V${line + into * BOX_DEPTH} H75 V${line}`} vectorEffect="non-scaling-stroke" />
              <path d={`M38 ${line} V${line + into * 5} H62 V${line}`} vectorEffect="non-scaling-stroke" />
              <path d={penaltyArc(end)} vectorEffect="non-scaling-stroke" />
              <Goal end={end} />
            </g>
          );
        })}
        <path
          d={[
            corner(left, far, 1, 1, 1),
            corner(right, far, -1, 1, 0),
            corner(left, near, 1, -1, 0),
            corner(right, near, -1, -1, 1),
          ].join(" ")}
          vectorEffect="non-scaling-stroke"
        />
      </g>
      <g fill="var(--chalk)">
        {[50, far + SPOT_FROM_LINE, near - SPOT_FROM_LINE].map((y) => (
          <ellipse key={y} cx="50" cy={y} rx="0.75" ry={ry(0.75)} />
        ))}
      </g>
    </svg>
  );
}

// The ball's panels: a pentagon facing you, and the next five, cut off by the
// edge of the ball, out past each of its corners.
const pentagon = (cx: number, cy: number, r: number, turn = 0) =>
  Array.from({ length: 5 }, (_, i) => {
    const a = ((-90 + turn + i * 72) * Math.PI) / 180;
    return `${(cx + r * Math.cos(a)).toFixed(2)} ${(cy + r * Math.sin(a)).toFixed(2)}`;
  }).join(" L");
const BALL_PANELS = [
  `M${pentagon(10, 10, 3.4)} Z`,
  ...Array.from({ length: 5 }, (_, i) => {
    const a = ((-90 + i * 72) * Math.PI) / 180;
    return `M${pentagon(10 + 9.6 * Math.cos(a), 10 + 9.6 * Math.sin(a), 3.2, 36)} Z`;
  }),
];
const BALL_SEAMS = Array.from({ length: 5 }, (_, i) => {
  const a = ((-90 + i * 72) * Math.PI) / 180;
  const p = (r: number) => `${(10 + r * Math.cos(a)).toFixed(2)} ${(10 + r * Math.sin(a)).toFixed(2)}`;
  return `M${p(3.4)} L${p(6.6)}`;
}).join(" ");

/** The match ball, waiting on the centre spot for kick-off: standing on the
 *  turf like the shirts, with its shadow on the grass. */
function Ball() {
  return (
    <span aria-hidden className="pointer-events-none absolute left-1/2 top-1/2 h-0 w-0 [transform-style:preserve-3d]">
      <span className="absolute -left-[2.2cqw] -top-[0.8cqw] h-[1.6cqw] w-[4.4cqw] bg-[radial-gradient(closest-side,rgba(0,0,0,0.5),transparent)]" />
      <span className="stand absolute bottom-0 left-0 block w-[3cqw]">
      <svg viewBox="0 0 20 20" className="relative block w-full">
        <defs>
          <clipPath id="ball-clip">
            <circle cx="10" cy="10" r="9.4" />
          </clipPath>
          <radialGradient id="ball-shade" cx="0.35" cy="0.3" r="0.8">
            <stop offset="0" stopColor="#fff" stopOpacity="0.5" />
            <stop offset="0.55" stopColor="#fff" stopOpacity="0" />
            <stop offset="1" stopColor="#000" stopOpacity="0.45" />
          </radialGradient>
        </defs>
        <circle cx="10" cy="10" r="9.4" fill="#F4F3EF" />
        <g clipPath="url(#ball-clip)">
          {BALL_PANELS.map((d) => (
            <path key={d} d={d} fill="#1B1C1F" />
          ))}
          <path d={BALL_SEAMS} stroke="#1B1C1F" strokeOpacity="0.5" strokeWidth="0.5" />
        </g>
        <circle cx="10" cy="10" r="9.4" fill="url(#ball-shade)" />
        <circle cx="10" cy="10" r="9.4" fill="none" stroke="rgba(0,0,0,0.35)" strokeWidth="0.5" />
      </svg>
      </span>
    </span>
  );
}

/** The big screen behind the far goal, up on two posts so it shows over the
 *  forwards' heads, running the week's numbers. Its lit pixels are the board
 *  showing through a grid of holes over the text. */
function Hoarding({ messages }: { messages: string[] }) {
  if (messages.length === 0) return null;
  const run = messages.map((m) => `${m} ◆ `).join("");
  return (
    // Standing well behind the far goal line, facing the camera.
    <div aria-hidden className="pointer-events-none absolute left-1/2 top-[-9%] h-0 w-0 [transform-style:preserve-3d]">
      <div className="stand absolute bottom-0 left-0 flex w-[62cqw] flex-col items-center max-sm:w-[84cqw]">
        <div className="relative h-[6.4cqw] w-full overflow-hidden rounded-[3px] max-sm:h-[9cqw] bg-[#0B0C0D] shadow-[inset_0_0_0_2px_#2A2D31,0_6px_14px_rgba(0,0,0,0.45)]">
          <div className="flex h-full w-max animate-hoarding items-center whitespace-nowrap font-display text-[max(3.6cqw,12px)] font-extrabold max-sm:text-[5.2cqw] uppercase leading-none tracking-[0.08em] text-[#FFC247]">
            <span>{run}</span>
            <span>{run}</span>
          </div>
          <div className="absolute inset-0 bg-[radial-gradient(circle,transparent_0.6px,#0B0C0D_0.9px)] [background-size:2px_2px]" />
        </div>
        {/* The posts */}
        <div className="flex h-[10cqw] w-[78%] justify-between max-sm:h-[17cqw]">
          <span className="block h-full w-[0.9cqw] bg-gradient-to-b from-[#3A3E44] to-[#1E2125]" />
          <span className="block h-full w-[0.9cqw] bg-gradient-to-b from-[#3A3E44] to-[#1E2125]" />
        </div>
      </div>
    </div>
  );
}

function groupByRow(xi: Player[]) {
  const rows: Record<Player["position"], Player[]> = { GK: [], DEF: [], MID: [], FWD: [] };
  for (const p of xi) rows[p.position].push(p);
  return rows;
}

/** Projected points per gameweek, drawn against this player's own best week —
 *  reads as "when are his fixtures kind". */
function FixtureRun({ xpByGw }: { xpByGw: Record<string, number> }) {
  const weeks = Object.entries(xpByGw)
    .map(([gw, xp]) => ({ gw: Number(gw), xp }))
    .sort((a, b) => a.gw - b.gw);
  if (weeks.length < 2) return null;
  const peak = Math.max(...weeks.map((w) => w.xp), 0.1);
  const best = weeks.reduce((a, b) => (b.xp > a.xp ? b : a));

  return (
    <div className="mt-4 border-t border-line pt-3">
      <p className="label mb-2.5">Next {weeks.length} gameweeks &middot; projected points</p>
      <div className="flex items-end gap-1.5">
        {weeks.map((w, i) => {
          const isBest = w.gw === best.gw;
          return (
            <div key={w.gw} className="flex flex-1 flex-col items-center gap-1">
              <span className={`text-[10px] tabular-nums ${isBest ? "font-semibold text-pts" : "text-ink-400"}`}>
                {w.xp.toFixed(1)}
              </span>
              <div className="flex h-10 w-full items-end">
                <div
                  className={`w-full origin-bottom animate-rise rounded-t ${isBest ? "bg-pts" : "bg-pts/35"}`}
                  style={{ height: `${Math.max(6, (w.xp / peak) * 100)}%`, animationDelay: `${i * 50}ms` }}
                />
              </div>
              <span className="text-[10px] text-ink-500">GW{w.gw}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

/** This week's points as a spread, not one number: the chance of each band
 *  of score, from a blank to a big haul, plus the likely range. */
const BANDS: { label: string; from: number; to: number; tone: string }[] = [
  { label: "0–2", from: 0, to: 2, tone: "bg-ink-500/50" },
  { label: "3–5", from: 3, to: 5, tone: "bg-pts/35" },
  { label: "6–9", from: 6, to: 9, tone: "bg-pts/70" },
  { label: "10–14", from: 10, to: 14, tone: "bg-gold/70" },
  { label: "15+", from: 15, to: 99, tone: "bg-gold" },
];

function Spread({ dist }: { dist: PointsDist }) {
  const shares = BANDS.map((b) => dist.pmf.slice(b.from, b.to + 1).reduce((a, x) => a + x, 0));
  const peak = Math.max(...shares, 0.01);
  return (
    <div className="mt-4 border-t border-line pt-3">
      <p className="label mb-2.5">
        This gameweek &middot; likely {dist.p10}&ndash;{dist.p90} pts
      </p>
      <div className="grid grid-cols-5 gap-2">
        {BANDS.map((b, i) => (
          <div key={b.label} className="flex flex-col items-center gap-1">
            <span className="text-[11px] font-medium tabular-nums text-ink-200">{pct(shares[i])}</span>
            <div className="flex h-10 w-full items-end">
              <div className={`w-full rounded-t ${b.tone}`} style={{ height: `${Math.max(4, (shares[i] / peak) * 100)}%` }} />
            </div>
            <span className="text-[10px] text-ink-500">{b.label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function PlayerShirt({
  player,
  x,
  y,
  order,
  isActive,
  coinFlip,
  onSelect,
  across,
}: {
  player: Player;
  /** Where he stands on the turf, in % of its width and of its length from
   *  the far goal line. */
  x: number;
  y: number;
  /** Position in the line-up sequence: the keeper first, the forwards last. */
  order: number;
  isActive: boolean;
  coinFlip: boolean;
  onSelect: () => void;
  /** How many share his line, so the shirts can be as big as fits. */
  across: number;
}) {
  const pts = player.predicted_points;
  return (
    // A point on the grass. The shirt stands up from it, in 3D, so it turns
    // with the pitch; its shadows lie flat on the turf around it.
    <button
      type="button"
      onClick={onSelect}
      aria-pressed={isActive}
      aria-label={`${player.name}, ${player.team}, ${pts.toFixed(1)} projected points${
        player.is_captain ? ", captain" : player.is_vice_captain ? ", vice-captain" : ""
      }`}
      className="group absolute h-0 w-0 focus:outline-none [transform-style:preserve-3d]"
      style={{ left: `${x}%`, top: `${y}%` }}
    >
      <span
        aria-hidden
        className="absolute left-0 top-0 h-0 w-0 transition-transform duration-500 [transition-timing-function:cubic-bezier(0.3,1.5,0.5,1)] group-hover:scale-[0.7]"
      >
        <span className="absolute -left-[5cqw] -top-[1.4cqw] h-[2.8cqw] w-[10cqw] bg-[radial-gradient(closest-side,rgba(0,0,0,0.5),transparent)]" />
        {SHADOWS.map((s) => (
          <span
            key={s.angle}
            className="absolute left-0 top-[-0.6cqw] h-[1.2cqw] origin-left rounded-full bg-[linear-gradient(90deg,rgba(0,0,0,0.28),transparent)]"
            style={{ width: `${s.length}cqw`, transform: `rotate(${s.angle}deg)` }}
          />
        ))}
      </span>

      <span
        className="stand stand-up absolute bottom-0 left-0 flex flex-col items-center"
        style={{
          animationDelay: `${0.25 + order * 0.07}s`,
          width: `min(var(--shirt), calc(var(--stage) * ${(0.92 / (across + 1)).toFixed(3)}))`,
        }}
      >
        {/* Quick look on hover (desktop), above the shirt */}
        <span className="pointer-events-none absolute bottom-[calc(100%+6px)] left-1/2 z-20 hidden w-44 -translate-x-1/2 translate-y-1.5 rounded-lg border border-line-strong bg-surface p-3 text-left opacity-0 shadow-raised transition-all duration-200 group-hover:translate-y-0 group-hover:opacity-100 md:block">
          <span className="flex items-center gap-1.5 text-[13.5px] font-semibold text-ink-100">
            <Crest team={player.team} className="h-4 w-4" />
            {player.name}
          </span>
          <span className="mt-1 flex justify-between text-[12px] text-ink-400">
            {player.team}
            <b className="font-semibold text-ink-100">&pound;{player.now_cost_m.toFixed(1)}m</b>
          </span>
          <span className="flex justify-between text-[12px] text-ink-400">
            Projected<b className="font-semibold text-ink-100">{pts.toFixed(1)} pts</b>
          </span>
          <span className="flex justify-between text-[12px] text-ink-400">
            Starts<b className="font-semibold text-ink-100">{Math.round(player.start_probability * 100)}%</b>
          </span>
        </span>

        {/* Hovered, he hops off the grass and his shadow tightens under him */}
        <span className="relative block w-full transition-transform duration-500 [transition-timing-function:cubic-bezier(0.3,1.6,0.5,1)] group-hover:-translate-y-[14%] group-focus-visible:-translate-y-[14%]">
          {player.is_captain && (
            <span
              aria-hidden
              className="absolute -inset-[2cqw] z-0 rounded-full bg-[radial-gradient(circle,rgba(227,169,60,0.4),transparent_65%)]"
            />
          )}
          <Shirt
            team={player.team}
            number={pts.toFixed(1)}
            uid={`xi-${player.player_id}`}
            goalkeeper={player.position === "GK"}
            captain={player.is_captain}
            vice={player.is_vice_captain}
            armbandDelay={1.4}
            className={`relative z-[1] block w-full transition-transform duration-300 md:drop-shadow-[0_5px_5px_rgba(0,0,0,0.3)] ${
              isActive ? "scale-110" : ""
            }`}
          />
          {coinFlip && (
            <span
              title="Coin flip with a bench player"
              className="absolute -left-[1cqw] top-[18%] z-[3] grid h-[min(4.6cqw,20px)] w-[min(4.6cqw,20px)] place-items-center rounded-md bg-violet text-[clamp(8px,2.4cqw,11px)] font-bold text-white shadow-[0_2px_6px_rgba(0,0,0,0.4)] ring-2 ring-[#1B4326]"
            >
              &frac12;
            </span>
          )}
        </span>
        <span
          className={`relative z-[2] -mt-[0.8cqw] max-w-[130%] truncate rounded-md px-[1.4cqw] py-px text-[clamp(10.5px,2.4cqw,12px)] font-semibold leading-snug shadow-[0_2px_6px_rgba(0,0,0,0.35)] transition-colors duration-300 group-focus-visible:outline group-focus-visible:outline-2 group-focus-visible:outline-gold ${
            isActive ? "bg-gold text-[#2A1A00]" : "bg-plate text-plate-text"
          }`}
        >
          {player.name}
        </span>
      </span>
    </button>
  );
}

export default function PitchView({
  startingXi,
  coinFlipIds = [],
  board = [],
}: {
  startingXi: Player[];
  /** Starters in a coin-flip call with a bench player (CoinFlips). */
  coinFlipIds?: number[];
  /** What the LED board behind the far goal runs. */
  board?: string[];
}) {
  const [active, setActive] = useState<Player | null>(null);
  const rows = groupByRow(startingXi);
  const hangIndex = new Map(
    HANG_ORDER.flatMap((pos) => rows[pos]).map((p, i) => [p.player_id, i] as const)
  );

  const placed = ROW_ORDER.flatMap((pos) =>
    rows[pos].map((p, i) => ({
      player: p,
      x: (100 / (rows[pos].length + 1)) * (i + 1),
      y: ROW_Y[pos] * 100,
      across: rows[pos].length,
    }))
  );

  return (
    <div>
      {/* The ground as a model on a table: the turf tipped back in real
          perspective, the shirts standing on it. It leans towards the
          pointer and can be dragged round; let go and it springs back. */}
      <Orbit crane={18} className="relative mx-auto aspect-[1/0.95] w-full cursor-grab [--orbit-spin:0deg] [--orbit-tilt:56deg] [--shirt:15cqw] [--stage:78cqw] [container-type:inline-size] active:cursor-grabbing max-sm:aspect-[1/1.3] max-sm:[--orbit-tilt:52deg] max-sm:[--shirt:24cqw] max-sm:[--stage:94cqw]">
        <div className="absolute inset-0 [perspective-origin:50%_0%] [perspective:200cqw]">
          <div
            className="absolute left-[11%] top-[0%] aspect-[1/1.2] w-[78%] [transform-style:preserve-3d] max-sm:left-[3%] max-sm:top-[6%] max-sm:w-[94%]"
            style={{ transform: "rotateX(var(--orbit-tilt)) rotateZ(var(--orbit-spin))", transformOrigin: "50% 58%" }}
          >
            {/* The turf: mown in bands, the light ones a touch yellower where
                the blades lean away, the grain of the grass (globals.css),
                floodlight in the corners and the edges falling into shadow */}
            <div
              aria-hidden
              className="absolute inset-0 overflow-hidden rounded-lg bg-[repeating-linear-gradient(180deg,rgb(var(--c-grass))_0,rgb(var(--c-grass))_7.9%,rgb(var(--c-grass-dark))_8.4%,rgb(var(--c-grass-dark))_16.2%,rgb(var(--c-grass))_16.7%)] shadow-[0_40px_60px_-20px_rgba(0,0,0,0.7)] transition-colors duration-300"
            >
              <div className="absolute inset-0 bg-[repeating-linear-gradient(180deg,rgba(255,236,150,0.05)_0_8.33%,transparent_8.33%_16.66%)]" />
              <div className="turf-blades absolute inset-0 max-sm:hidden" />
              <div className="absolute inset-0 bg-[radial-gradient(55%_40%_at_0%_0%,rgba(255,244,214,0.16),transparent_70%),radial-gradient(55%_40%_at_100%_0%,rgba(255,244,214,0.16),transparent_70%),radial-gradient(55%_40%_at_0%_100%,rgba(214,232,255,0.1),transparent_70%),radial-gradient(55%_40%_at_100%_100%,rgba(214,232,255,0.1),transparent_70%),radial-gradient(45%_35%_at_50%_62%,rgba(255,255,255,0.05),transparent_75%)]" />
              <div className="absolute inset-0 shadow-[inset_0_0_80px_rgba(0,0,0,0.45)]" />
              <Markings />
            </div>

            <Hoarding messages={board} />
            <Ball />

            {placed.map(({ player, x, y, across }) => (
              <PlayerShirt
                key={player.player_id}
                player={player}
                x={x}
                y={y}
                across={across}
                order={hangIndex.get(player.player_id) ?? 0}
                isActive={active?.player_id === player.player_id}
                coinFlip={coinFlipIds.includes(player.player_id)}
                onSelect={() => setActive(active?.player_id === player.player_id ? null : player)}
              />
            ))}
          </div>
        </div>
      </Orbit>

      {active ? (
        <div className="mt-5 animate-rise border-t border-line pt-4">
          <div className="flex items-start justify-between gap-3">
            <div className="flex items-center gap-3">
              <Crest team={active.team} className="h-10 w-10 flex-none" />
              <div>
                <p className="text-[17px] font-semibold tracking-[-0.01em] text-ink-100">{active.name}</p>
                <p className="text-[12.5px] text-ink-400">
                  {active.team} &middot; {active.position}
                  {active.is_captain && <span className="text-gold"> &middot; captain (2&times;)</span>}
                  {active.is_vice_captain && <span className="text-gold"> &middot; vice-captain</span>}
                </p>
              </div>
            </div>
            <button
              onClick={() => setActive(null)}
              className="px-1 py-1 text-[13px] text-ink-400 underline-offset-2 transition-colors hover:text-ink-100 hover:underline"
            >
              Close
            </button>
          </div>

          <dl className="mt-4 flex">
            {[
              { label: "Projected", value: active.predicted_points.toFixed(1), tone: "text-pts" },
              { label: "Price", value: `£${active.now_cost_m.toFixed(1)}m`, tone: "text-ink-100" },
              { label: "Starts", value: `${Math.round(active.start_probability * 100)}%`, tone: "text-ink-100" },
            ].map((s, i) => (
              <div key={s.label} className={`pr-6 ${i > 0 ? "border-l border-line pl-6" : ""}`}>
                <dt className="text-[12px] text-ink-400">{s.label}</dt>
                <dd className={`font-kit text-[24px] font-bold leading-tight tabular-nums ${s.tone}`}>{s.value}</dd>
              </div>
            ))}
          </dl>

          {active.dist && <Spread dist={active.dist} />}
          <FixtureRun xpByGw={active.xp_by_gw} />
        </div>
      ) : (
        <p className="mt-3 text-center text-[12.5px] text-ink-500">
          Tap a shirt for the player&apos;s projection and fixture run
        </p>
      )}
    </div>
  );
}
