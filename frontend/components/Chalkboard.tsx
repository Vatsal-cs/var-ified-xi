// File: Chalkboard.tsx
// Path: var-ified-xi/frontend/components/Chalkboard.tsx
//
// Below the stadium the page is a coach's board at night: chalk on the turf,
// faint and behind everything. Set pieces and runs (O ours, X theirs), the
// formation, the centre circle and a penalty box at full size, a tally of the
// gameweeks gone, and notes on this week in the coach's hand — the captain,
// the transfer, when the chips go. As you scroll each one is drawn in, the
// notes are written out and the ball travels its pass (globals.css); without
// that support they're simply there. The board stops short of the footer: the
// end of the page is left clear.

import type { CSSProperties, ReactNode } from "react";
import type { OptimizedTeam } from "@/lib/types";

// ── Chalk shorthand ────────────────────────────────────────────────────────

const ring = (x: number, y: number, r = 12) =>
  `M${x + r} ${y} A${r} ${r} 0 1 1 ${x - r} ${y} A${r} ${r} 0 1 1 ${x + r} ${y}`;
const cross = (x: number, y: number, s = 10) =>
  `M${x - s} ${y - s} L${x + s} ${y + s} M${x + s} ${y - s} L${x - s} ${y + s}`;

/** An arrowhead at (x, y) for a line arriving in direction (dx, dy). */
function head(x: number, y: number, dx: number, dy: number, size = 15) {
  const len = Math.hypot(dx, dy);
  const [ux, uy] = [-dx / len, -dy / len];
  const barb = (a: number) =>
    `M${x} ${y} l${((ux * Math.cos(a) - uy * Math.sin(a)) * size).toFixed(1)} ${((ux * Math.sin(a) + uy * Math.cos(a)) * size).toFixed(1)}`;
  return `${barb(0.5)} ${barb(-0.5)}`;
}

/** A line from one player's ring to another's, stopping at both rings. */
function link([x1, y1]: number[], [x2, y2]: number[], gap = 15) {
  const len = Math.hypot(x2 - x1, y2 - y1);
  const [ux, uy] = [(x2 - x1) / len, (y2 - y1) / len];
  return `M${(x1 + ux * gap).toFixed(1)} ${(y1 + uy * gap).toFixed(1)} L${(x2 - ux * gap).toFixed(1)} ${(y2 - uy * gap).toFixed(1)}`;
}

/** A long ball in dashes along a quadratic curve. Each dash is its own short
 *  line, so the whole thing can still be drawn in end to end. */
function dashed(from: number[], ctrl: number[], to: number[], dash = 10, gap = 8) {
  const at = (t: number) =>
    [0, 1].map((k) => (1 - t) ** 2 * from[k] + 2 * (1 - t) * t * ctrl[k] + t ** 2 * to[k]);
  const pts = Array.from({ length: 201 }, (_, i) => at(i / 200));
  let d = "";
  let run = 0;
  let on = true;
  for (let i = 1; i < pts.length; i++) {
    const step = Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]);
    if (on) d += `${run === 0 ? `M${pts[i - 1][0].toFixed(1)} ${pts[i - 1][1].toFixed(1)} ` : ""}L${pts[i][0].toFixed(1)} ${pts[i][1].toFixed(1)} `;
    run += step;
    if (run >= (on ? dash : gap)) {
      on = !on;
      run = 0;
    }
  }
  return d.trim();
}

// ── The pieces ─────────────────────────────────────────────────────────────

type Piece = {
  w: number;
  h: number;
  /** Chalk lines, drawn in as the piece scrolls into view. */
  lines: string[];
  /** Fine lines, drawn thinner. */
  fine?: string[];
  /** Words chalked on the board, in the coach's hand. */
  words?: { x: number; y: number; text: string; size?: number; turn?: number }[];
  /** The ball's route as the piece scrolls past, in the piece's own pixels. */
  ball?: string;
  /** Faded further back: the full-size pitch markings. */
  big?: boolean;
};

const FORMATION_SPOTS = {
  gk: [150, 300],
  def: [[45, 238], [115, 248], [185, 248], [255, 238]],
  mid: [[80, 165], [150, 175], [220, 165]],
  fwd: [[70, 85], [150, 70], [230, 85]],
};
const { gk, def, mid, fwd } = FORMATION_SPOTS;

