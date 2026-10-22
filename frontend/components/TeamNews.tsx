// File: TeamNews.tsx
// Path: var-ified-xi/frontend/components/TeamNews.tsx
//
// What the team-news reader (backend team_news.py) found for the players in
// this decision, worst first, each with its source. "Out" and "doubtful"
// calls worse than FPL's own flag have already lowered the projection; those
// are marked. Rotation risk is information only.

import type { NewsItem, NewsRecord, NewsStatus, TeamNewsView } from "@/lib/types";
import { Term } from "./ui";
import Ago from "./Ago";
import Crest from "./Crest";

const STATUS: Record<NewsStatus, { label: string; tone: string }> = {
  out: { label: "Out", tone: "border-risk/40 text-risk" },
  doubtful: { label: "Doubt", tone: "border-warn/40 text-warn" },
  rotation_risk: { label: "Rotation", tone: "border-violet/40 text-violet" },
  expected_to_start: { label: "Starts", tone: "border-pts/35 text-pts" },
  no_news: { label: "No news", tone: "border-line text-ink-500" },
};

function host(url: string) {
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return "source";
  }
}

function Row({ item, applied }: { item: NewsItem; applied?: { chance: number; fpl_chance: number } }) {
  const s = STATUS[item.status];
  return (
    <li className="flex items-start gap-3 py-2.5">
      <span className={`pill mt-0.5 w-[74px] flex-none justify-center ${s.tone}`}>{s.label}</span>
      <div className="min-w-0 flex-1">
        <p className="flex items-center gap-1.5 font-body text-sm text-ink-100">
          <Crest team={item.club} className="h-4 w-4 flex-none" />
          <span className="font-medium">{item.name}</span>
          <span className="ml-1.5 tabular-nums text-[11px] text-ink-500">{item.club}</span>
        </p>
        {item.reason && <p className="mt-0.5 font-body text-[13px] leading-snug text-ink-300">{item.reason}</p>}
        <p className="mt-1 tabular-nums text-[10.5px] text-ink-500">
          {item.source_url ? (
            <a href={item.source_url} target="_blank" rel="noopener noreferrer" className="underline decoration-line-strong underline-offset-2 hover:text-ink-300">
              {item.source_title ?? host(item.source_url)}
            </a>
          ) : (
            "no source"
          )}
          {item.source_date && <> &middot; {item.source_date}</>}
          {applied && (
            <span className="text-warn">
              {" "}
              &middot; projection uses {applied.chance}% to play (FPL said {applied.fpl_chance}%)
            </span>
          )}
        </p>
      </div>
    </li>
  );
}

/** How the reader's calls turned out, scored after each gameweek
 *  (research/2026-10-team-news), drawn as bars. Rotation calls only start
 *  moving projections once enough of them have been checked and right. */
function Record({ record }: { record?: NewsRecord | null }) {
  if (!record) return null;
  const rows: { s: NewsStatus; label: string }[] = [
    { s: "out", label: "Out calls" },
    { s: "doubtful", label: "Doubts" },
    { s: "rotation_risk", label: "Rotation" },
  ];
  const rot = record.by_status.rotation_risk ?? { calls: 0, correct: 0 };
  const bar = record.rotation_bar;
  const rate = rot.calls ? rot.correct / rot.calls : 0;
  const live = rot.calls >= bar.calls && rate >= bar.rate;
  return (
    <div className="mt-6">
      <p className="text-[13px] font-semibold text-ink-200">
        The reader&apos;s record
        {record.gameweeks.length > 0 && <span className="font-normal text-ink-400"> &middot; since GW{record.gameweeks[0]}</span>}
      </p>
      <ul className="mt-2.5 space-y-2.5">
        {rows.map(({ s, label }) => {
          const r = record.by_status[s] ?? { calls: 0, correct: 0 };
          const share = r.calls ? r.correct / r.calls : 0;
          return (
            <li key={s} className="grid grid-cols-[84px_1fr_88px] items-center gap-3 text-[13px]">
              <span className="text-ink-300">{label}</span>
              <span className="relative h-1.5 overflow-hidden rounded-full bg-ink-500/20">
                <span className="absolute inset-y-0 left-0 rounded-full bg-pts" style={{ width: `${share * 100}%` }} />
              </span>
              <span className="text-right tabular-nums text-ink-400">
                {r.calls ? `${r.correct}/${r.calls} right` : "none yet"}
              </span>
            </li>
          );
        })}
      </ul>
      <div className="mt-4">
        <div className="flex justify-between text-[12.5px] text-ink-400">
          <span>Rotation calls checked</span>
          <span className="tabular-nums">
            {rot.calls} of {bar.calls}
          </span>
        </div>
        <span className="relative mt-1.5 block h-1.5 overflow-hidden rounded-full bg-ink-500/20">
          <span
            className="absolute inset-y-0 left-0 rounded-full bg-violet"
            style={{ width: `${Math.min(1, rot.calls / bar.calls) * 100}%` }}
          />
        </span>
        <p className="mt-1.5 text-[12px] leading-relaxed text-ink-500">
          {live
            ? "Reached: rotation calls now move projections."
            : `Rotation calls are shown, not used, until ${bar.calls} have been checked at ${Math.round(bar.rate * 100)}%+ right.`}
        </p>
      </div>
    </div>
  );
}

