"""
The deadline reminder (deadline_reminder.py). Run from backend/:

    python -m unittest discover -s tests -v
"""
import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import deadline_reminder as dr

DEADLINE = datetime(2026, 11, 6, 18, 30, tzinfo=timezone.utc)
NOW = DEADLINE - timedelta(hours=4, minutes=40)


def _player(pid, name, position):
    return {"player_id": pid, "name": name, "position": position}


def _plan(**changes):
    plan = {
        "generated_at": (NOW - timedelta(hours=2)).isoformat(),
        "gameweek": 10,
        "deadline": "2026-11-06T18:30:00Z",
        "starting_xi": [_player(1, "Raya", "GKP"), _player(4, "Gabriel", "DEF"),
                        _player(31, "Konsa", "DEF"), _player(411, "Haaland", "FWD")],
        "bench": [_player(2, "Verbruggen", "GKP"), _player(447, "Botman", "DEF")],
        "captain_id": 4,
        "vice_captain_id": 411,
        "transfer_plan": {"weeks": [{"gameweek": 10, "hits": 0, "hit_cost": 0,
                                     "transfers_out": [{"name": "Calafiori"}],
                                     "transfers_in": [{"name": "Gabriel"}]}]},
        "chip_plan": {"scenarios": [{"plan": [{"chip": "bboost", "now": False, "player": None}]}]},
        "team_news": {"items": []},
    }
    plan.update(changes)
    return plan


def _week(plan):
    return plan["transfer_plan"]["weeks"][0]


class WhenItFires(unittest.TestCase):
    def test_inside_the_last_five_hours(self):
        self.assertTrue(dr.is_due(DEADLINE, DEADLINE - timedelta(hours=4, minutes=59)))

    def test_not_before_them(self):
        self.assertFalse(dr.is_due(DEADLINE, DEADLINE - timedelta(hours=5, minutes=1)))

    def test_a_late_run_still_reminds(self):
        """GitHub's scheduler can run hours late: better late than not at all."""
        self.assertTrue(dr.is_due(DEADLINE, DEADLINE - timedelta(minutes=20)))

    def test_a_run_shortly_before_the_window_waits_for_it(self):
        """GitHub ran the hourly schedule every 5-8 hours, so the window can pass unseen."""
        at = dr.first_reminder_at(DEADLINE)
        self.assertEqual(at, DEADLINE - timedelta(hours=5))
        self.assertEqual(dr.time_to_wait(at, DEADLINE - timedelta(hours=8)), timedelta(hours=3))

    def test_no_waiting_days_ahead_or_once_it_is_open(self):
        at = dr.first_reminder_at(DEADLINE)
        self.assertIsNone(dr.time_to_wait(at, DEADLINE - timedelta(hours=11)))
        self.assertIsNone(dr.time_to_wait(at, DEADLINE - timedelta(hours=4)))


EARLY = datetime(2026, 11, 21, 11, 0, tzinfo=timezone.utc)      # GW11: Sat 5am your time
EVENING = datetime(2026, 11, 21, 3, 0, tzinfo=timezone.utc)     # Fri 9pm your time