const PIECES = {
  formation: {
    w: 300,
    h: 330,
    lines: [gk, ...def, ...mid, ...fwd].map(([x, y]) => ring(x, y, 11)),
    fine: [
      link(gk, def[1]), link(gk, def[2]),
      link(def[0], def[1]), link(def[1], def[2]), link(def[2], def[3]),
      link(def[0], mid[0]), link(def[1], mid[0]), link(def[1], mid[1]), link(def[2], mid[1]), link(def[2], mid[2]), link(def[3], mid[2]),
      link(mid[0], mid[1]), link(mid[1], mid[2]),
      link(mid[0], fwd[0]), link(mid[1], fwd[1]), link(mid[2], fwd[2]), link(mid[0], fwd[1]), link(mid[2], fwd[1]),
    ],
    words: [{ x: 12, y: 30, text: "4-3-3", size: 30, turn: -6 }],
  },
  oneTwo: {
    w: 260,
    h: 260,
    lines: [
      ring(40, 215), ring(205, 140), cross(118, 170),
      `M54 208 L190 147 ${head(190, 147, 136, -61)}`,
      `M48 200 C70 120 110 70 175 48 ${head(175, 48, 65, -22)}`,
      `M200 126 L180 62 ${head(180, 62, -20, -64)}`,
    ],
    words: [{ x: 150, y: 235, text: "one-two", size: 24, turn: -4 }],
    ball: "M40 215 L205 140 L178 56",
  },
  overlap: {
    w: 260,
    h: 260,
    lines: [
      ring(70, 210), ring(150, 150), cross(205, 190), cross(108, 92),
      `M80 198 C170 210 235 120 190 40 ${head(190, 40, -45, -80)}`,
      `M150 136 L180 60 ${head(180, 60, 30, -76)}`,
    ],
    ball: "M150 150 L182 52",
  },
  shot: {
    w: 260,
    h: 260,
    lines: [
      "M70 30 H190 M70 30 V12 M190 30 V12 M70 12 H190", "M40 30 V95 H220 V30",
      ring(150, 215), cross(110, 160),
      `M140 202 C120 180 160 165 135 140 ${head(135, 140, -25, -25)}`,
      `M135 140 L108 40 ${head(108, 40, -27, -100)}`,
    ],
    words: [{ x: 168, y: 130, text: "top bins", size: 24, turn: -8 }],
    ball: "M150 215 C120 180 160 165 135 140 L104 22",
  },
  corner: {
    w: 300,
    h: 260,
    lines: [
      "M10 30 H295 M10 30 V250",
      "M10 42 A12 12 0 0 0 22 30",
      "M95 30 V150 H295", "M155 30 V70 H265",
      "M175 30 V14 H245 V30",
      ring(215, 205), ring(275, 215), cross(190, 118), cross(240, 140),
      `M212 190 L204 108 ${head(204, 108, -8, -82)}`,
      `M270 200 L254 122 ${head(254, 122, -16, -78)}`,
    ],
    fine: ["M18 38 C90 150 170 125 205 80"],
    words: [{ x: 30, y: 215, text: "near post!", size: 26, turn: -5 }],
    ball: "M18 38 C90 150 170 125 205 80",
  },
  press: {
    w: 260,
    h: 250,
    lines: [
      cross(130, 125, 11),
      ring(40, 55), ring(225, 70), ring(135, 228),
      `${link([40, 55], [130, 125], 18)} ${head(116, 114, 90, 70)}`,
      `${link([225, 70], [130, 125], 18)} ${head(146, 116, -95, 55)}`,
      `${link([135, 228], [130, 125], 18)} ${head(131, 143, -5, -103)}`,
    ],
    words: [{ x: 150, y: 30, text: "PRESS!", size: 30, turn: 6 }],
  },
  switchPlay: {
    w: 380,
    h: 210,
    lines: [ring(30, 185), ring(350, 40), dashed([42, 178], [190, 0], [336, 46]), head(336, 46, 146, 46)],
    words: [{ x: 120, y: 150, text: "switch it", size: 26, turn: -10 }],
    ball: "M30 185 Q190 0 350 40",
  },
  centreCircle: {
    w: 720,
    h: 440,
    lines: [
      "M0 220 H720",
      "M510 220 A150 150 0 1 1 210 220 A150 150 0 1 1 510 220",
      ring(360, 220, 4),
    ],
    big: true,
  },
  box: {
    w: 420,
    h: 330,
    lines: [
      "M40 0 V330",
      "M40 25 H230 V305 H40", "M40 95 H105 V235 H40",
      "M230 90.7 A95 95 0 0 1 230 229.3",
      ring(165, 165, 3),
      "M40 128 H18 V202 H40",
    ],
    big: true,
  },
} satisfies Record<string, Piece>;

