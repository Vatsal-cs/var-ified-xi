// File: PitchView.tsx
// Path: var-ified-xi/frontend/components/PitchView.tsx
//
// The XI as club shirts on the pitch, the projection as the shirt number.
// They're hung up one at a time — keeper first, forwards last — and the
// captain's armband goes on once they're all in. Hover a shirt for a quick
// look; tap it for the full spread and fixture run.
"use client";

import { useState } from "react";
import type { Player, PointsDist } from "@/lib/types";
import Crest from "@/components/Crest";
import Shirt from "@/components/Shirt";
import { goalkeeperKit, kitFor } from "@/lib/teams";
import { pct } from "@/lib/odds";

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

/** The colour of the floodlit pool under a shirt: the shirt itself, or its
 *  trim when the shirt is too dark to glow on night-time grass. */
function poolColour(team: string, goalkeeper: boolean) {
  const kit = goalkeeper ? goalkeeperKit(team) : kitFor(team);
  const hex = kit.shirt.replace("#", "");
  const [r, g, b] = [0, 2, 4].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255);
  const lum = 0.2126 * r + 0.7152 * g + 0.0722 * b;
  return lum < 0.12 ? (kit.stripe ?? kit.trim) : kit.shirt;
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
        className="shirt-hang flex animate-hang flex-col items-center"
        style={{ animationDelay: `${0.35 + order * 0.07}s` }}
      >
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
          {/* Floodlight: a pool of the club's colour on the grass below */}
          <span
            aria-hidden
            className="absolute left-1/2 top-[80%] z-0 h-[3.6cqw] w-[105%] -translate-x-1/2 rounded-[50%] opacity-55 blur-[7px] transition-opacity duration-300 group-hover:opacity-90"
            style={{ background: poolColour(player.team, player.position === "GK") }}
          />
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
}: {
  startingXi: Player[];
  /** Starters in a coin-flip call with a bench player (CoinFlips). */
  coinFlipIds?: number[];
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
      <div className="relative mx-auto aspect-[1/1.04] w-full [container-type:inline-size]">
        {/* The turf, tipped back like a broadcast camera's view */}
        <div aria-hidden className="absolute inset-0 [perspective-origin:50%_100%] [perspective:200cqw]">
          <div
            className="absolute inset-x-0 bottom-0 h-[115.4%] origin-bottom overflow-hidden rounded-lg bg-[repeating-linear-gradient(180deg,rgb(var(--c-grass))_0_8.33%,rgb(var(--c-grass-dark))_8.33%_16.66%)] shadow-[0_30px_60px_-30px_rgba(0,0,0,0.8)] transition-colors duration-300"
            style={{ transform: `rotateX(${TILT}deg)` }}
          >
            {/* Floodlights in the four corners, and the shadow at the edges */}
            <div className="absolute inset-0 bg-[radial-gradient(55%_40%_at_0%_0%,rgba(255,244,214,0.16),transparent_70%),radial-gradient(55%_40%_at_100%_0%,rgba(255,244,214,0.16),transparent_70%),radial-gradient(55%_40%_at_0%_100%,rgba(214,232,255,0.1),transparent_70%),radial-gradient(55%_40%_at_100%_100%,rgba(214,232,255,0.1),transparent_70%)]" />
            <div className="absolute inset-0 shadow-[inset_0_0_80px_rgba(0,0,0,0.5)]" />
            {/* Chalk markings */}
            <svg className="absolute inset-0 h-full w-full" viewBox="0 0 100 100" preserveAspectRatio="none">
              <g fill="none" stroke="var(--chalk)" strokeWidth="1.4" vectorEffect="non-scaling-stroke">
                <rect x="3" y="2.5" width="94" height="95" rx="1" vectorEffect="non-scaling-stroke" />
                <line x1="3" y1="50" x2="97" y2="50" vectorEffect="non-scaling-stroke" />
                <ellipse cx="50" cy="50" rx="13" ry="10.8" vectorEffect="non-scaling-stroke" />
                <rect x="25" y="2.5" width="50" height="13" vectorEffect="non-scaling-stroke" />
                <rect x="38" y="2.5" width="24" height="5" vectorEffect="non-scaling-stroke" />
                <rect x="25" y="84.5" width="50" height="13" vectorEffect="non-scaling-stroke" />
                <rect x="38" y="92.5" width="24" height="5" vectorEffect="non-scaling-stroke" />
              </g>
            </svg>
          </div>
        </div>

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
