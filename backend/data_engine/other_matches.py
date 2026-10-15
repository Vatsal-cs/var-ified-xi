"""
File: other_matches.py
Path: var-ified-xi/backend/data_engine/other_matches.py

Every match a Premier League player plays that FPL doesn't show.

FPL's data is Premier League only, so the model can't see a Champions League
game on Wednesday, a League Cup tie, or a player flying to South America for
two World Cup qualifiers. All of those decide who's tired or rested on
Saturday. This reads them from ESPN's public JSON feed (unofficial: no key,
so it's cached on disk and asked politely):

  * club matches — Champions League, Europa League, Conference League, League
    Cup, FA Cup — for every Premier League club, with each player's role:
    started, came on, or unused;
  * international matches — friendlies, Nations League, every World Cup
    qualifying zone, AFCON and its qualifiers, the Asian Cup, CONCACAF Nations
    League — with the same roles, and where each was played.

ESPN players are linked to FPL players by name within each club's season
squad, so a common name at another club can't be mistaken for yours.

attach() turns this into inputs on each Premier League match row: rest since
the team's last other match, the next one coming, whether the player started
it, and his international load in the fortnight before. Used by the model
since it passed its test (config.OTHER_MATCHES, research/2026-10-other-matches).
"""

import argparse
import gzip
import json
import logging
import re
import threading
import time
import unicodedata
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import requests

import config

logger = logging.getLogger(__name__)

ESPN = "https://site.api.espn.com/apis/site/v2/sports/soccer"
CACHE = config.RAW_DIR / "espn"
CLUB_LEAGUES = ["uefa.champions", "uefa.europa", "uefa.europa.conf", "eng.league_cup", "eng.fa"]
INTL_LEAGUES = ["fifa.friendly", "uefa.nations", "fifa.worldq.uefa", "fifa.worldq.conmebol",
                "fifa.worldq.concacaf", "fifa.worldq.caf", "fifa.worldq.afc", "fifa.worldq.ofc",
                "caf.nations_qual", "caf.nations", "afc.asian.cup", "concacaf.nations.league",
                "uefa.euroq"]
LEAGUE_LABEL = {"uefa.champions": "Champions League", "uefa.europa": "Europa League",
                "uefa.europa.conf": "Conference League", "eng.league_cup": "League Cup",
                "eng.fa": "FA Cup", "fifa.friendly": "Friendly", "uefa.nations": "Nations League",
                "fifa.worldq.uefa": "World Cup qualifier", "fifa.worldq.conmebol": "World Cup qualifier",
                "fifa.worldq.concacaf": "World Cup qualifier", "fifa.worldq.caf": "World Cup qualifier",
                "fifa.worldq.afc": "World Cup qualifier", "fifa.worldq.ofc": "World Cup qualifier",
                "caf.nations_qual": "AFCON qualifier", "caf.nations": "AFCON",
                "afc.asian.cup": "Asian Cup", "concacaf.nations.league": "CONCACAF Nations League",
                "uefa.euroq": "Euro qualifier"}
# ESPN's nationality vs its national-team names, where they differ.
NATION_ALIAS = {"Ireland": "Republic of Ireland", "United States": "USA", "Korea Republic": "South Korea",
                "Côte d'Ivoire": "Ivory Coast", "Czech Republic": "Czechia", "Turkey": "Türkiye",
                "DR Congo": "Congo DR", "Cape Verde Islands": "Cape Verde"}
EUROPE = {"England", "Scotland", "Wales", "Northern Ireland", "Republic of Ireland", "Ireland",
          "France", "Spain", "Portugal", "Germany", "Italy", "Netherlands", "Belgium",
          "Luxembourg", "Switzerland", "Austria", "Denmark", "Norway", "Sweden", "Finland",
          "Iceland", "Poland", "Czechia", "Czech Republic", "Slovakia", "Hungary", "Slovenia",
          "Croatia", "Serbia", "Bosnia and Herzegovina", "Bosnia-Herzegovina", "Montenegro",
          "North Macedonia", "Albania", "Kosovo", "Greece", "Bulgaria", "Romania", "Moldova",
          "Ukraine", "Belarus", "Lithuania", "Latvia", "Estonia", "Malta", "Cyprus", "Andorra",
          "San Marino", "Liechtenstein", "Monaco", "Gibraltar", "Faroe Islands", "Georgia",
          "Armenia", "Azerbaijan", "Turkey", "Türkiye", "Israel", "Kazakhstan"}

