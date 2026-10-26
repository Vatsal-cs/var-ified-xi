# No hits before GW9 (October 2026) — not adopted

Pre-registered in `PREREGISTRATION.md` (commit 652ddfe): the shipping
procedure with hit advice ignored before GW9, against production, in the
simulator's paired branch test over GW2-8 (each decision scored over the next
six gameweeks from the same position). 3 seeds per season, `--bag-size 1`.

| | 2024-25 | 2025-26 | Pooled |
|---|---:|---:|---:|
| Branch test, no early hits − production | +41 [−23, +151] | 0 | +41, won 3 of 6 — **no detectable effect** |

Not "better" (2025-26 isn't ahead), so production keeps following hit advice
from GW2.

What the 15 changed decisions say is more useful than the total:

| Season | Decisions changed | Value of skipping the hit (6 GWs) |
|---|---:|---|
| 2024-25 | 11 over 3 seeds | GW3 **+52, +54, +50**; every other week −30, −17, −4, 0, 0, +4, +6, +7 (net −34) |
| 2025-26 | 0 | production advised no hits at all in GW2-8 |

The whole effect is one decision: the GW3 2024-25 hit on De Bruyne
(projected 10.5 after his start). Without it, early hits were slightly
*positive*. A blanket early-season ban would mostly be insurance against
that one kind of week, and the harness can't tell that from luck. The
underlying problem it points at, early-season over-projection after a big
game (research/2026-10-top-gap §4), is a projection issue to fix in the model
rather than in the hit rule.

## Reproduce

```bash
research/2026-10-early-hits/run.sh
python -m data_engine.evaluation research/2026-10-early-hits/eh_*.json \
       --reference branch:production --variants branch:production_early_nohits --block 1
```
