"""
Lineup choice after autosubs (data_engine/lineup.py). Run from backend/:

    python -m unittest discover -s tests -v
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from data_engine import lineup

# 2 GK (1-2), 5 DEF (3-7), 5 MID (8-12), 3 FWD (13-15)
POS = {1: 1, 2: 1, 3: 2, 4: 2, 5: 2, 6: 2, 7: 2,
       8: 3, 9: 3, 10: 3, 11: 3, 12: 3, 13: 4, 14: 4, 15: 4}
XP = {1: 4, 2: 2, 3: 5, 4: 4.5, 5: 4, 6: 3.9, 7: 1, 8: 6, 9: 5, 10: 2.8,
      11: 3.0, 12: 2.9, 13: 7, 14: 4.2, 15: 1}


class ChooseLineup(unittest.TestCase):
    def test_certain_starters_pick_the_top_projections(self):
        xi, bench, _ = lineup.choose_lineup(list(POS), POS, {p: 1.0 for p in POS}, XP)
        self.assertEqual(sorted(xi), [1, 3, 4, 5, 6, 8, 9, 11, 12, 13, 14])
        self.assertEqual(bench[0], 2)            # the reserve keeper sits first

    def test_rotation_risk_starts_with_cover_on_the_bench(self):
        # MID 10: a 50% starter worth 5.6 if he plays (xP 2.8), just below
        # MID 12's certain 2.9. Starting him with 12 first on the bench
        # expects 0.5 x 5.6 + 0.5 x 2.9 = 4.25 for that slot, not 2.9.
        play = {p: 1.0 for p in POS}
        play[10] = 0.5
        xi, bench, _ = lineup.choose_lineup(list(POS), POS, play, XP)
        self.assertIn(10, xi)
        self.assertEqual(bench[1], 12)

    def test_incomplete_squad_is_left_alone(self):
        squad = [p for p in POS if p != 15]
        self.assertIsNone(lineup.choose_lineup(squad, POS, {p: 1.0 for p in POS}, XP))


if __name__ == "__main__":
    unittest.main()