# FPL's club names -> ESPN's.
FPL_TO_ESPN = {"Man City": "Manchester City", "Man Utd": "Manchester United",
               "Spurs": "Tottenham Hotspur", "Nott'm Forest": "Nottingham Forest",
               "Wolves": "Wolverhampton Wanderers", "Brighton": "Brighton & Hove Albion",
               "Bournemouth": "AFC Bournemouth", "Newcastle": "Newcastle United",
               "West Ham": "West Ham United", "Leicester": "Leicester City",
               "Leeds": "Leeds United", "Luton": "Luton Town", "Sheffield Utd": "Sheffield United",
               "Ipswich": "Ipswich Town", "Coventry": "Coventry City", "Hull": "Hull City"}

NEUTRAL = {"xm_days_before": 14.0, "xm_days_after": 14.0, "xm_count_14": 0.0,
           "xm_started_before": 0.0, "xm_rested_before": 0.0,
           "intl_apps_14": 0.0, "intl_starts_14": 0.0, "intl_far_14": 0.0,
           "intl_days_before": 21.0,
           "xm_apps_30": 0.0, "xm_ga_30": 0.0, "xm_shots_30": 0.0, "xm_sot_30": 0.0,
           "xm_ga_adj_30": 0.0, "xm_shots_adj_30": 0.0, "xm_opp_30": 1.0}
# Rest and load: who is tired or rested. The shipped inputs (config).
LOAD_FEATURES = list(config.OTHER_MATCH_COLUMNS)
# Form in those games: appearances, goals + assists, shots, shots on target
# across cup, European and international matches in the 30 days before.
FORM_FEATURES = ["xm_apps_30", "xm_ga_30", "xm_shots_30", "xm_sot_30"]
# The same, weighted by how strong each opponent was (strength_factor): a
# goal against San Marino or a League Two side counts for much less than one
# against Bayern. xm_opp_30 is the average weight of the opponents faced.
FORM_ADJ_FEATURES = ["xm_apps_30", "xm_ga_adj_30", "xm_shots_adj_30", "xm_opp_30"]
FEATURES = LOAD_FEATURES + FORM_FEATURES + [c for c in FORM_ADJ_FEATURES if c not in FORM_FEATURES]

_session = requests.Session()
_session.headers["User-Agent"] = "Mozilla/5.0 (var-ified-xi; cached, low volume)"
_lock = threading.Lock()
_last_request = [0.0]
MIN_INTERVAL = 0.35          # seconds between requests, across all threads


def _fetch(url: str, text: bool = False):
    """One request, spaced from every other one; ESPN refuses bursts (403),
    so a refusal waits and tries again. Raises if it never gets through —
    a silently missing month would read as "no matches"."""
    for attempt in range(6):
        with _lock:
            wait = _last_request[0] + MIN_INTERVAL - time.time()
            if wait > 0:
                time.sleep(wait)
            _last_request[0] = time.time()
        try:
            r = _session.get(url, timeout=30)
            if r.status_code in (403, 429):
                time.sleep(15 * (attempt + 1))
                continue
            r.raise_for_status()
            if text:
                r.encoding = "utf-8"
                return r.text
            return r.json()
        except requests.RequestException:
            time.sleep(3 * (attempt + 1))
    raise RuntimeError(f"ESPN unavailable: {url}")


PACK_DIR = config.DATA_DIR / "other_matches"
_packs = None


def _packed(name: str):
    """A finished season's data, committed to the repo (pack()), so a fresh
    checkout — the cloud refresh — never has to fetch past seasons."""
    global _packs
    if _packs is None:
        _packs = {}
        for f in sorted(PACK_DIR.glob("*.json.gz")):
            _packs.update(json.loads(gzip.decompress(f.read_bytes())))
    return _packs.get(name)


def _cached(name: str, url: str, process, max_age_hours: float = None, text: bool = False):
    """process(raw JSON) -> the few fields used, cached on disk. A finished
    month or match never changes, so it's cached for good."""
    path = CACHE / f"{name}.json"
    if path.exists() and (max_age_hours is None
                          or time.time() - path.stat().st_mtime < max_age_hours * 3600):
        return json.loads(path.read_text())
    if not path.exists():
        hit = _packed(name)
        if hit is not None:
            return hit
    out = process(_fetch(url, text))
    CACHE.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out))
    return out


