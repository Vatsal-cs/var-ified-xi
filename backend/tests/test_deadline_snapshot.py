"""Deadline snapshots (data_engine/deadline_snapshot.py): the right gameweek
and matches, one odds pull per gameweek, and the API key never logged."""
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

import requests

from data_engine import deadline_snapshot as ds

UTC = timezone.utc


def _boot():
    return {
        "events": [
            {"id": 1, "deadline_time": "2026-08-15T10:00:00Z"},
            {"id": 11, "deadline_time": "2026-11-21T11:00:00Z"},
            {"id": 12, "deadline_time": "2026-11-28T11:00:00Z"},
            {"id": 13, "deadline_time": "2026-12-02T18:00:00Z"},
        ],
        "elements": [{"id": 1, "web_name": "A", "ep_next": "4.0", "extra": 1}],
        "teams": [{"id": 1, "name": "Arsenal", "short_name": "ARS", "strength": 5}],
    }


class Windows(unittest.TestCase):
    def test_season_label(self):
        self.assertEqual(ds.season_label(_boot()), "2026-27")

    def test_next_deadline_and_the_one_after(self):
        gw, dl, nxt = ds.next_deadline(_boot(), datetime(2026, 11, 25, tzinfo=UTC))
        self.assertEqual(gw, 12)
        self.assertEqual(nxt, datetime(2026, 12, 2, 18, tzinfo=UTC))

    def test_matches_between_deadlines_only(self):
        dl, nxt = datetime(2026, 11, 28, 11, tzinfo=UTC), datetime(2026, 12, 2, 18, tzinfo=UTC)
        events = [{"id": "a", "commence_time": "2026-11-28T12:30:00Z"},
                  {"id": "b", "commence_time": "2026-12-02T19:30:00Z"},
                  {"id": "c", "commence_time": "2026-11-28T09:00:00Z"}]
        self.assertEqual([e["id"] for e in ds.gameweek_events(events, dl, nxt)], ["a"])

    def test_snapshot_keeps_listed_fields_only(self):
        snap = ds.fpl_snapshot(_boot(), [{"event": 12}, {"event": 13}], 12,
                               datetime(2026, 11, 28, tzinfo=UTC))
        self.assertNotIn("extra", snap["players"][0])
        self.assertEqual(len(snap["fixtures"]), 1)


class Key(unittest.TestCase):
    def test_key_never_logged(self):
        secret = "sk-test-123"
        err = requests.ConnectionError(f"failed: https://x/?apiKey={secret}")
        with mock.patch.object(ds.requests, "get", side_effect=err), \
             self.assertLogs(ds.logger, level="WARNING") as logs:
            self.assertEqual(ds._odds_get("https://x", secret), (None, None))
        self.assertNotIn(secret, " ".join(logs.output))


class OncePerGameweek(unittest.TestCase):
    def _run(self, now, key="k"):
        tmp = Path(tempfile.mkdtemp())
        with mock.patch.object(ds, "OUT_DIR", tmp), \
             mock.patch.object(ds.fetch_data, "fetch_bootstrap_static", return_value=_boot()), \
             mock.patch.object(ds.fetch_data, "fetch_fixtures", return_value=[]), \
             mock.patch.object(ds, "odds_snapshot", return_value={"events": [1]}) as odds, \
             mock.patch.dict(ds.os.environ, {"ODDS_API_KEY": key}):
            ds.main(now)
            ds.main(now)
        return tmp, odds

    def test_one_odds_pull_inside_the_window(self):
        tmp, odds = self._run(datetime(2026, 11, 28, 3, tzinfo=UTC))  # 8h before GW12
        self.assertEqual(odds.call_count, 1)
        self.assertTrue((tmp / "2026-27" / "gw12_odds.json.gz").exists())
        self.assertTrue((tmp / "2026-27" / "gw12_fpl.json.gz").exists())

    def test_no_odds_outside_the_window_or_without_a_key(self):
        _, odds = self._run(datetime(2026, 11, 27, 11, tzinfo=UTC))  # 24h before
        self.assertEqual(odds.call_count, 0)
        _, odds = self._run(datetime(2026, 11, 28, 3, tzinfo=UTC), key="")
        self.assertEqual(odds.call_count, 0)


if __name__ == "__main__":
    unittest.main()
