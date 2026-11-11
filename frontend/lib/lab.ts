// File: lab.ts
// Path: var-ified-xi/frontend/lib/lab.ts
//
// Every study in backend/research, as the lab page shows it (app/lab). The
// numbers are copied from each study's README; the commits are when its plan
// (PREREGISTRATION.md) and its result (README.md) first entered the repo, so
// the page can show which came first. Add a study here when its folder lands.

export type Verdict = "shipped" | "worse" | "none";

/** A commit: short hash and author time. */
export type Commit = { hash: string; at: string };

/** When the plan and the result were committed. The same hash for both means
 *  they went in together, so the order can't be shown from the history. */
export type Proof = { plan?: Commit; result?: Commit };

/** One tested change, measured in points against the model at the time. */
export type LabTest = {
  label: string;
  /** Small print beside the label when it isn't the usual two-season backtest. */
  note?: string;
  est: number;
  lo: number;
  hi: number;
  /** 2024-25 and 2025-26, the tuning seasons. */
  seasons?: [number, number];
  /** 2022-23 and 2023-24, run once, only for a change that came out better. */
  heldBack?: [number, number];
  verdict: Verdict;
  question: string;
  finding: string;
  harness: string;
  proof: Proof;
};

/** A question answered with something other than a points total. */
export type LabCheck = {
  title: string;
  outcome: string;
  result: string;
  proof: Proof;
};

const BACKTEST = "Backtest: the squad rebuilt each week from that week's projections, 5 seeds a season.";
const SIMULATOR = "Season simulator: one squad carried all season under that season's real rules, 3 seeds a season.";
const BRANCH =
  "Paired branch test in the simulator: each week both versions decide from the same position and are scored on the next six weeks, 3 seeds a season.";

const c = (hash: string, at: string): Commit => ({ hash, at });
const both = (hash: string, at: string): Proof => ({ plan: c(hash, at), result: c(hash, at) });