def season_months(season: str) -> list:
    start = int(season[:4])
    return [f"{start}{m:02d}" for m in range(7, 13)] + [f"{start + 1}{m:02d}" for m in range(1, 6)]


def _month_is_past(month: str) -> bool:
    y, m = int(month[:4]), int(month[4:])
    now = datetime.now(timezone.utc)
    return (y, m) < (now.year, now.month)


def _events_from(data) -> list:
    out = []
    for e in (data or {}).get("events", []):
        c = (e.get("competitions") or [{}])[0]
        out.append({
            "id": e["id"], "date": e["date"],
            "teams": [[x["team"]["displayName"], x["team"].get("id"), x.get("homeAway")]
                      for x in c.get("competitors", [])],
            "finished": bool(e.get("status", {}).get("type", {}).get("completed")),
            "venue_country": (c.get("venue") or {}).get("address", {}).get("country"),
        })
    return out


def events(league: str, month: str) -> list:
    """[{id, league, date, teams: [[name, espn_id]], finished, venue_country}] for one month."""
    rows = _cached(f"e_{league}_{month}", f"{ESPN}/{league}/scoreboard?dates={month}&limit=500",
                   _events_from, None if _month_is_past(month) else 6)
    return [{**r, "league": league, "date": pd.Timestamp(r["date"]).tz_convert(None)} for r in rows]


STATS = {"totalGoals": "goals", "goalAssists": "assists", "totalShots": "shots",
         "shotsOnTarget": "sot"}


def _lineup_from(data) -> list:
    out = []
    for team in (data or {}).get("rosters", []):
        tname = team.get("team", {}).get("displayName")
        for a in team.get("roster", []):
            role = "start" if a.get("starter") else ("sub" if a.get("subbedIn") else "unused")
            row = {"team": tname, "athlete_id": str(a.get("athlete", {}).get("id")),
                   "name": a.get("athlete", {}).get("displayName", ""), "role": role}
            for st in a.get("stats", []):
                if st.get("name") in STATS:
                    try:
                        row[STATS[st["name"]]] = float(st.get("value", st.get("displayValue")) or 0)
                    except (TypeError, ValueError):
                        pass
            out.append(row)
    return out


def lineup(league: str, event_id: str) -> list:
    """[{team, athlete_id, name, role, goals, assists, shots, sot}] for a
    finished match; role is start / sub / unused."""
    return _cached(f"m_{league}_{event_id}", f"{ESPN}/{league}/summary?event={event_id}", _lineup_from)


def _parallel(fn, args: list, workers: int = 4) -> list:
    with ThreadPoolExecutor(max_workers=workers) as pool:
        return list(pool.map(lambda a: fn(*a), args))


# ---------------------------------------------------------------------------
# Linking ESPN players to FPL players
# ---------------------------------------------------------------------------
_LETTERS = str.maketrans({"ł": "l", "Ł": "L", "ø": "o", "Ø": "O", "æ": "ae", "Æ": "AE",
                          "ß": "ss", "đ": "d", "Đ": "D", "þ": "th", "ı": "i"})


def _norm(name: str) -> list:
    s = unicodedata.normalize("NFKD", str(name).translate(_LETTERS)).encode("ascii", "ignore").decode().lower()
    return [t for t in re.sub(r"[^a-z ]", " ", s).split() if t not in {"de", "da", "dos", "van", "der", "jr"}]


def _score(a: list, b: list) -> float:
    sa, sb = set(a), set(b)
    if not sa or not sb:
        return 0.0
    if sa == sb:
        return 1.0
    inter = len(sa & sb)
    if inter == 0:
        return 0.0
    # a shorter name fully inside a longer one ("Gabriel Magalhaes" in
    # "Gabriel dos Santos Magalhaes") is nearly as good as equal
    if sa <= sb or sb <= sa:
        return 0.9
    return inter / len(sa | sb)


def pl_team_ids(season: str) -> dict:
    """{ESPN club name: ESPN team id} for the Premier League that season,
    read from its fixtures."""
    ids = {}
    for month in season_months(season):
        for e in events("eng.1", month):
            for name, tid, *_ in e["teams"]:
                ids[name] = tid
    return ids


def _squad_from(data) -> list:
    return [[str(a["id"]), a.get("fullName") or a.get("displayName", ""), a.get("citizenship")]
            for a in (data or {}).get("athletes", [])]


