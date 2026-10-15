"""
Tests for the points distributions, the chip planner and the team-news
reader's parsing and rules. Run from backend/:

    python -m unittest discover -s tests -v
"""
import json
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd

import config
from data_engine import chip_planner, distributions as D, team_news


def _tables():
    """Tiny tables: a 60+ match scores 2 or 8 (centre 5), or 3 or 9 (centre 6)."""
    def pmf(scores):
        p = np.zeros(D.SIZE)
        for s in scores:
            p[s - D.SUPPORT_MIN] += 1 / len(scores)
        return p
    full = {"centers": np.array([5.0, 6.0]), "pmf": np.array([pmf([2, 8]), pmf([3, 9])])}
    return {"full": {str(e): full for e in (1, 2, 3, 4)},
            "cameo": {str(e): pmf([1]) for e in (1, 2, 3, 4)}}


def _mean(p):
    return float((p * np.arange(D.SUPPORT_MIN, D.SUPPORT_MAX + 1)).sum())


class Distributions(unittest.TestCase):
    def test_match_mixes_minutes(self):
        p = D.match_pmf(_tables(), 3, p_full=0.5, p_cameo=0.25, pts_if_60=5.0)
        self.assertAlmostEqual(p.sum(), 1.0)
        self.assertAlmostEqual(p[0 - D.SUPPORT_MIN], 0.25)        # no minutes
        self.assertAlmostEqual(p[1 - D.SUPPORT_MIN], 0.25)        # cameo
        self.assertAlmostEqual(_mean(p), 0.25 * 1 + 0.5 * 5)

    def test_between_groups_blends(self):
        p = D.full_pmf(_tables(), 3, 5.5)
        self.assertAlmostEqual(_mean(p), 5.5)
        self.assertTrue(all(p[s - D.SUPPORT_MIN] > 0 for s in (2, 3, 8, 9)))

    def test_beyond_last_group_moves_up(self):
        p = D.full_pmf(_tables(), 4, 7.5)                       # 1.5 past the last centre
        self.assertAlmostEqual(_mean(p), 7.5)
        self.assertAlmostEqual(p.sum(), 1.0)

    def test_double_gameweek_adds_matches(self):
        one = D.match_pmf(_tables(), 3, 1.0, 0.0, 5.0)
        two = D.combine([one, one])
        self.assertAlmostEqual(_mean(two), 10.0)
        self.assertAlmostEqual(two[16 - D.SUPPORT_MIN], 0.25)    # 8 + 8

    def test_beats_and_ties(self):
        a = D.match_pmf(_tables(), 3, 1.0, 0.0, 6.0)             # 3 or 9
        b = D.match_pmf(_tables(), 3, 1.0, 0.0, 5.0)             # 2 or 8
        win, tie = D.beats(a, b)
        self.assertAlmostEqual(win, 0.75)                        # loses only 3 v 8
        self.assertAlmostEqual(tie, 0.0)

    def test_head_to_head_is_pulled_toward_even(self):
        a = D.match_pmf(_tables(), 3, 1.0, 0.0, 6.0)             # beats b 75% raw
        b = D.match_pmf(_tables(), 3, 1.0, 0.0, 5.0)
        p = D.head_to_head(a, b)
        self.assertTrue(0.5 < p < 0.75)
        self.assertAlmostEqual(p + D.head_to_head(b, a), 1.0)
        self.assertAlmostEqual(D.head_to_head(a, b, scale=1.0), 0.75)

    def test_payload_folds_negatives_into_zero(self):
        p = np.zeros(D.SIZE)
        p[-2 - D.SUPPORT_MIN] = 0.5
        p[6 - D.SUPPORT_MIN] = 0.5
        out = D.payload(p)
        self.assertAlmostEqual(out["pmf"][0], 0.5)
        self.assertAlmostEqual(sum(out["pmf"]), 1.0, places=3)
        self.assertEqual(out["p_return"], 0.5)


class ProjectionShrink(unittest.TestCase):
    def test_pulls_toward_position_mean_only_when_on(self):
        from data_engine import train_model
        bundle = {"full_means": {3: 4.0, 4: 5.0}}
        raw = np.array([8.0, 2.0, 7.0])
        types = [3, 3, 4]
        with mock.patch.object(config, "CONDITIONAL_SHRINK", None):
            np.testing.assert_allclose(train_model._shrink(bundle, raw, types), raw)
        with mock.patch.object(config, "CONDITIONAL_SHRINK", {"k": 0.5}):
            np.testing.assert_allclose(train_model._shrink(bundle, raw, types), [6.0, 3.0, 6.0])
        with mock.patch.object(config, "CONDITIONAL_SHRINK", {"k_by_pos": {3: 1.0, 4: 0.0}}):
            np.testing.assert_allclose(train_model._shrink(bundle, raw, types), [8.0, 2.0, 5.0])