const P = {
  ownership: { plan: c("e38a0bf", "2026-10-20T14:38:30-06:00"), result: c("2c238ee", "2026-10-20T16:00:54-06:00") },
  longForm: { plan: c("68c8331", "2026-10-31T16:28:52-06:00"), result: c("a86b796", "2026-10-31T17:16:39-06:00") },
  otherMatches: { plan: c("e3d27e6", "2026-10-15T05:06:27-06:00"), result: c("e6736f3", "2026-10-15T07:12:22-06:00") },
  seedAveraging: both("53b4074", "2026-10-08T23:38:45-06:00"),
  modelBatch: { plan: c("46669ab", "2026-10-31T18:42:53-06:00"), result: c("afa225a", "2026-11-01T06:11:32-06:00") },
  understat: { plan: c("6eb6a40", "2026-10-31T19:22:07-06:00"), result: c("afa225a", "2026-11-01T06:11:32-06:00") },
  lineup: { plan: c("a03050c", "2026-10-26T16:18:59-06:00"), result: c("4c680fe", "2026-10-26T16:48:04-06:00") },
  horizonDecay: { plan: c("ec79f7a", "2026-10-26T16:21:08-06:00"), result: c("5417906", "2026-10-26T17:32:00-06:00") },
  benchWeight: both("4d0fada", "2026-10-10T11:56:35-06:00"),
  opponentForm: { plan: c("d02d0f8", "2026-10-15T07:45:23-06:00"), result: c("44eddcd", "2026-10-15T09:23:36-06:00") },
  captainCrowd: { plan: c("f5a7d6e", "2026-11-01T11:49:29-06:00"), result: c("8af26ce", "2026-11-01T12:07:53-06:00") },
  laggedTeamForm: { plan: c("5176649", "2026-10-15T15:43:19-06:00"), result: c("bc03988", "2026-10-15T16:47:31-06:00") },
  horizonAvailability: both("f573e2f", "2026-10-08T21:04:24-06:00"),
  marketRatings: { plan: c("55d67c0", "2026-10-15T16:57:15-06:00"), result: c("204fed9", "2026-10-15T17:53:01-06:00") },
  teamFormAdd: { plan: c("d0cfc7a", "2026-10-15T12:50:59-06:00"), result: c("c9119d2", "2026-10-15T13:33:52-06:00") },
  projectionShrink: { plan: c("89892ac", "2026-10-14T21:06:43-06:00"), result: c("7796dff", "2026-10-14T22:11:58-06:00") },
  ratingsHindsight: { plan: c("7f62e4e", "2026-10-31T11:42:33-06:00"), result: c("6a1c527", "2026-10-31T12:47:39-06:00") },
  seasonStage: { plan: c("f2ce959", "2026-10-26T16:22:27-06:00"), result: c("5417906", "2026-10-26T17:32:00-06:00") },
  staleRatings: { plan: c("cdedaab", "2026-10-17T12:11:53-06:00"), result: c("8054ede", "2026-10-17T12:34:54-06:00") },
  formTilt: { plan: c("a16906c", "2026-10-17T13:13:45-06:00"), result: c("cb02ee7", "2026-10-17T13:55:47-06:00") },
  rotationCalibration: { plan: c("773db89", "2026-10-20T14:50:19-06:00"), result: c("c7f77ee", "2026-10-21T06:47:47-06:00") },
  marketReplace: { plan: c("773db89", "2026-10-20T14:50:19-06:00"), result: c("c7f77ee", "2026-10-21T06:47:47-06:00") },
  bookings: { plan: c("ac5d390", "2026-11-08T14:02:56-06:00"), result: c("4f2e6ed", "2026-11-08T14:19:40-06:00") },
  transferFlow: { plan: c("e571380", "2026-10-26T15:15:51-06:00"), result: c("2a74d6f", "2026-10-26T16:05:37-06:00") },
  residualModel: { plan: c("8e8ad7d", "2026-10-15T10:46:27-06:00"), result: c("cada453", "2026-10-15T11:00:02-06:00") },
  priceFeature: { plan: c("23d2b00", "2026-10-14T20:16:48-06:00"), result: c("71efa3a", "2026-10-14T21:29:54-06:00") },
  teamForm: both("dc01545", "2026-10-11T09:02:34-06:00"),
  projectionBias: { plan: c("6c7b16a", "2026-10-12T19:15:47-06:00"), result: c("b55fa79", "2026-10-12T19:34:18-06:00") },
  europeBias: both("44eddcd", "2026-10-15T09:23:36-06:00"),
  europeForm: { plan: c("8354e27", "2026-10-21T07:49:59-06:00"), result: c("2c3d5cb", "2026-10-21T07:51:03-06:00") },
  distributions: both("0774190", "2026-10-14T19:15:53-06:00"),
  historyCheck: { plan: c("52d61cb", "2026-10-17T12:51:30-06:00"), result: c("b4e838f", "2026-10-17T13:06:14-06:00") },
  upside: { plan: c("b53f571", "2026-11-01T12:16:03-06:00"), result: c("59f336d", "2026-11-01T13:11:22-06:00") },
  earlyHits: { plan: c("652ddfe", "2026-10-26T15:30:13-06:00"), result: c("2a74d6f", "2026-10-26T16:05:37-06:00") },
  teamNews: { plan: c("0774190", "2026-10-14T19:15:53-06:00") },
} satisfies Record<string, Proof>;