def squads(season: str, team_ids: dict) -> dict:
    """{ESPN club name: [(athlete_id, name tokens, nationality)]} for one season."""
    year = season[:4]
    current = not _month_is_past(f"{int(year) + 1}06")
    def one(name, tid):
        rows = _cached(f"s_{tid}_{year}", f"{ESPN}/eng.1/teams/{tid}/roster?season={year}",
                       _squad_from, 24 if current else None)
        return name, [(aid, _norm(n), nat) for aid, n, nat in rows]
    return dict(_parallel(one, list(team_ids.items())))


def link_players(players: pd.DataFrame, season_squads: dict) -> dict:
    """players: [player_id, name, club (FPL name)] -> {player_id: ESPN athlete id}.
    Matched inside the player's own club first, then across the league only
    when the name is unique there."""
    everyone = [(aid, toks, club) for club, sq in season_squads.items() for aid, toks, _ in sq]
    out = {}
    for pid, name, club in players[["player_id", "name", "club"]].itertuples(index=False):
        toks = _norm(name)
        espn_club = FPL_TO_ESPN.get(club, club)
        squad = season_squads.get(espn_club, [])
        best = sorted(((_score(toks, t), aid) for aid, t, _ in squad), reverse=True)
        if best and best[0][0] >= 0.6 and (len(best) == 1 or best[0][0] > best[1][0]):
            out[int(pid)] = best[0][1]
            continue
        # "Andrew Robertson" / "Andy Robertson": the same surname, and nobody
        # else at the club has it
        if toks:
            same = [aid for aid, t, _ in squad if t and t[-1] == toks[-1]]
            if len(same) == 1:
                out[int(pid)] = same[0]
                continue
        exact = [aid for aid, t, _ in everyone if _score(toks, t) == 1.0]
        if len(exact) == 1:
            out[int(pid)] = exact[0]
    return out


# ---------------------------------------------------------------------------
# One season's other matches
# ---------------------------------------------------------------------------
def season_tables(season: str, pl_clubs: list) -> tuple:
    """(club_matches, appearances) for a season.

    club_matches: one row per (PL club, other match): club (ESPN name), date,
    league, finished.
    appearances: one row per (ESPN athlete, match) for club AND international
    matches: athlete_id, date, kind (club/intl), role, far (international
    played outside Europe)."""
    months = season_months(season)
    clubs = {FPL_TO_ESPN.get(c, c) for c in pl_clubs}
    club_ev = [e for evs in _parallel(events, [(lg, m) for lg in CLUB_LEAGUES for m in months])
               for e in evs if any(n in clubs for n, *_ in e["teams"])]
    intl_ev = [e for evs in _parallel(events, [(lg, m) for lg in INTL_LEAGUES for m in months])
               for e in evs]
    club_rows = [{"club": n, "date": e["date"], "league": e["league"], "finished": e["finished"],
                  "event_id": e["id"]} for e in club_ev for n, *_ in e["teams"] if n in clubs]
    done = [e for e in club_ev + intl_ev if e["finished"]]
    lineups = _parallel(lineup, [(e["league"], e["id"]) for e in done])
    ratings = club_ratings(season)
    apps = []
    for e, lu in zip(done, lineups):
        kind = "intl" if e["league"] in INTL_LEAGUES else "club"
        far = kind == "intl" and bool(e["venue_country"]) and e["venue_country"] not in EUROPE
        names = [t[0] for t in e["teams"]]
        factor = {}
        for side in names:
            opp = next((n for n in names if n != side), None)
            rating = (nation_rating(opp, e["date"]) if kind == "intl"
                      else ratings.get(str(e["id"]), {}).get(opp))
            factor[side] = strength_factor(rating, kind) if opp else 1.0
        for a in lu:
            if kind == "club" and a["team"] not in clubs:
                continue
            apps.append({"athlete_id": a["athlete_id"], "date": e["date"], "kind": kind,
                         "role": a["role"], "far": far, "league": e["league"],
                         "opp_factor": factor.get(a["team"], 1.0),
                         **{k: a.get(k, 0.0) for k in STATS.values()}})
    return pd.DataFrame(club_rows), pd.DataFrame(apps)


