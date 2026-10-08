"""
Harness-fidelity tests: the research harnesses must see only what a manager
could have known at each deadline, play by that season's rules, and run the
procedure that actually ships.

Each test pins one fix from the October 2026 audit, so a regression shows up
as a named failure rather than as a quietly better-looking backtest. Run from
backend/:

    python -m unittest discover -s tests -v
"""
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd

import config
from data_engine import (
    availability_data,
    backtest,
    entry_data,
    evaluation,
    planner,
    rules,
    season_sim,
    transfer_optimizer,
)


class SeasonRulesTable(unittest.TestCase):
    def test_caps_by_season(self):
        self.assertEqual(rules.for_season("2023-24").max_free_transfers, 2)
        self.assertEqual(rules.for_season("2024-25").max_free_transfers, 5)
        self.assertEqual(rules.for_season("2026-27").max_free_transfers,
                         config.MAX_FREE_TRANSFERS)

    def test_2025_26_gw16_top_up(self):
        r = rules.for_season("2025-26")
        self.assertEqual(rules.free_transfers_for(r, 16, banked=1), 5)
        self.assertEqual(rules.free_transfers_for(r, 15, banked=1), 1)

    def test_2022_23_unlimited_week_then_one(self):
        r = rules.for_season("2022-23")
        self.assertEqual(rules.free_transfers_for(r, 17, banked=2), config.SQUAD_SIZE)
        self.assertEqual(rules.bank_after(r, 17, available=15, used=9), 1)

    def test_bank_respects_the_seasons_cap(self):
        r = rules.for_season("2023-24")
        self.assertEqual(rules.bank_after(r, 10, available=2, used=0), 2)
        self.assertEqual(rules.bank_after(r, 10, available=2, used=2), 1)

    def test_creation_week_banks_nothing(self):
        # The simulator opens its squad with an empty bank; one transfer
        # arrives for the next gameweek, as for the user's GW2-created team.
        r = rules.for_season("2025-26")
        self.assertEqual(rules.bank_after(r, 2, available=0, used=0), 1)


def _toy_pool():
    """15 owned players worth 1 point a week, plus five far better ones on
    the market, each a cheaper replacement for an owned midfielder."""
    rows, pid = [], 1
    for etype, n in {1: 2, 2: 5, 3: 5, 4: 3}.items():
        for _ in range(n):
            rows.append({"player_id": pid, "element_type": etype, "team": pid,
                         "now_cost": 50, "web_name": f"P{pid}"})
            pid += 1
    for k in range(5):
        rows.append({"player_id": 90 + k, "element_type": 3, "team": 90 + k,
                     "now_cost": 45, "web_name": f"Star{k}"})
    df = pd.DataFrame(rows)
    df["predicted_points"] = [1.0] * 15 + [20.0] * 5
    df["horizon_points"] = df["predicted_points"]
    return df


def _state(free, gw=14):
    owned = list(range(1, 16))
    return entry_data.TeamState(entry_id=0, name="t", gameweek=gw, squad=owned,
                                bank=0, squad_value=750, free_transfers=free,
                                sell_prices={p: 50 for p in owned})


class RulesInsideTheHorizon(unittest.TestCase):
    """A top-up or unlimited week inside the horizon is known in advance."""

    def test_top_up_week_gets_five(self):
        df = _toy_pool()
        gws = [14, 15, 16]
        xp = {r.player_id: {g: r.predicted_points for g in gws} for r in df.itertuples()}
        plan = transfer_optimizer.plan_transfers(
            df, _state(1), xp, gws, max_total_hits=0, rules=rules.for_season("2025-26"))
        self.assertEqual(plan["weeks"][2]["free_transfers"], 5)

    def test_unlimited_week_and_reset(self):
        df = _toy_pool()
        gws = [16, 17, 18]
        xp = {r.player_id: {g: r.predicted_points for g in gws} for r in df.itertuples()}
        plan = transfer_optimizer.plan_transfers(
            df, _state(1, gw=16), xp, gws, max_total_hits=0,
            rules=rules.for_season("2022-23"))
        self.assertEqual(plan["weeks"][1]["free_transfers"], config.SQUAD_SIZE)
        self.assertLessEqual(plan["weeks"][2]["free_transfers"], 1)

    def test_default_rules_unchanged(self):
        # Today's rules: five banked transfers carry into next week, capped at
        # five, so all five stars (who only score next week) arrive free.
        df = _toy_pool()
        gws = [6, 7]
        # Owned players still score in week 6, so selling them early costs.
        xp = {r.player_id: {6: 1.0 if r.player_id < 90 else 0.0, 7: r.predicted_points}
              for r in df.itertuples()}
        plan = transfer_optimizer.plan_transfers(df, _state(5, gw=6), xp, gws,
                                                 max_total_hits=0)
        self.assertEqual(plan["weeks"][0]["transfer_count"], 0)
        self.assertEqual(plan["weeks"][1]["transfer_count"], 5)
        self.assertEqual(plan["weeks"][1]["hits"], 0)


