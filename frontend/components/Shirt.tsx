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

/** The shirt outline, for marks that want the silhouette alone. */
export const SHIRT_PATH = BODY;

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

  return (
    <svg viewBox="0 0 120 120" className={className} aria-hidden>
      <defs>
        <linearGradient id={`light-${id}`} x1="0" y1="0" x2="0.6" y2="1">
          <stop offset="0" stopColor="#fff" stopOpacity="0.22" />
          <stop offset="0.45" stopColor="#fff" stopOpacity="0" />
          <stop offset="1" stopColor="#000" stopOpacity="0.22" />
        </linearGradient>
        <clipPath id={`clip-${id}`}>
          <path d={BODY} />
        </clipPath>
        {striped && (
          <pattern id={`stripe-${id}`} width="12" height="12" patternUnits="userSpaceOnUse">
            <rect width="12" height="12" fill={kit.shirt} />
            <rect x="6" width="6" height="12" fill={kit.stripe} />
          </pattern>
        )}
      </defs>

      <path d={NECK_INSIDE} fill={kit.shirt} />
      <path d={NECK_INSIDE} fill="rgba(0,0,0,0.45)" />
      <path d={BODY} fill={striped ? `url(#stripe-${id})` : kit.shirt} />
      {kit.sleeve && <path d={SLEEVES} fill={kit.sleeve} clipPath={`url(#clip-${id})`} />}
      {/* Fabric light: brighter shoulders, a darker hem */}
      <rect width="120" height="120" fill={`url(#light-${id})`} clipPath={`url(#clip-${id})`} />
      <path d={COLLAR_BACK} fill="none" stroke={edge} strokeWidth="2" strokeLinecap="round" opacity="0.9" />
      <path d={COLLAR_FRONT} fill="none" stroke={edge} strokeWidth="3.4" strokeLinecap="round" />
      <path d={CUFFS} stroke={kit.sleeve ? kit.shirt : edge} strokeWidth="3.6" strokeLinecap="round" />
      <path d={BODY} fill="none" stroke="rgba(0,0,0,0.2)" strokeWidth="1" strokeLinejoin="round" />

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
        <g transform="rotate(-34 101 33)">
          <g className="armband animate-pop" style={{ animationDelay: `${armbandDelay}s` }}>
            <rect
              x="91"
              y="28.5"
              width="20"
              height="9"
              rx="2"
              fill={captain ? "#E3A93C" : "#15171B"}
              stroke="rgba(0,0,0,0.25)"
            />
            <text
              x="101"
              y="35.6"
              textAnchor="middle"
              fontSize="7.5"
              fontWeight="800"
              fill={captain ? "#2A1A00" : "#F2F0EC"}
              className="font-body"
            >
              {captain ? "C" : "V"}
            </text>
          </g>
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
