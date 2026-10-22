// File: CaptainOdds.tsx
// Path: var-ified-xi/frontend/components/CaptainOdds.tsx
//
// The armband as head-to-heads: the XI's next three best projections, each in
// his shirt, with how often he'd outscore the captain this week. Head-to-heads
// are recalibrated on two past seasons (backend research/2026-10-distributions).

import type { CaptainOdds as Odds, Player } from "@/lib/types";
import { pct } from "@/lib/odds";
import Shirt from "./Shirt";
import { Term } from "./ui";

export default function CaptainOdds({ odds, players = [] }: { odds: Odds[]; players?: Player[] }) {
  if (odds.length < 2) return null;
  const [cap, ...others] = odds;
  const find = (id: number) => players.find((p) => p.player_id === id);

  return (
    <div>
      <p className="text-[14px] font-medium text-ink-100">
        <Term explain="Each player's full points distribution, built from how players projected like him actually scored over two past seasons. 'Beats' is how often he'd outscore the captain, ties left out.">
          Could anyone outscore {cap.name}?
        </Term>
      </p>
      <ul className="mt-3 space-y-2">
        {others.map((o, i) => {
          const b = o.beats_captain ?? 0;
          const p = find(o.player_id);
          return (
            <li key={o.player_id} className="grid grid-cols-[34px_86px_1fr_40px] items-center gap-2.5 text-[14px]">
              <Shirt
                team={p?.team}
                number={o.projected.toFixed(1)}
                uid={`odds-${o.player_id}`}
                goalkeeper={p?.position === "GK"}
                className="h-[34px] w-[34px]"
              />
              <span className="truncate font-medium text-ink-100">{o.name}</span>
              <span className="relative block h-2 overflow-hidden rounded-full bg-ink-500/20" aria-hidden>
                <span
                  className="absolute inset-y-0 left-0 origin-left animate-grow rounded-full bg-ink-100"
                  style={{ width: `${b * 100}%`, animationDelay: `${0.35 + i * 0.12}s` }}
                />
                <span className="absolute inset-y-0 left-1/2 w-0.5 bg-base" />
              </span>
              <span className="text-right font-semibold tabular-nums text-ink-100">{pct(b)}</span>
            </li>
          );
        })}
      </ul>
      <p className="mt-3 text-[12.5px] leading-relaxed text-ink-500">
        {cap.name} likely scores {cap.p10}&ndash;{cap.p90} ({cap.p10 * 2}&ndash;{cap.p90 * 2} doubled). The gap in
        each bar is a coin flip; the armband goes to the highest projection because that wins over a season.
      </p>
    </div>
  );
}
