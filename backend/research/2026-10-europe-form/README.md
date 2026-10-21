# Form in European, cup and international games (October 2026) — stopped at step 1

Pre-registered in `PREREGISTRATION.md` (commit 485470c) as three gated steps.
Step 1 asks whether that form predicts the model's misses at all; it didn't,
so steps 2 and 3 never ran (`step1_output.txt`).

Midfielders and forwards projected 2.5+ who played such a game in the 30
days before (3,991 player-gameweeks, 2024-25 and 2025-26):

| | Projected | Scored |
|---|---:|---:|
| Scored or assisted in those games (1,308) | 3.91 | 3.93 |
| Didn't (2,683) | 3.57 | 3.54 |
| **Difference in misses** | | **+0.04 [−0.21, +0.29]** (2024-25 −0.12, 2025-26 +0.20) |

Players who score in Europe do score more in the Premier League — and the
model already projects them that much higher, from their league form,
chances, price and ownership. Opponent strength made no difference (misses
+0.02 against strong and weak opponents alike), nor did shots on target.
Nothing is built; the load features (rest, rotation, travel) stay as shipped.

    python research/2026-10-europe-form/step1_signal.py
