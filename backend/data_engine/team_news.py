"""
File: team_news.py
Path: var-ified-xi/backend/data_engine/team_news.py

Reads the latest team news before FPL does.

FPL's injury flags are the model's only view of who's fit, and they lag:
they're updated by hand, often hours after a manager's press conference, and
they never say "fit but likely to be benched". This asks an AI model with web
search — Google's Gemini 2.5 Flash with Google Search, free, or Claude if
that key is set instead — to read the news for the clubs that matter to you — your squad, the
players the plan wants to buy, the Wildcard squad — and report each player
as out, doubtful, rotation risk or expected to start, with a source.

What it changes, deliberately narrow:
  * "out" and "doubtful" feed the projection the same way an FPL flag would
    (chance of playing 0, or the reported chance), but only when they're
    WORSE than FPL's own flag and come with a source from the last few days.
    That's the information FPL itself would publish a few hours later.
  * "rotation risk" is shown, never applied. Predicted line-ups are guesses,
    and nothing here has been tested against what happened.
There are no archived press conferences to backtest on, so the reader is
judged live: every call it makes is saved with the source, for checking
against who actually played (research/2026-10-team-news).

Needs GEMINI_API_KEY (free from aistudio.google.com: Gemini 2.5 Flash with
Google Search grounding is free up to 500 requests a day; a run uses ~4) or
ANTHROPIC_API_KEY (paid, ~$0.30-1 a run). Without either, nothing runs and
the dashboard says so. Runs only when a deadline is close
(TEAM_NEWS_WINDOW_HOURS) and reuses a fresh result for TEAM_NEWS_TTL_HOURS.
"""

import json
import logging
import os
import re
import time
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import quote_plus, urlparse
import xml.etree.ElementTree as ET

import requests

import config

logger = logging.getLogger(__name__)

API_URL = "https://api.anthropic.com/v1/messages"
STATUSES = ("out", "doubtful", "rotation_risk", "expected_to_start", "no_news")
APPLIED = ("out", "doubtful")
CLUBS_PER_CALL = 3

SYSTEM = """You check Premier League team news for Fantasy Premier League managers.
Use web search to find the most recent news: manager press conferences, club
injury updates, suspensions, and reputable outlets (BBC Sport, Sky Sports, The
Athletic, the Guardian, premierleague.com, club websites). Only use news
published in the last 7 days. Never guess: if you find nothing recent about a
player, his status is "no_news". Statuses:
  out               - ruled out of this match (injury, illness, suspension, not in squad)
  doubtful          - a genuine fitness or availability doubt for this match
  rotation_risk     - fit, but credible reporting says he may be benched or rested
  expected_to_start - fit and expected to start
  no_news           - nothing recent found
Reply with one JSON object in a ```json block and nothing after it."""


def _now():
    return datetime.now(timezone.utc)


GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


def provider() -> str | None:
    """Which model reads the news: Gemini when its (free) key is set, else
    Claude when its key is, else none."""
    if os.environ.get("GEMINI_API_KEY"):
        return "gemini"
    if os.environ.get("ANTHROPIC_API_KEY"):
        return "claude"
    return None


_gemini_model = [None]          # the free model that answered this run


def model_name() -> str | None:
    if provider() == "gemini":
        return _gemini_model[0] or config.TEAM_NEWS_GEMINI_MODELS[0]
    return config.TEAM_NEWS_MODEL if provider() == "claude" else None


def enabled() -> bool:
    return provider() is not None and config.TEAM_NEWS_ENABLED


def _prompt(clubs: list, gameweek: int, deadline: str) -> str:
    lines = [f"Today is {_now():%A %d %B %Y, %H:%M} UTC. Gameweek {gameweek} deadline: {deadline}.",
             "Find the latest team news for each club below, ahead of its match. Report on",
             "every listed player, and add any other player at these clubs who is ruled out.", ""]
    for c in clubs:
        lines.append(f"- {c['club']} ({c['fixture']}):")
        lines += [f"    {p['name']} (id {p['player_id']}, {p['position']})" for p in c["players"]]
    lines += ["", "JSON shape:",
              '{"players": [{"player_id": <id from the list, or null>, "name": "...", "club": "...",',
              '  "status": "out|doubtful|rotation_risk|expected_to_start|no_news",',
              '  "start_chance": <0-100, your estimate he starts>, "reason": "<= 120 chars",',
              '  "source_url": "https://...", "source_date": "YYYY-MM-DD"}]}']
    return "\n".join(lines)


