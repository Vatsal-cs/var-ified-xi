# Ownership as a model input, actually filled in — pre-registration
Written 2026-10-20 14:38 MDT, before any run.

Why (found in the GW7 audit): selected_by_percent has been in FEATURE_COLUMNS
all along, but every training row held 0 — the archive keeps ownership under
another name and this season's rows never carried it — so neither model ever
split on it (zero gain), while live prediction rows held real percentages
(mean 2.2, up to 75). Ownership is the crowd's read of quality and minutes,
the one input that isn't in the model at all.

## Variant (backtest.py "ownership")
production with config.OWNERSHIP_FEATURE = True: training rows get the share
of managers owning the player that gameweek, in percent (archive: selections /
(total selections / 15); this season: the same from FPL's per-gameweek
`selected`). Live rows already carry FPL's selected_by_percent.

## Primary — backtest, points
production vs ownership, seeds 42, 7, 13, 101, 2024; 2024-25 (trained on
itself) and 2025-26 (plus 2024-25); --bag-size 1. ACCEPT only if "better"
(pooled 95% CI above zero AND ahead in both seasons); then ONCE on 2022-23 and
2023-24, logged in config's "Uses so far"; ship only if > 0 in both.
Otherwise the flag stays off and selected_by_percent is dropped from
FEATURE_COLUMNS (it does nothing, and a column that is 0 in training but not
live is a trap for the next change).
