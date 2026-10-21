"""
File: team_news.py
Path: var-ified-xi/backend/data_engine/team_news.py

Reads the latest team news before FPL does.

FPL's injury flags are the model's only view of who's fit, and they lag:
they're updated by hand, often hours after a manager's press conference, and
they never say "fit but likely to be benched". This asks an AI model with web
search — Google's Gemini 2.5 Flash with Google Search, free — to read the
news for the clubs that matter to you — your squad, the players the plan
wants to buy, the Wildcard squad — and report each player as out, doubtful,
rotation risk or expected to start, with a source.

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
Google Search grounding is free up to 500 requests a day; a run uses ~4).
Without it, nothing runs and the dashboard says so. Runs only when a deadline
is close (TEAM_NEWS_WINDOW_HOURS) and reuses a fresh result for
TEAM_NEWS_TTL_HOURS.
"""

import json
import logging
import os
import re
import time
import unicodedata
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import quote_plus, urlparse
import xml.etree.ElementTree as ET

import requests

import config

logger = logging.getLogger(__name__)

STATUSES = ("out", "doubtful", "rotation_risk", "expected_to_start", "no_news")
APPLIED = ("out", "doubtful")
CLUBS_PER_CALL = 3


def _now():
    return datetime.now(timezone.utc)


GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


def provider() -> str | None:
    """Which model reads the news: Gemini when its (free) key is set, else none."""
    return "gemini" if os.environ.get("GEMINI_API_KEY") else None


_gemini_model = [None]          # the free model that answered this run


def model_name() -> str | None:
    if provider() == "gemini":
        return _gemini_model[0] or config.TEAM_NEWS_GEMINI_MODELS[0]
    return None


def enabled() -> bool:
    return provider() is not None and config.TEAM_NEWS_ENABLED


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
             "headline id it comes from, and that headline must name the player himself.",
             "A question headline (\"Will X start?\") or a past injury scare he has since played",
             "through is not an injury doubt. But a headline predicting he may be dropped,",
             "benched or rested (\"X could drop out\", \"set to rotate\") IS rotation_risk.",
             "The manager's latest press conference outranks earlier reports.", ""]
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


# Bumped whenever the reading instructions change, so a cached read from the
# old ones isn't reused. 2: headlines must name the player; question
# headlines and past scares aren't doubts (Oct 2026). 3: ...but a predicted
# benching is still rotation_risk — version 2 turned GW7's correct "Cherki
# could drop out" into no_news.
PROMPT_VERSION = 3


def _fold(text: str) -> str:
    """Lower case, accents off: "Sávio" and "Savio" read the same."""
    return "".join(c for c in unicodedata.normalize("NFKD", text.lower())
                   if not unicodedata.combining(c))


def _names_him(title: str, name: str) -> bool:
    """Does the headline name this player? Any part of his name of four
    letters or more ("Mukiele" in "Nordi Mukiele") is enough."""
    words = set(re.findall(r"[a-z]+", _fold(title)))
    return any(len(w) >= 4 and w in words for w in re.findall(r"[a-z]+", _fold(name)))