export const LAB_TESTS: LabTest[] = [
  // ---- Shipped ----
  {
    label: "Ownership as an input",
    est: 122, lo: 26, hi: 216, seasons: [59, 63], heldBack: [65, 14],
    verdict: "shipped",
    question: "Does the share of managers who own a player help predict his points?",
    finding:
      "It was already listed as an input, but it was 0 on every training row while live rows held real percentages, so the model never learned from it. Filled in properly, it won both tuning seasons and both held-back ones.",
    harness: BACKTEST, proof: P.ownership,
  },
  {
    label: "Ten-game and season-long form",
    est: 102, lo: 9, hi: 187, seasons: [33, 69], heldBack: [42, 19],
    verdict: "shipped",
    question: "Should form look further back than the last three to five games?",
    finding:
      "Every other form input looked back three to five games, so a good player in a cold month read much like a poor one on a hot run. Accuracy barely moved (MAE within ±0.003): the gain is in which players get picked, not in the size of the projections.",
    harness: BACKTEST, proof: P.longForm,
  },
  {
    label: "Cup, European and international matches",
    est: 87, lo: 13, hi: 159, seasons: [67, 20], heldBack: [43, 11],
    verdict: "shipped",
    question: "Do rest and load from games FPL doesn't show say who will be rotated?",
    finding:
      "Every cup, European and international match of every Premier League club, from ESPN's public feed, linked to 97–98% of regular players. Who played midweek, and for how long, is what moved points. Adding their goals and shots in those games didn't (further down).",
    harness: BACKTEST, proof: P.otherMatches,
  },
  {
    label: "Average five models trained on different seeds",
    est: 25, lo: -37, hi: 92, seasons: [11, 14], heldBack: [36, -12],
    verdict: "shipped",
    question: "Do five averaged models make steadier picks, at no cost in points?",
    finding:
      "Shipped on its own test, written down first: steadier picks at no cost. The starting XIs of independently trained versions agreed 86–88% of the time, up from 75–78%, in all four seasons, and points weren't worse (held back: +23 [−34, +82]).",
    harness: BACKTEST, proof: P.seedAveraging,
  },

  // ---- Worse ----
  {
    label: "Last season's minutes and per-90 record",
    est: -147, lo: -237, hi: -56, seasons: [-80, -67],
    verdict: "worse",
    question: "Does a player's previous season add anything to this season's form?",
    finding:
      "Worse in both seasons. Last season's record overlaps with price and ownership, which the model already has, and accuracy barely moved: the loss is in which players it picked.",
    harness: BACKTEST, proof: P.modelBatch,
  },
  {
    label: "Deeper trees (depth 6, not 4)",
    est: -145, lo: -252, hi: -39, seasons: [-34, -111],
    verdict: "worse",
    question: "Does a more flexible model pick better players?",
    finding: "Deeper trees fit more noise. Worse in both seasons, by 111 points in 2025-26.",
    harness: BACKTEST, proof: P.modelBatch,
  },
  {
    label: "Understat shot data",
    est: -111, lo: -198, hi: -27, seasons: [-14, -97],
    verdict: "worse",
    question: "Do shots, key passes, non-penalty xG, xGChain and xGBuildup help?",
    finding:
      "Linked to 99–100% of played rows, and accuracy didn't move. FPL's own per-match xG, xA and bonus data already describe shot volume and build-up; ten inputs that say nearly the same thing just give the trees more ways to split on noise.",
    harness: BACKTEST, proof: P.understat,
  },
  {
    label: "Pick the XI on points after autosubs",
    note: "simulator",
    est: -37, lo: -75, hi: -4, seasons: [-13, -24],
    verdict: "worse",
    question: "Should the starting XI be the one with the most expected points after autosubs?",
    finding:
      "Right in principle, worse in practice: 0 of 6 runs ahead. The less certain starters it promotes almost always played and scored less. Expected points already prices rotation risk about right.",
    harness: SIMULATOR, proof: P.lineup,
  },

  // ---- No detectable effect ----
  {
    label: "Goals and shots in cup and European games",
    est: 81, lo: -4, hi: 168, seasons: [69, 12],
    verdict: "none",
    question: "On top of rest and load, does what players did in those games help?",
    finding:
      "Ahead in 9 of 10 runs, but the interval crosses zero, so only rest and load shipped. Weighted by the opponent's strength, it did no better (−17).",
    harness: BACKTEST, proof: P.otherMatches,
  },
  {
    label: "Value later weeks more (0.95 a week, not 0.85)",
    note: "branch test",
    est: 60, lo: -109, hi: 239, seasons: [110, -49],
    verdict: "none",
    question: "Should the six-week planner discount later weeks less?",
    finding: "Helped in 2024-25 and hurt in 2025-26. The 0.85 stays, now as a tested setting rather than an argued one.",
    harness: BRANCH, proof: P.horizonDecay,
  },
  {
    label: "Count the bench at 3%, not 12%",
    est: 25, lo: -10, hi: 62,
    verdict: "none",
    question: "Does valuing bench players less move money into the starting XI and score more?",
    finding:
      "No weight (6%, 3% or 1%) came out better in the backtest. In the simulator, 3% changed 32 of 216 weekly decisions and did slightly worse on them (−36 [−85, +11]). The expensive bench came from the squad builder, not this weight.",
    harness: BACKTEST, proof: P.benchWeight,
  },
  {
    label: "Strength of recent opponents",
    est: 18, lo: -65, hi: 99, seasons: [8, 10],
    verdict: "none",
    question: "Does it matter who a player's recent form came against?",
    finding:
      "The model already sees each upcoming opponent's strength and each player's underlying chances (xG, xA); adjusting past form for the opponents faced adds nothing it can turn into points.",
    harness: BACKTEST, proof: P.opponentForm,
  },
  {
    label: "Form scaled by opponent strength",
    est: 11, lo: -45, hi: 66, seasons: [16, -5],
    verdict: "none",
    question: "Should xG, xGI and points be scaled by how strong each opponent was?",
    finding: "Ahead in 3 of 10 runs. Same reason as above: the opponent is already in the model.",
    harness: BACKTEST, proof: P.opponentForm,
  },
  {
    label: "The crowd's captain",
    est: 11, lo: -23, hi: 44, seasons: [20, -10],
    verdict: "none",
    question: "Should the armband go to the most-owned player within a point of the best projection?",
    finding:
      "The armband changed hands in 24% of gameweeks and the points came out even. Ownership is already an input, so the crowd's pick carries nothing the projection lacks.",
    harness: BACKTEST, proof: P.captainCrowd,
  },
  {
    label: "This season's team form, with last season's ratings",
    est: 6, lo: -118, hi: 123, seasons: [13, -7],
    verdict: "none",
    question: "Run exactly as live works, does this season's team form help?",
    finding: "Both sides rated teams on last season's ratings, as the live model must. No detectable effect, so team form stays off.",
    harness: BACKTEST, proof: P.laggedTeamForm,
  },
  {
    label: "Injured players' later weeks, by return dates",
    note: "branch test",
    est: 5, lo: -26, hi: 33, seasons: [5, 0],
    verdict: "none",
    question: "Should an injured player's later weeks count by his expected return, not a flat tenth?",
    finding: "It changed 11 of 222 weekly decisions, all in 2024-25, and none in 2025-26. Nothing measurable won.",
    harness: BRANCH, proof: P.horizonAvailability,
  },
  {
    label: "Team form from betting odds",
    est: 1, lo: -107, hi: 111, seasons: [4, -3],
    verdict: "none",
    question: "Does team form built from the goals the odds expected improve on last season's ratings?",
    finding: "No detectable effect: +4 and −3.",
    harness: BACKTEST, proof: P.marketRatings,
  },
  {
    label: "Recent-xG team form added to the ratings",
    est: 0, lo: -110, hi: 112, seasons: [41, -41],
    verdict: "none",
    question: "Does recent xG for and against add to the published team ratings?",
    finding: "Helped one season and hurt the other by the same amount.",
    harness: BACKTEST, proof: P.teamFormAdd,
  },
  {
    label: "Pull the top projections toward the average",
    est: -1, lo: -54, hi: 53, seasons: [20, -21],
    verdict: "none",
    question: "The top projections run high out of sample. Does shrinking them win points?",
    finding:
      "Shrinking fixes the spread, but squads are picked on the order of projections, which it barely changes. Accuracy a little better, points the same.",
    harness: BACKTEST, proof: P.projectionShrink,
  },
  {
    label: "FPL's team ratings as shown at each kickoff",
    est: -3, lo: -131, hi: 122, seasons: [-73, 70],
    verdict: "none",
    question: "Is the model losing points by rating teams on last season's ratings?",
    finding:
      "The archive keeps only FPL's end-of-season ratings, which made fresh ratings look worth about 100 points a season. Rated with the versions published before each kickoff, the gap vanished: it was hindsight (+202 [+42, +367]). Team-ratings work stopped here.",
    harness: BACKTEST, proof: P.ratingsHindsight,
  },
  {
    label: "Season stage (matches played)",
    est: -13, lo: -70, hi: 44, seasons: [34, -47],
    verdict: "none",
    question: "Does telling the model how far into the season it is fix early over-projection?",
    finding: "Split: +34 in one season, −47 in the other.",
    harness: BACKTEST, proof: P.seasonStage,
  },
  {
    label: "Train on stale team ratings, as live plays on them",
    note: "2025-26 only",
    est: -14, lo: -85, hi: 58,
    verdict: "none",
    question: "Does the model trust last season's ratings too much because it learned on fresh ones?",
    finding: "Teaching it on stale ratings didn't win points, so that trust isn't what costs them.",
    harness: BACKTEST, proof: P.staleRatings,
  },
  {
    label: "Early-season tilt toward points per match",
    est: -18, lo: -45, hi: 9, seasons: [-11, -7],
    verdict: "none",
    question: "Should recent points per match count for more in gameweeks 1–10?",
    finding:
      "The error fit said recent points deserved a little more weight early on. Squads picked on it lost points in both seasons.",
    harness: BACKTEST, proof: P.formTilt,
  },
  {
    label: "Club rotation rate",
    est: -19, lo: -80, hi: 43, seasons: [12, -31],
    verdict: "none",
    question: "Does how often a club changes its starters help predict minutes?",
    finding: "It made the minutes model jumpier about every player at a club that rotates.",
    harness: BACKTEST, proof: P.rotationCalibration,
  },
  {
    label: "Odds-based ratings replacing last season's",
    est: -28, lo: -128, hi: 75, seasons: [14, -42],
    verdict: "none",
    question: "Can a free, current rating replace last season's FPL ratings?",
    finding: "No detectable effect, behind in 2025-26. Every free replacement tried failed to beat last season's ratings.",
    harness: BACKTEST, proof: P.marketReplace,
  },
  {
    label: "Points-if-60+ calibrated to real averages",
    est: -29, lo: -123, hi: 69, seasons: [6, -35],
    verdict: "none",
    question: "Does correcting the top-end over-projection pick better squads?",
    finding: "It pulled the premium players down, and squads built on it scored less.",
    harness: BACKTEST, proof: P.rotationCalibration,
  },
  {
    label: "Yellow and red cards",
    est: -31, lo: -116, hi: 52, seasons: [4, -35],
    verdict: "none",
    question: "Does knowing who gets booked change who's worth picking?",
    finding:
      "A yellow costs 1 point and the model already learns the average card cost from the scores it trains on. Who gets booked is too small a difference to change its picks.",
    harness: BACKTEST, proof: P.bookings,
  },
  {
    label: "Net transfers in before the deadline",
    est: -47, lo: -127, hi: 35, seasons: [-25, -22],
    verdict: "none",
    question: "Does where the crowd is moving predict points?",
    finding: "The minutes model got a little better at saying who plays 60+ in both seasons, yet the squads scored less in both.",
    harness: BACKTEST, proof: P.transferFlow,
  },
  {
    label: "A second model that learns the first one's mistakes",
    note: "2024-25 only, stopped",
    est: -51, lo: -166, hi: 53,
    verdict: "none",
    question: "Can a correction model fix the patterns in the main model's misses?",
    finding:
      "Behind in 3 of 4 seeds, so it could no longer pass and the rest was stopped. It also predicted slightly worse on the season it wasn't fitted on: one season's misses don't carry to the next.",
    harness: BACKTEST, proof: P.residualModel,
  },
  {
    label: "Season rates per 90 minutes",
    est: -61, lo: -130, hi: 14, seasons: [-36, -25],
    verdict: "none",
    question: "Are per-90 rates better than per-match averages?",
    finding: "Behind in both seasons. Long-run form already gives the model a player's level; per-90 versions are near-duplicates.",
    harness: BACKTEST, proof: P.modelBatch,
  },
  {
    label: "Long windows for starts, xG, xA and clean sheets",
    est: -66, lo: -157, hi: 27, seasons: [-7, -58],
    verdict: "none",
    question: "Long-run form worked for points. Does it work for every other input too?",
    finding: "Behind in both seasons: more near-duplicate inputs.",
    harness: BACKTEST, proof: P.modelBatch,
  },
  {
    label: "Form trend: last three games against the season",
    est: -75, lo: -161, hi: 11, seasons: [-44, -30],
    verdict: "none",
    question: "Does a player heating up or cooling down tell the model more than his level?",
    finding: "Behind in both seasons.",
    harness: BACKTEST, proof: P.modelBatch,
  },
  {
    label: "Drop price and ownership",
    est: -99, lo: -249, hi: 46, seasons: [-22, -77],
    verdict: "none",
    question: "Would the model be better without both market inputs?",
    finding: "Behind in both seasons, 8 of 10 runs.",
    harness: BACKTEST, proof: P.priceFeature,
  },
  {
    label: "Team strength from recent xG, replacing FPL's ratings",
    est: -119, lo: -292, hi: 51, seasons: [34, -153],
    verdict: "none",
    question: "Does each team's recent xG rate it better than FPL's published ratings?",
    finding:
      "2025-26 alone was clearly worse (−153 [−276, −24]), and a replay of 2026-27 was worse on every seed. A few matches of xG are noisier than a rating built on a whole season of squad quality.",
    harness: BACKTEST, proof: P.teamForm,
  },
  {
    label: "Drop price as an input",
    est: -128, lo: -287, hi: 30, seasons: [-61, -67],
    verdict: "none",
    question: "Is price a stale reputation signal the model would be better without?",
    finding:
      "Asked after the model started an expensive, out-of-form forward. Taking price out lost points in all 10 runs: it carries a judgement of quality the form inputs don't.",
    harness: BACKTEST, proof: P.priceFeature,
  },
];