class ProductionProcedure(unittest.TestCase):
    def test_hit_week_only_when_advised(self):
        df = _toy_pool()
        gws = [6]
        xp = {r.player_id: {6: r.predicted_points} for r in df.itertuples()}
        decision = planner.plan_week(df, _state(1, gw=6), xp, gws)
        free_week = decision["plan"]["immediate"]
        self.assertEqual(free_week["hits"], 0)
        self.assertEqual(free_week["transfer_count"], 1)
        # Each further star gains 19 for a 4-point hit: worth it.
        self.assertTrue(decision["plan"]["hit_recommendation"]["worth_it"])
        self.assertIsNotNone(decision["hit_week"])
        self.assertGreater(decision["hit_week"]["hits"], 0)

    def test_vice_is_second_best(self):
        df = _toy_pool()
        xp = {r.player_id: {6: r.predicted_points} for r in df.itertuples()}
        result = planner.plan_week(df, _state(1, gw=6), xp, [6])["result"]
        values = df.set_index("player_id")["predicted_points"]
        ranked = sorted(result["starting_ids"], key=lambda p: -values[p])
        self.assertEqual(result["captain_id"], ranked[0])
        self.assertEqual(result["vice_captain_id"], ranked[1])

    def test_main_uses_the_shared_planner(self):
        import main
        with mock.patch.object(planner, "plan_week",
                               return_value={"result": "R", "plan": "P", "hit_week": None}) as pw:
            df = pd.DataFrame({"player_id": [1], "xp_by_gw": [{6: 1.0}]})
            self.assertEqual(main._plan_from_team(df, _state(1, gw=6), 6), ("R", "P"))
            pw.assert_called_once()


class AvailabilityLag(unittest.TestCase):
    def test_snapshot_after_t_informs_t_plus_one(self):
        raw = pd.DataFrame({"id": [7, 7], "gw": [4, 5], "status": ["i", "a"],
                            "chance_of_playing_next_round": [0, None]})
        flags = availability_data.from_playerstats(raw)
        self.assertEqual(flags.set_index("round").loc[5, "status"], "i")
        self.assertEqual(flags.set_index("round").loc[6, "status"], "a")

    def test_attach_fills_fit_and_never_zero(self):
        flags = pd.DataFrame({"element": [7], "round": [5], "status": ["d"],
                              "chance_of_playing": [50.0], "news": [""]})
        rows = pd.DataFrame({"element": [7, 8], "round": [5, 5]})
        with mock.patch.object(availability_data, "fetch_season_availability",
                               return_value=flags):
            coverage = availability_data.attach(rows, "2025-26")
        self.assertEqual(coverage, 0.5)
        self.assertEqual(list(rows["status"]), ["d", "a"])
        self.assertEqual(list(rows["chance_of_playing"]), [50.0, 100.0])


class DoubleGameweeks(unittest.TestCase):
    def test_second_match_uses_deadline_form(self):
        fixtures = pd.DataFrame({
            "player_id": [1, 1, 2],
            "kickoff_time": pd.to_datetime(["2025-12-20", "2025-12-23", "2025-12-20"]),
            "points_avg_3": [4.0, 9.0, 2.0],      # the 9.0 has seen match one
            "was_home": [1, 0, 1],
            "opp_strength_defence": [1100, 1300, 1200],
            "minutes": [90, 20, 90],
            "total_points": [2, 1, 6],
        })
        out = backtest.frozen_form_for_doubles(fixtures)
        p1 = out[out["player_id"] == 1]
        self.assertEqual(list(p1["points_avg_3"]), [4.0, 4.0])
        self.assertEqual(list(p1["was_home"]), [1, 0])
        self.assertEqual(list(p1["opp_strength_defence"]), [1100, 1300])
        # Each match keeps its own result.
        self.assertEqual(list(p1["minutes"]), [90, 20])
        self.assertEqual(list(p1["total_points"]), [2, 1])


