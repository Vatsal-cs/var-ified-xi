# A second model that learns the first one's mistakes — result

**Not used. Stopped early once it could no longer pass.** Pre-registered in
PREREGISTRATION.md (commit 9b0c08e).

On 2024-25 the corrected model scored **−51** points against production
[−166, +53], behind in 3 of 4 completed seeds (`evaluation.txt`). The rule
needs it ahead in both tuning seasons, which a fifth 2024-25 seed can't
change, so the 2025-26 runs were stopped rather than finished.

It also predicted slightly worse on the season it wasn't fitted on (MAE
0.904 → 0.926 on 2025-26 with a 2024-25 corrector; 0.988 → 1.003 the other
way), and occasionally made large swings (+6.3 points on one projection):
the patterns in one season's misses don't carry to the next.

What did hold up, and is shown on the dashboard instead of being forced into
the model: expensive players in a poor run scored +0.34 a match more than
projected across both seasons — so the pick checks flag such players as
information, not as a reason to sell.
