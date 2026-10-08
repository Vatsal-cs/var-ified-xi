"""
Rule-correctness tests: the FPL transfer economy and chip windows.

These encode rules, not tuned behaviour, so they should only change when FPL
changes the game. Run from backend/:

    python -m unittest discover -s tests -v
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from data_engine import chips, entry_data, transfer_optimizer

# The live 2026/27 chip windows, as bootstrap-static publishes them.
CHIP_WINDOWS = [
    {"name": "wildcard", "start_event": 2, "stop_event": 19},
    {"name": "wildcard", "start_event": 20, "stop_event": 38},
    {"name": "freehit", "start_event": 2, "stop_event": 19},
    {"name": "bboost", "start_event": 1, "stop_event": 19},
    {"name": "3xc", "start_event": 1, "stop_event": 19},
    {"name": "freehit", "start_event": 20, "stop_event": 38},
    {"name": "bboost", "start_event": 20, "stop_event": 38},
    {"name": "3xc", "start_event": 20, "stop_event": 38},
]
BOOTSTRAP = {"chips": CHIP_WINDOWS, "game_settings": {"max_extra_free_transfers": 4}}


def history(*transfers_from_first_gw, first=1):
    return [{"event": first + i, "event_transfers": n}
            for i, n in enumerate(transfers_from_first_gw)]


class FreeTransferReplay(unittest.TestCase):
    def test_real_entry_created_at_gw2(self):
        # Entry 9927826: created at GW2; used 0, 1, 0, 2 transfers in GW2-5.
        # Observed: 2 free transfers at GW5, 1 at GW6.
        h = history(0, 1, 0, 2, first=2)
        self.assertEqual(entry_data.replay_free_transfers(h, set(), 3), 1)
        self.assertEqual(entry_data.replay_free_transfers(h, set(), 4), 1)
        self.assertEqual(entry_data.replay_free_transfers(h, set(), 5), 2)
        self.assertEqual(entry_data.replay_free_transfers(h, set(), 6), 1)

    def test_gw1_starter_banks_up_to_five(self):
        h = history(0, 0, 0, 0, 0, 0, 0)          # GW1-7, never transfers
        got = [entry_data.replay_free_transfers(h, set(), gw) for gw in range(2, 9)]
        self.assertEqual(got, [1, 2, 3, 4, 5, 5, 5])

    def test_wildcard_week_spends_nothing(self):
        h = history(0, 0, 11, first=1)             # GW3 is a wildcard
        self.assertEqual(entry_data.replay_free_transfers(h, {3}, 4), 3)
        self.assertEqual(entry_data.replay_free_transfers(h, set(), 4), 1)

    def test_cap_is_a_parameter(self):
        h = history(0, 0, 0, 0)
        self.assertEqual(entry_data.replay_free_transfers(h, set(), 5, cap=2), 2)

    def test_no_history_means_one(self):
        self.assertEqual(entry_data.replay_free_transfers([], set(), 1), 1)

    def test_cap_read_from_live_settings(self):
        self.assertEqual(entry_data.free_transfer_cap(BOOTSTRAP), 5)


class ChipWindows(unittest.TestCase):
    def test_first_half_set_expires_at_gw19(self):
        got = entry_data.available_chips(BOOTSTRAP, [], 6)
        self.assertEqual(got, {"wildcard": 19, "freehit": 19, "bboost": 19, "3xc": 19})

    def test_spending_a_first_half_chip_does_not_touch_the_second_set(self):
        used = [{"name": "3xc", "event": 3}]
        self.assertNotIn("3xc", entry_data.available_chips(BOOTSTRAP, used, 6))
        self.assertEqual(entry_data.available_chips(BOOTSTRAP, used, 20)["3xc"], 38)

    def test_second_half_chip_spent(self):
        used = [{"name": "wildcard", "event": 21}]
        self.assertNotIn("wildcard", entry_data.available_chips(BOOTSTRAP, used, 25))

    def test_unplayed_first_half_chips_do_not_roll_over(self):
        # Nothing played all first half: GW20 still offers exactly one set.
        got = entry_data.available_chips(BOOTSTRAP, [], 20)
        self.assertEqual(set(got.values()), {38})
        self.assertEqual(len(got), 4)


class ExpiryPlan(unittest.TestCase):
    def setUp(self):
        self.preds = pd.DataFrame({
            "player_id": [1, 2, 3],
            "web_name": ["Cap", "Bench", "Other"],
            "xp_by_gw": [{6: 7.0, 7: 9.0}, {6: 5.0, 7: 1.0}, {6: 1.0, 7: 1.0}],
        })
        self.plan = {"weeks": [
            {"gameweek": 6, "squad_ids": [1, 2, 3], "starting_ids": [1, 3], "captain_id": 1},
            {"gameweek": 7, "squad_ids": [1, 2, 3], "starting_ids": [1, 3], "captain_id": 1},
        ]}

    def test_best_weeks_and_one_chip_per_week(self):
        out = chips.expiry_plan({"bboost": 19, "3xc": 19}, 6, self.plan, self.preds)
        best = {b["chip"]: b for b in out["best_weeks"]}
        self.assertEqual(best["3xc"]["gameweek"], 7)          # captain 9.0 > 7.0
        self.assertEqual(best["bboost"]["gameweek"], 6)       # bench 5.0 > 1.0
        self.assertEqual(out["gameweeks_left"], 14)
        self.assertFalse(out["urgent"])

    def test_conflict_goes_to_the_more_valuable_chip(self):
        preds = pd.DataFrame({                                 # bench best in GW7 too
            "player_id": [1, 2, 3],
            "web_name": ["Cap", "Bench", "Other"],
            "xp_by_gw": [{6: 7.0, 7: 9.0}, {6: 1.0, 7: 12.0}, {6: 1.0, 7: 1.0}],
        })
        out = chips.expiry_plan({"bboost": 19, "3xc": 19}, 6, self.plan, preds)
        best = {b["chip"]: b["gameweek"] for b in out["best_weeks"]}
        self.assertEqual(best["bboost"], 7)                   # 12 beats the captain's 9
        self.assertEqual(best["3xc"], 6)

    def test_urgent_when_weeks_run_short(self):
        out = chips.expiry_plan({"wildcard": 19, "freehit": 19, "bboost": 19}, 18)
        self.assertEqual(out["gameweeks_left"], 2)
        self.assertTrue(out["urgent"])


class HitAccounting(unittest.TestCase):
    """A state with no free transfers left must pay for its first extra move."""

    def _squad(self):
        rows, pid = [], 1
        for etype, n in {1: 2, 2: 5, 3: 5, 4: 3}.items():
            for _ in range(n):
                rows.append({"player_id": pid, "element_type": etype, "team": pid,
                             "now_cost": 50, "web_name": f"P{pid}"})
                pid += 1
        # One far better midfielder, cheaper than anyone he could replace.
        rows.append({"player_id": 99, "element_type": 3, "team": 99,
                     "now_cost": 45, "web_name": "Star"})
        df = pd.DataFrame(rows)
        df["predicted_points"] = [1.0] * 15 + [20.0]
        df["horizon_points"] = df["predicted_points"]
        return df

    def test_zero_free_transfers_charges_the_first_move(self):
        df = self._squad()
        owned = list(range(1, 16))
        state = entry_data.TeamState(
            entry_id=0, name="t", gameweek=6, squad=owned, bank=0, squad_value=750,
            free_transfers=0, sell_prices={p: 50 for p in owned})
        xp = {r.player_id: {6: r.predicted_points} for r in df.itertuples()}
        week = transfer_optimizer.plan_transfers(df, state, xp, [6])["immediate"]
        self.assertEqual(week["transfer_count"], 1)
        self.assertEqual(week["hits"], 1)
        self.assertEqual(week["hit_cost"], 4)


if __name__ == "__main__":
    unittest.main()