def _host(url: str) -> str:
    try:
        return urlparse(url).netloc.lower().removeprefix("www.")
    except Exception:
        return ""


# ---------------------------------------------------------------------------
# Free path: our own headlines, read by free Gemini (no search tool needed)
# ---------------------------------------------------------------------------
# On Gemini's free tier only the 2.5 models can search Google, and those are
# closed to new projects; the 3.x models are free but can't search. So the
# news is fetched here from free feeds — Google News headlines and BBC Sport's
# club feed — and the model only reads them. Every call it makes has to cite
# one of these headlines, which is what makes it checkable.
NEWS_DAYS = 6
HEADLINES_PER_CLUB = 25
QUERY = '"{club}" (injury OR injured OR "team news" OR fitness OR doubt OR "ruled out" OR suspended OR "press conference") when:{days}d'
FULL_NAME = {"Man City": "Manchester City", "Man Utd": "Manchester United", "Spurs": "Tottenham Hotspur",
             "Nott'm Forest": "Nottingham Forest", "Wolves": "Wolverhampton Wanderers",
             "Brighton": "Brighton & Hove Albion", "Bournemouth": "AFC Bournemouth",
             "Newcastle": "Newcastle United", "West Ham": "West Ham United",
             "Leicester": "Leicester City", "Leeds": "Leeds United", "Ipswich": "Ipswich Town",
             "Coventry": "Coventry City", "Hull": "Hull City", "Sheffield Utd": "Sheffield United"}
_feeds = requests.Session()
_feeds.headers["User-Agent"] = "Mozilla/5.0 (var-ified-xi team news; a few requests a week)"


def _rss(url: str) -> list:
    try:
        r = _feeds.get(url, timeout=30)
        r.raise_for_status()
        root = ET.fromstring(r.content)
    except Exception as e:
        logger.info("News feed unavailable (%s): %s", url[:80], e)
        return []
    out = []
    for it in root.iter("item"):
        try:
            when = parsedate_to_datetime(it.findtext("pubDate") or "")
        except (TypeError, ValueError):
            continue
        out.append({"title": (it.findtext("title") or "").strip(), "link": it.findtext("link"),
                    "source": (it.findtext("source") or "BBC Sport").strip(), "when": when})
    return out


def headlines(club: str) -> list:
    """This club's news from the last NEWS_DAYS days, newest first: Google
    News search for injury/team-news stories, plus BBC Sport's club feed."""
    name = FULL_NAME.get(club, club)
    slug = re.sub(r"[^a-z]+", "-", name.lower().replace("&", "and")).strip("-")
    items = _rss("https://news.google.com/rss/search?q=" + quote_plus(QUERY.format(club=name, days=NEWS_DAYS))
                 + "&hl=en-GB&gl=GB&ceid=GB:en")
    items += _rss(f"https://feeds.bbci.co.uk/sport/football/teams/{slug}/rss.xml")
    cutoff = _now() - timedelta(days=NEWS_DAYS)
    seen, out = set(), []
    for it in sorted(items, key=lambda i: i["when"], reverse=True):
        key = it["title"].lower()[:80]
        if it["when"] >= cutoff and it["link"] and key not in seen:
            seen.add(key)
            out.append(it)
    return out[:HEADLINES_PER_CLUB]


