"""
Team form from recent expected goals (team_form.py). Run from backend/:

    python -m unittest discover -s tests -v
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from data_engine import team_form as tf


def _rows(matches):
    """Per-player rows for (fixture, home, away, home xG, away xG, day)."""
    out = []
    for fx, h, a, xh, xa, day in matches:
        ko = pd.Timestamp("2026-08-01") + pd.Timedelta(days=day)
        out += [{"fixture": fx, "team": h, "opponent_team": a, "kickoff_time": ko, "expected_goals": xh},
                {"fixture": fx, "team": a, "opponent_team": h, "kickoff_time": ko, "expected_goals": xa}]
    return pd.DataFrame(out)


class TeamForm(unittest.TestCase):
    def test_rating_never_includes_its_own_match(self):
        rows = _rows([(1, 10, 20, 3.0, 0.5, 0), (2, 10, 20, 0.2, 0.1, 7)])
        before, now = tf.ratings(tf.team_matches(rows), {10: (1.0, 1.0), 20: (1.0, 1.0)})
        first = before[(before.team == 10) & (before.fixture == 1)].iloc[0]
        self.assertAlmostEqual(first.att, 1.0)            # only the prior
        second = before[(before.team == 10) & (before.fixture == 2)].iloc[0]
        self.assertGreater(second.att, 1.0)               # now knows the 3.0 xG
        self.assertLess(now[10][0], second.att)           # then the 0.2 pulls it down

    def test_against_is_the_opponents_for(self):
        m = tf.team_matches(_rows([(1, 10, 20, 2.0, 0.7, 0)]))
        row = m[m.team == 10].iloc[0]
        self.assertAlmostEqual(row.xg_against, 0.7)

    def test_priors_shrink_and_promoted_take_relegated(self):
        prev = {"A": (2.0, 0.8), "B": (1.0, 1.6), "Gone": (0.9, 2.0)}
        p = tf.priors(prev, {1: "A", 2: "B", 3: "New"})
        self.assertAlmostEqual(p[1][0], 0.5 * 2.0 + 0.5 * tf.LEAGUE_XG)
        self.assertEqual(p[3], (0.9, 2.0))

    def test_attach_and_match_columns(self):
        rows = _rows([(1, 10, 20, 2.0, 0.5, 0), (2, 20, 10, 1.0, 1.5, 7)])
        now = tf.attach(rows, {10: (2.0, 0.8), 20: (1.0, 1.6)})
        r = rows[(rows.fixture == 1) & (rows.team == 10)].iloc[0]
        self.assertAlmostEqual(r.team_xg_for, 2.0)
        self.assertAlmostEqual(r.opp_xg_against, 1.6)
        self.assertAlmostEqual(r.match_xg_for, 2.0 * 1.6 / tf.LEAGUE_XG)
        future = pd.DataFrame({"team": [10], "opponent_team": [20]})
        tf.apply_current(future, now)
        self.assertAlmostEqual(future.team_xg_for.iloc[0], now[10][0])


if __name__ == "__main__":
    unittest.main()
