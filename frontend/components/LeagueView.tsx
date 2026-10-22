// File: LeagueView.tsx
// Path: var-ified-xi/frontend/components/LeagueView.tsx
//
// Ownership inside the league you're actually trying to win, which is a very
// different number from the global ownership FPL shows you. Points you and a
// rival both scored cancel out — so what moves you past them is the players
// they don't have, and what threatens you is the ones they all have and you
// don't. Players are drawn as their shirts; the dots under each are the
// managers ahead of you, filled for every one who owns him.

import Link from "next/link";
import type { LeagueView as LeagueViewData, Player, RivalOwnership } from "@/lib/types";
import Shirt from "./Shirt";
import { ChipToken, chipName, Term } from "./ui";

function Owners({ owned, of, tone }: { owned: number; of: number; tone: string }) {
  return (
    <span className="flex gap-1" aria-label={`${owned} of ${of} own him`}>
      {Array.from({ length: of }, (_, i) => (
        <span key={i} className={`h-1.5 w-1.5 rounded-full ${i < owned ? tone : "bg-ink-500/30"}`} />
      ))}
    </span>
  );
}

function ShirtGrid({
  items,
  of,
  tone,
  players,
  prefix,
}: {
  items: RivalOwnership[];
  of: number;
  tone: string;
  players: Player[];
  prefix: string;
}) {
  return (
    <ul className="grid grid-cols-3 gap-x-2 gap-y-5 sm:grid-cols-4">
      {items.map((d, i) => {
        const club = d.team ?? players.find((p) => p.player_id === d.player_id)?.team;
        return (
          <li
            key={d.player_id}
            className="shirt-hang flex animate-hang flex-col items-center text-center"
            style={{ animationDelay: `${0.15 + i * 0.05}s` }}
          >
            <Shirt
              team={club}
              number={d.cost_m?.toFixed(1) ?? "—"}
              uid={`${prefix}-${d.player_id}`}
              className="h-16 w-16 drop-shadow-[0_6px_6px_rgba(0,0,0,0.22)]"
            />
            <span className="-mt-1 max-w-full truncate rounded-md bg-plate px-2 py-px text-[12px] font-semibold text-plate-text">
              {d.name}
            </span>
            <span className="mt-1.5">
              <Owners owned={d.owned_by} of={of} tone={tone} />
            </span>
            <span className="mt-1 text-[11.5px] tabular-nums text-ink-400">
              {d.owned_by} of {of} own him
            </span>
          </li>
        );
      })}
    </ul>
  );
}

