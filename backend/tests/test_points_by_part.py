"""Points-by-part model (research/2026-11-components): the parts must add
back up to total points, and switching it on must change only stage 2."""
import unittest

import numpy as np
import pandas as pd

import config
from data_engine import train_model


def _rows(n=600, seed=0):
    rng = np.random.default_rng(seed)
    et = rng.integers(1, 5, n)
    goals = rng.poisson(0.2, n)
    assists = rng.poisson(0.15, n)
    cs = rng.integers(0, 2, n)
    bonus = rng.integers(0, 4, n)
    rest = rng.integers(-2, 3, n)
    gp = pd.Series(et).map(train_model.GOAL_POINTS).to_numpy()
    csp = pd.Series(et).map(train_model.CLEAN_SHEET_POINTS).to_numpy()
    df = pd.DataFrame({
        "element_type": et, "minutes": 90, "goals_scored": goals, "assists": assists,
        "clean_sheets": cs, "bonus": bonus,
        "total_points": 2 + goals * gp + 3 * assists + cs * csp + bonus + rest,
    })
    for c in config.FEATURE_COLUMNS:
        if c not in df.columns:
            df[c] = rng.normal(size=n)
    return df


class PointsByPart(unittest.TestCase):
    def test_parts_add_up_on_average(self):
        df = _rows()
        X = train_model._prep_X(df)
        parts = train_model._fit_parts(df, X)
        pred = train_model._predict_parts(parts, X, df["element_type"])
        self.assertEqual(len(pred), len(df))
        # Fitted on noise features, the sum should land near the mean score.
        self.assertAlmostEqual(pred.mean(), df["total_points"].mean(), delta=0.6)

    def test_off_by_default(self):
        self.assertFalse(config.POINTS_BY_PART)


if __name__ == "__main__":
    unittest.main()
