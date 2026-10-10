"""
Bench weight and Wildcard planning. Run from backend/:

    python -m unittest discover -s tests -v
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np
import pandas as pd

from data_engine import entry_data, optimizer, transfer_optimizer
from test_harness import _toy_pool, _state


def _market():
    """Per position: players whose points rise with price, with diminishing
    returns at the top — as real projections do."""
    rows, pid = [], 1
    for etype, n in {1: 4, 2: 10, 3: 10, 4: 6}.items():
        for k in range(n):
            cost = 40 + 10 * k
            rows.append({"player_id": pid, "element_type": etype, "team": pid,
                         "now_cost": cost, "web_name": f"P{pid}",
                         "predicted_points": 1.0 + 3.0 * (1 - 0.7 ** k)})
            pid += 1
    return pd.DataFrame(rows)


class BenchWeight(unittest.TestCase):
    def test_lower_weight_spends_less_on_the_bench(self):
        df = _market()
        cost = df.set_index("player_id")["now_cost"]
        spend = {}
        for w in (0.01, 0.5):
            r = optimizer.optimize_squad(df, bench_weight=w, budget=1000)
            spend[w] = cost[r["bench_ids"]].sum()
        self.assertLess(spend[0.01], spend[0.5])


class Wildcard(unittest.TestCase):
    def test_every_week_zero_transfer_is_free(self):
        df = _toy_pool()
        gws = [6, 7]
        xp = {r.player_id: {g: r.predicted_points for g in gws} for r in df.itertuples()}
        plan = transfer_optimizer.plan_transfers(df, _state(1, gw=6), xp, gws,
                                                 max_total_hits=0, wildcard=True)
        self.assertEqual(plan["weeks"][0]["transfer_count"], 5)   # all five stars
        self.assertEqual(plan["weeks"][0]["hits"], 0)

    def test_bank_is_kept_through_a_wildcard(self):
        df = _toy_pool()
        gws = [6, 7]
        xp = {r.player_id: {6: 0.0 if r.player_id >= 90 else 1.0, 7: r.predicted_points}
              for r in df.itertuples()}
        # Stars only score from week 7: with 2 banked, week 7 starts with 3.
        plan = transfer_optimizer.plan_transfers(df, _state(2, gw=6), xp, gws,
                                                 max_total_hits=0, wildcard=True)
        self.assertLessEqual(plan["weeks"][1]["transfer_count"] - plan["weeks"][1]["hits"], 3)
        self.assertEqual(plan["weeks"][1]["hits"], 0)


if __name__ == "__main__":
    unittest.main()