export const LAB_CHECKS: LabCheck[] = [
  {
    title: "Are some player types projected too low as a rule?",
    outcome: "No bias found",
    result:
      "Attackers against steady defenders: +0.02 points a match [−0.43, +0.41]. Players back from one missed match and one-big-game scorers: no bias either.",
    proof: P.projectionBias,
  },
  {
    title: "Are players who just played in Europe projected wrong?",
    outcome: "No bias found",
    result: "Midweek starters scored −0.08 points [−0.32, +0.14] against players with no midweek game.",
    proof: P.europeBias,
  },
  {
    title: "Does form in European, cup and international games predict the model's misses?",
    outcome: "Stopped at step 1",
    result: "+0.04 points [−0.21, +0.29]: no signal, so steps 2 and 3 were never built.",
    proof: P.europeForm,
  },
  {
    title: "Do the probabilities come true as often as they say?",
    outcome: "Two passed, one fixed",
    result:
      "Ranges and chances of 10+ points held up on seasons they weren't fitted on, within 2 points in every bin. Head-to-heads failed: a \"70%\" favourite won 65–68%. Scaling their log-odds fixed it, stated as a correction made after seeing the result.",
    proof: P.distributions,
  },
  {
    title: "How much past data should the model train on?",
    outcome: "Unchanged",
    result:
      "Judged on 2026-27 itself. No alternative cleared the bar set beforehand (ahead on 4 of 5 seeds and by 10+ points). Training on this season alone was 66 points worse.",
    proof: P.historyCheck,
  },
  {
    title: "Does picking on a player's good day buy more huge seasons?",
    outcome: "Closed",
    result:
      "One version came close on the tuning seasons. On the held-back seasons it gave fewer huge seasons, 0.3% and 0.2% against 1%, and cost points.",
    proof: P.upside,
  },
  {
    title: "Should the planner avoid −4 hits before gameweek 9?",
    outcome: "No detectable effect",
    result: "+41 in 2024-25, all from one hit. In 2025-26 no early hits were advised, so nothing changed.",
    proof: P.earlyHits,
  },
  {
    title: "Does the AI team-news reader make good calls?",
    outcome: "Judged live",
    result:
      "There are no archived press conferences, so it can't be backtested. \"Out\" calls must be right 85% of the time to stay on, and rotation calls must be right 60% of the time over 30 checks before they change anything. Verdict at the gameweek 19 deadline.",
    proof: P.teamNews,
  },
];