def _prompt_headlines(clubs: list, gameweek: int, deadline: str, numbered: dict) -> str:
    lines = [f"Today is {_now():%A %d %B %Y} UTC. Gameweek {gameweek} deadline: {deadline}.",
             "Below are recent news headlines for each club, then the players to report on.",
             "Use ONLY these headlines — no outside knowledge. Ignore women's, academy and",
             "under-21 teams. Report every listed player; add any other player at these clubs",
             "whom a headline says is ruled out. Each call that isn't no_news must cite the",
             "headline id it comes from.", ""]
    for c in clubs:
        lines.append(f"{c['club']} ({c['fixture']}):")
        for hid, h in numbered.get(c["club"], []):
            lines.append(f"  [{hid}] {h['when']:%d %b} | {h['source']} | {h['title']}")
        if not numbered.get(c["club"]):
            lines.append("  (no recent headlines)")
        lines.append("  Players: " + "; ".join(f"{p['name']} (id {p['player_id']}, {p['position']})"
                                               for p in c["players"]))
        lines.append("")
    lines += ["Statuses: out = ruled out of this match; doubtful = a genuine doubt;",
              "rotation_risk = fit but reported likely to be benched or rested;",
              "expected_to_start = fit and expected to start; no_news = nothing in the headlines.",
              "Return JSON:",
              '{"players": [{"player_id": <id from the list, or null>, "name": "...", "club": "...",',
              '  "status": "...", "start_chance": <0-100>, "reason": "<= 120 chars", "source_id": "<headline id or null>"}]}']
    return "\n".join(lines)


def _call_gemini(prompt: str) -> str:
    """One call to a free Gemini model (no tools). Tries the models in
    config.TEAM_NEWS_GEMINI_MODELS in order — all free-tier text models."""
    body = {"systemInstruction": {"parts": [{"text": "You extract Premier League team news from the "
                                                     "headlines you are given, for FPL managers. "
                                                     "Never guess beyond them."}]},
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.1, "maxOutputTokens": 8192,
                                 "responseMimeType": "application/json"}}
    headers = {"x-goog-api-key": os.environ["GEMINI_API_KEY"], "content-type": "application/json"}
    models = [_gemini_model[0]] if _gemini_model[0] else list(config.TEAM_NEWS_GEMINI_MODELS)
    last = None
    for model in models:
        # Reading headlines needs little reasoning; long "thinking" only makes
        # the free model slow (3.8 Flash thinks at medium unless told).
        think = {**body, "generationConfig": {**body["generationConfig"],
                                              "thinkingConfig": {"thinkingLevel": "low"}}}
        payload = think if "flash-lite" not in model else body
        for attempt in range(3):
            try:
                r = requests.post(GEMINI_URL.format(model=model), headers=headers, json=payload, timeout=300)
            except requests.Timeout:
                last = f"{model}: timed out"
                r = None
                break
            if r.status_code == 429:                   # free tier: a few requests a minute
                time.sleep(30 * (attempt + 1))
                continue
            if r.status_code == 400 and payload is think and "thinking" in r.text.lower():
                payload = body                         # this model won't take the setting
                continue
            break
        if r is None:
            continue
        if r.status_code in (400, 403, 404):
            last = f"{model}: {r.status_code} {r.text[:160]}"
            logger.info("Team news: %s not available to this key, trying the next", model)
            continue
        r.raise_for_status()
        _gemini_model[0] = model
        cand = (r.json().get("candidates") or [{}])[0]
        return "".join(p.get("text", "") for p in cand.get("content", {}).get("parts", []))
    raise RuntimeError(f"team news: no free Gemini model answered ({last})")


def _cite(items: list, raw: str, index: dict) -> list:
    """Replace each call's source with the headline it cites; a call citing
    nothing we gave it gets no source, so it can't change a projection."""
    cited = {}
    try:
        for p in _json_from(raw).get("players", []):
            cited[(str(p.get("name", ""))[:40], str(p.get("club", ""))[:30])] = str(p.get("source_id") or "")
    except (ValueError, AttributeError):
        pass
    for it in items:
        h = index.get(cited.get((it["name"], it["club"]), ""))
        it["source_url"] = h["link"] if h else None
        it["source_date"] = h["when"].date().isoformat() if h else None
        it["source_title"] = h["title"][:140] if h else None
    return items


