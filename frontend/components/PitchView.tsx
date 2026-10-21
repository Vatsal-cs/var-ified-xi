// File: PitchView.tsx
// Path: var-ified-xi/frontend/components/PitchView.tsx
"use client";

import { useState } from "react";
import type { Player, PointsDist } from "@/lib/types";
import { kitFor } from "@/lib/teams";
import Crest from "@/components/Crest";
import { pct } from "@/lib/odds";

const ROW_ORDER: Player["position"][] = ["FWD", "MID", "DEF", "GK"];
const ROW_Y: Record<Player["position"], number> = { FWD: 17, MID: 40, DEF: 63, GK: 86 };

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
            <div key={w.gw} className="group/bar flex flex-1 flex-col items-center gap-1">
              <span
                className={`font-mono text-[9px] tabular-nums ${
                  isBest ? "text-pts" : "text-ink-400"
                }`}
              >
                {w.xp.toFixed(1)}
              </span>
              <div className="flex h-10 w-full items-end">
                <div
                  className={`w-full rounded-t-sm transition-all duration-500 ease-out ${
                    isBest ? "bg-pts" : "bg-pts/35"
                  } group-hover/bar:bg-pts`}
                  style={{
                    height: `${Math.max(6, (w.xp / peak) * 100)}%`,
                    transitionDelay: `${i * 40}ms`,
                  }}
                />
              </div>
              <span className="font-mono text-[9px] text-ink-500">{w.gw}</span>
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
  { label: "6–9", from: 6, to: 9, tone: "bg-pts/65" },
  { label: "10–14", from: 10, to: 14, tone: "bg-gold/60" },
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
            <span className="font-mono text-[10px] tabular-nums text-ink-200">{pct(shares[i])}</span>
            <div className="flex h-10 w-full items-end">
              <div
                className={`w-full rounded-t-sm ${b.tone}`}
                style={{ height: `${Math.max(4, (shares[i] / peak) * 100)}%` }}
              />
            </div>
            <span className="font-mono text-[9px] text-ink-500">{b.label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

/** The colour of the light pool under a shirt: the shirt itself, or its
 *  trim when the shirt is too dark to glow on night-time grass. */
function poolColour(kit: { shirt: string; trim: string }) {
  const hex = kit.shirt.replace("#", "");
  const [r, g, b] = [0, 2, 4].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255);
  const lum = 0.2126 * r + 0.7152 * g + 0.0722 * b;
  return lum < 0.18 ? kit.trim : kit.shirt;
}

