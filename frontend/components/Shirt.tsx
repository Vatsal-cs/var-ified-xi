// File: Shirt.tsx
// Path: var-ified-xi/frontend/components/Shirt.tsx
//
// A player drawn as his club shirt: the kit's colours (stripes and contrasting
// sleeves included), the crest on the chest, and a number — the site uses it
// for projected points. Captains and vices wear an armband on the left sleeve.
// Plain SVG, so it renders on the server and scales to any size.

import { crestUrls, goalkeeperKit, kitFor } from "@/lib/teams";

// The outline, with a round neck cut out of it.
const BODY =
  "M44 12 L20 22 L8 40 L22 50 L32 43 L32 106 Q32 110 36 110 L84 110 Q88 110 88 106 L88 43 L98 50 " +
  "L112 40 L100 22 L76 12 C72 19 66 22 60 22 C54 22 48 19 44 12 Z";
// The inside of the back of the shirt, seen through the neck.
const NECK_INSIDE = "M44 12 C50 16.5 70 16.5 76 12 C72 19 66 22 60 22 C54 22 48 19 44 12 Z";
const COLLAR_FRONT = "M44 12 C48 19 54 22 60 22 C66 22 72 19 76 12";
const COLLAR_BACK = "M44 12 C50 16.5 70 16.5 76 12";
const SLEEVES = "M20 22 L8 40 L22 50 L32 43 L34 24 Z M100 22 L112 40 L98 50 L88 43 L86 24 Z";
const CUFFS = "M8 40 L22 50 M112 40 L98 50";

// The captain's armband: a band round the left sleeve, parallel to its cuff,
// clipped to the sleeve so it wraps the arm rather than floating on it.
const LEFT_SLEEVE = "M100 22 L112 40 L98 50 L88 43 L86 24 Z";
const ARMBAND = "M90.6 50.4 L114.4 33.4 L109.4 27.2 L85.7 44.1 Z";
const ARMBAND_TEXT = { x: 100, y: 38.8, angle: -35.5 };

