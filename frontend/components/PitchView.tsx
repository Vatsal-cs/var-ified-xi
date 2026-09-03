// File: PitchView.tsx
// Path: var-ified-xi/frontend/components/PitchView.tsx
"use client";

import { useState } from "react";
import type { Player } from "@/lib/types";

const ROW_ORDER: Player["position"][] = ["FWD", "MID", "DEF", "GK"];
const ROW_Y: Record<Player["position"], number> = { FWD: 16, MID: 41, DEF: 65, GK: 88 };

function groupByRow(xi: Player[]) {
  const rows: Record<Player["position"], Player[]> = { GK: [], DEF: [], MID: [], FWD: [] };
  for (const p of xi) rows[p.position].push(p);
  return rows;
}

/** Projected points per gameweek across the horizon, drawn as bars relative to
 *  this player's own best week — reads as "when are his fixtures kind". */
function FixtureRun({ xpByGw }: { xpByGw: Record<string, number> }) {
  const weeks = Object.entries(xpByGw)
    .map(([gw, xp]) => ({ gw: Number(gw), xp }))
    .sort((a, b) => a.gw - b.gw);
  if (weeks.length < 2) return null;
  const peak = Math.max(...weeks.map((w) => w.xp), 0.1);

  return (
    <div className="mt-4 border-t border-pitch-line pt-3">
      <p className="label mb-2">Next {weeks.length} gameweeks (projected pts)</p>
      <div className="flex items-end gap-1.5">
        {weeks.map((w) => (
          <div key={w.gw} className="flex flex-1 flex-col items-center gap-1">
            <span className="font-mono text-[9px] text-ink-300">{w.xp.toFixed(1)}</span>
            <div
              className="w-full rounded-sm bg-var-green/60"
              style={{ height: `${Math.max(3, (w.xp / peak) * 36)}px` }}
            />
            <span className="font-mono text-[9px] text-ink-500">{w.gw}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function PitchView({ startingXi }: { startingXi: Player[] }) {
  const [active, setActive] = useState<Player | null>(null);
  const rows = groupByRow(startingXi);

  return (
    <div>
      <div className="relative mx-auto aspect-[3/4] w-full max-w-md overflow-hidden rounded-xl border border-pitch-line bg-gradient-to-b from-[#101613] to-[#0A0E0C]">
        <svg
          className="absolute inset-0 h-full w-full"
          viewBox="0 0 100 133"
          preserveAspectRatio="none"
          aria-hidden
        >
          <rect x="3" y="3" width="94" height="127" fill="none" stroke="#243029" strokeWidth="0.4" />
          <line x1="3" y1="66.5" x2="97" y2="66.5" stroke="#243029" strokeWidth="0.4" />
          <circle cx="50" cy="66.5" r="9" fill="none" stroke="#243029" strokeWidth="0.4" />
          <rect x="28" y="3" width="44" height="16" fill="none" stroke="#243029" strokeWidth="0.4" />
          <rect x="28" y="114" width="44" height="16" fill="none" stroke="#243029" strokeWidth="0.4" />
        </svg>

        {ROW_ORDER.map((pos) =>
          rows[pos].map((p, i) => {
            const count = rows[pos].length;
            const x = (100 / (count + 1)) * (i + 1);
            const y = ROW_Y[pos];
            const isActive = active?.player_id === p.player_id;
            return (
              <button
                key={p.player_id}
                onClick={() => setActive(isActive ? null : p)}
                style={{ left: `${x}%`, top: `${(y / 133) * 100}%` }}
                className="group absolute -translate-x-1/2 -translate-y-1/2 focus:outline-none"
                aria-pressed={isActive}
                aria-label={`${p.name}, ${p.predicted_points.toFixed(1)} projected points`}
              >
                <span
                  className={`flex h-11 w-11 flex-col items-center justify-center rounded-full border text-[10px] font-mono font-semibold transition-transform group-hover:scale-105 sm:h-12 sm:w-12 ${
                    p.is_captain
                      ? "border-var-green bg-var-green text-pitch-night"
                      : isActive
                      ? "border-var-green bg-pitch-panel2 text-ink-100"
                      : "border-pitch-line bg-pitch-panel2 text-ink-200"
                  }`}
                >
                  <span>{p.is_captain ? "C" : p.is_vice_captain ? "V" : p.position}</span>
                  <span className="text-[8px] font-normal opacity-70">
                    {p.predicted_points.toFixed(1)}
                  </span>
                </span>
                <span className="mt-1 block max-w-[76px] truncate text-center font-mono text-[9px] text-ink-300">
                  {p.name}
                </span>
              </button>
            );
          })
        )}
      </div>

      {active ? (
        <div className="mx-auto mt-4 max-w-md animate-rise rounded-xl border border-pitch-line bg-pitch-panel p-4">
          <div className="flex items-start justify-between">
            <div>
              <p className="font-display text-lg font-semibold tracking-tight text-ink-100">
                {active.name}
              </p>
              <p className="font-mono text-xs text-ink-400">
                {active.team} &middot; {active.position}
                {active.is_captain && <span className="text-var-green"> &middot; captain (2&times;)</span>}
                {active.is_vice_captain && <span className="text-var-amber"> &middot; vice</span>}
              </p>
            </div>
            <button
              onClick={() => setActive(null)}
              className="font-mono text-xs text-ink-400 hover:text-ink-100"
            >
              close
            </button>
          </div>
          <div className="mt-3 flex flex-wrap gap-6 font-mono text-sm">
            <div>
              <p className="label">Proj. pts</p>
              <p className="mt-0.5 text-var-green">{active.predicted_points.toFixed(2)}</p>
            </div>
            <div>
              <p className="label">Price</p>
              <p className="mt-0.5 text-ink-100">&pound;{active.now_cost_m.toFixed(1)}m</p>
            </div>
            <div>
              <p className="label">Starts 60&apos;+</p>
              <p className="mt-0.5 text-ink-100">
                {Math.round(active.start_probability * 100)}%
              </p>
            </div>
          </div>
          <FixtureRun xpByGw={active.xp_by_gw} />
        </div>
      ) : (
        <p className="mt-3 text-center font-mono text-[11px] text-ink-500">
          Tap a player for their projection and fixture run
        </p>
      )}
    </div>
  );
}