# ---------------------------------------------------------------------------
# How strong the opponent was
# ---------------------------------------------------------------------------
# Goals against San Marino or a League Two side say little about a player;
# against Bayern they say a lot. Clubs get an Elo rating built from every
# Champions/Europa/Conference League and English cup result since 2022
# (ClubElo's feed was down when this was written); national teams get
# eloratings.net's rating from the end of the previous year. Ratings are
# always the ones held BEFORE the match.
ELO_START = {"uefa.champions": 1700.0, "uefa.europa": 1550.0, "uefa.europa.conf": 1400.0}
ELO_PL, ELO_LOWER = 1650.0, 1350.0          # English clubs first seen in a cup tie
ELO_K, ELO_HOME = 20.0, 60.0
CLUB_REF, NATION_REF = 1650.0, 1800.0      # rating that counts as "Premier League standard"
FIRST_SEASON = "2022-23"


def _results_from(data) -> list:
    out = []
    for e in (data or {}).get("events", []):
        c = (e.get("competitions") or [{}])[0]
        if not e.get("status", {}).get("type", {}).get("completed"):
            continue
        teams = {x.get("homeAway"): (x["team"]["displayName"], x.get("score")) for x in c.get("competitors", [])}
        if "home" in teams and "away" in teams:
            out.append([e["id"], e["date"], teams["home"][0], teams["away"][0],
                        teams["home"][1], teams["away"][1], bool(c.get("neutralSite"))])
    return out


def results(league: str, month: str) -> list:
    return _cached(f"r_{league}_{month}", f"{ESPN}/{league}/scoreboard?dates={month}&limit=500",
                   _results_from, None if _month_is_past(month) else 6)


def _seasons_until(season: str) -> list:
    first, last = int(FIRST_SEASON[:4]), int(season[:4])
    return [f"{y}-{str(y + 1)[2:]}" for y in range(first, last + 1)]


_club_cache = {}


def club_ratings(season: str) -> dict:
    """{event id: {club: pre-match rating}} for every club match from 2022-23
    up to the end of `season`."""
    if season in _club_cache:
        return _club_cache[season]
    seasons = _seasons_until(season)
    pl = {n for s in seasons for n in pl_team_ids(s)}
    jobs = [(lg, m) for s in seasons for m in season_months(s) for lg in CLUB_LEAGUES]
    games = []
    for (lg, _), rows in zip(jobs, _parallel(results, jobs)):
        games += [(pd.Timestamp(r[1]), lg, *r) for r in rows]
    games.sort(key=lambda g: g[0])
    elo, out = {}, {}
    def start(club, lg):
        return ELO_START.get(lg) or (ELO_PL if club in pl else ELO_LOWER)
    for _, lg, eid, _, home, away, hs, as_, neutral in games:
        try:
            hs, as_ = float(hs), float(as_)
        except (TypeError, ValueError):
            continue
        rh, ra = elo.get(home, start(home, lg)), elo.get(away, start(away, lg))
        out[str(eid)] = {home: rh, away: ra}
        exp = 1 / (1 + 10 ** ((ra - rh - (0 if neutral else ELO_HOME)) / 400))
        res = 1.0 if hs > as_ else 0.5 if hs == as_ else 0.0
        n = abs(hs - as_)
        g = 1 if n <= 1 else 1.5 if n == 2 else (11 + n) / 8
        delta = ELO_K * g * (res - exp)
        elo[home], elo[away] = rh + delta, ra - delta
    _club_cache[season] = out
    return out


_nation_cache = {}


def nation_ratings() -> dict:
    """{(normalised country name, year): rating at the END of that year}."""
    if _nation_cache:
        return _nation_cache
    names = {}
    for line in (_cached("elo_teams", "https://www.eloratings.net/en.teams.tsv",
                         lambda d: d, None, text=True) or "").splitlines():
        parts = line.split("\t")
        if len(parts) >= 2 and not parts[0].endswith("_loc"):
            names[parts[0]] = parts[1:]                    # every spelling eloratings uses
    this_year = datetime.now(timezone.utc).year
    for year in range(int(FIRST_SEASON[:4]) - 1, this_year):
        text = _cached(f"elo_{year}", f"https://www.eloratings.net/{year}.tsv", lambda d: d, None,
                       text=True) or ""
        for line in text.splitlines():
            parts = line.split("\t")
            if len(parts) > 3 and parts[2] in names:
                try:
                    rating = float(parts[3])
                except ValueError:
                    continue
                for n in names[parts[2]]:
                    _nation_cache[(" ".join(_norm(n)), year)] = rating
    return _nation_cache


