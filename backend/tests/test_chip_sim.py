"""
Chips in the season simulator (data_engine/chip_sim.py). Run from backend/:

    python -m unittest discover -s tests -v
"""
import sys
import unittest
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config
from data_engine import chip_planner, chip_sim

# 2 GK (1-2), 5 DEF (3-7), 5 MID (8-12), 3 FWD (13-15)
POS = {1: 1, 2: 1, 3: 2, 4: 2, 5: 2, 6: 2, 7: 2,
       8: 3, 9: 3, 10: 3, 11: 3, 12: 3, 13: 4, 14: 4, 15: 4}
SQUAD = list(POS)
XI = [1, 3, 4, 5, 6, 8, 9, 10, 11, 13, 14]
BENCH = [2, 7, 12, 15]


def week(points: dict, minutes: dict = None) -> pd.DataFrame:
    ids = sorted(set(POS) | set(points))
    return pd.DataFrame({
        "player_id": ids,
        "element_type": [POS.get(p, 3) for p in ids],
        config.TARGET_COL: [points.get(p, 0) for p in ids],
        "minutes": [(minutes or {}).get(p, 90) for p in ids],
    })


def result(captain=13, vice=8):
    return {"starting_ids": XI, "bench_ids": BENCH, "captain_id": captain, "vice_captain_id": vice}


class FixtureRule(unittest.TestCase):
    def test_blank_and_doubles_take_their_chips(self):
        counts = {25: {"doubles": 2, "blanks": 0}, 29: {"doubles": 0, "blanks": 4},
                  33: {"doubles": 4, "blanks": 0}}
        placed = chip_sim.fixture_rule(list(range(20, 39)), counts)
        self.assertEqual(placed, {"freehit": 29, "bboost": 33, "3xc": 25})

    def test_no_special_weeks_means_the_last_weeks(self):
        placed = chip_sim.fixture_rule(list(range(3, 20)), {})
        self.assertEqual(placed, {"3xc": 19, "bboost": 18, "freehit": 17})

    def test_ties_go_to_the_earlier_week(self):
        counts = {24: {"doubles": 2, "blanks": 0}, 25: {"doubles": 2, "blanks": 0}}
        placed = chip_sim.fixture_rule(list(range(20, 39)), counts)
        self.assertEqual((placed["bboost"], placed["3xc"]), (24, 25))
        self.assertEqual(placed["freehit"], 38)

    def test_counts_from_a_season_frame(self):
        df = pd.DataFrame({
            "round": [1, 1, 1, 2, 2],
            "team": [1, 1, 2, 1, 3],
            "kickoff_time": ["a", "b", "c", "d", "e"],
        })
        counts = chip_sim.fixture_counts(df)
        self.assertEqual(counts[1], {"doubles": 1, "blanks": 1})
        self.assertEqual(counts[2], {"doubles": 0, "blanks": 1})


class RealisedGains(unittest.TestCase):
    def test_bench_boost_and_triple_captain(self):
        points = {p: 2 for p in POS}
        points.update({13: 10, 2: 1, 7: 6, 12: 3, 15: 0})
        rows = week(points)
        normal = sum(points[p] for p in XI) + points[13]
        gains = chip_sim.realised_gains(result(), SQUAD, rows, {p: 1.0 for p in POS}, normal)
        self.assertEqual(gains["bboost"], 1 + 6 + 3 + 0)
        self.assertEqual(gains["3xc"], 10)
        self.assertEqual(gains["freehit"], 0)

    def test_triple_captain_falls_to_the_vice(self):
        points = {p: 2 for p in POS}
        points.update({13: 0, 8: 7})
        rows = week(points, {13: 0})
        normal = 999                                   # only Triple Captain is read here
        gains = chip_sim.realised_gains(result(), SQUAD, rows, {p: 1.0 for p in POS}, normal)
        self.assertEqual(gains["3xc"], 7)

    def test_bench_boost_counts_a_benched_player_once(self):
        # Starter 14 didn't play: the first bench forward comes on. With the
        # Bench Boost nobody is subbed, so the gain is the rest of the bench.
        points = {p: 2 for p in POS}
        points.update({14: 0, 15: 5})
        rows = week(points, {14: 0})
        normal = sum(points[p] for p in XI if p != 14) + points[15] + points[13]
        gains = chip_sim.realised_gains(result(), SQUAD, rows, {p: 1.0 for p in POS}, normal)
        self.assertEqual(gains["bboost"], points[2] + points[7] + points[12])

    def test_free_hit_against_the_real_week(self):
        fh_ids = list(range(101, 116))
        fh_pos = dict(zip(fh_ids, POS.values()))
        points = {p: 2 for p in POS}
        points.update({p: 4 for p in fh_ids})
        rows = week(points)
        rows["element_type"] = rows["player_id"].map(lambda p: POS.get(p, fh_pos.get(p)))
        normal = sum(points[p] for p in XI) + points[13]
        fh = {"starting_ids": fh_ids[:1] + fh_ids[2:12], "bench_ids": [fh_ids[1]] + fh_ids[12:],
              "captain_id": fh_ids[0], "vice_captain_id": fh_ids[2]}
        gains = chip_sim.realised_gains(result(), SQUAD, rows, {p: 1.0 for p in rows["player_id"]},
                                        normal, fh)
        self.assertEqual(gains["freehit"], 12 * 4 - normal)


class Placements(unittest.TestCase):
    def test_hindsight_leaves_a_losing_chip_unplayed(self):
        gains = {3: {"3xc": 4, "bboost": 9, "freehit": -5},
                 4: {"3xc": 12, "bboost": 2, "freehit": -2}}
        self.assertEqual(chip_sim.hindsight([3, 4], gains), {"bboost": 3, "3xc": 4})

    def test_planner_fills_the_weeks_left_when_chips_outnumber_them(self):
        # Two chips, one week before the deadline: the more valuable one is
        # played rather than neither.
        weeks = [{"gameweek": 19, "3xc": 6.0, "bboost": 9.0, "freehit": None}]
        placed = chip_planner.assign(weeks, ["3xc", "bboost"])
        self.assertEqual([(p["chip"], p["gameweek"]) for p in placed], [("bboost", 19)])

    def test_policies_add_their_chips_to_the_same_weeks(self):
        ledger = chip_sim.ChipLedger(rounds=list(range(2, 7)), counts={})
        ledger.gains = {g: {"3xc": g, "bboost": 10 * g, "freehit": 0} for g in range(3, 7)}
        ledger.planner = {("bboost", 0): 3}
        base = [{"gw": g, "points": 50} for g in range(2, 7)]
        weeks = ledger.per_gw(base)
        self.assertEqual([w["points"] for w in weeks["planner"]], [50, 80, 50, 50, 50])
        # The fixture rule with no special weeks: 3xc at 6, bboost at 5, freehit at 4.
        self.assertEqual([w["points"] for w in weeks["fixture_rule"]], [50, 50, 50, 100, 56])
        self.assertEqual(ledger.unplayed(), [("3xc", 0), ("freehit", 0)])


if __name__ == "__main__":
    unittest.main()