class AnEarlyDeadline(unittest.TestCase):
    """A 5am deadline put both emails in the night: the first moves to 9pm."""

    def test_the_first_goes_out_the_evening_before(self):
        self.assertEqual(dr.first_reminder_at(EARLY), EVENING)
        self.assertFalse(dr.is_due(EARLY, EVENING - timedelta(hours=1)))
        self.assertTrue(dr.is_due(EARLY, EVENING))

    def test_as_soon_as_the_news_before_it_is_read(self):
        read = EVENING - timedelta(minutes=25)
        self.assertTrue(dr.is_due(EARLY, read + timedelta(minutes=8), read))
        self.assertFalse(dr.is_due(EARLY, read + timedelta(minutes=8), read - timedelta(hours=3)))

    def test_says_its_time(self):
        self.assertIn("Sat 21 Nov, 5:00am", dr.message(_plan(gameweek=11), 11, EARLY, EVENING))

    def test_a_midday_deadline_keeps_five_hours(self):
        self.assertIsNone(dr.evening_before(DEADLINE))

    def _deadline(self, now, get):
        with mock.patch.object(dr.requests, "get", get):
            return dr.next_deadline(_plan(), now)

    def test_a_passed_deadline_moves_on_to_the_next(self):
        resp = mock.Mock()
        resp.json.return_value = {"events": [{"id": 9, "deadline_time": "2026-10-31T11:00:00Z"},
                                             {"id": 10, "deadline_time": "2026-11-06T18:30:00Z"},
                                             {"id": 11, "deadline_time": "2026-11-21T11:00:00Z"}]}
        self.assertEqual(self._deadline(NOW, mock.Mock(return_value=resp)), (10, DEADLINE))

    def test_falls_back_on_the_plan_if_fpl_is_down(self):
        down = mock.Mock(side_effect=dr.requests.ConnectionError("down"))
        self.assertEqual(self._deadline(NOW, down), (10, DEADLINE))

    def test_nothing_after_the_last_deadline(self):
        down = mock.Mock(side_effect=dr.requests.ConnectionError("down"))
        self.assertIsNone(self._deadline(DEADLINE + timedelta(days=1), down))


