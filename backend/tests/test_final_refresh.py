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
        self.assertEqual(dr.time_to_wait(DEADLINE, MARK - timedelta(hours=3), 2), timedelta(hours=3))

    def test_a_run_days_before_does_not_wait(self):
        self.assertIsNone(dr.time_to_wait(DEADLINE, MARK - timedelta(hours=10), 2))


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


if __name__ == "__main__":
    unittest.main()
