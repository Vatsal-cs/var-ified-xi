"""
The final refresh before a deadline (final_refresh.py) and the read it forces
(team_news.get). Run from backend/:

    python -m unittest discover -s tests -v
"""
import json
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config
import deadline_reminder as dr
import final_refresh as fr
from data_engine import team_news

DEADLINE = datetime(2026, 11, 6, 18, 30, tzinfo=timezone.utc)
MARK = DEADLINE - timedelta(hours=2)


class WhenItRefreshes(unittest.TestCase):
    def test_not_before_the_two_hour_mark(self):
        self.assertFalse(fr.should_refresh(DEADLINE, MARK - timedelta(minutes=1), None))

    def test_at_the_mark_if_the_news_is_older(self):
        self.assertTrue(fr.should_refresh(DEADLINE, MARK, MARK - timedelta(hours=1)))

    def test_a_late_run_still_refreshes(self):
        now = DEADLINE - timedelta(minutes=40)
        self.assertTrue(fr.should_refresh(DEADLINE, now, MARK - timedelta(hours=1)))

    def test_not_if_the_news_was_read_since_the_mark(self):
        self.assertFalse(fr.should_refresh(DEADLINE, MARK + timedelta(minutes=30), MARK + timedelta(minutes=5)))

    def test_not_too_close_to_the_deadline(self):
        self.assertFalse(fr.should_refresh(DEADLINE, DEADLINE - timedelta(minutes=10), None))

    def test_a_run_before_the_mark_waits_for_it(self):
        self.assertEqual(config.news_read_marks(DEADLINE), [MARK])
        self.assertEqual(dr.time_to_wait(MARK, MARK - timedelta(hours=3)), timedelta(hours=3))

    def test_a_run_days_before_does_not_wait(self):
        self.assertIsNone(dr.time_to_wait(MARK, MARK - timedelta(hours=10)))

    def test_an_early_deadline_reads_before_the_evening_email_too(self):
        early = datetime(2026, 11, 21, 11, 0, tzinfo=timezone.utc)        # Sat 5am your time
        evening = datetime(2026, 11, 21, 2, 30, tzinfo=timezone.utc)      # Fri 8:30pm
        self.assertEqual(config.news_read_marks(early), [evening, early - timedelta(hours=2)])
        self.assertTrue(fr.should_refresh(early, evening, evening - timedelta(hours=1)))
        self.assertFalse(fr.should_refresh(early, evening + timedelta(hours=2), evening + timedelta(minutes=3)))
        self.assertTrue(fr.should_refresh(early, early - timedelta(hours=2), evening + timedelta(minutes=3)))


class TheForcedRead(unittest.TestCase):
    """Inside the last two hours an older read isn't reused, however recent."""

    def _get(self, read_at, now):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "team_news.json"
            path.write_text(json.dumps({"gameweek": 10, "fetched_at": read_at.isoformat(), "errors": [],
                                        "prompt_version": team_news.PROMPT_VERSION, "items": []}))
            fresh = {"gameweek": 10, "fetched_at": now.isoformat(), "items": []}
            with mock.patch.object(config, "TEAM_NEWS_PATH", path), \
                 mock.patch.object(team_news, "enabled", return_value=True), \
                 mock.patch.object(team_news, "_now", return_value=now), \
                 mock.patch.object(team_news, "_log_calls"), \
                 mock.patch.object(team_news, "_keep_calls"), \
                 mock.patch.object(team_news, "fetch", return_value=fresh) as fetch:
                team_news.get([], 10, DEADLINE)
        return fetch.called

    def test_reads_again_at_the_mark_even_if_the_last_read_is_recent(self):
        self.assertTrue(self._get(MARK - timedelta(minutes=30), MARK + timedelta(minutes=1)))

    def test_reuses_a_recent_read_before_the_mark(self):
        self.assertFalse(self._get(MARK - timedelta(hours=2), MARK - timedelta(minutes=1)))

    def test_reuses_a_read_from_inside_the_window(self):
        self.assertFalse(self._get(MARK + timedelta(minutes=1), MARK + timedelta(minutes=30)))


class WhenGeminiIsBusy(unittest.TestCase):
    """GW10's 9:55 read: 503s lost six clubs and forgot that Konsa was doubtful."""

    def setUp(self):
        team_news._gemini_model[0] = None
        self.addCleanup(lambda: team_news._gemini_model.__setitem__(0, None))

    def _reply(self, status):
        r = mock.Mock(status_code=status, text="")
        r.json.return_value = {"candidates": [{"content": {"parts": [{"text": "ok"}]}}]}
        r.raise_for_status.side_effect = None if status == 200 else RuntimeError(str(status))
        return r

    def _call(self, statuses):
        with mock.patch.dict("os.environ", {"GEMINI_API_KEY": "x"}), \
             mock.patch.object(config, "TEAM_NEWS_GEMINI_MODELS", ["a", "b"]), \
             mock.patch.object(team_news.time, "sleep"), \
             mock.patch.object(team_news.requests, "post",
                               side_effect=[self._reply(s) for s in statuses]) as post:
            return team_news._call_gemini("prompt"), post

    def test_tries_again(self):
        text, post = self._call([503, 200])
        self.assertEqual(text, "ok")
        self.assertEqual(post.call_count, 2)

    def test_falls_back_to_the_next_model(self):
        text, _ = self._call([503, 503, 503, 200])
        self.assertEqual(text, "ok")
        self.assertEqual(team_news._gemini_model[0], "b")

    def test_says_so_if_every_model_is_busy(self):
        with self.assertRaises(RuntimeError):
            self._call([503] * 6)

    def test_a_failed_club_keeps_its_last_calls(self):
        konsa = {"name": "Konsa", "club": "Arsenal", "status": "doubtful"}
        other = {"name": "Barnes", "club": "Newcastle", "status": "no_news"}
        news = {"items": [], "failed_clubs": ["Arsenal"]}
        team_news._keep_earlier_calls(news, {"items": [konsa, other]})
        self.assertEqual(news["items"], [konsa])

    def test_nothing_to_keep_if_the_read_worked(self):
        news = {"items": [], "failed_clubs": []}
        team_news._keep_earlier_calls(news, {"items": [{"club": "Arsenal"}]})
        self.assertEqual(news["items"], [])


if __name__ == "__main__":
    unittest.main()
