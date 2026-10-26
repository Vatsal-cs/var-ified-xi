"""
The scheduled refresh's gate (check_deadline.py). Run from backend/:

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

import check_deadline

NOW = datetime(2026, 10, 13, 7, 0, tzinfo=timezone.utc)
BOOT = {"events": [{"id": 6, "is_current": True}]}


def _fixtures(finished=True, last_kickoff="2026-10-12T19:00:00Z"):
    return [{"kickoff_time": "2026-10-11T15:30:00Z", "finished_provisional": True},
            {"kickoff_time": last_kickoff, "finished_provisional": finished}]


class AfterGameweek(unittest.TestCase):
    def _run(self, fixtures, generated):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "optimized_team.json"
            path.write_text(json.dumps({"generated_at": generated.isoformat()}))
            resp = mock.Mock(); resp.json.return_value = fixtures
            with mock.patch.object(check_deadline.requests, "get", return_value=resp), \
                 mock.patch.object(check_deadline, "FRONTEND_JSON_PATH", path):
                return check_deadline._finished_since_refresh(BOOT, NOW)

    def test_runs_once_after_the_last_match(self):
        self.assertTrue(self._run(_fixtures(), NOW - timedelta(days=2)))

    def test_not_again_once_refreshed(self):
        self.assertFalse(self._run(_fixtures(), NOW - timedelta(hours=1)))

    def test_not_while_a_match_is_unfinished(self):
        self.assertFalse(self._run(_fixtures(finished=False), NOW - timedelta(days=2)))


class StandingsConfirmed(unittest.TestCase):
    """GW8 2026-27: the post-gameweek run read the table before FPL added
    bonus points and autosubs, and showed you 4th until the next deadline."""
    def _run(self, data_checked, league):
        boot = {"events": [{"id": 8, "is_current": True, "data_checked": data_checked}]}
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "optimized_team.json"
            path.write_text(json.dumps({"league": league}))
            with mock.patch.object(check_deadline, "FRONTEND_JSON_PATH", path):
                return check_deadline._standings_confirmed_since_refresh(boot)

    def test_runs_when_the_table_was_read_provisional(self):
        self.assertTrue(self._run(True, {"gameweek_read": 8, "final": False}))

    def test_runs_when_the_table_predates_the_flag(self):
        self.assertTrue(self._run(True, {"gameweek_read": 8}))

    def test_not_before_fpl_confirms(self):
        self.assertFalse(self._run(False, {"gameweek_read": 8, "final": False}))

    def test_not_again_once_final(self):
        self.assertFalse(self._run(True, {"gameweek_read": 8, "final": True}))

    def test_not_without_a_league(self):
        self.assertFalse(self._run(True, None))


if __name__ == "__main__":
    unittest.main()