# ESPN's national-team names -> eloratings'.
ELO_NAMES = {"USA": "United States", "Türkiye": "Turkey", "Republic of Ireland": "Ireland",
             "Bosnia-Herzegovina": "Bosnia and Herzegovina", "Congo DR": "DR Congo",
             "Kyrgyz Republic": "Kyrgyzstan", "St. Kitts and Nevis": "Saint Kitts and Nevis",
             "St. Lucia": "Saint Lucia", "St. Vincent and the Grenadines": "Saint Vincent and the Grenadines",
             "Chinese Taipei": "Taiwan", "Timor-Leste": "East Timor", "Brunei Darussalam": "Brunei",
             "Korea Republic": "South Korea", "China PR": "China", "St. Martin": "Saint Martin"}


def nation_rating(name: str, date) -> float | None:
    """eloratings' rating at the end of the year before the match."""
    r = nation_ratings()
    for n in (ELO_NAMES.get(name, name), name):
        key = " ".join(_norm(n))
        for y in (date.year - 1, date.year - 2):
            if (key, y) in r:
                return r[(key, y)]
    return None


def strength_factor(rating: float | None, kind: str) -> float:
    """How much an output counts against this opponent, relative to Premier
    League standard: 1 at the reference rating, ~0.3 against a side 400
    points weaker, capped to [0.2, 1.5]."""
    if rating is None:
        return 1.0
    ref = NATION_REF if kind == "intl" else CLUB_REF
    return float(min(1.5, max(0.2, 10 ** ((rating - ref) / 800))))


# ---------------------------------------------------------------------------
# Inputs on Premier League match rows
# ---------------------------------------------------------------------------
def _naive(ts) -> pd.Series:
    ts = pd.to_datetime(ts)
    if getattr(ts.dt, "tz", None) is not None:
        ts = ts.dt.tz_convert(None)
    return ts