export default function Shirt({
  team,
  number,
  uid,
  goalkeeper = false,
  captain = false,
  vice = false,
  armbandDelay = 1.6,
  className = "",
}: {
  team: string | undefined;
  number: string;
  /** Unique within the page: names this shirt's gradients and patterns. */
  uid: string;
  goalkeeper?: boolean;
  captain?: boolean;
  vice?: boolean;
  /** Seconds before the armband pops on. */
  armbandDelay?: number;
  className?: string;
}) {
  const kit = goalkeeper ? goalkeeperKit(team) : kitFor(team);
  const id = uid.replace(/[^a-zA-Z0-9_-]/g, "");
  const striped = !!kit.stripe;
  const crest = crestUrls(team)[0];
  const edge = striped ? kit.shirt : kit.trim;
  const band = captain ? { fill: "#E3A93C", line: "#9A6A14", text: "#2A1A00", letter: "C" } : { fill: "#17181B", line: "#000", text: "#F2F0EC", letter: "V" };

  return (
    <svg viewBox="0 0 120 120" className={className} aria-hidden>
      <defs>
        {/* Light: a rounded torso (darker at the sides), a sheen across the
            chest, a darker hem, and a fine knit. */}
        <linearGradient id={`torso-${id}`} x1="0" x2="1">
          <stop offset="0" stopColor="#000" stopOpacity="0.26" />
          <stop offset="0.3" stopColor="#000" stopOpacity="0" />
          <stop offset="0.62" stopColor="#fff" stopOpacity="0.06" />
          <stop offset="1" stopColor="#000" stopOpacity="0.26" />
        </linearGradient>
        <linearGradient id={`arm-${id}`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#fff" stopOpacity="0.1" />
          <stop offset="1" stopColor="#000" stopOpacity="0.16" />
        </linearGradient>
        <radialGradient id={`sheen-${id}`} cx="0.4" cy="0.28" r="0.55">
          <stop offset="0" stopColor="#fff" stopOpacity="0.3" />
          <stop offset="0.6" stopColor="#fff" stopOpacity="0" />
        </radialGradient>
        <linearGradient id={`hem-${id}`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0.6" stopColor="#000" stopOpacity="0" />
          <stop offset="1" stopColor="#000" stopOpacity="0.24" />
        </linearGradient>
        <pattern id={`knit-${id}`} width="2.4" height="2.4" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
          <rect width="1.2" height="2.4" fill="#fff" opacity="0.05" />
        </pattern>
        <clipPath id={`clip-${id}`}>
          <path d={BODY} />
        </clipPath>
        <clipPath id={`sleeves-${id}`}>
          <path d={SLEEVES} />
        </clipPath>
        <clipPath id={`lsleeve-${id}`}>
          <path d={LEFT_SLEEVE} />
        </clipPath>
        {striped && (
          <pattern id={`stripe-${id}`} width="12" height="12" patternUnits="userSpaceOnUse">
            <rect width="12" height="12" fill={kit.shirt} />
            <rect x="6" width="6" height="12" fill={kit.stripe} />
          </pattern>
        )}
      </defs>

      <path d={NECK_INSIDE} fill={kit.shirt} />
      <path d={NECK_INSIDE} fill="rgba(0,0,0,0.5)" />
      <path d={BODY} fill={striped ? `url(#stripe-${id})` : kit.shirt} />
      {kit.sleeve && <path d={SLEEVES} fill={kit.sleeve} clipPath={`url(#clip-${id})`} />}

      <g clipPath={`url(#clip-${id})`}>
        <rect width="120" height="120" fill={`url(#knit-${id})`} />
        <rect x="32" y="12" width="56" height="100" fill={`url(#torso-${id})`} />
        <rect width="120" height="120" fill={`url(#arm-${id})`} clipPath={`url(#sleeves-${id})`} />
        <rect width="120" height="120" fill={`url(#sheen-${id})`} />
        <rect width="120" height="120" fill={`url(#hem-${id})`} />
        {/* Underarms, two soft folds and the shoulder seams */}
        <path d="M32 43 L22 50 L20 47 Z M88 43 L98 50 L100 47 Z" fill="#000" opacity="0.18" />
        <path
          d="M40 60 C46 72 44 90 40 104 M80 58 C75 72 77 90 82 104"
          stroke="#000"
          strokeOpacity="0.08"
          strokeWidth="3"
          fill="none"
          strokeLinecap="round"
        />
        <path d="M34 24 L32 43 M86 24 L88 43" stroke="#fff" strokeOpacity="0.14" strokeWidth="0.8" fill="none" />
      </g>

      <path d={COLLAR_BACK} fill="none" stroke={edge} strokeWidth="2" strokeLinecap="round" opacity="0.9" />
      <path d={COLLAR_FRONT} fill="none" stroke={edge} strokeWidth="3.6" strokeLinecap="round" />
      <path
        d="M45.5 14.5 C49.5 20.5 54.5 23.5 60 23.5 C65.5 23.5 70.5 20.5 74.5 14.5"
        fill="none"
        stroke="#000"
        strokeOpacity="0.18"
        strokeWidth="1"
      />
      <path d={CUFFS} stroke={kit.sleeve ? kit.shirt : edge} strokeWidth="3.6" strokeLinecap="round" />
      <path d={BODY} fill="none" stroke="rgba(0,0,0,0.25)" strokeWidth="1" strokeLinejoin="round" />

      {crest && <image href={crest} x="65" y="29" width="12" height="12" />}

      {striped && <rect x="44" y="62" width="32" height="30" rx="5" fill="#fff" />}
      <text
        x="60"
        y="86"
        textAnchor="middle"
        className="font-kit"
        fontWeight="700"
        fontSize="31"
        letterSpacing="-0.5"
        fill={striped ? "#111" : kit.trim}
      >
        {number}
      </text>

      {(captain || vice) && (
        <g className="armband animate-pop" style={{ animationDelay: `${armbandDelay}s` }}>
          <g clipPath={`url(#lsleeve-${id})`}>
            <path d={ARMBAND} fill={band.fill} />
            <path d={ARMBAND} fill="none" stroke={band.line} strokeOpacity="0.6" strokeWidth="0.8" />
          </g>
          <text
            x={ARMBAND_TEXT.x}
            y={ARMBAND_TEXT.y + 2.6}
            textAnchor="middle"
            fontSize="7.5"
            fontWeight="900"
            fill={band.text}
            className="font-body"
            transform={`rotate(${ARMBAND_TEXT.angle} ${ARMBAND_TEXT.x} ${ARMBAND_TEXT.y})`}
          >
            {band.letter}
          </text>
        </g>
      )}
    </svg>
  );
}

/** The hanger a shirt hangs from, in the kit room. */
export function Hanger({ className = "" }: { className?: string }) {
  return (
    <svg viewBox="0 0 120 30" className={className} aria-hidden>
      <path d="M60 3 C66 3 66 11 60 12 L60 15" fill="none" stroke="var(--hanger)" strokeWidth="2.2" strokeLinecap="round" />
      <path d="M60 15 L22 28 L98 28 Z" fill="none" stroke="var(--hanger)" strokeWidth="2.2" strokeLinejoin="round" />
    </svg>
  );
}