def _cite(items: list, raw: str, index: dict) -> list:
    """Replace each call's source with the headline it cites; a call citing
    nothing we gave it gets no source, so it can't change a projection.

    The cited headline must also name the player. Oct 2026, GW7: a headline
    about Sunderland's Meunier came back as "Mukiele out", and would have
    zeroed a fit player's projection. A call whose headline is about someone
    else is dropped to no_news."""
    cited = {}
    try:
        for p in _json_from(raw).get("players", []):
            cited[(str(p.get("name", ""))[:40], str(p.get("club", ""))[:30])] = str(p.get("source_id") or "")
    except (ValueError, AttributeError):
        pass
    for it in items:
        h = index.get(cited.get((it["name"], it["club"]), ""))
        if h and it["status"] != "no_news" and not _names_him(h["title"], it["name"]):
            logger.warning("Team news: %s cited a headline that doesn't name him (%r); dropped.",
                           it["name"], h["title"][:80])
            it.update(status="no_news", start_chance=None,
                      reason=f"Cited a headline about someone else: {h['title'][:90]}")
            h = None
        it["source_url"] = h["link"] if h else None
        it["source_date"] = h["when"].date().isoformat() if h else None
        it["source_title"] = h["title"][:140] if h else None
    return items


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
    for i in range(0, len(clubs), CLUBS_PER_CALL):
        chunk = clubs[i:i + CLUBS_PER_CALL]
        try:
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
            time.sleep(5)                                # stay inside the free per-minute limit
        except Exception as e:                       # one club group failing isn't fatal
            errors.append(f"{', '.join(c['club'] for c in chunk)}: {e}")
            logger.warning("Team news for %s failed: %s", [c["club"] for c in chunk], e)
    return {"gameweek": gameweek, "fetched_at": _now().isoformat(), "model": model_name(),
            "prompt_version": PROMPT_VERSION,
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
    # Nor is one read under an older prompt: a prompt fix should act at once.
    fresh = cached and not cached.get("errors") and cached.get("prompt_version") == PROMPT_VERSION and \
        _now() - datetime.fromisoformat(cached["fetched_at"]) < timedelta(hours=config.TEAM_NEWS_TTL_HOURS)
    near = deadline - _now() < timedelta(hours=config.TEAM_NEWS_WINDOW_HOURS)
    if fresh or not (near or force):
        return cached
    logger.info("Reading team news for %d clubs...", len(clubs))
    news = fetch(clubs, gameweek, deadline.isoformat())
    config.TEAM_NEWS_PATH.write_text(json.dumps(news, indent=1))
    _log_calls(news)
    _keep_calls(news)
    return news


def _keep_calls(news: dict) -> None:
    """This gameweek's latest read, in a file that keeps every gameweek: what
    judge() scores once the gameweek is played."""
    path = config.TEAM_NEWS_CALLS_PATH
    try:
        calls = json.loads(path.read_text()) if path.exists() else {}
    except (OSError, json.JSONDecodeError):
        calls = {}
    # The newest read replaces the gameweek's calls: the one in force at the
    # deadline is what gets scored.
    week = calls[str(news["gameweek"])] = {}
    for it in news.get("items", []):
        if it.get("player_id") is not None:
            week[str(it["player_id"])] = {"name": it["name"], "club": it["club"], "status": it["status"],
                                          "chance": it.get("start_chance"), "at": news["fetched_at"]}
    path.write_text(json.dumps(calls, indent=1, ensure_ascii=False))


# How each call is scored against the gameweek's real minutes
# (research/2026-10-team-news/PREREGISTRATION.md).
CORRECT_IF = {
    "out": lambda minutes, starts: minutes == 0,
    "doubtful": lambda minutes, starts: minutes < 60,
    "rotation_risk": lambda minutes, starts: starts == 0,
    "expected_to_start": lambda minutes, starts: starts > 0,
    "no_news": lambda minutes, starts: starts > 0,
}
ROTATION_BAR = {"calls": 30, "rate": 0.60}      # before rotation calls may move a projection


def judge(calls: dict, played, finished_gws: set) -> dict:
    """The reader's record: for every finished gameweek, each player's last
    call against what happened. played: rows with player_id, round, minutes,
    starts (a double gameweek's matches are summed). Only gameweeks FPL marks
    finished count, since a gameweek in progress has zero rows for matches not
    yet played."""
    by_status = {s: {"calls": 0, "correct": 0} for s in STATUSES}
    recent = []
    if played is None or played.empty:
        return {"gameweeks": [], "by_status": by_status, "recent": [], "rotation_bar": ROTATION_BAR}
    real = played.groupby(["player_id", "round"])[["minutes", "starts"]].sum()
    judged = sorted(int(g) for g in calls if int(g) in finished_gws)
    for gw in judged:
        for pid, c in calls[str(gw)].items():
            key = (int(pid), gw)
            if c["status"] not in CORRECT_IF or key not in real.index:
                continue
            minutes, starts = (float(v) for v in real.loc[key])
            ok = bool(CORRECT_IF[c["status"]](minutes, starts))
            by_status[c["status"]]["calls"] += 1
            by_status[c["status"]]["correct"] += int(ok)
            if c["status"] != "no_news":
                recent.append({"gameweek": gw, "name": c["name"], "status": c["status"],
                               "minutes": int(minutes), "started": starts > 0, "correct": ok})
    return {"gameweeks": judged, "by_status": by_status, "recent": recent[-12:],
            "rotation_bar": ROTATION_BAR}


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
    rows, in place, when they're worse than FPL's own flag and recent; "out"
    also marks him injured for the rest of the plan, as an FPL flag would.
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
        # Checked again here so a cached read from before the rule can't act.
        if item.get("source_title") and not _names_him(item["source_title"], item.get("name", "")):
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
        if status == "out" and "status" in predict_df.columns:
            # As FPL's own injury flag does: "out" counts for every week of the
            # plan, not just this one, until a return date says otherwise —
            # otherwise the plan could buy a player who is out for weeks.
            mine = predict_df["player_id"] == pid
            predict_df.loc[mine & predict_df["status"].isin(["a", "d"]), "status"] = "i"
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
