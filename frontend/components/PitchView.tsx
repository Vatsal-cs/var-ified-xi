// File: PitchView.tsx
// Path: var-ified-xi/frontend/components/PitchView.tsx
"use client";

import { useEffect, useState } from "react";
import type { Player } from "@/lib/types";

const ROW_ORDER: Player["position"][] = ["FWD", "MID", "DEF", "GK"];
// vertical position (%) for each row, attacking direction = up the screen
const ROW_Y: Record<Player["position"], number> = {
  FWD: 14,
  MID: 40,
  DEF: 64,
  GK: 88,
};

function groupByRow(startingXi: Player[]) {
  const rows: Record<Player["position"], Player[]> = { GK: [], DEF: [], MID: [], FWD: [] };
  for (const p of startingXi) rows[p.position].push(p);
  return rows;
}

export default function PitchView({ startingXi }: { startingXi: Player[] }) {
  const [reviewing, setReviewing] = useState(true);
  const [active, setActive] = useState<Player | null>(null);
  const rows = groupByRow(startingXi);

  useEffect(() => {
    const t = setTimeout(() => setReviewing(false), 1400);
    return () => clearTimeout(t);
  }, []);

  return (
    <div className="relative">
      <div className="relative mx-auto aspect-[3/4] w-full max-w-md overflow-hidden rounded-lg border border-pitch-line bg-gradient-to-b from-[#0E1512] to-[#0A0E0C] sm:max-w-lg">
        {/* pitch markings */}
        <svg className="absolute inset-0 h-full w-full" viewBox="0 0 100 133" preserveAspectRatio="none">
          <rect x="2" y="2" width="96" height="129" fill="none" stroke="#26332C" strokeWidth="0.4" />
          <line x1="2" y1="66.5" x2="98" y2="66.5" stroke="#26332C" strokeWidth="0.4" />
          <circle cx="50" cy="66.5" r="10" fill="none" stroke="#26332C" strokeWidth="0.4" />
          <rect x="26" y="2" width="48" height="18" fill="none" stroke="#26332C" strokeWidth="0.4" />
          <rect x="26" y="113" width="48" height="18" fill="none" stroke="#26332C" strokeWidth="0.4" />
        </svg>

        {/* scanline sweep on load */}
        {reviewing && (
          <div className="pointer-events-none absolute inset-x-0 top-0 h-24 animate-scanline bg-gradient-to-b from-transparent via-var-green/25 to-transparent" />
        )}

        {reviewing && (
          <div className="absolute inset-0 z-10 flex items-center justify-center bg-pitch-night/40">
            <span className="animate-pulseDot font-mono text-xs uppercase tracking-[0.3em] text-var-green">
              Reviewing squad&hellip;
            </span>
          </div>
        )}

        {/* player nodes */}
        {ROW_ORDER.map((pos) =>
          rows[pos].map((p, i) => {
            const count = rows[pos].length;
            const xStep = 100 / (count + 1);
            const x = xStep * (i + 1);
            const y = ROW_Y[pos];
            return (
              <button
                key={p.player_id}
                onClick={() => setActive(p)}
                style={{
                  left: `${x}%`,
                  top: `${(y / 133) * 100}%`,
                  animationDelay: `${1.3 + i * 0.08}s`,
                }}
                className={`group absolute -translate-x-1/2 -translate-y-1/2 opacity-0 ${
                  !reviewing ? "animate-stamp" : ""
                }`}
              >
                <span
                  className={`flex h-11 w-11 flex-col items-center justify-center rounded-full border text-[10px] font-mono font-bold shadow-lg transition-transform group-hover:scale-110 sm:h-12 sm:w-12 ${
                    p.is_captain
                      ? "border-var-green bg-var-green text-pitch-night"
                      : "border-var-greendim bg-pitch-panel2 text-ink-100"
                  }`}
                >
                  {p.is_captain ? "C" : p.is_vice_captain ? "V" : p.position}
                </span>
                <span className="mt-1 block max-w-[70px] truncate text-center font-mono text-[9px] text-ink-300 sm:max-w-[80px]">
                  {p.name}
                </span>
              </button>
            );
          })
        )}
      </div>

      {/* selected player readout */}
      {active && (
        <div className="mx-auto mt-4 max-w-md rounded-md border border-pitch-line bg-pitch-panel p-4 sm:max-w-lg animate-fadeUp">
          <div className="flex items-start justify-between">
            <div>
              <p className="font-display text-lg uppercase tracking-wide text-ink-100">{active.name}</p>
              <p className="font-mono text-xs text-ink-500">
                {active.team} &middot; {active.position}
                {active.is_captain && <span className="text-var-green"> &middot; CAPTAIN (2x)</span>}
                {active.is_vice_captain && <span className="text-var-amber"> &middot; VICE-CAPTAIN</span>}
              </p>
            </div>
            <button
              onClick={() => setActive(null)}
              className="font-mono text-xs text-ink-500 hover:text-ink-100"
              aria-label="Close player detail"
            >
              CLOSE
            </button>
          </div>
          <div className="mt-3 flex gap-6 font-mono text-sm">
            <div>
              <p className="text-[10px] uppercase tracking-wider text-ink-500">Predicted pts</p>
              <p className="text-var-green">{active.predicted_points.toFixed(2)}</p>
            </div>
            <div>
              <p className="text-[10px] uppercase tracking-wider text-ink-500">Price</p>
              <p className="text-ink-100">&pound;{active.now_cost_m.toFixed(1)}m</p>
            </div>
          </div>
        </div>
      )}
      {!active && (
        <p className="mt-3 text-center font-mono text-[11px] text-ink-500">
          Tap a player for the model&apos;s prediction breakdown
        </p>
      )}
    </div>
  );
}