export default function LeagueView({ league, players = [] }: { league: LeagueViewData; players?: Player[] }) {
  const { differentials, template_gaps, chips_spent, rivals_ahead } = league;
  const you = chips_spent.find((r) => r.is_you);
  // Chips are issued per half season, so only chips played inside the set
  // currently in play count against it.
  const win = league.chip_window ?? { start: 1, end: 38 };
  const inWindow = (gw: number) => gw >= win.start && gw <= win.end;
  const yourLeft = 4 - (you?.chips.filter((c) => inWindow(c.gameweek)).length ?? 0);

  return (
    <div className="space-y-14">
      {rivals_ahead === 0 ? (
        <p className="prose-note">
          You&apos;re top of this league. From here the template is your friend: owning what your rivals own
          protects the lead, and differentials are what the chasers need, not you.
        </p>
      ) : (
        <div className="grid gap-12 lg:grid-cols-2 lg:gap-0">
          {/* What can gain you places */}
          <section className="lg:pr-10">
            <h3 className="heading">Only you have them</h3>
            <p className="mb-5 mt-1 text-[14px] text-ink-400">
              When these score, you gain on everyone above you who doesn&apos;t own them. Shirt numbers are
              prices.
            </p>
            {differentials.length === 0 ? (
              <p className="prose-note">
                Nothing in your XI is a differential — your team closely matches the managers ahead. You&apos;ll
                track them rather than catch them.
              </p>
            ) : (
              <ShirtGrid items={differentials} of={rivals_ahead} tone="bg-pts" players={players} prefix="diff" />
            )}
          </section>

          {/* What can cost you places */}
          <section className="lg:border-l lg:border-line lg:pl-10">
            <h3 className="heading">They have them, you don&apos;t</h3>
            <p className="mb-5 mt-1 text-[14px] text-ink-400">
              Every haul from these costs you ground, and you get nothing back when they blank.
            </p>
            {template_gaps.length === 0 ? (
              <p className="prose-note">
                You own every player that half or more of the managers ahead of you hold. No standing exposure.
              </p>
            ) : (
              <ShirtGrid items={template_gaps} of={rivals_ahead} tone="bg-risk" players={players} prefix="gap" />
            )}
          </section>
        </div>
      )}

      {/* The table, with the chips everyone has spent */}
      <section>
        <h3 className="heading">The table</h3>
        <p className="mb-4 mt-1 text-[14px] text-ink-400">
          <Term explain="FPL issues chips in two half-season sets. Each set must be played inside its window — the first by the GW19 deadline — and an unplayed chip is lost rather than carried over. Everyone gets a fresh set at GW20.">
            Chips played this half
          </Term>{" "}
          (GW{win.start}–{win.end}) next to each manager.
        </p>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[460px] text-left">
            <thead>
              <tr className="border-y border-line text-[12.5px] text-ink-400">
                <th className="py-2.5 pr-3 font-medium">#</th>
                <th className="py-2.5 pr-3 font-medium">Manager</th>
                <th className="py-2.5 pr-3 text-right font-medium">Points</th>
                <th className="py-2.5 pr-3 text-right font-medium">vs you</th>
                <th className="py-2.5 pl-3 font-medium">Chips</th>
              </tr>
            </thead>
            <tbody>
              {chips_spent.map((r) => {
                const gap = you ? r.total - you.total : 0;
                const played = r.chips.filter((c) => inWindow(c.gameweek));
                return (
                  <tr
                    key={r.entry}
                    className={`border-b border-line ${r.is_you ? "bg-gold-wash shadow-[inset_3px_0_0_rgb(var(--c-gold))]" : ""}`}
                  >
                    <td className="py-3 pl-2 pr-3 text-[13px] tabular-nums text-ink-400">{r.rank}</td>
                    <td className={`py-3 pr-3 text-[14.5px] ${r.is_you ? "font-semibold text-ink-100" : "text-ink-200"}`}>
                      {r.is_you ? "You" : r.name}
                    </td>
                    <td className="py-3 pr-3 text-right font-kit text-[18px] font-bold tabular-nums text-ink-100">
                      {r.total}
                    </td>
                    <td
                      className={`py-3 pr-3 text-right text-[13px] font-semibold tabular-nums ${
                        r.is_you ? "text-ink-400" : gap > 0 ? "text-risk" : "text-pts"
                      }`}
                    >
                      {r.is_you ? "—" : gap > 0 ? `+${gap}` : gap}
                    </td>
                    <td className="py-3 pl-3">
                      {played.length === 0 ? (
                        <span className="text-[12.5px] text-ink-500">none yet</span>
                      ) : (
                        <span className="flex gap-1.5">
                          {played.map((c) => (
                            <span key={c.chip} title={`${chipName(c.chip)}, GW${c.gameweek}`}>
                              <ChipToken chip={c.chip} size={24} />
                            </span>
                          ))}
                        </span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        {yourLeft > 0 && (
          <p className="mt-4 max-w-[70ch] text-[14px] leading-relaxed text-ink-300">
            You have {yourLeft} of this half&apos;s chips left. Rivals who played theirs early haven&apos;t lost
            anything for good — everyone gets a new set at GW{win.end + 1} — so yours are only an edge if you play
            them by the GW{win.end} deadline.{" "}
            <Link href="/plan" className="font-medium text-gold underline decoration-gold/40 underline-offset-2">
              Plan &amp; chips
            </Link>{" "}
            has the best week for each.
          </p>
        )}
      </section>
    </div>
  );
}
