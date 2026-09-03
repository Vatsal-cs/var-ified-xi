// File: PipelineExplainer.tsx
// Path: var-ified-xi/frontend/components/PipelineExplainer.tsx
//
// The five stages the backend actually runs, in order. Plain language, one
// expandable panel each.

const STAGES = [
  {
    n: "1",
    title: "Pull the data",
    summary: "Every player's match history, straight from FPL's free API.",
    body: [
      "Each run fetches the full player and team list, the fixture list, and a gameweek-by-gameweek history for all 600+ players. That's official data — minutes, goals, assists, bonus, expected goals and assists, defensive actions — for every match played this season.",
      "It's combined with three past seasons from a public archive, so the model has around 90,000 real (form → points) examples to learn from rather than just the handful this season has produced so far.",
    ],
  },
  {
    n: "2",
    title: "Turn it into form signals",
    summary: "Rolling averages over the last 3–5 games, plus the fixture ahead.",
    body: [
      "Raw stats don't predict much on their own. Each player's history becomes rolling averages — minutes, points, expected goals/assists, bonus-point score, how often they actually start, defensive contributions.",
      "For training, every average is shifted back a gameweek so a row never sees its own result. For the prediction it isn't shifted — the last match played is fair information about the next one. Fixture difficulty is folded in by comparing each team's attacking strength against the opponent's defence.",
    ],
  },
  {
    n: "3",
    title: "Predict points — two models",
    summary: "\"Will he play?\" and \"how well?\" are different questions.",
    body: [
      "Rotation risk is the biggest single source of error in fantasy football, so it gets its own model: a classifier estimates the odds a player doesn't play, comes off the bench, or starts properly. A second model estimates points given a proper start, trained only on players who actually played 60+ minutes — so it learns quality, not availability. Multiplying the two gives expected points.",
      "A third model estimates each player's ceiling — a good-day score rather than an average one — which is what the captain pick uses, since the armband doubles points. Accuracy is measured on gameweeks the model never saw, then it's retrained on everything so it goes into the weekend current.",
    ],
  },
  {
    n: "4",
    title: "Solve for the best move",
    summary: "A real optimizer, planning six gameweeks at once.",
    body: [
      "A Mixed-Integer Linear Program (PuLP/CBC) decides everything together: which 15 players, which 11 start, who captains, and — when it knows your real team — which transfers to make in each of the next six gameweeks.",
      "It obeys every FPL rule: £100m budget, 2/5/5/3 squad, a legal formation, max 3 per club, one free transfer a week banked up to five, and −4 for each extra. It only takes a hit when the extra points clearly beat the 4 it costs. Planning six weeks at once is what stops it chasing one fixture into a wall.",
    ],
  },
  {
    n: "5",
    title: "Write it out",
    summary: "One JSON file — exactly what this page shows.",
    body: [
      "The result — transfers, starting XI, captain, and the six-week plan — is written to a single file that this page reads directly. No live server picks anything on request.",
      "A scheduled job re-runs the whole engine before every deadline and commits the result, which redeploys the page automatically. Every number here comes from fresh form, fresh prices, and a fresh solve.",
    ],
  },
];

export default function PipelineExplainer() {
  return (
    <div className="card divide-y divide-pitch-line overflow-hidden">
      {STAGES.map((s) => (
        <details key={s.n} className="group">
          <summary className="flex cursor-pointer list-none items-center gap-4 px-5 py-4 marker:content-none hover:bg-pitch-panel2/40">
            <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full border border-pitch-line font-mono text-xs text-ink-400">
              {s.n}
            </span>
            <span className="flex-1">
              <span className="block font-display text-base font-semibold tracking-tight text-ink-100">
                {s.title}
              </span>
              <span className="block font-body text-[13px] text-ink-400">{s.summary}</span>
            </span>
            <span className="font-mono text-ink-500 transition-transform group-open:rotate-45">
              +
            </span>
          </summary>
          <div className="space-y-3 px-5 pb-5 pl-16 font-body text-[15px] leading-relaxed text-ink-300">
            {s.body.map((para, i) => (
              <p key={i}>{para}</p>
            ))}
          </div>
        </details>
      ))}
    </div>
  );
}
