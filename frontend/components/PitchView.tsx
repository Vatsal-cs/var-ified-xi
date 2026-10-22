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
import { pct } from "@/lib/odds";

const ROW_ORDER: Player["position"][] = ["FWD", "MID", "DEF", "GK"];
const ROW_Y: Record<Player["position"], number> = { FWD: 13, MID: 37.5, DEF: 62, GK: 86.5 };
const HANG_ORDER: Player["position"][] = ["GK", "DEF", "MID", "FWD"];

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
}: {
  player: Player;
  x: number;
  y: number;
  /** Position in the hanging sequence: the keeper first, the forwards last. */
  order: number;
  isActive: boolean;
  coinFlip: boolean;
  onSelect: () => void;
}) {
  const pts = player.predicted_points;
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
      className="group absolute z-10 w-[16cqw] -translate-x-1/2 -translate-y-1/2 focus:outline-none"
      style={{ left: `${x}%`, top: `${y}%` }}
    >
      <span
        className="shirt-hang flex animate-hang flex-col items-center"
        style={{ animationDelay: `${0.35 + order * 0.07}s` }}
      >
        {/* Quick look on hover (desktop) */}
        <span className="pointer-events-none absolute bottom-[calc(100%-4px)] left-1/2 z-20 hidden w-44 -translate-x-1/2 translate-y-1.5 rounded-xl border border-line bg-surface p-3 text-left opacity-0 shadow-raised transition-all duration-200 group-hover:translate-y-0 group-hover:opacity-100 md:block">
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
          <Shirt
            team={player.team}
            number={pts.toFixed(1)}
            uid={`xi-${player.player_id}`}
            goalkeeper={player.position === "GK"}
            captain={player.is_captain}
            vice={player.is_vice_captain}
            armbandDelay={1.5}
            className={`block w-[min(15cqw,76px)] drop-shadow-[0_6px_6px_rgba(0,0,0,0.3)] transition-transform duration-300 ${
              isActive ? "scale-110" : ""
            }`}
          />
          {coinFlip && (
            <span
              title="Coin flip with a bench player"
              className="absolute -left-[1cqw] top-[18%] grid h-[min(4.6cqw,20px)] w-[min(4.6cqw,20px)] place-items-center rounded-md bg-violet text-[clamp(8px,2.4cqw,11px)] font-bold text-white shadow"
            >
              &frac12;
            </span>
          )}
        </span>
        <span
          className={`-mt-[0.8cqw] max-w-full truncate rounded-md px-[1.4cqw] py-px text-[clamp(9px,2.5cqw,12px)] font-semibold leading-snug transition-colors duration-300 ${
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
    rows[pos].map((p, i) => ({
      player: p,
      x: (100 / (rows[pos].length + 1)) * (i + 1),
      y: ROW_Y[pos],
    }))
  );

  return (
    <div>
      <div className="relative mx-auto aspect-[1/1.04] w-full overflow-hidden rounded-2xl bg-[repeating-linear-gradient(180deg,rgb(var(--c-grass))_0_12.5%,rgb(var(--c-grass-dark))_12.5%_25%)] transition-colors duration-300 [container-type:inline-size]">
        {/* Chalk markings */}
        <svg className="pointer-events-none absolute inset-0 h-full w-full" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden>
          <g fill="none" stroke="var(--chalk)" strokeWidth="1.2" vectorEffect="non-scaling-stroke">
            <rect x="2.5" y="2" width="95" height="96" rx="1" vectorEffect="non-scaling-stroke" />
            <line x1="2.5" y1="50" x2="97.5" y2="50" vectorEffect="non-scaling-stroke" />
            <ellipse cx="50" cy="50" rx="12" ry="11.5" vectorEffect="non-scaling-stroke" />
            <rect x="26" y="2" width="48" height="14" vectorEffect="non-scaling-stroke" />
            <rect x="38" y="2" width="24" height="5.5" vectorEffect="non-scaling-stroke" />
            <rect x="26" y="84" width="48" height="14" vectorEffect="non-scaling-stroke" />
            <rect x="38" y="92.5" width="24" height="5.5" vectorEffect="non-scaling-stroke" />
          </g>
        </svg>

        {placed.map(({ player, x, y }) => (
          <PlayerShirt
            key={player.player_id}
            player={player}
            x={x}
            y={y}
            order={hangIndex.get(player.player_id) ?? 0}
            isActive={active?.player_id === player.player_id}
            coinFlip={coinFlipIds.includes(player.player_id)}
            onSelect={() => setActive(active?.player_id === player.player_id ? null : player)}
          />
        ))}
      </div>

      {active ? (
        <div className="mx-auto mt-4 animate-rise rounded-2xl border border-line bg-surface p-4 shadow-panel">
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
              className="rounded-lg px-2 py-1 text-xs text-ink-400 transition-colors hover:bg-surface-raised hover:text-ink-100"
            >
              Close
            </button>
          </div>

          <div className="mt-4 grid grid-cols-3 gap-2.5">
            {[
              { label: "Projected", value: active.predicted_points.toFixed(1), tone: "text-pts" },
              { label: "Price", value: `£${active.now_cost_m.toFixed(1)}m`, tone: "text-ink-100" },
              { label: "Starts", value: `${Math.round(active.start_probability * 100)}%`, tone: "text-ink-100" },
            ].map((s) => (
              <div key={s.label} className="rounded-xl bg-surface-raised p-2.5">
                <p className="label">{s.label}</p>
                <p className={`mt-0.5 font-kit text-[22px] font-bold tabular-nums ${s.tone}`}>{s.value}</p>
              </div>
            ))}
          </div>

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
