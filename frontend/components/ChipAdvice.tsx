// File: ChipAdvice.tsx
// Path: var-ified-xi/frontend/components/ChipAdvice.tsx
//
// When to play Triple Captain / Bench Boost / Wildcard / Free Hit. Two
// separate questions, answered in order:
//
//   1. Deadline — chips come in half-season sets and an unplayed chip is
//      lost, so "wait for a double gameweek" is only right if one arrives in
//      time. The expiry panel says how long you have and what the best week in
//      sight is worth.
//   2. Calendar — named suggestions when a double or blank gameweek is close
//      enough to act on, or an explicit "watching, nothing yet".

import type { ChipExpiry, ChipPlan, ChipSuggestion, ChipWatch } from "@/lib/types";
import ChipPlanner from "./ChipPlanner";

const CHIP_LABEL: Record<ChipSuggestion["chip"], string> = {
  bboost: "Bench Boost",
  "3xc": "Triple Captain",
  freehit: "Free Hit",
  wildcard: "Wildcard",
};

function ExpiryPanel({ expiry, plan }: { expiry: ChipExpiry; plan?: ChipPlan }) {
  const { deadline_gw, gameweeks_left, chips_left, urgent, best_weeks, visible_through_gw } = expiry;
  if (chips_left.length === 0) return null;
  const best = Object.fromEntries(best_weeks.map((b) => [b.chip, b]));

  return (
    <div className={urgent ? "panel-lead pt-5" : "border-t border-line pt-5"}>
      <p className={`label ${urgent ? "text-risk" : "text-gold"}`}>
        Use them or lose them &middot; deadline GW{deadline_gw}
      </p>
      <p className="mt-2 text-[24px] font-semibold leading-tight tracking-[-0.02em] text-ink-100">
        {chips_left.length} chip{chips_left.length === 1 ? "" : "s"} left, {gameweeks_left}{" "}
        gameweek{gameweeks_left === 1 ? "" : "s"} to play {chips_left.length === 1 ? "it" : "them"}
      </p>
      <p className="mt-2 max-w-[62ch] font-body text-sm leading-relaxed text-ink-300">
        FPL gives two sets of chips a season. This set can&apos;t be carried past the GW
        {deadline_gw} deadline — an unplayed chip is lost, not saved — and only one chip can
        be played per gameweek.
        {urgent
          ? " You're now at the point where every remaining week needs a chip."
          : " Waiting for a double gameweek is fine only if one is confirmed before then."}
      </p>

      {plan && plan.scenarios.length > 0 ? (
        <ChipPlanner plan={plan} />
      ) : (
        <>
        <ul className="mt-4 divide-y divide-line border-y border-line">
          {chips_left.map((chip) => {
            const b = best[chip];
            return (
              <li key={chip} className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1 py-2.5">
                <span className="font-body text-sm font-medium text-ink-100">{CHIP_LABEL[chip]}</span>
                <span className="tabular-nums text-[11.5px] text-ink-300">
                  {b ? (
                    <>
                      best week in sight <span className="text-ink-100">GW{b.gameweek}</span>
                      {b.player ? <> &middot; {b.player}</> : <> &middot; bench</>}{" "}
                      <span className="text-pts">+{b.value.toFixed(1)} pts</span>
                    </>
                  ) : (
                    "no single-week projection — best on a blank, a double or a squad rebuild"
                  )}
                </span>
              </li>
            );
          })}
        </ul>
        {visible_through_gw && visible_through_gw < deadline_gw && (
          <p className="mt-3 tabular-nums text-[11px] text-ink-500">
            Projections reach GW{visible_through_gw}; weeks after that come into view as the
            season moves. Triple Captain adds one more copy of the captain&apos;s projection;
            Bench Boost adds the bench&apos;s.
          </p>
        )}
        </>
      )}
    </div>
  );
}

export default function ChipAdvice({
  advice,
  watch,
  expiry,
  plan,
  horizonGws,
}: {
  advice?: ChipSuggestion[];
  watch?: ChipWatch;
  expiry?: ChipExpiry;
  plan?: ChipPlan;
  horizonGws: number;
}) {
  const next = watch?.next_double_gw ?? watch?.next_blank_gw;

  return (
    <div className="space-y-4">
      {expiry && <ExpiryPanel expiry={expiry} plan={plan} />}

      {advice && advice.length > 0 ? (
        <div className="space-y-3">
          {advice.map((a) => (
            <div
              key={`${a.chip}-${a.gameweek}`}
              className="callout border-warn"
            >
              <p className="label text-warn">
                GW{a.gameweek} &middot; {CHIP_LABEL[a.chip]}
              </p>
              <p className="mt-1.5 font-body text-sm text-ink-200">{a.reason}</p>
            </div>
          ))}
        </div>
      ) : (
        // Nothing on the calendar yet — say so explicitly, so it never reads
        // as "this feature doesn't work".
        <div className="callout">
          <p className="font-body text-sm text-ink-300">
            {next ? (
              <>
                A gameweek worth a chip is on the calendar (GW{next}), but it&apos;s further out
                than the {horizonGws}-gameweek planning window — too early to say who you&apos;d
                own by then. It&apos;ll turn into a named suggestion once it&apos;s in range.
              </>
            ) : (
              <>
                No double or blank gameweek on the fixture calendar yet
                {watch ? ` (checked through GW${watch.checked_through_gw})` : ""}. They come
                from mid-season reschedules and are usually confirmed a few weeks ahead. This
                re-checks every run.
              </>
            )}
          </p>
        </div>
      )}
    </div>
  );
}
