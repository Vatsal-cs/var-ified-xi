"""
Seed-averaging tests (train_model, config.MODEL_BAG_SIZE). Run from backend/:

    python -m unittest discover -s tests -v
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd

import config
from data_engine import train_model


def _frame(n=1200, seed=0):
    rng = np.random.default_rng(seed)
    df = pd.DataFrame({c: rng.normal(size=n) for c in config.FEATURE_COLUMNS})
    df["element_type"] = rng.integers(1, 5, size=n)
    df["minutes"] = rng.choice([0, 30, 90], size=n, p=[0.3, 0.1, 0.6])
    df["minutes_avg_3"] = np.where(df["minutes"] > 0, 60.0, 0.0) + rng.normal(size=n)
    df[config.TARGET_COL] = np.where(df["minutes"] >= 60, rng.poisson(4, size=n), rng.poisson(1, size=n))
    df["round"] = np.repeat(np.arange(1, 11), n // 10)
    df["player_id"] = np.arange(n)
    return df


class Bagging(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.train = _frame()
        cls.pred = _frame(n=200, seed=1)
        old = config.MODEL_BAG_SIZE
        try:
            config.MODEL_BAG_SIZE = 1
            cls.single = train_model.train_models(cls.train, save=False)
            config.MODEL_BAG_SIZE = 3
            cls.bag = train_model.train_models(cls.train, save=False)
        finally:
            config.MODEL_BAG_SIZE = old

    def test_size_one_is_a_single_model(self):
        self.assertNotIn("members", self.single)
        self.assertIn("minutes_clf", self.single)

    def test_bag_members_and_seeds(self):
        self.assertEqual(len(self.bag["members"]), 3)
        s = config.MODEL_SEED
        self.assertEqual(self.bag["seeds"], [s, s + train_model.BAG_SEED_STRIDE,
                                             s + 2 * train_model.BAG_SEED_STRIDE])
        self.assertEqual(config.MODEL_SEED, s)                # restored after fitting

    def test_first_member_is_the_single_model(self):
        a = train_model.predict_points(self.single, self.pred)["predicted_points"]
        b = train_model.predict_points(self.bag["members"][0], self.pred)["predicted_points"]
        np.testing.assert_allclose(a, b)

    def test_bag_projection_is_the_members_mean(self):
        bag = train_model.predict_points(self.bag, self.pred)["predicted_points"].to_numpy()
        each = np.mean([train_model.predict_points(m, self.pred)["predicted_points"].to_numpy()
                        for m in self.bag["members"]], axis=0)
        np.testing.assert_allclose(bag, each, atol=0.011)   # rounding to 2 dp

    def test_flags_apply_once_to_the_average(self):
        flagged = self.pred.assign(status="i", chance_of_playing=0.0)
        out = train_model.predict_points(self.bag, flagged)["predicted_points"]
        self.assertTrue((out == 0).all())


if __name__ == "__main__":
    unittest.main()
