// File: WildcardPanel.tsx
// Path: var-ified-xi/frontend/components/WildcardPanel.tsx
//
// "Is a Wildcard worth playing this week, and what would it build?" —
// computed on every refresh while the chip is in hand (main._wildcard_option).
// Rival ownership is shown so the differentials are visible; it never shapes
// the picks, which come from the model's own projections.

import type { PickCheck, WildcardOption, WildcardPlayer } from "@/lib/types";
import { kitFor } from "@/lib/teams";

const ORDER: Record<string, number> = { GK: 0, DEF: 1, MID: 2, FWD: 3 };

function Row({ p, captain, vice, ahead, check }: { p: WildcardPlayer; captain: boolean; vice: boolean; ahead: number; check?: boolean }) {
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
          {check && <span className="rounded-[2px] border border-warn/40 px-1 font-mono text-[9.5px] uppercase tracking-wider text-warn">check</span>}
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
  const checks = option.checks ?? [];
  const checked = new Set(checks.map((c) => c.player_id));

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
                   vice={p.player_id === option.vice_captain_id} ahead={option.rivals_ahead}
                   check={checked.has(p.player_id)} />
            ))}
          </ul>
        </div>
        <div className="mt-4 md:mt-0">
          <p className="label mb-1">Bench</p>
          <ul className="divide-y divide-line border-y border-line">
            {bench.map((p) => (
              <Row key={p.player_id} p={p} captain={false} vice={false} ahead={option.rivals_ahead}
                   check={checked.has(p.player_id)} />
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

      {checks.length > 0 && <SecondLook checks={checks} />}
    </div>
  );
}

/** Picks the model likes more than their season so far suggests, with the
 *  cost of leaving each out — the call stays yours. */
function SecondLook({ checks }: { checks: PickCheck[] }) {
  return (
    <div className="mt-5 rounded-[2px] border border-warn/30 bg-warn/[0.04] p-4">
      <p className="label">Worth a second look</p>
      <ul className="mt-2 space-y-2.5">
        {checks.map((c) => (
          <li key={c.player_id} className="font-body text-sm">
            <span className="font-medium text-ink-100">{c.name}</span>
            <span className="text-ink-300"> &mdash; {c.flags.join("; ")}.</span>
            {c.drop_cost != null && (
              <span className="block font-mono text-[11px] text-ink-400">
                leaving him out costs {c.drop_cost.toFixed(1)} pts over six weeks
                {c.replacement && c.replacement.length > 0 && <> &middot; the squad brings in {c.replacement.join(", ")}</>}
              </span>
            )}
            {c.alternatives && c.alternatives.length > 0 && (
              <div className="mt-1.5">
                <span className="font-mono text-[10px] uppercase tracking-[0.16em] text-ink-500">Could pick instead</span>
                <ul className="mt-1 space-y-1">
                  {c.alternatives.map((a) => (
                    <li key={a.player_id} className="flex flex-wrap items-baseline gap-x-2 font-mono text-[11.5px]">
                      <span className="text-ink-100">{a.name}</span>
                      <span className="text-ink-500">{a.team} &middot; &pound;{a.cost_m.toFixed(1)}m</span>
                      <span className="text-ink-300">
                        {a.next.toFixed(1)} next &middot; {a.six_weeks.toFixed(1)} six weeks{" "}
                        <span className={a.vs >= 0 ? "text-pts" : "text-ink-500"}>
                          ({a.vs >= 0 ? "+" : ""}{a.vs.toFixed(1)})
                        </span>{" "}
                        &middot; {a.ppg.toFixed(1)} a game so far
                      </span>
                      {a.flags && a.flags.length > 0 && (
                        <span className="text-warn">same check: {a.flags.join("; ")}</span>
                      )}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </li>
        ))}
      </ul>
      <p className="mt-3 font-body text-xs leading-relaxed text-ink-400">
        These flags are information, not a ruling: across two past seasons, expensive players in a
        poor run actually scored more than projected, so a flag alone isn&apos;t a reason to sell. A
        small cost means it&apos;s a coin flip and your read of the player decides it. The bracket is
        each swap&apos;s six-week projection against the flagged player&apos;s, if held all six weeks;
        &ldquo;leaving him out costs&rdquo; is the exact figure, because the plan can also change
        later transfers.
      </p>
    </div>
  );
}