/** Tally marks for the gameweeks gone, in fives. */
function tally(done: number): Piece {
  const lines: string[] = [];
  for (let g = 0; g < Math.ceil(done / 5); g++) {
    const x0 = 14 + g * 74;
    const inGroup = Math.min(5, done - g * 5);
    for (let i = 0; i < Math.min(4, inGroup); i++) lines.push(`M${x0 + i * 14} 30 L${x0 + i * 14 + 2} 92`);
    if (inGroup === 5) lines.push(`M${x0 - 8} 80 L${x0 + 52} 40`);
  }
  return {
    w: Math.max(200, 30 + Math.ceil(done / 5) * 74),
    h: 150,
    lines,
    words: [{ x: 12, y: 135, text: `${done} down, ${38 - done} to go`, size: 26, turn: -3 }],
  };
}

// ── Drawing them ───────────────────────────────────────────────────────────

function ChalkPiece({ piece, id }: { piece: Piece; id: string }) {
  return (
    <div className="chalk-piece relative" style={{ width: piece.w, height: piece.h }}>
      <svg
        viewBox={`0 0 ${piece.w} ${piece.h}`}
        width={piece.w}
        height={piece.h}
        className={`chalk-draw absolute inset-0 overflow-visible ${piece.big ? "opacity-70" : ""}`}
      >
        <defs>
          {/* Chalk never goes on quite straight */}
          <filter id={`chalk-${id}`}>
            <feTurbulence type="fractalNoise" baseFrequency="0.8" numOctaves="1" seed={id.length * 7} />
            <feDisplacementMap in="SourceGraphic" scale="3" />
          </filter>
        </defs>
        <g fill="none" stroke="var(--doodle)" strokeLinecap="round" strokeLinejoin="round" filter={`url(#chalk-${id})`}>
          {piece.lines.map((d, i) => (
            <path key={i} d={d} pathLength={1} strokeWidth={piece.big ? 3 : 2.6} />
          ))}
          {piece.fine?.map((d, i) => (
            <path key={`f${i}`} d={d} pathLength={1} strokeWidth={1.4} />
          ))}
        </g>
        {piece.words?.map((w) => (
          <text
            key={w.text}
            x={w.x}
            y={w.y}
            fontSize={w.size ?? 26}
            fill="var(--doodle-text)"
            className="chalk-write font-chalk font-bold"
            transform={w.turn ? `rotate(${w.turn} ${w.x} ${w.y})` : undefined}
          >
            {w.text}
          </text>
        ))}
      </svg>
      {piece.ball && <ChalkBall path={piece.ball} />}
    </div>
  );
}

/** A ball in chalk that travels its pass as you scroll past. */
function ChalkBall({ path }: { path: string }) {
  return (
    <svg
      viewBox="0 0 20 20"
      className="chalk-ball absolute left-0 top-0 h-5 w-5"
      style={{ offsetPath: `path("${path}")` } as CSSProperties}
    >
      <g fill="none" stroke="var(--doodle-text)" strokeWidth="1.4" strokeLinejoin="round">
        <circle cx="10" cy="10" r="8" />
        <path d="M10 6.4 L13.4 8.9 L12.1 12.9 L7.9 12.9 L6.6 8.9 Z M10 6.4 V2 M13.4 8.9 L17.6 7.6 M12.1 12.9 L14.7 16.5 M7.9 12.9 L5.3 16.5 M6.6 8.9 L2.4 7.6" />
      </g>
    </svg>
  );
}

/** A note on the board in the coach's hand, written out as you scroll. */
function Note({ lines }: { lines: { text: string; struck?: boolean; ring?: string }[] }) {
  return (
    <div className="chalk-write font-chalk text-[30px] font-bold leading-[1.05] text-[color:var(--doodle-text)]">
      {lines.map((l) => (
        <p key={l.text} className={l.struck ? "line-through decoration-2" : ""}>
          {l.ring && (
            <span className="mr-1.5 inline-grid h-[1.15em] w-[1.15em] place-items-center rounded-full border-2 border-current text-[0.8em] leading-none">
              {l.ring}
            </span>
          )}
          {l.text}
        </p>
      ))}
    </div>
  );
}