def _call(prompt: str) -> str:
    """One Messages API call with web search; returns the final text. Follows
    pause_turn (a long search turn the API hands back to be continued)."""
    headers = {"x-api-key": os.environ["ANTHROPIC_API_KEY"], "anthropic-version": "2023-06-01",
               "content-type": "application/json"}
    messages = [{"role": "user", "content": prompt}]
    body = {"model": config.TEAM_NEWS_MODEL, "max_tokens": 4096, "system": SYSTEM,
            "tools": [{"type": "web_search_20260209", "name": "web_search",
                       "max_uses": config.TEAM_NEWS_MAX_SEARCHES}]}
    for _ in range(4):
        r = requests.post(API_URL, headers=headers, json={**body, "messages": messages}, timeout=300)
        r.raise_for_status()
        msg = r.json()
        if msg.get("stop_reason") != "pause_turn":
            return "".join(b.get("text", "") for b in msg["content"] if b.get("type") == "text")
        messages = messages + [{"role": "assistant", "content": msg["content"]}]
    raise RuntimeError("team news: search turn never finished")


def _json_from(text: str) -> dict:
    """The first complete JSON value in a reply (fenced or not); a bare list
    is read as the players."""
    m = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    body = m.group(1) if m else text
    starts = [k for k in (body.find("{"), body.find("[")) if k >= 0]
    if not starts:
        raise ValueError("no JSON in the reply")
    obj, _ = json.JSONDecoder().raw_decode(body[min(starts):])
    return {"players": obj} if isinstance(obj, list) else obj


def parse(text: str, known_ids: set) -> list:
    """The reply's JSON, cleaned: known statuses only, chances clamped, ids
    checked against the players asked about (None if he wasn't on the list)."""
    items = []
    for p in _json_from(text).get("players", []):
        status = str(p.get("status", "")).strip().lower()
        if status not in STATUSES:
            continue
        pid = p.get("player_id")
        try:
            pid = int(pid) if pid is not None else None
        except (TypeError, ValueError):
            pid = None
        try:
            chance = max(0, min(100, int(p.get("start_chance"))))
        except (TypeError, ValueError):
            chance = None
        url = str(p.get("source_url") or "")
        items.append({
            "player_id": pid if pid in known_ids else None,
            "name": str(p.get("name", ""))[:40],
            "club": str(p.get("club", ""))[:30],
            "status": status,
            "start_chance": chance,
            "reason": str(p.get("reason", ""))[:160],
            "source_url": url if url.startswith("http") else None,
            "source_date": str(p.get("source_date") or "")[:10] or None,
        })
    return items


def fetch(clubs: list, gameweek: int, deadline: str) -> dict:
    """clubs: [{"club", "fixture", "players": [{player_id, name, position}]}]."""
    known = {p["player_id"] for c in clubs for p in c["players"]}
    items, errors = [], []
    use = provider()
    for i in range(0, len(clubs), CLUBS_PER_CALL):
        chunk = clubs[i:i + CLUBS_PER_CALL]
        try:
            if use == "gemini":
                numbered, index = {}, {}
                for ci, c in enumerate(chunk):
                    hs = headlines(c["club"])
                    numbered[c["club"]] = [(f"{chr(65 + ci)}{k + 1}", h) for k, h in enumerate(hs)]
                    index.update(dict(numbered[c["club"]]))
                raw = _call_gemini(_prompt_headlines(chunk, gameweek, deadline, numbered))
                try:
                    items += _cite(parse(raw, known), raw, index)
                except ValueError:
                    logger.warning("Team news reply not readable; it began: %r", raw[:300])
                    raise
                time.sleep(5)                            # stay inside the free per-minute limit
            else:
                items += parse(_call(_prompt(chunk, gameweek, deadline)), known)
        except Exception as e:                       # one club group failing isn't fatal
            errors.append(f"{', '.join(c['club'] for c in chunk)}: {e}")
            logger.warning("Team news for %s failed: %s", [c["club"] for c in chunk], e)
    return {"gameweek": gameweek, "fetched_at": _now().isoformat(), "model": model_name(),
            "clubs": [c["club"] for c in clubs], "items": items, "errors": errors}


