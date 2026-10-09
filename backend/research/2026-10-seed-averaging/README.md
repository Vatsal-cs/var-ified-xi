# Seed averaging (October 2026) — shipped

Five copies of the two-stage model, each with a different seed, projections
averaged (`config.MODEL_BAG_SIZE = 5`). Pre-registered as **steadier picks at no
cost** (`PREREGISTRATION.md`): points not worse, accuracy not worse, and the picks
of independently-trained versions agreeing more often.

| | 2024-25 | 2025-26 | 2022-23 (held back) | 2023-24 (held back) |
|---|---:|---:|---:|---:|
| Starting XI shared between seeds | 75% → **87%** | 78% → **88%** | 75% → **86%** | 77% → **87%** |
| Points vs production (5 seeds) | +11 | +14 | +36 | −12 |
| MAE | 0.9957 → 0.9943 | 0.9114 → 0.9109 | 1.1302 → 1.1296 | 0.9703 → 0.9700 |

Captain agreement between seeds: 81% → 89% on the tuning seasons, 70% → 81% on
the held-back ones. Points pooled: +25 [−37, +92] tuning, +23 [−34, +82] held
back — not worse, which is what was required.

On the live team (8 Oct 2026), 6 independent single models and 6 independent
bags all chose Palmer → Saka with Groß as captain (`live_stability.json`). The
moves planned for later weeks matched between runs only 9% (single) and 12%
(bags) of the time: those weeks are near-ties, and averaging doesn't settle them.

## Reproduce

From `backend/`:

```bash
python research/2026-10-seed-averaging/stability.py "bag_*.json"    # tuning seasons
python research/2026-10-seed-averaging/stability.py "conf_*.json"   # held-back seasons
```