def features(rows: pd.DataFrame, club_matches: pd.DataFrame, apps: pd.DataFrame,
             espn_id: dict) -> pd.DataFrame:
    """rows: one per (player, PL match) with player_id, club (FPL name) and
    kickoff_time. Returns FEATURES aligned to rows. Only things known before
    kick-off: past matches, and the fixture list ahead."""
    out = pd.DataFrame({k: v for k, v in NEUTRAL.items()}, index=rows.index)
    kick = _naive(rows["kickoff_time"]).to_numpy("datetime64[ns]")
    gap = np.timedelta64(3, "h")
    day = np.timedelta64(1, "D")
    aid = rows["player_id"].map(lambda p: espn_id.get(int(p))).to_numpy(object)

    starts = set()
    if not apps.empty:
        club_starts = apps[(apps["kind"] == "club") & (apps["role"] == "start")]
        starts = set(zip(club_starts["athlete_id"], _naive(club_starts["date"]).dt.normalize()))

    if not club_matches.empty:
        cm = club_matches.assign(club_fpl=club_matches["club"].map(
            {v: k for k, v in FPL_TO_ESPN.items()}).fillna(club_matches["club"]))
        for club, g in cm.groupby("club_fpl"):
            m = (rows["club"] == club).to_numpy()
            if not m.any():
                continue
            g = g.assign(date=_naive(g["date"])).sort_values("date")
            D = g["date"].to_numpy("datetime64[ns]")
            done = g["finished"].to_numpy(bool)
            K = kick[m]
            ib = np.searchsorted(D, K - gap, side="left") - 1          # last match before
            ia = np.searchsorted(D, K + gap, side="right")             # first match after
            i14 = np.searchsorted(D, K - 14 * day, side="right")
            has_b, has_a = ib >= 0, ia < len(D)
            last = np.where(has_b, D[np.clip(ib, 0, None)], np.datetime64("NaT"))
            db = np.where(has_b, (K - last) / day, 14.0)
            da = np.where(has_a, (D[np.clip(ia, None, len(D) - 1)] - K) / day, 14.0)
            out.loc[m, "xm_days_before"] = np.minimum(14.0, db)
            out.loc[m, "xm_days_after"] = np.minimum(14.0, da)
            out.loc[m, "xm_count_14"] = np.where(has_b, ib + 1 - i14, 0).clip(0)
            # Who started it is only known once it's been played; a midweek
            # game still ahead of the deadline says nothing about the player.
            recent = has_b & (db <= 7) & done[np.clip(ib, 0, None)]
            ids = aid[m]
            st = np.array([a is not None and (a, pd.Timestamp(l).normalize()) in starts if r else False
                           for a, l, r in zip(ids, last, recent)])
            linked = np.array([a is not None for a in ids])
            out.loc[m, "xm_started_before"] = np.where(recent & linked, st, 0.0).astype(float)
            out.loc[m, "xm_rested_before"] = np.where(recent & linked, ~st, 0.0).astype(float)

    if not apps.empty:
        played = apps[apps["role"] != "unused"].copy()
        if "opp_factor" not in played.columns:
            played["opp_factor"] = 1.0
        played["ga"] = played["goals"].fillna(0) + played["assists"].fillna(0)
        for a, g in played.groupby("athlete_id"):
            m = aid == a
            if not m.any():
                continue
            g = g.assign(date=_naive(g["date"])).sort_values("date")
            D = g["date"].to_numpy("datetime64[ns]")
            K = kick[m]
            hi = np.searchsorted(D, K - gap, side="left")
            lo = np.searchsorted(D, K - 30 * day, side="right")
            n = (hi - lo).clip(0)
            out.loc[m, "xm_apps_30"] = n.astype(float)
            g = g.assign(ga_adj=g["ga"] * g["opp_factor"], shots_adj=g["shots"].fillna(0) * g["opp_factor"])
            fsum = g["opp_factor"].to_numpy(float).cumsum()
            at_f = lambda i: np.where(i > 0, fsum[np.clip(i - 1, 0, None)], 0.0)
            out.loc[m, "xm_opp_30"] = np.where(n > 0, (at_f(hi) - at_f(lo)) / np.maximum(n, 1), 1.0)
            for col, src in (("xm_ga_30", "ga"), ("xm_shots_30", "shots"), ("xm_sot_30", "sot"),
                             ("xm_ga_adj_30", "ga_adj"), ("xm_shots_adj_30", "shots_adj")):
                c = g[src].fillna(0).to_numpy(float).cumsum()
                at = lambda i: np.where(i > 0, c[np.clip(i - 1, 0, None)], 0.0)
                out.loc[m, col] = (at(hi) - at(lo)).clip(0)

        intl = apps[(apps["kind"] == "intl") & (apps["role"] != "unused")]
        for a, g in intl.groupby("athlete_id"):
            m = aid == a
            if not m.any():
                continue
            g = g.assign(date=_naive(g["date"])).sort_values("date")
            D = g["date"].to_numpy("datetime64[ns]")
            S = (g["role"] == "start").to_numpy().astype(int).cumsum()
            F = g["far"].to_numpy().astype(int).cumsum()
            K = kick[m]
            hi = np.searchsorted(D, K - gap, side="left")             # matches strictly before
            lo = np.searchsorted(D, K - 14 * day, side="right")
            n = (hi - lo).clip(0)
            cs = lambda c, i: np.where(i > 0, c[np.clip(i - 1, 0, None)], 0)
            out.loc[m, "intl_apps_14"] = n.astype(float)
            out.loc[m, "intl_starts_14"] = (cs(S, hi) - cs(S, lo)).clip(0).astype(float)
            out.loc[m, "intl_far_14"] = ((cs(F, hi) - cs(F, lo)) > 0).astype(float)
            last = np.where(hi > 0, D[np.clip(hi - 1, 0, None)], np.datetime64("NaT"))
            out.loc[m, "intl_days_before"] = np.where(hi > 0, np.minimum(21.0, (K - last) / day), 21.0)
    return out


def attach(df: pd.DataFrame, season: str, names: dict, clubs: dict) -> float:
    """Adds FEATURES to df in place. names: {player_id: full name};
    clubs: {team id in df: FPL club name}. Returns the share of players
    linked to an ESPN player (logged — a low number means the names drifted)."""
    df["club"] = df["team"].map(clubs)
    players = (df[["player_id", "club"]].drop_duplicates()
               .assign(name=lambda d: d["player_id"].map(names)).dropna())
    team_ids = pl_team_ids(season)
    espn_id = link_players(players, squads(season, team_ids))
    club_matches, apps = season_tables(season, sorted(players["club"].unique()))
    feats = features(df, club_matches, apps, espn_id)
    for col in FEATURES:
        df[col] = feats[col].to_numpy()
    df.drop(columns=["club"], inplace=True)
    share = len(espn_id) / max(1, players["player_id"].nunique())
    logger.info("Other matches %s: %d club fixtures, %d appearances, %.0f%% of players linked",
                season, len(club_matches), len(apps), share * 100)
    return share