class TheMessage(unittest.TestCase):
    def test_first_line_carries_the_whole_call(self):
        first = dr.message(_plan(), 10, DEADLINE, NOW, "owner").splitlines()[0]
        self.assertEqual(first, "@owner GW10 deadline in 4h 40m: Calafiori out, Gabriel in. Gabriel captain.")

    def test_deadline_is_in_your_time(self):
        self.assertIn("Fri 6 Nov, 12:30pm", dr.message(_plan(), 10, DEADLINE, NOW))

    def test_lists_vice_lineup_and_bench(self):
        text = dr.message(_plan(), 10, DEADLINE, NOW)
        self.assertIn("**Captain:** Gabriel, **vice:** Haaland", text)
        self.assertIn("**XI:** Raya; Gabriel, Konsa; Haaland", text)
        self.assertIn("**Bench, in order:** Verbruggen, Botman", text)

    def test_says_when_to_hold(self):
        plan = _plan()
        _week(plan).update(transfers_out=[], transfers_in=[])
        self.assertIn("No transfer, save it", dr.message(plan, 10, DEADLINE, NOW))

    def test_says_when_a_transfer_costs_a_hit(self):
        plan = _plan()
        _week(plan).update(hits=1, hit_cost=4)
        self.assertIn("Calafiori out, Gabriel in (a −4 hit)", dr.message(plan, 10, DEADLINE, NOW))

    def test_says_when_to_play_a_chip(self):
        plan = _plan(chip_plan={"scenarios": [{"plan": [{"chip": "3xc", "now": True, "player": "Haaland",
                                                         "value": 8.0}]}]})
        text = dr.message(plan, 10, DEADLINE, NOW)
        self.assertIn("Play Triple Captain on Haaland.", text.splitlines()[0])
        self.assertIn("**Chip:** Triple Captain on Haaland", text)

    def test_never_orders_a_free_hit_it_has_no_team_for(self):
        plan = _plan(chip_plan={"scenarios": [{"plan": [{"chip": "freehit", "now": True, "value": 7.5,
                                                         "player": None}]}]})
        text = dr.message(plan, 10, DEADLINE, NOW)
        self.assertNotIn("Play", text.splitlines()[0])
        self.assertIn("**Chip:** none. The planner rates a Free Hit +7.5", text)

    def test_a_free_hit_comes_with_its_team(self):
        fh = {"gameweek": 10, "play": True, "gain": 7.6, "captain_id": 7, "vice_captain_id": 411,
              "starting_xi": [_player(9, "Sánchez", "GKP"), _player(7, "Saka", "MID"), _player(411, "Haaland", "FWD")],
              "bench": [_player(8, "Henderson", "GKP")]}
        plan = _plan(free_hit=fh, team={"free_transfers": 1},
                     chip_plan={"scenarios": [{"plan": [{"chip": "freehit", "now": True, "value": 7.6,
                                                         "player": None}]}]})
        text = dr.message(plan, 10, DEADLINE, NOW)
        self.assertEqual(text.splitlines()[0], "GW10 deadline in 4h 40m: Play your Free Hit. Saka captain.")
        self.assertIn("**Chip:** Free Hit, +7.6 on your own XI this week", text)
        self.assertIn("**XI:** Sánchez; Saka; Haaland", text)
        self.assertIn("comes back for GW11 with 1 free transfer, as now", text)
        self.assertNotIn("Calafiori", text)

    def test_a_free_hit_for_later_is_not_this_weeks_team(self):
        fh = {"gameweek": 10, "play": False, "gain": 2.0, "captain_id": 7, "vice_captain_id": 411,
              "starting_xi": [_player(7, "Saka", "MID")], "bench": []}
        text = dr.message(_plan(free_hit=fh), 10, DEADLINE, NOW)
        self.assertIn("Calafiori out, Gabriel in. Gabriel captain.", text.splitlines()[0])

    def test_no_chip_plan_is_no_chip(self):
        self.assertIn("**Chip:** none this week", dr.message(_plan(chip_plan=None), 10, DEADLINE, NOW))

    def test_news_only_about_players_in_the_plan(self):
        items = [{"player_id": 447, "name": "Botman", "status": "rotation_risk"},
                 {"player_id": 4, "name": "Gabriel", "status": "doubtful"},
                 {"player_id": 411, "name": "Haaland", "status": "expected_to_start"},
                 {"player_id": 999, "name": "Someone", "status": "out"}]
        text = dr.message(_plan(team_news={"items": items}), 10, DEADLINE, NOW)
        self.assertIn("**News:** Botman could be benched, Gabriel doubtful", text)
        self.assertNotIn("Someone", text)

    def test_warns_if_the_plan_is_for_another_gameweek(self):
        text = dr.message(_plan(gameweek=9), 11, DEADLINE, NOW)
        self.assertIn("no plan for it yet", text.splitlines()[0])
        self.assertNotIn("Calafiori", text)

    def test_warns_if_the_plan_is_old(self):
        plan = _plan(generated_at=(NOW - timedelta(hours=11)).isoformat())
        self.assertIn("refresh may be stuck", dr.message(plan, 10, DEADLINE, NOW))
        self.assertNotIn("refresh may be stuck", dr.message(_plan(), 10, DEADLINE, NOW))


