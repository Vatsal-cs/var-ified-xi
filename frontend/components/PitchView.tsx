// File: PitchView.tsx
// Path: var-ified-xi/frontend/components/PitchView.tsx
//
// The XI as club shirts on the pitch, the projection as the shirt number.
// They're hung up one at a time — keeper first, forwards last — and the
// captain's armband goes on once they're all in. Hover a shirt for a quick
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
import { Tilt } from "@/components/motion";

const ROW_ORDER: Player["position"][] = ["FWD", "MID", "DEF", "GK"];
// Where each line stands on the turf, from the far touchline (0) to the near one (1).
const ROW_Y: Record<Player["position"], number> = { FWD: 0.15, MID: 0.39, DEF: 0.63, GK: 0.87 };

// The broadcast camera. The turf is tipped back TILT degrees about its near
// edge and seen with a perspective of PERSPECTIVE pitch-widths, so the far end
// narrows and the shirts there shrink. Lengths are in pitch widths.
const TILT = 18;
const PERSPECTIVE = 2;
const TURF_H = 1.2; // the turf is taller than the frame, so tipped back it fills it
const FRAME_H = 1.04;
const SIN = Math.sin((TILT * Math.PI) / 180);
const COS = Math.cos((TILT * Math.PI) / 180);

/** A point on the turf, in % of the frame, and how much nearer shirts grow. */
function project(xPct: number, row: number) {
  const h = (1 - row) * TURF_H; // height above the near touchline, before the tilt
  const scale = PERSPECTIVE / (PERSPECTIVE + h * SIN);
  return {
    x: 50 + (xPct - 50) * scale,
    y: ((FRAME_H - h * COS * scale) / FRAME_H) * 100,
    scale,
  };
}
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

/** The match ball, waiting on the centre spot for kick-off. */
function Ball() {
  const at = project(50, 0.5);
  return (
    <span
      aria-hidden
      className="pointer-events-none absolute z-[5] w-[3.2cqw] -translate-x-1/2 -translate-y-[85%]"
      style={{ left: `${at.x}%`, top: `${at.y}%`, scale: String(at.scale / project(50, ROW_Y.GK).scale) }}
    >
      <span className="absolute left-1/2 top-[88%] h-[1.1cqw] w-[150%] -translate-x-1/2 rounded-[50%] bg-black/40 blur-[2px]" />
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
  );
}

/** The LED board behind the far goal, running the week's numbers. Its lit
 *  pixels are the board showing through a grid of holes over the text. */
