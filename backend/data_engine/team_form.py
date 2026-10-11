"""
File: team_form.py
Path: var-ified-xi/backend/data_engine/team_form.py

How strong each team is, from its own recent matches — not from a rating
someone published before the season.

The model used to read team quality from FPL's published strength ratings.
Those are set before a season and barely move, and for 2026-27 FPL stopped
publishing them altogether (every team comes back 0). This measures it
instead, the same way for every season, from data both sources carry:

    attack   expected goals the team created per match
    defence  expected goals it conceded per match

Each is a recency-weighted average of the team's matches strictly BEFORE the
one being described (DECAY per match), started from a prior worth
PRIOR_MATCHES matches: last season's final rating pulled halfway toward the
league average, or — for a promoted club — the average of the clubs that went
down. So a rating at any point uses only what was known at that point, on
the same scale in training and in prediction.

From a team's and its opponent's ratings come the two numbers that matter
most for fantasy points — how many the team should score and concede in
THIS match:

    match_xg_for      = team attack  x opponent defence / league average
    match_xg_against  = opp attack   x team defence     / league average

Behind config.TEAM_FORM until it passes its test.
"""

import logging

import numpy as np
import pandas as pd

import config

logger = logging.getLogger(__name__)

DECAY = 0.9            # weight of each match relative to the one after it
PRIOR_MATCHES = 4.0    # how many matches the season-start prior counts as
CARRYOVER = 0.5        # share of last season's final rating kept at the start
LEAGUE_XG = 1.35       # league-average xG per team per match (PL 2022-26: 1.31-1.45)

TEAM_FORM_COLUMNS = list(config.TEAM_FORM_COLUMNS)

# Season-start ratings per team id, by season label, recorded when a past
# season is loaded so the simulator can rebuild "ratings as of the deadline".
SEASON_START = {}

# Describe the opponent or the specific match, not the player's own form:
# a double gameweek's second match has its own opponent.
MATCH_COLUMNS = ["opp_xg_for", "opp_xg_against", "match_xg_for", "match_xg_against"]


def team_matches(rows: pd.DataFrame) -> pd.DataFrame:
    """One row per (team, fixture): kickoff, xG for and against.

    rows: per-player per-match rows with team, opponent_team, fixture,
    kickoff_time and expected_goals. A team's xG is the sum over its
    players; its xG against is the opponent's.
    """
    g = (rows.groupby(["fixture", "team"], as_index=False)
             .agg(kickoff_time=("kickoff_time", "min"),
                  opponent=("opponent_team", "first"),
                  xg_for=("expected_goals", "sum")))
    opp = g[["fixture", "team", "xg_for"]].rename(columns={"team": "opponent",
                                                           "xg_for": "xg_against"})
    m = g.merge(opp, on=["fixture", "opponent"], how="left")
    m["xg_against"] = m["xg_against"].fillna(LEAGUE_XG)
    return m.sort_values(["kickoff_time", "fixture"]).reset_index(drop=True)


def priors(previous_final: dict, names_now: dict) -> dict:
    """Season-start (attack, defence) per team id.

    previous_final: {club name: (attack, defence)} at the end of last season,
    or None. names_now: {team id: club name} this season.
    """
    if not previous_final:
        return {tid: (LEAGUE_XG, LEAGUE_XG) for tid in names_now}
    gone = [v for name, v in previous_final.items() if name not in set(names_now.values())]
    promoted = tuple(np.mean([v[k] for v in gone]) for k in (0, 1)) if gone else (LEAGUE_XG, LEAGUE_XG)
    out = {}
    for tid, name in names_now.items():
        if name in previous_final:
            a, d = previous_final[name]
            out[tid] = (CARRYOVER * a + (1 - CARRYOVER) * LEAGUE_XG,
                        CARRYOVER * d + (1 - CARRYOVER) * LEAGUE_XG)
        else:
            out[tid] = promoted
    return out


def ratings(matches: pd.DataFrame, start: dict):
    """(ratings going into each match, ratings after the last one).

    Returns a frame [team, fixture, att, dfn] — each team's rating before
    that fixture — and {team: (att, dfn)} as of now.
    """
    rows, now = [], {}
    for team, grp in matches.groupby("team", sort=False):
        a0, d0 = start.get(team, (LEAGUE_XG, LEAGUE_XG))
        w, sa, sd = PRIOR_MATCHES, PRIOR_MATCHES * a0, PRIOR_MATCHES * d0
        for r in grp.itertuples():
            rows.append((team, r.fixture, sa / w, sd / w))
            w, sa, sd = w * DECAY + 1, sa * DECAY + r.xg_for, sd * DECAY + r.xg_against
        now[team] = (sa / w, sd / w)
    for team, (a0, d0) in start.items():
        now.setdefault(team, (a0, d0))
    return pd.DataFrame(rows, columns=["team", "fixture", "att", "dfn"]), now


def add_match_columns(df: pd.DataFrame) -> None:
    """match_xg_for / match_xg_against from the four rating columns, in place."""
    df["match_xg_for"] = df["team_xg_for"] * df["opp_xg_against"] / LEAGUE_XG
    df["match_xg_against"] = df["opp_xg_for"] * df["team_xg_against"] / LEAGUE_XG


def attach(rows: pd.DataFrame, start: dict) -> dict:
    """Adds TEAM_FORM_COLUMNS to per-player match rows, in place, each as it
    stood before that match. Returns the ratings as of now ({team: (att, dfn)})
    for predicting matches not yet played."""
    if rows.empty:
        for c in TEAM_FORM_COLUMNS:
            rows[c] = LEAGUE_XG
        return dict(start)
    before, now = ratings(team_matches(rows), start)
    key = before.set_index(["team", "fixture"])
    own = key.reindex(pd.MultiIndex.from_arrays([rows["team"], rows["fixture"]]))
    opp = key.reindex(pd.MultiIndex.from_arrays([rows["opponent_team"], rows["fixture"]]))
    rows["team_xg_for"] = own["att"].fillna(LEAGUE_XG).to_numpy()
    rows["team_xg_against"] = own["dfn"].fillna(LEAGUE_XG).to_numpy()
    rows["opp_xg_for"] = opp["att"].fillna(LEAGUE_XG).to_numpy()
    rows["opp_xg_against"] = opp["dfn"].fillna(LEAGUE_XG).to_numpy()
    add_match_columns(rows)
    return now


def apply_current(rows: pd.DataFrame, now: dict, team_col: str = "team",
                  opponent_col: str = "opponent_team") -> None:
    """Sets TEAM_FORM_COLUMNS on rows for matches not yet played, from the
    ratings as of now, in place."""
    get = lambda col, i: rows[col].map(lambda t: now.get(t, (LEAGUE_XG, LEAGUE_XG))[i])
    rows["team_xg_for"] = get(team_col, 0).astype(float)
    rows["team_xg_against"] = get(team_col, 1).astype(float)
    rows["opp_xg_for"] = get(opponent_col, 0).astype(float)
    rows["opp_xg_against"] = get(opponent_col, 1).astype(float)
    add_match_columns(rows)


def final_by_name(rows: pd.DataFrame, names: dict, start: dict = None) -> dict:
    """{club name: (attack, defence)} at the end of a season's rows."""
    _, now = ratings(team_matches(rows), start or {})
    return {names[t]: v for t, v in now.items() if t in names}