class OncePerGameweek(unittest.TestCase):
    """Five hourly runs land inside the window; only the first may email."""

    def _run(self, comments, now=NOW, test=False, argv=()):
        calls = []

        def github(method, path, **kwargs):
            calls.append((method, path, kwargs.get("json")))
            if path == "issues" and method == "GET":
                return [{"number": 7, "title": dr.REMINDER_ISSUE_TITLE}]
            return comments if method == "GET" else {"number": 7}

        real = dr.datetime
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "optimized_team.json"
            path.write_text(json.dumps(_plan()))
            clock = mock.Mock(wraps=real)
            clock.now.return_value = now
            with mock.patch.object(dr, "FRONTEND_JSON_PATH", path), \
                 mock.patch.object(dr, "datetime", clock), \
                 mock.patch.object(dr, "next_deadline", return_value=(10, DEADLINE)), \
                 mock.patch.object(dr, "_github", github), \
                 mock.patch.dict(os.environ, {"TEST": "true" if test else ""}):
                dr.main(list(argv))
        return [c for c in calls if c[0] == "POST"], calls

    def test_posts_when_nothing_was_sent(self):
        posts, _ = self._run([])
        self.assertEqual(len(posts), 1)
        self.assertEqual(posts[0][1], "issues/7/comments")
        self.assertIn(dr._marker(10), posts[0][2]["body"])

    def test_not_twice(self):
        posts, _ = self._run([{"body": f"earlier\n{dr._marker(10)}"}])
        self.assertEqual(posts, [])

    def test_last_weeks_reminder_does_not_count(self):
        posts, _ = self._run([{"body": dr._marker(9)}])
        self.assertEqual(len(posts), 1)

    def test_too_early_never_touches_github(self):
        posts, calls = self._run([], now=DEADLINE - timedelta(hours=30))
        self.assertEqual(calls, [])

    def test_a_test_goes_out_early_and_does_not_use_up_the_reminder(self):
        posts, _ = self._run([{"body": dr._marker(10)}], now=DEADLINE - timedelta(hours=30), test=True)
        self.assertEqual(len(posts), 1)
        self.assertNotIn(dr._marker(10), posts[0][2]["body"])

    def test_waiting_sleeps_and_sends_nothing(self):
        with mock.patch.object(dr.time, "sleep") as sleep:
            _, calls = self._run([], now=DEADLINE - timedelta(hours=8), argv=["--wait"])
        sleep.assert_called_once_with(3 * 3600)
        self.assertEqual(calls, [])

    def test_a_test_never_waits(self):
        with mock.patch.object(dr.time, "sleep") as sleep:
            self._run([], now=DEADLINE - timedelta(hours=8), test=True, argv=["--wait"])
        sleep.assert_not_called()

    def test_preview_sends_nothing(self):
        with mock.patch("builtins.print"):
            _, calls = self._run([], argv=["--preview"])
        self.assertEqual(calls, [])


