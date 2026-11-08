# Team-news reader — how it will be judged
Written 2026-10-14, before the reader's first call.

There are no archived press conferences, so the reader can't be backtested.
It is judged live instead, from data/team_news_log.json (every call it makes,
with its source) against who actually played.

## What it changes now
`config.TEAM_NEWS_ADJUST = True`: an "out" call sets the player's chance of
playing to 0, a "doubtful" call to the reported chance (25–75), only when that
is worse than FPL's own flag and the source is at most 4 days old. "Rotation
risk" is shown on the dashboard and never applied.

## How it's judged, at the GW19 deadline (or 30 applied calls, whichever first)
For every applied call, against the gameweek's real minutes:
- **"Out" precision:** share of applied "out" calls where the player then
  played 0 minutes. Keep applying "out" only if ≥ 85%.
- **"Doubtful":** share that played under 60 minutes, against the predicted
  chance used. Keep applying only if the share is within 15 points of the
  average chance used, or more pessimistic.
- **Rotation risk (shown only):** share that didn't start. Worth turning into
  an adjustment only if ≥ 60% over at least 30 calls, and then only as a new
  pre-registered test.
- Also reported: how many hours earlier than FPL's own flag the reader
  flagged the same player, and the projected points the adjustments moved.

If "out" or "doubtful" misses its bar, TEAM_NEWS_ADJUST goes off for that
status and the reader stays display-only for it.

## Addendum, 2026-11-08: "expected to start" raises (written before it runs)
Why: in GW10 the reader said Mukiele would start, the model gave him a 32%
chance of playing 60+ minutes, and he started and scored 9 on the bench.
Up to then all 7 "expected to start" calls had started, but Mukiele was the
only one that disagreed with the model, so this is one case, not evidence.

What changes (`config.TEAM_NEWS_RAISE = True`): an "expected to start" call
with a source at most 4 days old that names him sets his chance of playing
to the reported start chance (when above FPL's) and his chance of playing
60+ to at least that chance × 0.93 (how often a starter lasts 60 minutes,
2024-25 and 2025-26). This gameweek only. Never when FPL flags him injured,
suspended or unavailable. A call that agrees with the model changes nothing
and isn't listed.

How it's judged, at the GW19 deadline (or 20 applied raises, whichever
first), from the "applied" list in each deadline's plan
(frontend/public/optimized_team.json in git history):
- **Raise accuracy:** share of applied raises where the player started.
  Keep raising only if that share is at least the average start chance used
  minus 15 points.
- Also reported: the raised players' points against their raised and
  unraised projections, and how often a raise changed the XI.

If it misses the bar, TEAM_NEWS_RAISE goes off and "expected to start" is
display-only again.
