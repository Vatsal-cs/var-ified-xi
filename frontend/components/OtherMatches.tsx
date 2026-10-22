// File: OtherMatches.tsx
// Path: var-ified-xi/frontend/components/OtherMatches.tsx
//
// The games FPL doesn't show: each of your clubs' cup and European ties, and
// your players' international matches, over the planning window (backend
// other_matches.py, from ESPN's public feed). A midweek game before a
// gameweek is a rotation risk; a long-haul international trip is a tiredness
// one. Dates in UTC, like FPL's deadlines.

import type { OtherMatch, OtherMatchesView } from "@/lib/types";
import Crest from "./Crest";

const DAY = new Intl.DateTimeFormat("en-GB", { weekday: "short", day: "numeric", month: "short", timeZone: "UTC" });

function Game({ m }: { m: OtherMatch }) {
  return (
    <li className="flex flex-wrap items-baseline gap-x-2 tabular-nums text-[11.5px]">
      <span className="w-[88px] flex-none text-ink-400">{DAY.format(new Date(m.date))}</span>
      <span className="text-ink-200">
        {m.home ? "v" : "at"} {m.opponent ?? "—"}
      </span>
      <span className="text-ink-500">{m.competition}</span>
      {m.far && <span className="text-warn">long trip</span>}
    </li>
  );
}

export default function OtherMatches({ view }: { view: OtherMatchesView }) {
  if (!view.clubs.length && !view.international.length) {
    return (
      <p className="font-body text-sm text-ink-300">
        None of your players&apos; clubs play a cup or European game, and none of your players
        has international duty, before the end of the planning window.
      </p>
    );
  }
  return (
    <div className="grid gap-10 lg:grid-cols-2">
      <div className="border-t border-line pt-5">
        <p className="label mb-3">Midweek club games</p>
        {view.clubs.length ? (
          <ul className="space-y-3">
            {view.clubs.map((c) => (
              <li key={c.club}>
                <p className="flex flex-wrap items-center gap-x-1.5 font-body text-sm text-ink-100">
                  <Crest team={c.club} className="h-5 w-5 flex-none" />
                  <span className="font-medium">{c.club}</span>
                  <span className="ml-2 tabular-nums text-[11px] text-ink-500">{c.players.join(", ")}</span>
                </p>
                <ul className="mt-1 space-y-0.5">
                  {c.matches.map((m) => (
                    <Game key={m.date + m.competition} m={m} />
                  ))}
                </ul>
              </li>
            ))}
          </ul>
        ) : (
          <p className="font-body text-sm text-ink-300">No cup or European games for your clubs.</p>
        )}
      </div>
      <div className="border-t border-line pt-5">
        <p className="label mb-3">International duty</p>
        {view.international.length ? (
          <ul className="space-y-3">
            {view.international.map((p) => (
              <li key={p.player_id}>
                <p className="font-body text-sm text-ink-100">
                  <span className="font-medium">{p.name}</span>
                  <span className="ml-2 tabular-nums text-[11px] text-ink-500">{p.nation}</span>
                </p>
                <ul className="mt-1 space-y-0.5">
                  {p.matches.map((m) => (
                    <Game key={m.date + m.competition} m={m} />
                  ))}
                </ul>
              </li>
            ))}
          </ul>
        ) : (
          <p className="font-body text-sm text-ink-300">No international games in this window.</p>
        )}
      </div>
    </div>
  );
}