class TheSecondReminder(unittest.TestCase):
    """After the last news read, about two hours out, a second email says what changed."""
    MARK = DEADLINE - timedelta(hours=2)
    LATE = MARK + timedelta(minutes=10)

    def _first(self, plan=None):
        return dr.message(plan or _plan(), 10, DEADLINE, NOW)

    def test_due_only_once_the_last_read_is_in(self):
        self.assertTrue(dr.is_final(DEADLINE, self.LATE, self.MARK + timedelta(minutes=5)))
        self.assertFalse(dr.is_final(DEADLINE, self.LATE, self.MARK - timedelta(minutes=5)))
        self.assertFalse(dr.is_final(DEADLINE, self.LATE, None))
        self.assertFalse(dr.is_final(DEADLINE, self.MARK - timedelta(minutes=5), self.MARK - timedelta(minutes=9)))

    def _final(self, plan, earlier=None):
        return dr.message(plan, 10, DEADLINE, self.LATE, "owner", final=True,
                          earlier=self._first() if earlier is None else earlier)

    def test_says_when_nothing_changed(self):
        first = self._final(_plan()).splitlines()[0]
        self.assertEqual(first, "@owner GW10 final plan, deadline in 1h 50m: nothing changed since your "
                                "last reminder. Calafiori out, Gabriel in. Gabriel captain.")

    def test_says_what_changed(self):
        first = self._final(_plan(captain_id=411, vice_captain_id=4)).splitlines()[0]
        self.assertIn("changed since your last reminder: captain.", first)
        self.assertIn("Haaland captain.", first)

    def test_warns_a_new_transfer_costs_a_hit(self):
        plan = _plan()
        _week(plan).update(transfers_out=[{"name": "Murillo"}], transfers_in=[{"name": "Hill"}])
        text = self._final(plan)
        self.assertIn("changed since your last reminder: transfers", text.splitlines()[0])
        self.assertIn("another one costs a −4", text)

    def test_the_same_xi_in_another_order_is_no_change(self):
        plan = _plan()
        plan["starting_xi"] = [plan["starting_xi"][i] for i in (0, 2, 1, 3)]
        self.assertIn("nothing changed", self._final(plan).splitlines()[0])

    def test_a_new_bench_order_is_a_change(self):
        plan = _plan()
        plan["bench"] = plan["bench"][::-1]
        self.assertIn("changed since your last reminder: bench order", self._final(plan).splitlines()[0])

    def test_a_free_hits_rated_value_moving_is_no_change(self):
        chip = lambda v: {"scenarios": [{"plan": [{"chip": "freehit", "now": True, "value": v, "player": None}]}]}
        earlier = self._first(_plan(chip_plan=chip(7.5)))
        self.assertIn("nothing changed", self._final(_plan(chip_plan=chip(7.4)), earlier).splitlines()[0])

    def test_without_a_first_reminder_it_just_gives_the_plan(self):
        text = dr.message(_plan(), 10, DEADLINE, self.LATE, "owner", final=True)
        self.assertEqual(text.splitlines()[0], "@owner GW10 final plan, deadline in 1h 50m. "
                                               "Calafiori out, Gabriel in. Gabriel captain.")

    def test_markers_do_not_match_each_other(self):
        self.assertNotIn(dr._marker(10), dr._marker(10, final=True))
        self.assertNotIn(dr._marker(1), dr._marker(10))

    def _run(self, comments, read_at):
        posts = []

        def github(method, path, **kwargs):
            if method == "POST":
                posts.append(kwargs["json"]["body"])
                return {"number": 7}
            return [{"number": 7, "title": dr.REMINDER_ISSUE_TITLE}] if path == "issues" else comments

        real = dr.datetime
        clock = mock.Mock(wraps=real)
        clock.now.return_value = self.LATE
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "optimized_team.json"
            path.write_text(json.dumps(_plan()))
            with mock.patch.object(dr, "FRONTEND_JSON_PATH", path), \
                 mock.patch.object(dr, "datetime", clock), \
                 mock.patch.object(dr, "next_deadline", return_value=(10, DEADLINE)), \
                 mock.patch.object(dr, "last_read", return_value=read_at), \
                 mock.patch.object(dr, "_github", github), \
                 mock.patch.dict(os.environ, {"TEST": ""}):
                dr.main([])
        return posts

    def test_sends_after_the_first(self):
        posts = self._run([{"body": self._first()}], self.MARK + timedelta(minutes=5))
        self.assertEqual(len(posts), 1)
        self.assertIn("final plan", posts[0])
        self.assertIn(dr._marker(10, final=True), posts[0])

    def test_only_once(self):
        posts = self._run([{"body": self._first()}, {"body": dr._marker(10, final=True)}],
                          self.MARK + timedelta(minutes=5))
        self.assertEqual(posts, [])

    def test_waits_for_the_last_read(self):
        posts = self._run([{"body": self._first()}], self.MARK - timedelta(minutes=30))
        self.assertEqual(posts, [])

    def test_a_late_first_reminder_goes_out_if_the_read_never_came(self):
        self.assertEqual(len(self._run([], self.MARK - timedelta(minutes=30))), 1)


class TheIssue(unittest.TestCase):
    def test_reuses_the_issue_even_if_closed(self):
        issues = [{"number": 3, "title": "Something else"},
                  {"number": 7, "title": dr.REMINDER_ISSUE_TITLE, "state": "closed"}]
        with mock.patch.object(dr, "_github", return_value=issues) as gh:
            self.assertEqual(dr._issue(), 7)
        self.assertEqual(gh.call_count, 1)

    def test_opens_it_the_first_time(self):
        with mock.patch.object(dr, "_github", side_effect=[[], {"number": 8}]) as gh:
            self.assertEqual(dr._issue(), 8)
        self.assertEqual(gh.call_args.args[:2], ("POST", "issues"))


if __name__ == "__main__":
    unittest.main()