class OtherMatches(unittest.TestCase):
    def _run(self):
        from data_engine import other_matches as om
        t = pd.Timestamp
        rows = pd.DataFrame({"player_id": [1, 2, 1], "club": ["Arsenal", "Arsenal", "Arsenal"],
                             "kickoff_time": [t("2025-10-04 14:00"), t("2025-10-04 14:00"), t("2025-10-25 14:00")]})
        club = pd.DataFrame({"club": ["Arsenal", "Arsenal", "Arsenal"], "league": ["uefa.champions"] * 3,
                             "date": [t("2025-10-01 19:00"), t("2025-10-21 19:00"), t("2025-10-29 19:00")],
                             "finished": [True, True, False], "event_id": ["a", "b", "c"]})
        apps = pd.DataFrame({"athlete_id": ["A1", "A1", "A1"], "kind": ["club", "intl", "intl"],
                             "role": ["start", "start", "sub"], "far": [False, True, False],
                             "league": ["uefa.champions", "fifa.worldq.conmebol", "fifa.friendly"],
                             "date": [t("2025-10-01 19:00"), t("2025-10-12 23:00"), t("2025-10-14 19:00")],
                             "goals": [1.0, 0.0, 0.0], "assists": [0.0, 1.0, 0.0],
                             "shots": [3.0, 1.0, 0.0], "sot": [2.0, 1.0, 0.0],
                             "opp_factor": [1.2, 0.25, 1.0]})
        return om.features(rows, club, apps, {1: "A1", 2: "A2"})

    def test_club_rest_and_rotation(self):
        f = self._run()
        self.assertAlmostEqual(f.loc[0, "xm_days_before"], 2.79, places=2)        # Wed 19:00 -> Sat 14:00
        self.assertEqual(f.loc[0, "xm_count_14"], 1)
        self.assertEqual((f.loc[0, "xm_started_before"], f.loc[0, "xm_rested_before"]), (1.0, 0.0))
        self.assertEqual((f.loc[1, "xm_started_before"], f.loc[1, "xm_rested_before"]), (0.0, 1.0))
        self.assertAlmostEqual(f.loc[2, "xm_days_after"], 4.21, places=2)         # next game ahead

    def test_international_load_only_from_the_past(self):
        f = self._run()
        self.assertEqual(f.loc[0, "intl_apps_14"], 0)                              # all after kick-off
        self.assertEqual(f.loc[2, "intl_apps_14"], 2)
        self.assertEqual(f.loc[2, "intl_starts_14"], 1)
        self.assertEqual(f.loc[2, "intl_far_14"], 1)
        self.assertEqual(f.loc[2, "xm_ga_30"], 2)              # CL goal 24 days back + the assist
        self.assertEqual(f.loc[2, "xm_apps_30"], 3)
        self.assertAlmostEqual(f.loc[2, "xm_ga_adj_30"], 1.2 + 0.25)   # goal v strong side, assist v weak
        self.assertAlmostEqual(f.loc[2, "xm_opp_30"], (1.2 + 0.25 + 1.0) / 3)


class ChipPlanner(unittest.TestCase):
    def _players(self):
        # 2 GK, 5 DEF, 5 MID, 3 FWD; ids 1-15
        types = [1, 1] + [2] * 5 + [3] * 5 + [4] * 3
        return pd.DataFrame({"player_id": range(1, 16), "element_type": types,
                             "web_name": [f"p{i}" for i in range(1, 16)],
                             "team": range(1, 16), "now_cost": [50] * 15})

    def test_best_xi_respects_formation(self):
        p = self._players()
        pos = p.set_index("player_id")["element_type"].to_dict()
        xp = {i: float(i) for i in range(1, 16)}
        xi, bench = chip_planner.best_xi(list(range(1, 16)), xp, pos)
        self.assertEqual(len(xi), 11)
        self.assertEqual(sum(pos[i] == 1 for i in xi), 1)
        self.assertGreaterEqual(sum(pos[i] == 2 for i in xi), 3)
        self.assertEqual(len(bench), 4)

    def test_assign_puts_each_chip_in_a_different_best_week(self):
        weeks = [{"gameweek": 7, "3xc": 8.0, "bboost": 10.0, "freehit": 5.0},
                 {"gameweek": 8, "3xc": 9.0, "bboost": 14.0, "freehit": 4.0},
                 {"gameweek": 9, "3xc": 12.0, "bboost": 9.0, "freehit": 6.0}]
        placed = {p["chip"]: p["gameweek"] for p in chip_planner.assign(weeks, ["3xc", "bboost", "freehit"])}
        self.assertEqual(placed, {"3xc": 9, "bboost": 8, "freehit": 7})
        self.assertEqual(len(set(placed.values())), 3)

    def test_wildcard_week_is_blocked(self):
        weeks = [{"gameweek": 7, "3xc": 20.0, "bboost": 1.0},
                 {"gameweek": 8, "3xc": 5.0, "bboost": 1.0}]
        placed = chip_planner.assign(weeks, ["3xc"], blocked={7})
        self.assertEqual(placed[0]["gameweek"], 8)