def current_season(bootstrap: dict) -> str:
    """'2026-27', from the season's first deadline."""
    year = int(min(e["deadline_time"] for e in bootstrap["events"] if e.get("deadline_time"))[:4])
    return f"{year}-{str(year + 1)[2:]}"


def _same_nation(a: str, b: str) -> bool:
    a, b = NATION_ALIAS.get(a, a), NATION_ALIAS.get(b, b)
    return _norm(a) == _norm(b)


def view(bootstrap: dict, player_ids: list, start: pd.Timestamp, end: pd.Timestamp) -> dict:
    """For the dashboard: your players' matches outside the Premier League
    between start and end (naive UTC) — each club's cup and European games,
    and each player's international games, with where they're played."""
    season = current_season(bootstrap)
    teams = {t["id"]: t["name"] for t in bootstrap["teams"]}
    els = {e["id"]: e for e in bootstrap["elements"]}
    ids = [p for p in dict.fromkeys(player_ids) if p in els]
    months = sorted({f"{d.year}{d.month:02d}" for d in pd.date_range(start, end, freq="D")})
    pick = lambda leagues: [e for lg in leagues for m in months for e in events(lg, m)
                            if start < e["date"] < end]
    club_ev, intl_ev = pick(CLUB_LEAGUES), pick(INTL_LEAGUES)

    def match(e, side):
        other = [t[0] for t in e["teams"] if t[0] != side]
        mine = next((t for t in e["teams"] if t[0] == side), None)
        home = (mine[2] == "home") if mine and len(mine) > 2 and mine[2] else e["teams"][0][0] == side
        return {"date": e["date"].tz_localize("UTC").isoformat(),
                "competition": LEAGUE_LABEL.get(e["league"], e["league"]),
                "opponent": other[0] if other else None, "home": bool(home),
                "far": bool(e["venue_country"]) and e["venue_country"] not in EUROPE}

    club_rows = []
    for club in sorted({teams[els[p]["team"]] for p in ids}):
        espn = FPL_TO_ESPN.get(club, club)
        ms = sorted((match(e, espn) for e in club_ev if any(t[0] == espn for t in e["teams"])),
                    key=lambda m: m["date"])
        if ms:
            club_rows.append({"club": club, "matches": ms,
                              "players": [els[p]["web_name"] for p in ids if teams[els[p]["team"]] == club]})

    sq = squads(season, pl_team_ids(season))
    people = pd.DataFrame([{"player_id": p, "name": f"{els[p]['first_name']} {els[p]['second_name']}",
                            "club": teams[els[p]["team"]]} for p in ids])
    link = link_players(people, sq) if not people.empty else {}
    nationality = {aid: nat for squad in sq.values() for aid, _, nat in squad}
    intl_rows = []
    for p in ids:
        nat = nationality.get(link.get(p))
        if not nat:
            continue
        mine = [e for e in intl_ev if any(_same_nation(t[0], nat) for t in e["teams"])]
        if mine:
            side = next(t[0] for t in mine[0]["teams"] if _same_nation(t[0], nat))
            intl_rows.append({"player_id": p, "name": els[p]["web_name"], "nation": nat,
                              "matches": sorted((match(e, side) for e in mine), key=lambda m: m["date"])})
    return {"from": start.isoformat(), "to": end.isoformat(), "clubs": club_rows,
            "international": sorted(intl_rows, key=lambda r: r["matches"][0]["date"])}


def pack(season: str) -> int:
    """Bundles one finished season's cached data into data/other_matches/,
    to be committed. Returns how many entries."""
    months = set(season_months(season))
    names = {}
    for f in CACHE.glob("e_*.json"):
        if f.stem.rsplit("_", 1)[1] in months:
            names[f.stem] = json.loads(f.read_text())
    ids = {e["id"] for evs in names.values() for e in evs}
    for f in CACHE.glob("m_*.json"):
        if f.stem.rsplit("_", 1)[1] in ids:
            names[f.stem] = json.loads(f.read_text())
    for f in CACHE.glob(f"s_*_{season[:4]}.json"):
        names[f.stem] = json.loads(f.read_text())
    PACK_DIR.mkdir(parents=True, exist_ok=True)
    (PACK_DIR / f"{season}.json.gz").write_bytes(gzip.compress(json.dumps(names).encode(), 9))
    return len(names)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Bundle finished seasons' other-match data.")
    ap.add_argument("--pack", nargs="+", required=True, help="seasons, e.g. 2023-24 2024-25")
    for season in ap.parse_args().pack:
        print(season, pack(season), "entries")
