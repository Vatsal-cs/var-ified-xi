"""
File: odds_data.py
Path: var-ified-xi/backend/data_engine/odds_data.py

Match-level expectations derived from closing betting odds.

Bookmaker odds are the single strongest publicly available predictor of
football results — sharper than any rating system, because they price in
team news, motivation and lineups that a model can't see. football-data.co.uk
publishes closing 1X2 and over/under 2.5 odds for every Premier League match,
free, going back decades. From those this module derives, per fixture and per
team:

    team_xg      expected goals the team scores
    opp_xg       expected goals it concedes
    cs_prob      probability it keeps a clean sheet   (Poisson: e^-opp_xg)
    win_prob     probability it wins the match

STATUS: tested, rejected. Joined onto training rows and A/B'd in the
backtest — 4585 simulated points vs 4617 for the model without them, a
split result (helped 2025-26, hurt 2024-25). The pipeline's existing
rolling xG/xGC and team-strength features already carry most of this
signal. Kept for reproducibility: backtest.py's `odds` variant flips
config.ATTACH_ODDS to re-run it. Not used in production.

No API key. The current season's file updates after every round, so it only
ever contains matches already played — enough for training and backtests.
Upcoming-fixture odds for live prediction are approximated from team strength
(see feature_engineering) so the feature columns stay populated either way.
"""

import io
import logging
import math
from datetime import date

import numpy as np
import pandas as pd
import requests

from config import RAW_DIR

logger = logging.getLogger(__name__)

FOOTBALL_DATA_URL = "https://www.football-data.co.uk/mmz4281/{code}/E0.csv"

# football-data season code, e.g. "2024-25" -> "2425".
def _season_code(season: str) -> str:
    a, b = season.split("-")
    return f"{a[-2:]}{b[-2:]}"


# Canonical team names so football-data, the vaastav archive and the live FPL
# API all line up. Only the names that actually differ need an entry.
_ALIASES = {
    "man united": "man utd",
    "man city": "man city",
    "tottenham": "spurs",
    "spurs": "spurs",
    "nott'm forest": "nott'm forest",
    "nottingham forest": "nott'm forest",
    "wolves": "wolves",
    "wolverhampton wanderers": "wolves",
    "ipswich": "ipswich town",
    "sheffield united": "sheffield utd",
    "sheffield utd": "sheffield utd",
    "west ham": "west ham",
    "brighton": "brighton",
    "brighton and hove albion": "brighton",
    "newcastle": "newcastle",
    "newcastle united": "newcastle",
    "leeds": "leeds",
    "leeds united": "leeds",
}


def canonical_team(name: str) -> str:
    if not isinstance(name, str):
        return ""
    key = name.strip().lower()
    return _ALIASES.get(key, key)


def _demargin(odds_home, odds_draw, odds_away):
    """1X2 odds -> de-vigged probabilities (home, draw, away)."""
    inv = np.array([1 / odds_home, 1 / odds_draw, 1 / odds_away], dtype=float)
    return inv / inv.sum()


def _total_goals_lambda(over_odds, under_odds, line=2.5):
    """Back out the Poisson mean total goals implied by the over/under line.

    P(total > line) is de-vigged from the two prices, then a 1-D solve finds
    the lambda whose Poisson upper tail matches it.
    """
    if not (over_odds and under_odds) or over_odds <= 1 or under_odds <= 1:
        return 2.7  # league-average fallback
    p_over = (1 / over_odds) / (1 / over_odds + 1 / under_odds)
    threshold = math.floor(line)  # goals strictly greater than 2.5 == >= 3

    def p_over_for(lam):
        # P(X > threshold) = 1 - CDF(threshold)
        cdf = sum(math.exp(-lam) * lam**k / math.factorial(k) for k in range(threshold + 1))
        return 1 - cdf

    lo, hi = 0.2, 7.0
    for _ in range(40):
        mid = (lo + hi) / 2
        if p_over_for(mid) < p_over:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def _supremacy(p_home, p_away):
    """Expected goal difference (home minus away) from win probabilities.

    A smooth monotonic map calibrated so a coin-flip match -> 0 and a
    lopsided 85/8 -> roughly +2.2, which matches observed PL supremacy lines.
    """
    return 2.6 * (p_home - p_away)


