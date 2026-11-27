# Early-season after-a-haul correction (November 2026) — not used

Pre-registered in `PREREGISTRATION.md` (commit 2fc51ea) before any run.
The correction took about a point off a player who scored 10+ in his last
match, up to GW14. The amount came from the other tuning season.

| Paired vs lagged_ratings (5 seeds) | Pooled | 2024-25 | 2025-26 | Runs ahead |
|---|---:|---:|---:|---:|
| haul_dampen | −7 [−36, +19] | −21 [−46, −1] | +14 [+0, +31] | 4 of 10 |

**No detectable effect; it split by season. Nothing goes to the held-back
seasons.**
- The miss it targets is real and holds in all four replayed seasons
  (research/2026-11-model-audit).
- Fixing the projection did not win points in a squad rebuilt every week:
  2025-26 gained 14 and 2024-25 lost 21.
- As the pre-registration said up front, this backtest can't see the
  transfer harm (buying after a haul, then selling). By the rule it stops
  here rather than moving on to the simulator.

Files: `research/2026-11-components/backtest_*.json` and `evaluation.txt`
(same run).
