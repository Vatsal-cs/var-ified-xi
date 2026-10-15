// File: TeamNews.tsx
// Path: var-ified-xi/frontend/components/TeamNews.tsx
//
// What the team-news reader (backend team_news.py) found for the players in
// this decision, worst first, each with its source. "Out" and "doubtful"
// calls worse than FPL's own flag have already lowered the projection; those
// are marked. Rotation risk is information only.

import type { NewsItem, NewsStatus, TeamNewsView } from "@/lib/types";
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
              {host(item.source_url)}
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

export default function TeamNews({ news }: { news?: TeamNewsView }) {
  if (!news) return null;
  if (!news.fetched_at) {
    return (
      <p className="font-mono text-[11px] text-ink-500">
        Team news reader:{" "}
        {news.enabled
          ? "reads the news within 48 hours of the deadline."
          : "off. It needs an ANTHROPIC_API_KEY secret in the GitHub repo."}
      </p>
    );
  }
  const applied = Object.fromEntries(news.applied.map((a) => [a.player_id, a]));
  const flagged = news.items.filter((i) => i.status === "out" || i.status === "doubtful" || i.status === "rotation_risk");
  const quiet = news.items.filter((i) => !flagged.includes(i));

  return (
    <div className="rounded-[2px] border border-line bg-surface-raised/50 p-3.5">
      <p className="label">
        <Term explain="Claude, with web search, reads press conferences and club news for your squad, this week's buys and the Wildcard squad. 'Out' and 'doubt' calls worse than FPL's own flag lower the projection, as an FPL flag would. 'Rotation' is shown only — line-up predictions are guesses.">
          Team news
        </Term>{" "}
        &mdash; read <Ago iso={news.fetched_at} />
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
    </div>
  );
}