/** The fixes to the test bench, each checked against the direction it should
 *  move the totals (research/2026-10-harness-v2). */
export const BENCH_FIXES: { fix: string; expected: string; measured: string }[] = [
  {
    fix: "Score a double-gameweek player per match, not once",
    expected: "More points, all of it in double weeks",
    measured: "+137 [+34, +273], every point in the 7 double weeks",
  },
  {
    fix: "Freeze prices at the deadline in six-week projections",
    expected: "Lower simulator totals: the leak flattered them",
    measured: "Totals were higher with the leak in 7 of 8 runs",
  },
  {
    fix: "Use injury flags as FPL published them before each deadline",
    expected: "Better accuracy",
    measured: "MAE 1.086 → 0.996 and 0.991 → 0.911",
  },
  {
    fix: "Each season's own transfer rules (banking up to 5, not 2)",
    expected: "Correct transfer counts",
    measured: "Unit tests; first-week banking matches a real team",
  },
];

/** "48 min", "1 h 22 min", "16 h": how long after the plan the result went in. */
export function gap(proof: Proof): string | null {
  if (!proof.plan || !proof.result || proof.plan.hash === proof.result.hash) return null;
  const mins = Math.round((Date.parse(proof.result.at) - Date.parse(proof.plan.at)) / 60000);
  if (mins < 60) return `${mins} min`;
  const h = Math.floor(mins / 60);
  const m = mins % 60;
  return h >= 6 || m === 0 ? `${h} h` : `${h} h ${m} min`;
}

/** "31 Oct 2026", in the timezone the commits were made in. */
export function commitDate(at: string): string {
  return new Date(at).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric", timeZone: "America/Regina" });
}

/** Every study counted once (several tests can share one study's Proof), and
 *  how many of them have the plan in the history before the result. */
export function studyCount(): { studies: number; planFirst: number } {
  const proofs = new Set<Proof>([...LAB_TESTS.map((t) => t.proof), ...LAB_CHECKS.map((x) => x.proof)]);
  const planFirst = [...proofs].filter((p) => p.plan && (!p.result || p.plan.hash !== p.result.hash)).length;
  return { studies: proofs.size, planFirst };
}
