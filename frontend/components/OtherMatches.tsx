// File: OtherMatches.tsx
// Path: var-ified-xi/frontend/components/OtherMatches.tsx
//
// The games FPL doesn't show: each of your clubs' cup and European ties, and
// your players' international matches, over the planning window (backend
// other_matches.py, from ESPN's public feed). A midweek game before a
// gameweek is a rotation risk; a long-haul international trip is a tiredness
// one. Shown as one fixture list in date order. Dates in UTC, like FPL's
// deadlines.

import type { OtherMatch, OtherMatchesView } from "@/lib/types";
import Crest from "./Crest";

const DAY = new Intl.DateTimeFormat("en-GB", { weekday: "short", timeZone: "UTC" });
const DATE = new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "short", timeZone: "UTC" });

/** Each competition's colour, so the list reads at a glance. */
const COMP: { match: RegExp; short: string; colour: string }[] = [
  { match: /champions/i, short: "Champions League", colour: "#2F5DB8" },
  { match: /europa/i, short: "Europa League", colour: "#E8711A" },
  { match: /conference/i, short: "Conference League", colour: "#22A065" },
  { match: /league cup|carabao|efl/i, short: "League Cup", colour: "#8A7E6E" },
  { match: /fa cup/i, short: "FA Cup", colour: "#C8341F" },
  { match: /nations/i, short: "Nations League", colour: "#7A5CD6" },
  { match: /qualif|world cup/i, short: "Qualifier", colour: "#0E8A92" },
  { match: /friendl/i, short: "Friendly", colour: "#9A968F" },
];

function comp(name: string) {
  return COMP.find((c) => c.match.test(name)) ?? { short: name, colour: "#9A968F" };
}

type Row = { m: OtherMatch; who: React.ReactNode; crest?: string; key: string };

function Fixture({ row }: { row: Row }) {
  const c = comp(row.m.competition);
  const d = new Date(row.m.date);
  return (
    <li className="grid grid-cols-[52px_1fr] gap-4 border-b border-line py-3 sm:grid-cols-[64px_1fr_190px] sm:items-center">
      <span className="leading-tight">
        <span className="block text-[12px] text-ink-400">{DAY.format(d)}</span>
        <span className="block text-[15px] font-semibold tabular-nums text-ink-100">{DATE.format(d)}</span>
      </span>
      <span className="min-w-0">
        <span className="flex items-center gap-2 text-[14.5px] text-ink-100">
          {row.crest && <Crest team={row.crest} className="h-5 w-5 flex-none" />}
          <span className="truncate">
            {row.who} <span className="text-ink-400">{row.m.home ? "v" : "at"}</span> {row.m.opponent ?? "—"}
          </span>
        </span>
        <span className="mt-1 flex items-center gap-1.5 text-[12.5px] text-ink-400 sm:hidden">
          <span className="h-2 w-2 rounded-full" style={{ background: c.colour }} />
          {c.short}
          {row.m.far && <span className="font-semibold text-warn">&middot; long trip</span>}
        </span>
      </span>
      <span className="hidden items-center gap-2 text-[13px] text-ink-300 sm:flex">
        <span className="h-2 w-2 flex-none rounded-full" style={{ background: c.colour }} />
        <span className="truncate">{c.short}</span>
        {row.m.far && <span className="font-semibold text-warn">long trip</span>}
      </span>
    </li>
  );
}

export default function OtherMatches({ view }: { view: OtherMatchesView }) {
  if (!view.clubs.length && !view.international.length) {
    return (
      <p className="prose-note">
        None of your players&apos; clubs play a cup or European game, and none of your players has international
        duty, before the end of the planning window.
      </p>
    );
  }
  const clubRows: Row[] = view.clubs
    .flatMap((c) =>
      c.matches.map((m) => ({
        m,
        crest: c.club,
        key: `${c.club}-${m.date}`,
        who: (
          <>
            <span className="font-semibold">{c.club}</span>{" "}
            <span className="text-[12.5px] text-ink-400">({c.players.join(", ")})</span>
          </>
        ),
      }))
    )
    .sort((a, b) => a.m.date.localeCompare(b.m.date));
  const intlRows: Row[] = view.international
    .flatMap((p) =>
      p.matches.map((m) => ({
        m,
        key: `${p.player_id}-${m.date}`,
        who: (
          <>
            <span className="font-semibold">{p.name}</span>{" "}
            <span className="text-[12.5px] text-ink-400">for {p.nation}</span>
          </>
        ),
      }))
    )
    .sort((a, b) => a.m.date.localeCompare(b.m.date));

  return (
    <div className="space-y-12">
      <section>
        <h3 className="heading">Midweek club games</h3>
        <p className="mb-3 mt-1 text-[14px] text-ink-400">A tie before a gameweek is a rotation risk.</p>
        {clubRows.length ? (
          <ul className="border-t border-line">
            {clubRows.map((r) => (
              <Fixture key={r.key} row={r} />
            ))}
          </ul>
        ) : (
          <p className="prose-note">No cup or European games for your clubs.</p>
        )}
      </section>
      <section>
        <h3 className="heading">International duty</h3>
        <p className="mb-3 mt-1 text-[14px] text-ink-400">A long trip home means tired legs the weekend after.</p>
        {intlRows.length ? (
          <ul className="border-t border-line">
            {intlRows.map((r) => (
              <Fixture key={r.key} row={r} />
            ))}
          </ul>
        ) : (
          <p className="prose-note">No international games in this window.</p>
        )}
      </section>
    </div>
  );
}
