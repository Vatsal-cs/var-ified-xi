"""
A team set in the FPL app with a Wildcard or Free Hit, before the deadline
(overrides.json "team"). Run from backend/:

    python -m unittest discover -s tests -v
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import config
import main
from data_engine import transfer_optimizer
from test_harness import _toy_pool, _state


def _bootstrap(df):
    return {"elements": [{"id": int(r.player_id), "element_type": int(r.element_type),
                          "team": int(r.team), "now_cost": int(r.now_cost),
                          "web_name": r.web_name} for r in df.itertuples()]}


def _picks(ids):
    # XI: keeper 1, defenders 3-7, midfielders 8-11, forward 13; bench: keeper 2, 12, 14, 15
    return [{"id": i} for i in ids]


XI = [1, 3, 4, 5, 6, 7, 8, 9, 10, 11, 13]
BENCH = [2, 12, 14, 15]


class LockedFirstWeek(unittest.TestCase):
    def test_no_transfers_in_the_set_week_and_the_bank_carries(self):
        df = _toy_pool()
        gws = [6, 7]
        xp = {r.player_id: {g: r.predicted_points for g in gws} for r in df.itertuples()}
        plan = transfer_optimizer.plan_transfers(df, _state(2, gw=6), xp, gws, max_total_hits=0,
                                                 wildcard=True, locked_first_week=True)
        self.assertEqual(plan["weeks"][0]["transfer_count"], 0)
        # A Wildcard keeps the two it had: week 7 has two free, and uses them.
        self.assertEqual(plan["weeks"][1]["transfer_count"], 2)
        self.assertEqual(plan["weeks"][1]["hits"], 0)


class LockedTeam(unittest.TestCase):
    def _run(self, team, gw=6):
        df = _toy_pool()
        state = _state(1, gw=gw)
        state.chips_available = ["wildcard", "bboost"]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "overrides.json"
            path.write_text(json.dumps({"team": team}))
            with mock.patch.object(config, "OVERRIDES_PATH", path):
                return main._locked_team(state, _bootstrap(df), gw), state

    def _team(self, **kw):
        team = {"gameweek": 6, "chip": "wildcard", "bank_m": 1.5,
                "picks": _picks(XI + BENCH), "captain_id": 8, "vice_captain_id": 13}
        team.update(kw)
        return team

    def test_applied_to_the_team(self):
        locked, state = self._run(self._team(picks=_picks(XI[:7] + [90] + XI[8:] + BENCH)))
        self.assertIsNotNone(locked)
        self.assertIn(90, state.squad)                 # a new signing
        self.assertNotIn(9, state.squad)
        self.assertEqual(state.sell_prices[90], 45)    # bought at today's price
        self.assertEqual(state.bank, 15)
        self.assertEqual(state.chips_available, ["bboost"])
        self.assertEqual(locked["bench_ids"], BENCH)

    def test_ignored_after_its_gameweek(self):
        locked, state = self._run(self._team(gameweek=5))
        self.assertIsNone(locked)
        self.assertIn("wildcard", state.chips_available)

    def test_illegal_squads_are_ignored(self):
        for bad in (self._team(picks=_picks(XI + BENCH[:3])),            # 14 players
                    self._team(picks=_picks(XI[:1] + [2] + XI[2:] + [3] + BENCH[1:])),  # two keepers in the XI
                    self._team(captain_id=2),                            # captain on the bench
                    self._team(chip="bboost")):                          # doesn't change the squad
            locked, state = self._run(bad)
            self.assertIsNone(locked)
            self.assertEqual(state.squad, list(range(1, 16)))


class PlanLocked(unittest.TestCase):
    def test_your_lineup_shown_and_the_model_compared(self):
        df = _toy_pool()
        df["xp_by_gw"] = [{6: p, 7: p} for p in df["predicted_points"]]
        state = _state(1, gw=6)
        locked = {"chip": "wildcard", "gameweek": 6, "starting_ids": XI, "bench_ids": BENCH,
                  "captain_id": 8, "vice_captain_id": 13}
        result, plan, check = main._plan_locked(df, state, 6, locked)
        self.assertEqual(result["starting_ids"], XI)
        self.assertEqual(result["bench_ids"], BENCH)
        self.assertEqual(plan["weeks"][0]["transfer_count"], 0)
        self.assertEqual(plan["weeks"][0]["captain_id"], 8)
        self.assertIn("model_agrees", check)
        # Stars on the market at 20 a week: with the Wildcard still open the
        # model says what it would still change, and what that's worth.
        self.assertEqual(len(check["suggested_changes"]), 5)
        self.assertGreaterEqual(check["suggested_gain"], main.LOCKED_TWEAK_MIN)

    def test_no_changes_shown_when_the_team_is_already_best(self):
        df = _toy_pool()
        df = df[df.player_id < 90]                      # nothing better on the market
        df["xp_by_gw"] = [{6: p, 7: p} for p in df["predicted_points"]]
        locked = {"chip": "wildcard", "gameweek": 6, "starting_ids": XI, "bench_ids": BENCH,
                  "captain_id": 8, "vice_captain_id": 13}
        _, _, check = main._plan_locked(df, _state(1, gw=6), 6, locked)
        self.assertEqual(check["suggested_changes"], [])


if __name__ == "__main__":
    unittest.main()
