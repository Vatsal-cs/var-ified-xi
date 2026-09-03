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
    a: "The armband doubles points, so the pick that matters is the highest realistic ceiling, not the steadiest average. A separate model estimates each player's good-day score and the captain is taken from that.",
  },
  {
    q: "How good is the model, honestly?",
    a: "Backtested over two full past seasons, it scores about 16% more points than having no model at all (just using each player's recent average). One gameweek tells you very little either way — judge it over 6–10.",
  },
  {
    q: "What are the hard FPL rules it respects?",
    a: "£100m budget, exactly 2 goalkeepers / 5 defenders / 5 midfielders / 3 forwards, a legal starting formation, no more than 3 players from one club, one free transfer per week (bankable to five), and −4 points per extra transfer.",
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
        <div key={item.q} className="card p-4">
          <p className="font-body text-sm font-semibold text-ink-100">{item.q}</p>
          <p className="mt-1.5 font-body text-[14px] leading-relaxed text-ink-300">{item.a}</p>
        </div>
      ))}
    </div>
  );
}
