"""
Tests for the weeks-after-next availability rule (horizon_availability.py).
Run from backend/:

    python -m unittest discover -s tests -v
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

import config
from data_engine import horizon_availability as ha

DEADLINE = pd.Timestamp("2026-10-10 10:00")


def rows(status, news, gws=(6, 7, 8, 9), first=6, kickoffs=None):
    kickoffs = kickoffs or [DEADLINE + pd.Timedelta(days=7 * (g - first) + 1) for g in gws]
    return pd.DataFrame({"gw": list(gws), "status": status, "news": news,
                         "chance_of_playing": [0.0] + [None] * (len(gws) - 1),
                         "fixture_kickoff": kickoffs})


class ParseReturn(unittest.TestCase):
    def test_formats(self):
        self.assertEqual(ha.parse_return("Suspended until 02 Nov", DEADLINE),
                         ("suspended", pd.Timestamp("2026-11-02")))
        self.assertEqual(ha.parse_return("Hamstring injury - Expected back 13 Dec", DEADLINE),
                         ("expected", pd.Timestamp("2026-12-13")))
        self.assertEqual(ha.parse_return("Knee injury - Unknown return date", DEADLINE), (None, None))
        self.assertEqual(ha.parse_return("", DEADLINE), (None, None))

    def test_year_rolls_over(self):
        self.assertEqual(ha.parse_return("Expected back 05 Jan", pd.Timestamp("2026-12-20")),
                         ("expected", pd.Timestamp("2027-01-05")))


class Rule(unittest.TestCase):
    def test_next_week_never_touched(self):
        for status in ("i", "s"):
            r = rows(status, "")
            ha.apply(r, 6, DEADLINE)
            self.assertEqual(r.loc[0, "status"], status)
            self.assertEqual(r.loc[0, "chance_of_playing"], 0.0)

    def test_undated_suspension_is_one_match(self):
        r = rows("s", "")
        ha.apply(r, 6, DEADLINE)
        self.assertEqual(list(r["status"]), ["s", "a", "a", "a"])
        self.assertEqual(list(r["chance_of_playing"])[1:], [90.0, 90.0, 90.0])

    def test_dated_suspension_holds_until_the_date(self):
        # Kickoffs on 11 Oct, 18 Oct, 25 Oct, 1 Nov; banned until 25 Oct.
        r = rows("s", "Suspended until 25 Oct")
        ha.apply(r, 6, DEADLINE)
        self.assertEqual(list(r["status"]), ["s", "s", "a", "a"])

    def test_undated_injury_ramps(self):
        r = rows("i", "Knee injury - Unknown return date", gws=(6, 7, 8, 9, 10, 11))
        ha.apply(r, 6, DEADLINE)
        self.assertEqual(list(r["chance_of_playing"])[1:], [25.0, 40.0, 50.0, 60.0, 65.0])

    def test_dated_injury_steps_at_the_date(self):
        # Expected back 08 Nov: 18 Oct is 21 days short (out), 25 Oct and
        # 1 Nov within a fortnight (0.2), 8 Nov on the date (0.8).
        r = rows("i", "Hamstring injury - Expected back 08 Nov", gws=(6, 7, 8, 9, 10))
        ha.apply(r, 6, DEADLINE)
        self.assertEqual(list(r["status"]), ["i", "i", "a", "a", "a"])
        self.assertEqual(list(r["chance_of_playing"])[2:], [20.0, 20.0, 80.0])

    def test_left_the_club_and_doubts_untouched(self):
        for status in ("u", "n", "d", "a"):
            r = rows(status, "Has joined Lyon permanently.")
            before = r.copy()
            ha.apply(r, 6, DEADLINE)
            pd.testing.assert_frame_equal(r, before)

    def test_off_in_production_until_it_passes(self):
        self.assertFalse(config.HORIZON_AVAILABILITY)


if __name__ == "__main__":
    unittest.main()
