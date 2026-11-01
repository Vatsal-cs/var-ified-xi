"""
File: understat_data.py
Path: var-ified-xi/backend/data_engine/understat_data.py

Per-match shot data from Understat (free, no key): shots, key passes,
non-penalty xG, and xGChain / xGBuildup, the expected goals of every
possession a player was part of. FPL's own figures stop at xG and xA, so
build-up play and shot volume are invisible to the model.

Each finished match is fetched once and cached; a finished season is packed
into data/understat/{season}.json.gz and committed, so the cloud runs never
fetch past seasons. Under test in research/2026-10-understat
(config.UNDERSTAT); nothing here runs unless that is on.
"""

import gzip
import json
import logging
import time
from difflib import SequenceMatcher

import numpy as np
import pandas as pd
import requests

import config
from data_engine.other_matches import _norm, _score

logger = logging.getLogger(__name__)

BASE = "https://understat.com"
HEADERS = {"User-Agent": "Mozilla/5.0", "X-Requested-With": "XMLHttpRequest"}
CACHE = config.RAW_DIR / "understat"
PACK_DIR = config.DATA_DIR / "understat"
PAUSE = 0.7     # seconds between requests: one person's browsing, not a crawl

# Understat's club names -> FPL's, where they differ.
UNDERSTAT_TO_FPL = {
    "Manchester City": "Man City",
    "Manchester United": "Man Utd",
    "Newcastle United": "Newcastle",
    "Nottingham Forest": "Nott'm Forest",
    "Sheffield United": "Sheffield Utd",
    "Tottenham": "Spurs",
    "Wolverhampton Wanderers": "Wolves",
}

# Per-match columns joined onto each FPL row (NaN where he played but wasn't
# linked, so rolling averages skip the match rather than count it as zero).
MATCH_COLUMNS = ["us_shots", "us_key_passes", "us_npxg", "us_xgchain", "us_xgbuildup"]


def _get(path: str):
    for attempt in range(3):
        try:
            r = requests.get(f"{BASE}/{path}", headers=HEADERS, timeout=30)
            r.raise_for_status()
            time.sleep(PAUSE)
            return r.json()
        except (requests.RequestException, ValueError):
            time.sleep(3 * (attempt + 1))
    raise RuntimeError(f"Understat unavailable: {path}")


def _year(season: str) -> str:
    return season[:4]


def season_matches(season: str) -> list:
    """[{id, date, h, a}] for every finished league match of the season."""
    data = _get(f"getLeagueData/EPL/{_year(season)}")
    return [{"id": d["id"], "date": d["datetime"][:10],
             "h": d["h"]["title"], "a": d["a"]["title"]}
            for d in data["dates"] if d.get("isResult")]


def _match_rows(match_id: str) -> list:
    """[understat player id, name, side, minutes, shots, key passes, npxG,
    xGChain, xGBuildup] for everyone who played. Cached for good: a finished
    match never changes."""
    path = CACHE / f"{match_id}.json"
    if path.exists():
        return json.loads(path.read_text())
    data = _get(f"getMatchData/{match_id}")
    pen_xg = {}
    for side in ("h", "a"):
        for s in data["shots"].get(side, []):
            if s.get("situation") == "Penalty":
                pen_xg[s["player_id"]] = pen_xg.get(s["player_id"], 0.0) + float(s["xG"])
    rows = []
    for side in ("h", "a"):
        for r in data["rosters"].get(side, {}).values():
            rows.append([r["player_id"], r["player"], side, int(r["time"]), int(r["shots"]),
                         int(r["key_passes"]), round(float(r["xG"]) - pen_xg.get(r["player_id"], 0.0), 4),
                         round(float(r["xGChain"]), 4), round(float(r["xGBuildup"]), 4)])
    CACHE.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rows))
    return rows


def _pack_path(season: str):
    return PACK_DIR / f"{season}.json.gz"


def season_data(season: str) -> dict:
    """{match id: {date, h, a, rows}}: from the committed pack when there is
    one, otherwise fetched (and cached match by match)."""
    if _pack_path(season).exists():
        return json.loads(gzip.decompress(_pack_path(season).read_bytes()))
    out = {}
    for m in season_matches(season):
        out[m["id"]] = {**m, "rows": _match_rows(m["id"])}
    return out


def pack(season: str) -> int:
    """Fetches a finished season and writes its pack. Returns matches packed."""
    data = season_data(season)
    PACK_DIR.mkdir(parents=True, exist_ok=True)
    _pack_path(season).write_bytes(gzip.compress(json.dumps(data, separators=(",", ":")).encode(), 9))
    return len(data)


def appearances(season: str) -> pd.DataFrame:
    """One row per player per match: date, FPL club name, Understat id and
    name, minutes and the shot columns."""
    recs = []
    for m in season_data(season).values():
        for uid, name, side, mins, shots, kp, npxg, chain, build in m["rows"]:
            club = m[side]
            recs.append((m["date"], UNDERSTAT_TO_FPL.get(club, club), uid, name, mins,
                         shots, kp, npxg, chain, build))
    return pd.DataFrame(recs, columns=["date", "club", "uid", "name", "us_minutes"] + MATCH_COLUMNS)


