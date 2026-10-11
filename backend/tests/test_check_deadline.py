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


if __name__ == "__main__":
    unittest.main()