function Hoarding({ messages }: { messages: string[] }) {
  if (messages.length === 0) return null;
  const run = messages.map((m) => `${m}\u2003\u25C6\u2003`).join("");
  return (
    <div
      aria-hidden
      className="absolute left-1/2 top-[2.2%] h-[4.6%] w-[80%] -translate-x-1/2 overflow-hidden rounded-[2px] bg-[#0B0C0D] shadow-[inset_0_0_0_1px_rgba(255,255,255,0.08),0_8px_12px_-6px_rgba(0,0,0,0.6)]"
    >
      <div className="flex h-full w-max animate-hoarding items-center whitespace-nowrap font-display text-[max(3cqw,11px)] font-extrabold uppercase leading-none tracking-[0.08em] text-[#FFC247]">
        <span>{run}</span>
        <span>{run}</span>
      </div>
      <div className="absolute inset-0 bg-[radial-gradient(circle,transparent_0.6px,#0B0C0D_0.9px)] [background-size:2px_2px]" />
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
  scale = 1,
  order,
  isActive,
  coinFlip,
  onSelect,
}: {
  player: Player;
  x: number;
  y: number;
  /** Nearer the camera is bigger: the perspective's scale at this spot. */
  scale?: number;
  /** Position in the hanging sequence: the keeper first, the forwards last. */
  order: number;
  isActive: boolean;
  coinFlip: boolean;
  onSelect: () => void;
}) {
  const pts = player.predicted_points;
  // The two upper rows open their quick look downwards, so it never runs off
  // the top of the pitch; the lower rows open upwards.
  const below = y < 52;
  return (
    <button
      type="button"
      onClick={onSelect}
      aria-pressed={isActive}
      aria-label={`${player.name}, ${player.team}, ${pts.toFixed(1)} projected points${
        player.is_captain ? ", captain" : player.is_vice_captain ? ", vice-captain" : ""
      }`}
      // Sized in cqw, a share of the pitch's own width, so a phone's larger
      // text setting can't swell the shirts into each other: five across sit
      // 16.7% apart and each takes at most 16%.
      className="group absolute z-10 w-[16cqw] -translate-x-1/2 -translate-y-1/2 hover:z-30 focus:outline-none focus-visible:z-30"
      style={{ left: `${x}%`, top: `${y}%`, scale: String(scale) }}
    >
      <span
        className="shirt-hang relative flex animate-hang flex-col items-center"
        style={{ animationDelay: `${0.35 + order * 0.07}s` }}
      >
        {/* Floodlight shadows on the grass at his feet; they stay put when the
            shirt lifts on hover */}
        <span aria-hidden className="absolute left-1/2 z-0 h-0 w-0" style={{ top: "calc(min(15cqw, 76px) * 0.9)" }}>
          {SHADOWS.map((s) => (
            <span
              key={s.angle}
              className="absolute left-0 top-[-0.7cqw] h-[1.4cqw] origin-left rounded-full bg-black/25 blur-[2px]"
              style={{ width: `${s.length}cqw`, transform: `rotate(${s.angle}deg)` }}
            />
          ))}
        </span>
        {/* Quick look on hover (desktop) */}
        <span className={`pointer-events-none absolute left-1/2 z-20 hidden w-44 -translate-x-1/2 rounded-lg border border-line-strong bg-surface p-3 text-left opacity-0 shadow-raised transition-all duration-200 group-hover:translate-y-0 group-hover:opacity-100 md:block ${below ? "top-[calc(100%+4px)] -translate-y-1.5" : "bottom-[calc(100%-4px)] translate-y-1.5"}`}>
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

        <span className="relative block transition-transform duration-300 group-hover:-translate-y-1 group-hover:-rotate-3">
          {player.is_captain && (
            <span
              aria-hidden
              className="absolute -inset-[2.5cqw] z-0 rounded-full bg-[radial-gradient(circle,rgba(227,169,60,0.45),transparent_65%)]"
            />
          )}
          <Shirt
            team={player.team}
            number={pts.toFixed(1)}
            uid={`xi-${player.player_id}`}
            goalkeeper={player.position === "GK"}
            captain={player.is_captain}
            vice={player.is_vice_captain}
            armbandDelay={1.5}
            className={`relative z-[1] block w-[min(15cqw,76px)] drop-shadow-[0_6px_6px_rgba(0,0,0,0.3)] transition-transform duration-300 ${
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
          className={`relative z-[2] -mt-[0.8cqw] max-w-full truncate rounded-md px-[1.4cqw] py-px text-[clamp(9px,2.5cqw,12px)] font-semibold leading-snug shadow-[0_2px_6px_rgba(0,0,0,0.35)] transition-colors duration-300 ${
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
    rows[pos].map((p, i) => {
      const at = project((100 / (rows[pos].length + 1)) * (i + 1), ROW_Y[pos]);
      return { player: p, x: at.x, y: at.y, scale: at.scale / project(50, ROW_Y.GK).scale };
    })
  );

  return (
    <div>
      <Tilt max={2.5}>
        <div className="relative mx-auto aspect-[1/1.04] w-full [container-type:inline-size]">
          {/* The turf, tipped back like a broadcast camera's view */}
          <div aria-hidden className="absolute inset-0 [perspective-origin:50%_100%] [perspective:200cqw]">
            <div
              className="absolute inset-x-0 bottom-0 h-[115.4%] origin-bottom overflow-hidden rounded-lg bg-[repeating-linear-gradient(180deg,rgb(var(--c-grass))_0,rgb(var(--c-grass))_7.9%,rgb(var(--c-grass-dark))_8.4%,rgb(var(--c-grass-dark))_16.2%,rgb(var(--c-grass))_16.7%)] shadow-[0_30px_60px_-30px_rgba(0,0,0,0.8)] transition-colors duration-300"
              style={{ transform: `rotateX(${TILT}deg)` }}
            >
              {/* Mown in bands, the light ones a touch yellower where the blades
                  lean away, and the grain of the grass (globals.css) */}
              <div className="absolute inset-0 bg-[repeating-linear-gradient(180deg,rgba(255,236,150,0.05)_0_8.33%,transparent_8.33%_16.66%)]" />
              <div className="turf-blades absolute inset-0" />
              {/* Floodlights in the four corners, a sheen down the middle where
                  they cross, the far end falling into the dark, and the edges */}
              <div className="absolute inset-0 bg-[radial-gradient(55%_40%_at_0%_0%,rgba(255,244,214,0.16),transparent_70%),radial-gradient(55%_40%_at_100%_0%,rgba(255,244,214,0.16),transparent_70%),radial-gradient(55%_40%_at_0%_100%,rgba(214,232,255,0.1),transparent_70%),radial-gradient(55%_40%_at_100%_100%,rgba(214,232,255,0.1),transparent_70%),radial-gradient(45%_35%_at_50%_62%,rgba(255,255,255,0.05),transparent_75%),linear-gradient(180deg,rgba(0,0,0,0.22),transparent_32%)]" />
              <div className="absolute inset-0 shadow-[inset_0_0_80px_rgba(0,0,0,0.5)]" />
              <Markings />
            </div>
          </div>

          <Hoarding messages={board} />
        <Ball />

        {placed.map(({ player, x, y, scale }) => (
            <PlayerShirt
              key={player.player_id}
              player={player}
              x={x}
              y={y}
              scale={scale}
              order={hangIndex.get(player.player_id) ?? 0}
              isActive={active?.player_id === player.player_id}
              coinFlip={coinFlipIds.includes(player.player_id)}
              onSelect={() => setActive(active?.player_id === player.player_id ? null : player)}
            />
          ))}
        </div>
      </Tilt>

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