const CHIP_SHORT: Record<string, string> = { bboost: "BB", "3xc": "TC", freehit: "FH", wildcard: "WC" };

/** This week's notes, from the run that built the page. */
function notesFor(team: OptimizedTeam) {
  const notes: { text: string; struck?: boolean; ring?: string }[][] = [];
  const captain = team.starting_xi.find((p) => p.is_captain);
  if (captain) notes.push([{ ring: "C", text: captain.name }]);
  const week = team.transfer_plan?.weeks[0];
  if (week && week.transfers_in.length > 0) {
    notes.push([
      ...week.transfers_in.map((p) => ({ text: `${p.name} in` })),
      ...week.transfers_out.map((p) => ({ text: p.name, struck: true })),
    ]);
  }
  const chips = team.chip_plan?.scenarios[0]?.plan ?? [];
  if (chips.length > 0) {
    notes.push(
      [...chips]
        .sort((a, b) => a.gameweek - b.gameweek)
        .map((c) => ({ text: `${CHIP_SHORT[c.chip] ?? c.chip} → GW${c.gameweek}` }))
    );
  }
  notes.push([{ text: `${team.predicted_total_points.toFixed(1)} xP` }, { text: "trust the model" }]);
  return notes;
}

type Spot = {
  /** Pixels below the first screen. */
  y: number;
  side: "left" | "right" | "centre";
  /** How far in from that side; negative bleeds off the edge. */
  inset?: string;
  turn?: number;
  /** Also on a phone (the big markings, which sit behind the content). */
  phone?: boolean;
  node: ReactNode;
};

/** The chalk on the board, behind every page below the stadium. */
export default function Chalkboard({ team }: { team: OptimizedTeam }) {
  const notes = notesFor(team);
  const note = (i: number) => (notes[i] ? <Note lines={notes[i]} /> : null);
  const piece = (key: keyof typeof PIECES) => <ChalkPiece piece={PIECES[key]} id={key} />;
  const done = Math.max(0, (team.gameweek ?? 1) - 1);

  // One pass down the page, then the same again further down for long pages.
  const round: Omit<Spot, "y">[] = [
    { side: "left", inset: "1.5%", turn: -4, node: piece("formation") },
    { side: "right", inset: "3%", turn: 4, node: note(0) },
    { side: "right", inset: "1%", turn: 6, node: piece("oneTwo") },
    { side: "centre", phone: true, node: piece("centreCircle") },
    { side: "left", inset: "2.5%", turn: -3, node: note(1) },
    { side: "left", inset: "0.5%", turn: 3, node: piece("corner") },
    { side: "right", inset: "2.5%", turn: -4, node: done > 0 ? <ChalkPiece piece={tally(done)} id="tally" /> : null },
    { side: "right", inset: "1%", turn: 8, node: piece("press") },
    { side: "left", inset: "-40px", phone: true, node: piece("box") },
    { side: "right", inset: "3%", turn: 3, node: note(2) },
    { side: "left", inset: "1%", turn: -6, node: piece("overlap") },
    { side: "right", inset: "-30px", turn: -4, node: piece("switchPlay") },
    { side: "left", inset: "2%", turn: 5, node: piece("shot") },
    { side: "right", inset: "3%", turn: -3, node: note(3) },
  ];
  const STEP = 200;
  const spots: Spot[] = [0, 1].flatMap((r) =>
    round.map((s, i) => ({ ...s, y: r * round.length * STEP + i * STEP + (s.side === "centre" ? 40 : 0) }))
  );

  return (
    // Fades out well above the footer, so nothing is chalked at the end of the page
    <div
      aria-hidden
      className="pointer-events-none absolute inset-0 z-0 select-none overflow-clip [mask-image:linear-gradient(180deg,#000_calc(100%-700px),transparent_calc(100%-450px))]"
    >
      {spots.map(
        (s, i) =>
          s.node && (
            <div
              key={i}
              className={`absolute ${s.phone ? "" : "hidden md:block"}`}
              style={{
                top: `calc(75vh + ${s.y}px)`,
                ...(s.side === "centre"
                  ? { left: "50%", transform: "translateX(-50%)" }
                  : { [s.side]: s.inset, transform: s.turn ? `rotate(${s.turn}deg)` : undefined }),
              }}
            >
              {s.node}
            </div>
          )
      )}
    </div>
  );
}
