"""After a Free Hit the team goes back to the squad it had before it."""

import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_engine import entry_data  # noqa: E402

PICKS = {
    10: {"active_chip": None, "picks": [{"element": 1}, {"element": 2}],
         "entry_history": {"bank": 3}},
    11: {"active_chip": "freehit", "picks": [{"element": 8}, {"element": 9}],
         "entry_history": {"bank": 0}},
    12: {"active_chip": "bboost", "picks": [{"element": 1}, {"element": 5}],
         "entry_history": {"bank": 1}},
}


def fake_picks(entry_id, gameweek):
    return PICKS[gameweek]


class OwnedPicks(unittest.TestCase):
    @mock.patch.object(entry_data, "fetch_picks", side_effect=fake_picks)
    def test_free_hit_week_reads_the_week_before(self, _):
        got = entry_data.owned_picks(1, 11)
        self.assertEqual([p["element"] for p in got["picks"]], [1, 2])
        self.assertEqual(got["entry_history"]["bank"], 3)

    @mock.patch.object(entry_data, "fetch_picks", side_effect=fake_picks)
    def test_other_weeks_are_read_as_they_are(self, _):
        self.assertIs(entry_data.owned_picks(1, 10), PICKS[10])
        self.assertIs(entry_data.owned_picks(1, 12), PICKS[12])


if __name__ == "__main__":
    unittest.main()
