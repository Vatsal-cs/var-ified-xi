"""Fill the ESPN cache for the seasons the test uses (run once, then the
backtests read from disk)."""
import logging, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S")
for n in ("data_engine.historical_data", "urllib3"):
    logging.getLogger(n).setLevel(logging.WARNING)
from data_engine import historical_data, other_matches as om
for i, season in enumerate(sys.argv[1:] or ["2024-25", "2025-26", "2022-23", "2023-24"]):
    raw = historical_data.fetch_season(season, season_index=i)
    historical_data.attach_other_matches(raw, season, i)
    print(season, raw[om.FEATURES].mean().round(3).to_dict(), flush=True)