/** Before the first read of the week: when it happens and what it does. */
function Waiting({ enabled }: { enabled: boolean }) {
  return (
    <div className="flex items-start gap-3.5">
      <span className="grid h-10 w-10 flex-none place-items-center rounded-md bg-ink-100 text-[rgb(var(--c-base))]">
        <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
          <path d="M4 5h13v14a2 2 0 0 0 2 2H6a2 2 0 0 1-2-2z" />
          <path d="M17 9h3v10a2 2 0 0 1-2 2" />
          <path d="M7.5 9h6M7.5 12.5h6M7.5 16h4" />
        </svg>
      </span>
      <div>
        <p className="text-[15px] font-medium text-ink-100">
          {enabled ? "Reads the news 48 hours before the deadline" : "The reader is off"}
        </p>
        <p className="mt-0.5 text-[13px] leading-relaxed text-ink-400">
          {enabled
            ? "Google News and BBC Sport headlines for your clubs, read by a free AI model that has to cite a headline for every call."
            : "It needs a free Gemini key (aistudio.google.com, a project with no billing) saved as the GEMINI_API_KEY secret in the GitHub repo."}
        </p>
      </div>
    </div>
  );
}

export default function TeamNews({ news }: { news?: TeamNewsView }) {
  if (!news) return null;
  if (!news.fetched_at) {
    return (
      <div>
        <Waiting enabled={news.enabled} />
        <Record record={news.record} />
      </div>
    );
  }
  const applied = Object.fromEntries(news.applied.map((a) => [a.player_id, a]));
  const flagged = news.items.filter((i) => i.status === "out" || i.status === "doubtful" || i.status === "rotation_risk");
  const quiet = news.items.filter((i) => !flagged.includes(i));

  return (
    <div>
      <p className="text-[12.5px] text-ink-400">
        <Term explain="The last six days of headlines for each of your clubs (Google News and BBC Sport) are read by a free AI model (Gemini), for your squad, this week's buys and the Wildcard squad. Every call cites one of those headlines. 'Out' and 'doubt' calls worse than FPL's own flag lower the projection as an FPL flag would. 'Rotation' is shown only — line-up predictions are guesses.">
          Headlines read
        </Term>{" "}
        <Ago iso={news.fetched_at} />
        {news.model && <span className="text-ink-500"> by {news.model}</span>}
      </p>
      {flagged.length ? (
        <ul className="mt-1 divide-y divide-line">
          {flagged.map((i) => (
            <Row key={`${i.player_id ?? i.name}-${i.club}`} item={i} applied={i.player_id != null ? applied[i.player_id] : undefined} />
          ))}
        </ul>
      ) : (
        <p className="mt-2 font-body text-sm text-ink-300">No injury, suspension or rotation worries found.</p>
      )}
      {quiet.length > 0 && (
        <details className="mt-2 group">
          <summary className="cursor-pointer tabular-nums text-[11px] text-ink-400 hover:text-ink-200">
            {quiet.length} more: expected to start or no news
          </summary>
          <ul className="mt-1 divide-y divide-line">
            {quiet.map((i) => (
              <Row key={`${i.player_id ?? i.name}-${i.club}`} item={i} />
            ))}
          </ul>
        </details>
      )}
      {!!news.errors && (
        <p className="mt-2 tabular-nums text-[10.5px] text-ink-500">
          {news.errors} club group{news.errors === 1 ? "" : "s"} couldn&apos;t be read this run.
        </p>
      )}
      <Record record={news.record} />
    </div>
  );
}
