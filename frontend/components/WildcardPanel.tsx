// File: WildcardPanel.tsx
// Path: var-ified-xi/frontend/components/WildcardPanel.tsx
//
// "Is a Wildcard worth playing this week, and what would it build?" —
// computed on every refresh while the chip is in hand (main._wildcard_option).
// Rival ownership is shown so the differentials are visible; it never shapes
// the picks, which come from the model's own projections.

import type { WildcardOption, WildcardPlayer } from "@/lib/types";
import { kitFor } from "@/lib/teams";

const ORDER: Record<string, number> = { GK: 0, DEF: 1, MID: 2, FWD: 3 };

function Row({ p, captain, vice, ahead }: { p: WildcardPlayer; captain: boolean; vice: boolean; ahead: number }) {
  const kit = kitFor(p.team);
  const differential = ahead > 0 && p.owned_by_ahead === 0;
  return (
    <li className="flex items-baseline gap-3 py-2">
      <span className="w-8 flex-none font-mono text-[10px] uppercase tracking-[0.16em] text-ink-500">{p.position}</span>
      <span className="min-w-0 flex-1">
        <span className="font-body text-sm text-ink-100">{p.name}</span>
        {captain && <span className="ml-1.5 font-mono text-[10px] text-gold">C</span>}
        {vice && <span className="ml-1.5 font-mono text-[10px] text-ink-400">V</span>}
        <span className="ml-2 font-mono text-[11px] text-ink-500">{kit.abbr} &middot; £{p.cost_m.toFixed(1)}m</span>
        <span className="ml-2 inline-flex gap-1.5 align-middle">
          {p.new && <span className="rounded-[2px] border border-pts/40 px-1 font-mono text-[9.5px] uppercase tracking-wider text-pts">in</span>}
          {differential && <span className="rounded-[2px] border border-gold/40 px-1 font-mono text-[9.5px] uppercase tracking-wider text-gold">differential</span>}
        </span>
      </span>
      <span className="flex-none text-right font-mono text-[11.5px] tabular-nums text-ink-300">
        {p.predicted_points.toFixed(1)}
        <span className="ml-2 text-ink-500">{p.horizon_points.toFixed(1)}</span>
      </span>
    </li>
  );
}

export default function WildcardPanel({ option }: { option: WildcardOption }) {
  const sorted = (xs: WildcardPlayer[]) =>
    [...xs].sort((a, b) => ORDER[a.position] - ORDER[b.position] || b.predicted_points - a.predicted_points);
  const xi = sorted(option.squad.filter((p) => p.starting));
  const bench = sorted(option.squad.filter((p) => !p.starting));
  const differentials = option.squad.filter((p) => p.owned_by_ahead === 0).length;
  const worth = option.gain_six_weeks > 0;
  const free = option.free_alternative;

  return (
    <div className={worth ? "panel-lead p-5" : "panel p-5"}>
      <p className={`font-mono text-[10px] uppercase tracking-[0.24em] ${worth ? "text-gold" : "text-ink-500"}`}>
        Wildcard check &middot; GW{option.gameweek}
      </p>
      <p className="mt-2 font-display text-[28px] leading-tight text-ink-100">
        {worth ? "+" : ""}
        {option.gain_six_weeks.toFixed(1)} points over six weeks
      </p>
      <p className="mt-2 max-w-[62ch] font-body text-sm leading-relaxed text-ink-300">
        Against using your free transfer
        {free.out.length > 0 && (
          <> ({free.out.join(", ")} &rarr; {free.in.join(", ")})</>
        )}
        . GW{option.gameweek} projects <span className="text-ink-100">{option.points_with.toFixed(1)}</span> with
        the Wildcard and {option.points_without.toFixed(1)} without. It makes {option.changes} change
        {option.changes === 1 ? "" : "s"}, with £{option.xi_m.toFixed(1)}m in the XI and £
        {option.bench_m.toFixed(1)}m on the bench.
      </p>

      <div className="mt-4 grid gap-x-8 md:grid-cols-[1fr_1fr]">
        <div>
          <p className="label mb-1">Starting XI</p>
          <ul className="divide-y divide-line border-y border-line">
            {xi.map((p) => (
              <Row key={p.player_id} p={p} captain={p.player_id === option.captain_id}
                   vice={p.player_id === option.vice_captain_id} ahead={option.rivals_ahead} />
            ))}
          </ul>
        </div>
        <div className="mt-4 md:mt-0">
          <p className="label mb-1">Bench</p>
          <ul className="divide-y divide-line border-y border-line">
            {bench.map((p) => (
              <Row key={p.player_id} p={p} captain={false} vice={false} ahead={option.rivals_ahead} />
            ))}
          </ul>
          <p className="mt-3 font-mono text-[11px] leading-relaxed text-ink-500">
            &ldquo;In&rdquo; = a new signing. Columns: next gameweek, then six weeks.{" "}
            {option.rivals_ahead > 0 && (
              <>{differentials} of 15 are players none of the {option.rivals_ahead}{" "}managers ahead of you start
              — that&apos;s where places are gained. The picks come from the model&apos;s own projections;
              rival ownership is shown, never copied.</>
            )}
          </p>
        </div>
      </div>
    </div>
  );
}
