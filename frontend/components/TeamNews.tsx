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

const STATUS: Record<NewsStatus, { label: string; tone: string }> = {
  out: { label: "Out", tone: "border-risk/40 text-risk" },
  doubtful: { label: "Doubt", tone: "border-warn/40 text-warn" },
  rotation_risk: { label: "Rotation", tone: "border-gold/40 text-gold" },
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
        <p className="font-body text-sm text-ink-100">
          <span className="font-medium">{item.name}</span>
          <span className="ml-1.5 font-mono text-[11px] text-ink-500">{item.club}</span>
        </p>
        {item.reason && <p className="mt-0.5 font-body text-[13px] leading-snug text-ink-300">{item.reason}</p>}
        <p className="mt-1 font-mono text-[10.5px] text-ink-500">
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
 *  (research/2026-10-team-news). Rotation calls only start moving
 *  projections once enough of them have been checked and right. */
function Record({ record }: { record?: NewsRecord | null }) {
  if (!record) return null;
  if (record.gameweeks.length === 0) {
    return (
      <p className="mt-2 border-t border-line pt-2 font-mono text-[10.5px] text-ink-500">
        Record: every call is scored against who actually played once the gameweek ends.
      </p>
    );
  }
  const part = (s: NewsStatus, label: string) => {
    const r = record.by_status[s];
    return r && r.calls > 0 ? `${label} ${r.correct}/${r.calls} right` : null;
  };
  const parts = [part("out", "out"), part("doubtful", "doubt"), part("rotation_risk", "rotation")].filter(Boolean);
  const rot = record.by_status.rotation_risk;
  const bar = record.rotation_bar;
  const rate = rot.calls ? rot.correct / rot.calls : 0;
  const live = rot.calls >= bar.calls && rate >= bar.rate;
  return (
    <div className="mt-2 border-t border-line pt-2 font-mono text-[10.5px] text-ink-500">
      <p>
        Record since GW{record.gameweeks[0]}:{" "}
        {parts.length ? parts.join(" · ") : "no out, doubt or rotation calls checked yet"}
      </p>
      <p className="mt-0.5">
        Rotation calls can start moving projections only once {bar.calls} have been checked at{" "}
        {Math.round(bar.rate * 100)}%+ right
        {live ? " — reached." : ` — ${rot.calls} checked so far${rot.calls ? `, ${Math.round(rate * 100)}% right` : ""}.`}
      </p>
    </div>
  );
}

export default function TeamNews({ news }: { news?: TeamNewsView }) {
  if (!news) return null;
  if (!news.fetched_at) {
    return (
      <div>
        <p className="font-mono text-[11px] text-ink-500">
          Team news reader:{" "}
          {news.enabled
            ? "reads the news within 48 hours of the deadline."
            : "off. It needs a free Gemini key (aistudio.google.com, a project with no billing) saved as the GEMINI_API_KEY secret in the GitHub repo."}
        </p>
        <Record record={news.record} />
      </div>
    );
  }
  const applied = Object.fromEntries(news.applied.map((a) => [a.player_id, a]));
  const flagged = news.items.filter((i) => i.status === "out" || i.status === "doubtful" || i.status === "rotation_risk");
  const quiet = news.items.filter((i) => !flagged.includes(i));

  return (
    <div className="rounded-[2px] border border-line bg-surface-raised/50 p-3.5">
      <p className="label">
        <Term explain="The last six days of headlines for each of your clubs (Google News and BBC Sport) are read by a free AI model (Gemini), for your squad, this week's buys and the Wildcard squad. Every call cites one of those headlines. 'Out' and 'doubt' calls worse than FPL's own flag lower the projection as an FPL flag would. 'Rotation' is shown only — line-up predictions are guesses.">
          Team news
        </Term>{" "}
        &mdash; read <Ago iso={news.fetched_at} />
        {news.model && <span className="normal-case tracking-normal text-ink-500"> by {news.model}</span>}
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
          <summary className="cursor-pointer font-mono text-[11px] text-ink-400 hover:text-ink-200">
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
        <p className="mt-2 font-mono text-[10.5px] text-ink-500">
          {news.errors} club group{news.errors === 1 ? "" : "s"} couldn&apos;t be read this run.
        </p>
      )}
      <Record record={news.record} />
    </div>
  );
}
