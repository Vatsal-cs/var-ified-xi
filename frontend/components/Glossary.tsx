// File: Glossary.tsx
// Path: var-ified-xi/frontend/components/Glossary.tsx
//
// Plain answers to the questions this page tends to raise.

const QA: { q: string; a: string }[] = [
  {
    q: "What is a \"projected\" or \"predicted\" points number?",
    a: "The model's estimate of a player's score in a gameweek: the odds he actually starts, multiplied by what he's worth when he does. It's an average expectation, not a prediction of exactly what will happen.",
  },
  {
    q: "Why isn't it recommending a whole new team?",
    a: "It only does that in fresh-squad mode (Gameweek 1, or a wildcard). Once it knows your team, it works from the 15 you own and recommends the transfer that helps most, because that's all the rules let you do.",
  },
  {
    q: "When is a −4 hit worth taking?",
    a: "Only when the transfers it buys are projected to gain clearly more than 4 points over the planning horizon — not just break even. Breaking even on paper isn't worth a guaranteed −4, since the projection can be wrong. The engine solves it both ways and tells you which wins.",
  },
  {
    q: "Why does it plan six gameweeks ahead?",
    a: "So it doesn't sell a player to chase one good fixture and then have to buy him straight back. Later weeks are discounted and re-solved every run — only act on the gameweek that's due.",
  },
  {
    q: "How is the captain chosen?",
    a: "The player with the highest projected points in your XI. Picking on a 'good day ceiling' instead was tested over two full seasons and lost both, so it isn't used: chasing upside also drags high-variance players into the rest of the squad, and the squad lost more than the armband gained.",
  },
  {
    q: "What do the percentages mean?",
    a: "Each player has a full points distribution, not just an average: his chance of playing, and for the points if he does, how players the model projected the same way actually scored over two past seasons. 'Beats X 45%' is how often he'd outscore X, ties left out. Checked on a season it wasn't built from, and recalibrated where it was overconfident. Most start/bench calls land between 40% and 60% — genuinely close.",
  },
  {
    q: "Where does the team news come from?",
    a: "Within 48 hours of the deadline, the last six days of Google News and BBC Sport headlines for your players' clubs are read by Google's free Gemini model, which cites the headline behind every call. 'Out' and 'doubt' calls that are worse than FPL's own flag lower the projection, as an FPL flag would a few hours later. 'Rotation' is shown, never applied — predicted line-ups are guesses.",
  },
  {
    q: "How good is the model, honestly?",
    a: "Backtested over two full past seasons, it scores about 19% more points than having no model at all (just using each player's recent average). One gameweek tells you very little either way — judge it over 6–10.",
  },
  {
    q: "What are the hard FPL rules it respects?",
    a: "£100m budget, exactly 2 goalkeepers / 5 defenders / 5 midfielders / 3 forwards, a legal starting formation, no more than 3 players from one club, one free transfer per week (unused ones bank, up to five at once), and −4 points per extra transfer.",
  },
  {
    q: "Does it need my FPL login?",
    a: "No. It only reads your public team ID — the number in your team's URL. It never signs in and can't make transfers for you; you enter them yourself.",
  },
];

export default function Glossary() {
  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
      {QA.map((item) => (
        <div key={item.q} className="panel p-4">
          <p className="font-body text-sm font-semibold text-ink-100">{item.q}</p>
          <p className="mt-1.5 font-body text-[14px] leading-relaxed text-ink-300">{item.a}</p>
        </div>
      ))}
    </div>
  );
}