class TeamNews(unittest.TestCase):
    REPLY = """Here's what I found.
```json
{"players": [
 {"player_id": 380, "name": "Szoboszlai", "club": "Liverpool", "status": "out",
  "start_chance": 0, "reason": "Hamstring, Slot: out for two weeks",
  "source_url": "https://www.bbc.co.uk/sport/x", "source_date": "%s"},
 {"player_id": 999, "name": "Someone", "club": "Liverpool", "status": "Doubtful",
  "start_chance": 140, "reason": "knock", "source_url": "not a url", "source_date": "%s"},
 {"player_id": 411, "name": "Haaland", "club": "Man City", "status": "rested?",
  "start_chance": 50, "reason": "", "source_url": "https://x.com", "source_date": "%s"}
]}
```"""

    def _reply(self, days_ago=0):
        d = (datetime.now(timezone.utc) - timedelta(days=days_ago)).date().isoformat()
        return self.REPLY % (d, d, d)

    def test_parse_cleans_the_reply(self):
        items = team_news.parse(self._reply(), known_ids={380, 411})
        self.assertEqual([i["status"] for i in items], ["out", "doubtful"])   # unknown status dropped
        self.assertIsNone(items[1]["player_id"])                              # not on the list
        self.assertEqual(items[1]["start_chance"], 100)                       # clamped
        self.assertIsNone(items[1]["source_url"])

    def _rows(self, chance=None):
        return pd.DataFrame({"player_id": [380, 380, 411], "gw": [7, 8, 7],
                             "chance_of_playing": [chance, None, None]})

    def test_out_lowers_this_week_only(self):
        rows = self._rows()
        news = {"items": team_news.parse(self._reply(), known_ids={380, 411})}
        applied = team_news.apply(rows, news, 7)
        self.assertEqual(applied[0]["chance"], 0)
        self.assertEqual(rows.loc[0, "chance_of_playing"], 0)
        self.assertTrue(pd.isna(rows.loc[1, "chance_of_playing"]))           # GW8 untouched

    def test_not_applied_when_fpl_already_worse_or_news_stale(self):
        rows = self._rows(chance=0)
        news = {"items": team_news.parse(self._reply(), known_ids={380})}
        self.assertEqual(team_news.apply(rows, news, 7), [])
        rows = self._rows()
        news = {"items": team_news.parse(self._reply(days_ago=9), known_ids={380})}
        self.assertEqual(team_news.apply(rows, news, 7), [])

    def test_switch_turns_adjustments_off(self):
        rows = self._rows()
        news = {"items": team_news.parse(self._reply(), known_ids={380})}
        with mock.patch.object(config, "TEAM_NEWS_ADJUST", False):
            self.assertEqual(team_news.apply(rows, news, 7), [])

    def test_gemini_is_preferred_and_free(self):
        with mock.patch.dict("os.environ", {"GEMINI_API_KEY": "g", "ANTHROPIC_API_KEY": "a"}, clear=True):
            self.assertEqual(team_news.provider(), "gemini")
            self.assertEqual(team_news.model_name(), config.TEAM_NEWS_GEMINI_MODEL)
        with mock.patch.dict("os.environ", {"ANTHROPIC_API_KEY": "a"}, clear=True):
            self.assertEqual(team_news.provider(), "claude")

    def _gemini_response(self, chunks):
        r = mock.Mock(status_code=200)
        r.raise_for_status = lambda: None
        r.json = lambda: {"candidates": [{
            "content": {"parts": [{"text": self._reply()}]},
            "groundingMetadata": {"groundingChunks": chunks}}]}
        return r

    def test_gemini_call_reads_text_and_google_sources(self):
        chunks = [{"web": {"title": "bbc.co.uk", "uri": "https://vertexaisearch.example/redirect/1"}}]
        with mock.patch.dict("os.environ", {"GEMINI_API_KEY": "g"}, clear=True), \
             mock.patch.object(team_news.requests, "post", return_value=self._gemini_response(chunks)) as post:
            text, sources = team_news._call_gemini("prompt")
        body = post.call_args.kwargs["json"]
        self.assertEqual(body["tools"], [{"google_search": {}}])
        self.assertIn("Szoboszlai", text)
        self.assertEqual(sources, [("bbc.co.uk", "https://vertexaisearch.example/redirect/1")])

    def test_only_google_backed_sources_survive(self):
        items = team_news.parse(self._reply(), known_ids={380, 411})
        kept = team_news._keep_sources([dict(i) for i in items], [("bbc.co.uk", "https://r/1")])
        self.assertEqual(kept[0]["source_url"], "https://www.bbc.co.uk/sport/x")     # same site: kept
        none = team_news._keep_sources([dict(i) for i in items], [])
        self.assertIsNone(none[0]["source_url"])                                     # no search: unusable
        rows = self._rows()
        self.assertEqual(team_news.apply(rows, {"items": none}, 7), [])

    def test_no_key_means_no_call(self):
        with mock.patch.dict("os.environ", {}, clear=True), \
             mock.patch.object(team_news, "fetch") as fetch, \
             mock.patch.object(team_news, "load_cached", return_value=None):
            out = team_news.get([], 7, datetime.now(timezone.utc) + timedelta(hours=5))
        fetch.assert_not_called()
        self.assertIsNone(out)


if __name__ == "__main__":
    unittest.main()
