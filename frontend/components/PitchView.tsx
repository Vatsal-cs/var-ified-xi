// File: PitchView.tsx
// Path: var-ified-xi/frontend/components/PitchView.tsx
"use client";

import { useState } from "react";
import type { Player } from "@/lib/types";
import { kitFor, needsOutline } from "@/lib/teams";

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

function PlayerChip({
  player,
  x,
  y,
  isActive,
  onSelect,
}: {
  player: Player;
  x: number;
  y: number;
  isActive: boolean;
  onSelect: () => void;
}) {
  const kit = kitFor(player.team);
  const outline = needsOutline(kit);
  const armband = player.is_captain ? "C" : player.is_vice_captain ? "V" : null;

  return (
    <button
      onClick={onSelect}
      aria-pressed={isActive}
      aria-label={`${player.name}, ${player.team}, ${player.predicted_points.toFixed(
        1
      )} projected points`}
      // Fixed width so a long surname can't widen the button and shove the
      // whole column off its mark. Five across on a phone is the tight case.
      className="group absolute z-10 flex w-[62px] -translate-x-1/2 -translate-y-1/2 flex-col items-center focus:outline-none sm:w-[84px]"
      style={{ left: `${x}%`, top: `${y}%` }}
    >
      {/* Shirt */}
      <span className="relative block">
        <span
          className={`flex h-12 w-12 items-center justify-center rounded-full font-display text-[11px] font-bold tracking-wide shadow-lg transition-all duration-200 group-hover:-translate-y-1 group-hover:shadow-xl sm:h-[52px] sm:w-[52px] ${
            isActive ? "ring-2 ring-pts ring-offset-2 ring-offset-[#0d1a13]" : ""
          }`}
          style={{
            background: kit.shirt,
            color: kit.trim,
            boxShadow: outline
              ? "0 0 0 1.5px rgba(0,0,0,0.45), 0 6px 14px -6px rgba(0,0,0,0.8)"
              : "0 6px 14px -6px rgba(0,0,0,0.8)",
          }}
        >
          {kit.abbr}
        </span>

        {armband && (
          <span
            className={`absolute -right-1 -top-1 flex h-5 w-5 items-center justify-center rounded-full border-2 border-[#0d1a13] font-mono text-[9px] font-bold ${
              player.is_captain
                ? "bg-pts text-base"
                : "bg-warn text-base"
            }`}
          >
            {armband}
          </span>
        )}
      </span>

      {/* Name + points tag */}
      <span className="mt-1.5 block w-full rounded bg-[#08120d]/85 px-0.5 py-0.5 backdrop-blur-sm">
        <span className="block truncate text-center font-body text-[10px] font-medium leading-tight text-ink-100">
          {player.name}
        </span>
        <span className="block text-center font-mono text-[9px] leading-tight text-pts">
          {player.predicted_points.toFixed(1)}
        </span>
      </span>
    </button>
  );
}

export default function PitchView({ startingXi }: { startingXi: Player[] }) {
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
      <div className="relative mx-auto aspect-[3/4] w-full max-w-md overflow-hidden rounded-2xl border border-line shadow-glass">
        {/* Turf: a deep green base with mown stripes */}
        <div className="absolute inset-0 bg-[linear-gradient(175deg,#123d27_0%,#0f2f1f_45%,#0a2016_100%)]" />
        <div
          className="absolute inset-0 opacity-[0.55]"
          style={{
            backgroundImage:
              "repeating-linear-gradient(180deg, rgba(255,255,255,0.035) 0 8.33%, transparent 8.33% 16.66%)",
          }}
        />
        {/* Floodlight falloff from the top */}
        <div className="absolute inset-0 bg-[radial-gradient(120%_70%_at_50%_-5%,rgba(120,255,190,0.10),transparent_60%)]" />

        {/* Markings */}
        <svg
          className="absolute inset-0 h-full w-full"
          viewBox="0 0 100 133"
          preserveAspectRatio="none"
          aria-hidden
        >
          <g fill="none" stroke="rgba(255,255,255,0.16)" strokeWidth="0.45">
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

        {placed.map(({ player, x, y }) => (
          <PlayerChip
            key={player.player_id}
            player={player}
            x={x}
            y={y}
            isActive={active?.player_id === player.player_id}
            onSelect={() =>
              setActive(active?.player_id === player.player_id ? null : player)
            }
          />
        ))}
      </div>

      {active ? (
        <div className="mx-auto mt-4 max-w-md animate-rise rounded-xl border border-line bg-surface p-4 shadow-glass">
          <div className="flex items-start justify-between gap-3">
            <div className="flex items-center gap-3">
              <span
                className="flex h-9 w-9 flex-none items-center justify-center rounded-full font-display text-[10px] font-bold"
                style={{
                  background: kitFor(active.team).shirt,
                  color: kitFor(active.team).trim,
                }}
              >
                {kitFor(active.team).abbr}
              </span>
              <div>
                <p className="font-display text-lg font-semibold tracking-tight text-ink-100">
                  {active.name}
                </p>
                <p className="font-mono text-[11px] text-ink-400">
                  {active.team} &middot; {active.position}
                  {active.is_captain && (
                    <span className="text-pts"> &middot; captain (2&times;)</span>
                  )}
                  {active.is_vice_captain && (
                    <span className="text-warn"> &middot; vice</span>
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
            <div className="rounded-lg bg-surface-raised p-2.5">
              <p className="label">Proj. pts</p>
              <p className="mt-0.5 font-mono text-lg tabular-nums text-pts">
                {active.predicted_points.toFixed(1)}
              </p>
            </div>
            <div className="rounded-lg bg-surface-raised p-2.5">
              <p className="label">Price</p>
              <p className="mt-0.5 font-mono text-lg tabular-nums text-ink-100">
                &pound;{active.now_cost_m.toFixed(1)}
              </p>
            </div>
            <div className="rounded-lg bg-surface-raised p-2.5">
              <p className="label">Starts</p>
              <p className="mt-0.5 font-mono text-lg tabular-nums text-ink-100">
                {Math.round(active.start_probability * 100)}%
              </p>
            </div>
          </div>

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
