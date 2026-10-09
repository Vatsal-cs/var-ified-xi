"""
Tests for your own armband (main._apply_armband_override). Run from backend/:

    python -m unittest discover -s tests -v
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

import config
import main


def _setup():
    result = {"starting_ids": [1, 2, 3], "captain_id": 1, "vice_captain_id": 2,
              "total_predicted_points": 20.0}
    plan = {"weeks": [{"captain_id": 1}]}
    preds = pd.DataFrame({"player_id": [1, 2, 3], "predicted_points": [7.0, 6.0, 4.0]})
    return result, plan, preds


class ArmbandOverride(unittest.TestCase):
    def _run(self, override, gameweek=6):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "overrides.json"
            path.write_text(json.dumps(override))
            result, plan, preds = _setup()
            with mock.patch.object(config, "OVERRIDES_PATH", path):
                model = main._apply_armband_override(result, plan, preds, gameweek)
            return model, result, plan

    def test_applies_for_its_gameweek(self):
        model, result, plan = self._run({"gameweek": 6, "captain_id": 2, "vice_captain_id": 1})
        self.assertEqual((result["captain_id"], result["vice_captain_id"]), (2, 1))
        self.assertEqual(plan["weeks"][0]["captain_id"], 2)
        self.assertEqual(model, {"model_captain_id": 1, "model_vice_captain_id": 2})
        self.assertEqual(result["total_predicted_points"], 19.0)   # armband moves 7 -> 6

    def test_expires_after_its_gameweek(self):
        model, result, _ = self._run({"gameweek": 6, "captain_id": 2, "vice_captain_id": 1},
                                     gameweek=7)
        self.assertIsNone(model)
        self.assertEqual(result["captain_id"], 1)

    def test_ignored_if_not_in_the_xi(self):
        model, result, _ = self._run({"gameweek": 6, "captain_id": 99, "vice_captain_id": 1})
        self.assertIsNone(model)
        self.assertEqual(result["captain_id"], 1)

    def test_no_file_no_change(self):
        result, plan, preds = _setup()
        with mock.patch.object(config, "OVERRIDES_PATH", Path("/nonexistent/overrides.json")):
            self.assertIsNone(main._apply_armband_override(result, plan, preds, 6))
        self.assertEqual(result["captain_id"], 1)


if __name__ == "__main__":
    unittest.main()