function PlayerChip({
  player,
  x,
  y,
  isActive,
  onSelect,
  coinFlip = false,
  order = 0,
}: {
  player: Player;
  x: number;
  y: number;
  isActive: boolean;
  onSelect: () => void;
  coinFlip?: boolean;
  /** Position in the drop-in sequence: the keeper first, the forwards last. */
  order?: number;
}) {
  const kit = kitFor(player.team);
  const pts = player.predicted_points;
  // Badges are sized in em off a pitch-relative font size, so they scale with
  // the crest instead of with the phone's text setting.
  const badge =
    "absolute z-[3] rounded-[0.32em] px-[0.42em] py-[0.24em] font-body text-[clamp(8px,2.3cqw,10.5px)] font-extrabold leading-none tracking-[0.06em] shadow-[0_2px_6px_rgba(0,0,0,0.65)]";

  return (
    <button
      onClick={onSelect}
      aria-pressed={isActive}
      aria-label={`${player.name}, ${player.team}, ${pts.toFixed(1)} projected points${
        player.is_captain ? ", captain" : player.is_vice_captain ? ", vice-captain" : ""
      }`}
      // Everything is sized in cqw, a share of the pitch's own width, so a
      // phone's larger text setting can't swell the chips into each other:
      // five across sit 16.7% apart and each is 16% wide.
      className="group absolute z-10 flex w-[16cqw] -translate-x-1/2 -translate-y-1/2 animate-dropIn flex-col items-center focus:outline-none"
      style={{ left: `${x}%`, top: `${y}%`, animationDelay: `${0.15 + order * 0.07}s` }}
    >
      <span className="relative block h-[11cqw] w-[11cqw] transition-transform duration-200 group-hover:-translate-y-[0.8cqw]">
        {/* A pool of the club's colour on the grass, like a floodlit shadow */}
        <span
          aria-hidden
          className="absolute left-1/2 top-[98%] h-[2.2cqw] w-[120%] -translate-x-1/2 -translate-y-1/2 rounded-[50%] opacity-35 blur-[3px] transition-opacity duration-300 group-hover:opacity-80"
          style={{ background: poolColour(kit) }}
        />
        {/* The captain's halo */}
        {player.is_captain && (
          <span
            aria-hidden
            className="absolute -inset-[2cqw] animate-glow rounded-full bg-[radial-gradient(circle,rgba(224,166,74,0.5),transparent_66%)]"
          />
        )}
        <Crest
          team={player.team}
          className={`relative z-[1] h-full w-full drop-shadow-[0_4px_5px_rgba(0,0,0,0.7)] transition-transform duration-200 ${
            isActive ? "scale-110" : ""
          }`}
        />
        {player.is_captain && (
          <span className={`${badge} -bottom-[0.3cqw] -right-[1.8cqw] bg-gradient-to-b from-[#F7DC9E] to-[#D49A43] text-[#2B1D06]`}>
            C
          </span>
        )}
        {player.is_vice_captain && (
          <span className={`${badge} -bottom-[0.3cqw] -right-[2.4cqw] bg-[#0D1A13] text-gold ring-1 ring-inset ring-gold/70`}>
            VC
          </span>
        )}
        {coinFlip && (
          <span title="Coin flip with a bench player" className={`${badge} -left-[1.8cqw] -top-[0.3cqw] bg-violet text-[#160F26]`}>
            &frac12;
          </span>
        )}
      </span>

      {/* Name + points tag */}
      <span
        className={`mt-[1.8cqw] block w-full rounded-[3px] border px-[0.5cqw] py-[0.45cqw] backdrop-blur-sm transition-colors duration-200 ${
          isActive
            ? "border-gold/70 bg-base/90"
            : player.is_captain
              ? "border-gold/35 bg-base/85"
              : "border-white/[0.06] bg-base/80 group-hover:border-white/20"
        }`}
      >
        <span className="block truncate text-center font-body text-[clamp(8px,2.5cqw,11px)] font-medium leading-tight text-ink-100">
          {player.name}
        </span>
        <span
          className={`block text-center font-mono text-[clamp(8px,2.3cqw,10px)] leading-tight tabular-nums ${
            pts >= 5 ? "text-pts" : pts >= 4 ? "text-gold" : "text-ink-300"
          }`}
        >
          {pts.toFixed(1)}
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

  // Position every player once, so the chip component stays presentational.
  const placed = ROW_ORDER.flatMap((pos) =>
    rows[pos].map((p, i) => ({
      player: p,
      x: (100 / (rows[pos].length + 1)) * (i + 1),
      y: ROW_Y[pos],
    }))
  );

  return (
    <div>
      <div className="relative mx-auto aspect-[3/4] w-full max-w-md overflow-hidden rounded-[3px] border border-line shadow-panel [container-type:inline-size]">
        {/* Turf: a night-match green with mown stripes */}
        <div className="absolute inset-0 bg-[linear-gradient(175deg,#173A27_0%,#11301F_45%,#0B2016_100%)]" />
        <div
          className="absolute inset-0"
          style={{
            backgroundImage:
              "repeating-linear-gradient(180deg, rgba(255,255,255,0.035) 0 8.33%, transparent 8.33% 16.66%)",
          }}
        />
        {/* Four floodlights, one in each corner */}
        <div className="absolute inset-0 bg-[radial-gradient(60%_45%_at_0%_0%,rgba(255,236,190,0.10),transparent_70%),radial-gradient(60%_45%_at_100%_0%,rgba(255,236,190,0.10),transparent_70%),radial-gradient(60%_45%_at_0%_100%,rgba(190,220,255,0.06),transparent_70%),radial-gradient(60%_45%_at_100%_100%,rgba(190,220,255,0.06),transparent_70%)]" />
        {/* Edge vignette */}
        <div className="absolute inset-0 shadow-[inset_0_0_60px_rgba(0,0,0,0.55)]" />

        {/* Markings */}
        <svg
          className="absolute inset-0 h-full w-full"
          viewBox="0 0 100 133"
          preserveAspectRatio="none"
          aria-hidden
        >
          <g fill="none" stroke="rgba(255,255,255,0.28)" strokeWidth="0.45" style={{ filter: "drop-shadow(0 0 1.2px rgba(255,255,255,0.35))" }}>
            <rect x="3" y="3" width="94" height="127" />
            <line x1="3" y1="66.5" x2="97" y2="66.5" />
            <circle cx="50" cy="66.5" r="10" />
            <circle cx="50" cy="66.5" r="0.9" fill="rgba(255,255,255,0.3)" stroke="none" />
            {/* Attacking third box (top) */}
            <rect x="25" y="3" width="50" height="17" />
            <rect x="38" y="3" width="24" height="7" />
            {/* Defending box (bottom) */}
            <rect x="25" y="113" width="50" height="17" />
            <rect x="38" y="123" width="24" height="7" />
          </g>
        </svg>

        {placed.map(({ player, x, y }, i) => (
          <PlayerChip
            key={player.player_id}
            order={placed.length - 1 - i}
            player={player}
            x={x}
            y={y}
            isActive={active?.player_id === player.player_id}
            coinFlip={coinFlipIds.includes(player.player_id)}
            onSelect={() =>
              setActive(active?.player_id === player.player_id ? null : player)
            }
          />
        ))}
      </div>

      {active ? (
        <div className="mx-auto mt-4 max-w-md animate-rise rounded-[3px] border border-line bg-surface p-4 shadow-panel">
          <div className="flex items-start justify-between gap-3">
            <div className="flex items-center gap-3">
              <Crest team={active.team} className="h-10 w-10 flex-none drop-shadow-[0_3px_4px_rgba(0,0,0,0.6)]" />
              <div>
                <p className="font-display text-lg tracking-tight text-ink-100">
                  {active.name}
                </p>
                <p className="font-mono text-[11px] text-ink-400">
                  {active.team} &middot; {active.position}
                  {active.is_captain && (
                    <span className="text-gold"> &middot; captain (2&times;)</span>
                  )}
                  {active.is_vice_captain && (
                    <span className="text-gold/80"> &middot; vice-captain</span>
                  )}
                </p>
              </div>
            </div>
            <button
              onClick={() => setActive(null)}
              className="rounded px-1.5 py-0.5 font-mono text-xs text-ink-400 transition-colors hover:bg-surface-raised hover:text-ink-100"
            >
              close
            </button>
          </div>

          <div className="mt-4 grid grid-cols-3 gap-3">
            <div className="rounded-[2px] bg-surface-raised p-2.5">
              <p className="label">Proj. pts</p>
              <p className="mt-0.5 font-mono text-lg tabular-nums text-pts">
                {active.predicted_points.toFixed(1)}
              </p>
            </div>
            <div className="rounded-[2px] bg-surface-raised p-2.5">
              <p className="label">Price</p>
              <p className="mt-0.5 font-mono text-lg tabular-nums text-ink-100">
                &pound;{active.now_cost_m.toFixed(1)}
              </p>
            </div>
            <div className="rounded-[2px] bg-surface-raised p-2.5">
              <p className="label">Starts</p>
              <p className="mt-0.5 font-mono text-lg tabular-nums text-ink-100">
                {Math.round(active.start_probability * 100)}%
              </p>
            </div>
          </div>

          {active.dist && <Spread dist={active.dist} />}
          <FixtureRun xpByGw={active.xp_by_gw} />
        </div>
      ) : (
        <p className="mt-3 text-center font-mono text-[11px] text-ink-500">
          Tap any player for their projection and fixture run
        </p>
      )}
    </div>
  );
}
