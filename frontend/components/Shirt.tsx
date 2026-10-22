// File: Shirt.tsx
// Path: var-ified-xi/frontend/components/Shirt.tsx
//
// A player drawn as his club shirt: the kit's colours (stripes and contrasting
// sleeves included), the crest on the chest, and a number — the site uses it
// for projected points. Captains and vices wear an armband on the left sleeve.
// Plain SVG, so it renders on the server and scales to any size.

import { crestUrls, goalkeeperKit, kitFor } from "@/lib/teams";

const BODY =
  "M38 14 C44 18 50 20 60 20 C70 20 76 18 82 14 L104 26 C107 28 108 31 107 34 L99 52 C98 55 95 56 92 55 " +
  "L86 52 L86 108 C86 111 84 113 81 113 L39 113 C36 113 34 111 34 108 L34 52 L28 55 C25 56 22 55 21 52 " +
  "L13 34 C12 31 13 28 16 26 Z";
const SLEEVES =
  "M38 14 L16 26 C13 28 12 31 13 34 L21 52 C22 55 25 56 28 55 L34 52 L34 24 Z " +
  "M82 14 L104 26 C107 28 108 31 107 34 L99 52 C98 55 95 56 92 55 L86 52 L86 24 Z";

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

      <path d={BODY} fill={striped ? `url(#stripe-${id})` : kit.shirt} />
      {kit.sleeve && <path d={SLEEVES} fill={kit.sleeve} clipPath={`url(#clip-${id})`} />}
      {/* Fabric light: brighter shoulders, a darker hem */}
      <rect width="120" height="120" fill={`url(#light-${id})`} clipPath={`url(#clip-${id})`} />
      <path d="M46 15.5 C50 23 70 23 74 15.5" fill="none" stroke={edge} strokeWidth="3.2" strokeLinecap="round" />
      <path d="M13 34 L21 52 M107 34 L99 52" stroke={kit.sleeve ? kit.shirt : edge} strokeWidth="3.4" strokeLinecap="round" />
      <path d={BODY} fill="none" stroke="rgba(0,0,0,0.19)" strokeWidth="1" />

      {crest && <image href={crest} x="65" y="29" width="13" height="13" />}

      {striped && <rect x="44" y="64" width="32" height="30" rx="5" fill="#fff" />}
      <text
        x="60"
        y="88"
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
        <g transform="rotate(-62 99 40)">
          <g className="armband animate-pop" style={{ animationDelay: `${armbandDelay}s` }}>
            <rect
              x="88"
              y="34.5"
              width="22"
              height="11"
              rx="2"
              fill={captain ? "#E3A93C" : "#15171B"}
              stroke="rgba(0,0,0,0.25)"
            />
            <text
              x="99"
              y="43.4"
              textAnchor="middle"
              fontSize="9"
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