def link(players: pd.DataFrame, apps: pd.DataFrame) -> dict:
    """players: [player_id, name, club] -> {(understat id, club): player_id}.
    A name is matched inside its own club only, so two players called James
    at different clubs can't be confused; a surname unique in the squad
    settles nicknames ("Andy" / "Andrew Robertson")."""
    squads = {club: [(int(pid), _norm(n)) for pid, n in g[["player_id", "name"]].itertuples(index=False)]
              for club, g in players.drop_duplicates(["player_id", "club"]).groupby("club")}
    out = {}
    for (uid, club), g in apps.groupby(["uid", "club"]):
        toks = _norm(g["name"].iloc[0])
        squad = squads.get(club, [])
        best = sorted(((_score(toks, t), pid) for pid, t in squad), reverse=True)
        if best and best[0][0] >= 0.6 and (len(best) == 1 or best[0][0] > best[1][0]):
            out[(uid, club)] = best[0][1]
            continue
        same = [pid for pid, t in squad if t and toks and t[-1] == toks[-1]]
        if len(same) == 1:
            out[(uid, club)] = same[0]
    return out


def _alike(a: list, b: list) -> bool:
    """Any token of one name close to a token of the other ("casemiro" /
    "casimiro", "yarmolyuk" / "yarmoliuk")."""
    return any(SequenceMatcher(None, x, y).ratio() >= 0.8 for x in a for y in b)


def link_by_minutes(apps: pd.DataFrame, played: pd.DataFrame, taken: set) -> dict:
    """Second pass for players the names didn't settle, because the two sites
    spell them differently (Paqueta is "Lucas Tolentino Coelho de Lima" to
    FPL, Beto "Norberto Bercique Gomes Betuncal"). played: [player_id, club,
    name, date, minutes], one row per FPL appearance. Among the club's
    still-unlinked players (those with a similar name token, if any), the one
    whose minutes match his in at least 60% of his matches, and more often
    than anyone else's, is him."""
    free = played[~played["player_id"].isin(taken)]
    out = {}
    for (uid, club), g in apps.groupby(["uid", "club"]):
        pool = free[free["club"] == club]
        if pool.empty:
            continue
        toks = _norm(g["name"].iloc[0])
        names = pool.drop_duplicates("player_id").set_index("player_id")["name"]
        similar = [pid for pid, n in names.items() if _alike(toks, _norm(n))]
        if similar:
            pool = pool[pool["player_id"].isin(similar)]
        m = pool.merge(g[["date", "us_minutes"]], on="date")
        hits = (m["minutes"] - m["us_minutes"]).abs().le(3).groupby(m["player_id"]).sum().sort_values(ascending=False)
        if (len(hits) and hits.iloc[0] >= 0.6 * len(g)
                and (len(hits) == 1 or hits.iloc[0] > hits.iloc[1])):
            out[(uid, club)] = int(hits.index[0])
    return out


def attach(df: pd.DataFrame, season: str, names: dict, clubs: pd.Series) -> float:
    """Adds MATCH_COLUMNS to one season's FPL rows (in place). names maps
    player_id -> full name, clubs is each row's FPL club name; df needs
    player_id, kickoff_time and minutes. Returns the share of played rows
    linked."""
    for c in MATCH_COLUMNS:
        df[c] = 0.0
    try:
        apps = appearances(season)
    except RuntimeError as e:
        logger.warning("Understat %s unavailable: %s", season, e)
        return 0.0
    players = pd.DataFrame({"player_id": df["player_id"].to_numpy(), "club": clubs.to_numpy()})
    players["name"] = players["player_id"].map(names)
    ids = link(players.dropna(), apps)
    dates = pd.to_datetime(df["kickoff_time"]).dt.strftime("%Y-%m-%d").to_numpy()
    played_rows = players.assign(date=dates, minutes=df["minutes"].to_numpy())
    played_rows = played_rows[played_rows["minutes"] > 0].dropna()
    left = apps[[(u, c) not in ids for u, c in zip(apps["uid"], apps["club"])]]
    ids.update(link_by_minutes(left, played_rows, set(ids.values())))
    apps["player_id"] = [ids.get((u, c)) for u, c in zip(apps["uid"], apps["club"])]
    apps = apps.dropna(subset=["player_id"]).astype({"player_id": int})
    apps = apps.drop_duplicates(["player_id", "date"])
    key = pd.MultiIndex.from_arrays([df["player_id"].astype(int),
                                     pd.to_datetime(df["kickoff_time"]).dt.strftime("%Y-%m-%d")])
    lut = apps.set_index(["player_id", "date"])
    played = (df["minutes"] > 0).to_numpy()
    for c in MATCH_COLUMNS:
        vals = lut[c].reindex(key).to_numpy(dtype=float)
        # Didn't play: zero, like every FPL stat. Played but not linked: NaN.
        df[c] = np.where(played, vals, 0.0)
    linked = played & ~np.isnan(df["us_shots"].to_numpy())
    share = linked.sum() / max(played.sum(), 1)
    mins = lut["us_minutes"].reindex(key).to_numpy(dtype=float)
    agree = np.abs(mins[linked] - df["minutes"].to_numpy()[linked]) <= 5
    logger.info("Understat %s: %d match days, %.0f%% of played rows linked, minutes agree on %.0f%%",
                season, apps["date"].nunique(), 100 * share, 100 * agree.mean() if len(agree) else 0)
    return share
