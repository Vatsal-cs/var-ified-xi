// File: CaptainOdds.tsx
// Path: var-ified-xi/frontend/components/CaptainOdds.tsx
//
// The armband as head-to-heads: the captain's likely range, then the XI's next
// three best projections, each with how often he'd outscore the captain this
// week. Head-to-heads are recalibrated on two past seasons (backend
// research/2026-10-distributions); the 10+ chance and the likely range needed
// no correction.

import type { CaptainOdds as Odds, Player } from "@/lib/types";
import { pct } from "@/lib/odds";
import Crest from "./Crest";
import { Term } from "./ui";

export default function CaptainOdds({ odds, players = [] }: { odds: Odds[]; players?: Player[] }) {
  if (odds.length < 2) return null;
  const [cap, ...others] = odds;
  const club = (id: number) => players.find((p) => p.player_id === id)?.team;

  return (
    <div>
      <p className="text-[14px] font-medium text-ink-100">
        <Term explain="Each player's full points distribution, built from how players projected like him actually scored over two past seasons. 'Beats' is how often he'd outscore the captain, ties left out.">
          Could anyone outscore {cap.name}?
        </Term>
      </p>
      <p className="mt-1 text-[12.5px] text-ink-400">
        {cap.name} likely scores {cap.p10}&ndash;{cap.p90}, doubled {cap.p10 * 2}&ndash;{cap.p90 * 2} with the
        armband.
      </p>
      <ul className="mt-3 space-y-2.5">
        {others.map((o, i) => {
          const b = o.beats_captain ?? 0;
          return (
            <li key={o.player_id} className="grid grid-cols-[18px_88px_1fr_40px] items-center gap-2.5 text-[13.5px]">
              <Crest team={club(o.player_id)} className="h-[18px] w-[18px]" />
              <span className="truncate text-ink-100">{o.name}</span>
              <span className="relative block h-[7px] overflow-hidden rounded-full bg-surface-raised" aria-hidden>
                <span
                  className="absolute inset-y-0 left-0 origin-left animate-grow rounded-full bg-ink-100"
                  style={{ width: `${b * 100}%`, animationDelay: `${1.4 + i * 0.12}s` }}
                />
                <span className="absolute inset-y-0 left-1/2 w-0.5 bg-surface" />
              </span>
              <span className="text-right font-semibold tabular-nums text-ink-100">{pct(b)}</span>
            </li>
          );
        })}
      </ul>
      <p className="mt-2 text-[12px] text-ink-500">
        The gap in the middle of each bar is a coin flip. Nobody here is a sure thing in one week; the
        armband goes to the highest projection because that wins over a season.
      </p>
    </div>
  );
}