def fetch_season_odds(season: str) -> pd.DataFrame:
    """One row per match: canonical team names, date, and the four derived
    expectations for each side. Empty DataFrame if the season won't fetch.
    """
    cache = RAW_DIR / f"odds_{season}.csv"
    if cache.exists():
        raw = cache.read_text()
    else:
        url = FOOTBALL_DATA_URL.format(code=_season_code(season))
        try:
            resp = requests.get(url, timeout=30)
            resp.raise_for_status()
            raw = resp.text
            cache.write_text(raw)
        except requests.RequestException as e:
            logger.warning("Odds for %s unavailable (%s) — skipping.", season, e)
            return pd.DataFrame()

    df = pd.read_csv(io.StringIO(raw))
    home_col = "AvgH" if "AvgH" in df.columns else "B365H"
    draw_col = "AvgD" if "AvgD" in df.columns else "B365D"
    away_col = "AvgA" if "AvgA" in df.columns else "B365A"
    over_col = "Avg>2.5" if "Avg>2.5" in df.columns else "B365>2.5"
    under_col = "Avg<2.5" if "Avg<2.5" in df.columns else "B365<2.5"

    need = ["Date", "HomeTeam", "AwayTeam", home_col, draw_col, away_col]
    df = df.dropna(subset=need)
    if df.empty:
        return pd.DataFrame()

    rows = []
    for _, m in df.iterrows():
        try:
            p_h, p_d, p_a = _demargin(m[home_col], m[draw_col], m[away_col])
        except (ZeroDivisionError, ValueError):
            continue
        lam_total = _total_goals_lambda(m.get(over_col), m.get(under_col))
        sup = _supremacy(p_h, p_a)
        lam_home = max(0.15, (lam_total + sup) / 2)
        lam_away = max(0.15, (lam_total - sup) / 2)
        rows.append({
            "date": pd.to_datetime(m["Date"], dayfirst=True, errors="coerce").date(),
            "home": canonical_team(m["HomeTeam"]),
            "away": canonical_team(m["AwayTeam"]),
            "home_xg": round(lam_home, 3),
            "away_xg": round(lam_away, 3),
            "home_cs_prob": round(math.exp(-lam_away), 3),
            "away_cs_prob": round(math.exp(-lam_home), 3),
            "home_win_prob": round(float(p_h), 3),
            "away_win_prob": round(float(p_a), 3),
        })

    out = pd.DataFrame(rows).dropna(subset=["date"])
    logger.info("Odds %s: %d matches parsed", season, len(out))
    return out


def per_team_lookup(odds_df: pd.DataFrame) -> dict:
    """{(date, canonical_team): {team_xg, opp_xg, cs_prob, win_prob}} for both
    sides of every match, so a player row can be joined on its own team.
    """
    lut = {}
    for _, m in odds_df.iterrows():
        lut[(m["date"], m["home"])] = {
            "odds_team_xg": m["home_xg"], "odds_opp_xg": m["away_xg"],
            "odds_cs_prob": m["home_cs_prob"], "odds_win_prob": m["home_win_prob"],
        }
        lut[(m["date"], m["away"])] = {
            "odds_team_xg": m["away_xg"], "odds_opp_xg": m["home_xg"],
            "odds_cs_prob": m["away_cs_prob"], "odds_win_prob": m["away_win_prob"],
        }
    return lut


ODDS_FEATURE_COLUMNS = ["odds_team_xg", "odds_opp_xg", "odds_cs_prob", "odds_win_prob"]

# Neutral values when a match can't be matched to an odds row — league medians.
ODDS_NEUTRAL = {
    "odds_team_xg": 1.35, "odds_opp_xg": 1.35,
    "odds_cs_prob": 0.26, "odds_win_prob": 0.33,
}
