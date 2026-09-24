// File: LeagueView.tsx
// Path: var-ified-xi/frontend/components/LeagueView.tsx
//
// Ownership inside the league you're actually trying to win, which is a very
// different number from the global ownership FPL shows you. Points you and a
// rival both scored cancel out — so what moves you past them is the players
// they don't have, and what threatens you is the ones they all have and you
// don't.

import type { LeagueView as LeagueViewData } from "@/lib/types";
import { InfoNote, Term } from "./ui";

const CHIP_LABEL: Record<string, string> = {
  bboost: "Bench Boost",
  "3xc": "Triple Captain",
  freehit: "Free Hit",
  wildcard: "Wildcard",
};

function pct(share: number) {
  return `${Math.round(share * 100)}%`;
}

export default function LeagueView({ league }: { league: LeagueViewData }) {
  const { differentials, template_gaps, chips_spent, rivals_ahead } = league;
  const you = chips_spent.find((r) => r.is_you);
  const chipsLeft = 4 - (you?.chips.length ?? 0);

  return (
    <div className="space-y-6">
      <InfoNote title={`${league.league_name} — you're ${league.your_rank} of ${league.league_size}`}>
        Ownership below is measured across the{" "}
        <strong className="text-ink-100">{rivals_ahead} managers ahead of you</strong>, not
        the whole world. Those are the people you have to pass, and a player
        they all own can only keep you level — never gain you a place.
      </InfoNote>

      {rivals_ahead === 0 ? (
        <p className="prose-note">
          You&apos;re top of this league. From here the template is your friend:
          owning what your rivals own protects the lead, and differentials are
          what the chasers need, not you.
        </p>
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {/* What can gain you places */}
          <div className="panel p-5">
            <h3 className="label mb-3">Your differentials</h3>
            {differentials.length === 0 ? (
              <p className="prose-note">
                Nothing in your XI is a differential — your team closely matches
                the managers ahead. You&apos;ll track them rather than catch them.
              </p>
            ) : (
              <ul className="space-y-3">
                {differentials.map((d) => (
                  <li key={d.player_id} className="group">
                    <div className="flex items-baseline justify-between gap-3">
                      <span className="font-body text-sm font-medium text-ink-100">
                        {d.name}
                      </span>
                      <span className="font-mono text-[11px] tabular-nums text-ink-400">
                        £{d.cost_m?.toFixed(1)}m &middot;{" "}
                        <span className={d.owned_by === 0 ? "text-pts" : "text-ink-300"}>
                          {d.owned_by}/{rivals_ahead}
                        </span>
                      </span>
                    </div>
                    {/* Filled portion = rivals who ALSO have him, so a short
                        bar is the good case. */}
                    <div className="mt-2 h-[3px] w-full overflow-hidden bg-line">
                      <div
                        className="h-full bg-gold transition-[width] duration-700 ease-out"
                        style={{ width: `${Math.max(3, d.share * 100)}%` }}
                      />
                    </div>
                  </li>
                ))}
              </ul>
            )}
            <p className="prose-note mt-3">
              When these score, you gain on everyone above you who doesn&apos;t
              own them.
            </p>
          </div>

          {/* What can cost you places */}
          <div className="panel p-5">
            <h3 className="label mb-3">Template you&apos;re missing</h3>
            {template_gaps.length === 0 ? (
              <p className="prose-note">
                You own every player that half or more of the managers ahead of
                you hold. No standing exposure.
              </p>
            ) : (
              <ul className="space-y-3">
                {template_gaps.map((t) => (
                  <li key={t.player_id}>
                    <div className="flex items-baseline justify-between gap-3">
                      <span className="font-body text-sm font-medium text-ink-100">
                        {t.name}
                      </span>
                      <span className="font-mono text-[11px] tabular-nums text-warn">
                        £{t.cost_m?.toFixed(1)}m &middot; {pct(t.share)}
                      </span>
                    </div>
                    <div className="mt-2 h-[3px] w-full overflow-hidden bg-line">
                      <div
                        className="h-full bg-risk transition-[width] duration-700 ease-out"
                        style={{ width: `${Math.max(3, t.share * 100)}%` }}
                      />
                    </div>
                  </li>
                ))}
              </ul>
            )}
            <p className="prose-note mt-3">
              Every haul from these costs you ground, and you get nothing back
              when they blank. This is risk, not opportunity.
            </p>
          </div>
        </div>
      )}

      {/* Chips are a standing, invisible edge */}
      <div>
        <h3 className="label mb-3">
          <Term explain="Each chip can be played once per season. A chip spent on an ordinary gameweek is worth far less than one saved for a double or blank — and once it's gone, it's gone.">
            Chips spent
          </Term>
        </h3>
        <div className="panel overflow-x-auto p-5">
          <table className="w-full min-w-[420px] text-left">
            <thead>
              <tr className="border-b border-line">
                <th className="label pb-2 pr-3 font-normal">#</th>
                <th className="label pb-2 pr-3 font-normal">Manager</th>
                <th className="label pb-2 pr-3 text-right font-normal">Pts</th>
                <th className="label pb-2 font-normal">Chips gone</th>
              </tr>
            </thead>
            <tbody>
              {chips_spent.map((r) => (
                <tr
                  key={r.entry}
                  className={`border-b border-line/50 ${
                    r.is_you ? "bg-gold-wash" : ""
                  }`}
                >
                  <td className="py-2 pr-3 font-mono text-[11px] text-ink-500">{r.rank}</td>
                  <td className={`py-2 pr-3 font-body text-sm ${r.is_you ? "font-semibold text-ink-100" : "text-ink-300"}`}>
                    {r.is_you ? "You" : r.name}
                  </td>
                  <td className="py-2 pr-3 text-right font-mono text-[12px] tabular-nums text-ink-200">
                    {r.total}
                  </td>
                  <td className="py-2 font-mono text-[11px]">
                    {r.chips.length === 0 ? (
                      <span className="text-pts">all four intact</span>
                    ) : (
                      <span className="text-warn">
                        {r.chips
                          .map((c) => `${CHIP_LABEL[c.chip] ?? c.chip} (GW${c.gameweek})`)
                          .join(", ")}
                      </span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {chipsLeft === 4 && (
          <p className="prose-note mt-3">
            You still hold all four. Every chip a rival has already spent on an
            ordinary gameweek is points they can no longer score on a double —
            an edge that doesn&apos;t show up in the table above, and one you
            only collect by saving yours for the right week.
          </p>
        )}
      </div>
    </div>
  );
}