def _season_frame():
    """Two players over GW1-5; player 1's price rises every week, and he is
    flagged doubtful (50%) at the GW3 deadline; player 2 is injured."""
    rows = []
    for gw in range(1, 6):
        for pid, etype in ((1, 3), (2, 4)):
            rows.append({
                "player_id": pid, "round": gw, "element_type": etype,
                "minutes": 90, "total_points": 5, "now_cost": 100 + 10 * gw if pid == 1 else 80,
                "kickoff_time": pd.Timestamp("2025-08-01") + pd.Timedelta(days=7 * gw),
                "was_home": gw % 2, "team_strength_attack": 1100,
                "team_strength_defence": 1100, "opp_strength_attack": 1100,
                "opp_strength_defence": 1100, "fixture_difficulty": 0.0,
                "days_since_last_match": 7,
                "status": ("d" if pid == 1 else "i") if gw == 3 else "a",
                "chance_of_playing": (50.0 if pid == 1 else 0.0) if gw == 3 else 100.0,
            })
    return pd.DataFrame(rows)


def _echo_predict(bundle, rows):
    """Stand-in model whose projection IS the inputs under test."""
    out = rows.copy()
    out["predicted_points"] = out["now_cost"].astype(float)
    out["ceiling_points"] = out["chance_of_playing"].fillna(100).astype(float)
    out["p_full"] = np.where(out["status"].isin(["i", "s", "u", "n"]), 0.0, 1.0)
    return out


class HorizonInputs(unittest.TestCase):
    def setUp(self):
        df = _season_frame()
        with mock.patch.object(season_sim.train_model, "predict_points", _echo_predict):
            self.per_gw = season_sim.build_horizon_predictions(
                None, df[df["round"] < 3], df, gw=3, horizon=3).set_index(
                    ["player_id", "target_gw"])
            self.leaky = season_sim.build_horizon_predictions(
                None, df[df["round"] < 3], df, gw=3, horizon=3,
                legacy_prices=True).set_index(["player_id", "target_gw"])

    def test_price_frozen_at_deadline(self):
        for gw in (3, 4, 5):
            self.assertEqual(self.per_gw.loc[(1, gw), "predicted_points"], 130)

    def test_legacy_flag_reproduces_the_leak(self):
        self.assertEqual(self.leaky.loc[(1, 5), "predicted_points"], 150)

    def test_doubt_applies_to_next_round_only(self):
        self.assertEqual(self.per_gw.loc[(1, 3), "ceiling_points"], 50.0)
        self.assertEqual(self.per_gw.loc[(1, 4), "ceiling_points"], 100.0)

    def test_hard_status_applies_to_every_week(self):
        for gw in (3, 4, 5):
            self.assertEqual(self.per_gw.loc[(2, gw), "p_full"], 0.0)


class Evaluation(unittest.TestCase):
    def _runs(self, edge, noise=0.0, seeds=(1, 2, 3)):
        rng = np.random.default_rng(0)
        runs = []
        for season in ("A", "B"):
            for seed in seeds:
                base = rng.normal(60, 10, size=30)
                for name, shift in (("production", 0.0), ("v", edge)):
                    pts = base + shift + rng.normal(0, noise, size=30)
                    runs.append({"variant": name, "season": season, "seed": seed,
                                 "total": float(pts.sum()),
                                 "per_gw": [[g, float(p)] for g, p in enumerate(pts)]})
        return runs

    def test_constant_edge_is_better(self):
        c = evaluation.compare(self._runs(edge=2.0), "v", "production", ["A", "B"])
        self.assertEqual(c["verdict"], "better")
        self.assertAlmostEqual(c["pooled_diff"], 120.0, places=6)

    def test_pure_noise_is_not_a_result(self):
        c = evaluation.compare(self._runs(edge=0.0, noise=8.0), "v", "production", ["A", "B"])
        self.assertEqual(c["verdict"], "no detectable effect")

    def test_block_bootstrap_of_a_constant_is_exact(self):
        draws = evaluation.block_bootstrap_totals(np.full(10, 3.0), 4,
                                                  np.random.default_rng(0))
        self.assertTrue(np.allclose(draws, 30.0))


if __name__ == "__main__":
    unittest.main()