def load_cached(gameweek: int) -> dict | None:
    path = config.TEAM_NEWS_PATH
    if not path.exists():
        return None
    try:
        news = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return None
    return news if news.get("gameweek") == gameweek else None


def get(clubs: list, gameweek: int, deadline: datetime, force: bool = False) -> dict | None:
    """This gameweek's news: fetched if a deadline is close and the cache is
    stale, else whatever was cached for this gameweek (or None)."""
    cached = load_cached(gameweek)
    if not enabled():
        return cached
    # A result with failed club groups is never reused: the next run retries.
    fresh = cached and not cached.get("errors") and \
        _now() - datetime.fromisoformat(cached["fetched_at"]) < timedelta(hours=config.TEAM_NEWS_TTL_HOURS)
    near = deadline - _now() < timedelta(hours=config.TEAM_NEWS_WINDOW_HOURS)
    if fresh or not (near or force):
        return cached
    logger.info("Reading team news for %d clubs...", len(clubs))
    news = fetch(clubs, gameweek, deadline.isoformat())
    config.TEAM_NEWS_PATH.write_text(json.dumps(news, indent=1))
    _log_calls(news)
    return news


def _log_calls(news: dict) -> None:
    """Every call, kept for the live check against who actually played."""
    path = config.TEAM_NEWS_LOG_PATH
    try:
        log = json.loads(path.read_text()) if path.exists() else []
    except (OSError, json.JSONDecodeError):
        log = []
    log.append({k: news[k] for k in ("gameweek", "fetched_at", "model", "items")})
    path.write_text(json.dumps(log[-60:], indent=1))


def apply(predict_df, news: dict | None, gameweek: int, max_age_days: int = 4) -> list:
    """Out / doubtful calls lower FPL's chance of playing for this gameweek's
    rows, in place, when they're worse than FPL's own flag and recent.
    Returns what was applied, for the dashboard."""
    if not news or not config.TEAM_NEWS_ADJUST or predict_df is None or predict_df.empty:
        return []
    applied = []
    today = _now().date()
    rows_gw = predict_df["gw"] == gameweek if "gw" in predict_df.columns else True
    for item in news.get("items", []):
        pid, status = item.get("player_id"), item.get("status")
        if pid is None or status not in APPLIED or not item.get("source_url"):
            continue
        try:
            age = (today - datetime.fromisoformat(item["source_date"]).date()).days
        except (TypeError, ValueError):
            continue
        if age > max_age_days:
            continue
        chance = 0 if status == "out" else max(25, min(75, item.get("start_chance") or 50))
        mask = (predict_df["player_id"] == pid) & rows_gw
        if not mask.any():
            continue
        fpl = predict_df.loc[mask, "chance_of_playing"].iloc[0]
        fpl_chance = 100 if fpl is None or fpl != fpl else float(fpl)      # NaN -> fit
        if chance >= fpl_chance:
            continue
        predict_df.loc[mask, "chance_of_playing"] = chance
        applied.append({"player_id": pid, "status": status, "chance": chance,
                        "fpl_chance": int(fpl_chance)})
    return applied



if __name__ == "__main__":
    # python -m data_engine.team_news Arsenal Chelsea — reads those clubs now
    # and prints the calls (never the key). Used by .github/workflows/news-check.yml.
    import sys
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    clubs = [{"club": c, "fixture": "next match", "players": []} for c in (sys.argv[1:] or ["Arsenal"])]
    for c in clubs:
        print(f"{c['club']}: {len(headlines(c['club']))} headlines in the last {NEWS_DAYS} days")
    if provider():
        news = fetch(clubs, 0, "next deadline")
        print("model:", news["model"], "| errors:", news["errors"])
        for it in news["items"]:
            print(f"  {it['status']:<18} {it['name']:<22} {it['club']:<16} {it['reason'][:70]}"
                  f"  [{it.get('source_title') or 'no source'}]")
