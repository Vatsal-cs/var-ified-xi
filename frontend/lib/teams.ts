// File: teams.ts
// Path: var-ified-xi/frontend/lib/teams.ts
//
// Club kit colours and crests, so a player on the pitch reads as *someone*
// rather than as an anonymous grey disc. Shirt is the primary colour, trim is
// what sits on top of it (text, the ring around the badge); code names the
// club's crest on the Premier League's image server.
//
// Keys match the `team` strings the backend emits, which are FPL's own short
// names. Anything unrecognised falls back to a neutral slate, so a promoted
// club nobody has added yet still renders correctly.

export interface Kit {
  /** Shirt body. */
  shirt: string;
  /** Readable on top of `shirt`: collar, cuffs, the shirt number. */
  trim: string;
  /** Short badge text, 3 letters. */
  abbr: string;
  /** The club's Premier League code (FPL's teams[].code), which names its crest. */
  code?: number;
  /** Second colour of a striped shirt (Newcastle, Brentford…). */
  stripe?: string;
  /** Sleeves in a different colour (Arsenal's white, Villa's sky blue). */
  sleeve?: string;
}

const KITS: Record<string, Kit> = {
  Arsenal: { shirt: "#E2231A", trim: "#FFFFFF", sleeve: "#FFFFFF", abbr: "ARS", code: 3 },
  "Aston Villa": { shirt: "#7A1E3C", trim: "#95BFE5", sleeve: "#95BFE5", abbr: "AVL", code: 7 },
  Bournemouth: { shirt: "#DA291C", trim: "#111111", stripe: "#111111", abbr: "BOU", code: 91 },
  Brentford: { shirt: "#E30613", trim: "#111111", stripe: "#FFFFFF", abbr: "BRE", code: 94 },
  Brighton: { shirt: "#0057B8", trim: "#111111", stripe: "#FFFFFF", abbr: "BHA", code: 36 },
  Burnley: { shirt: "#6C1D45", trim: "#99D6EA", sleeve: "#99D6EA", abbr: "BUR", code: 90 },
  Chelsea: { shirt: "#0A4A9E", trim: "#FFFFFF", abbr: "CHE", code: 8 },
  "Coventry City": { shirt: "#78D0F3", trim: "#1B1B1B", abbr: "COV", code: 9 },
  "Crystal Palace": { shirt: "#C4122E", trim: "#111111", stripe: "#1B458F", abbr: "CRY", code: 31 },
  Everton: { shirt: "#123A8C", trim: "#FFFFFF", abbr: "EVE", code: 11 },
  Fulham: { shirt: "#F4F4F2", trim: "#111111", abbr: "FUL", code: 54 },
  "Hull City": { shirt: "#F18A01", trim: "#111111", abbr: "HUL", code: 88 },
  "Ipswich Town": { shirt: "#3A64A3", trim: "#FFFFFF", abbr: "IPS", code: 40 },
  Leeds: { shirt: "#F4F4F2", trim: "#1D428A", abbr: "LEE", code: 2 },
  Leicester: { shirt: "#003090", trim: "#FDBE11", abbr: "LEI", code: 13 },
  Liverpool: { shirt: "#C8102E", trim: "#FFFFFF", abbr: "LIV", code: 14 },
  Luton: { shirt: "#F78F1E", trim: "#002D62", abbr: "LUT", code: 102 },
  "Man City": { shirt: "#79B4E0", trim: "#1C2C5B", abbr: "MCI", code: 43 },
  "Man Utd": { shirt: "#DA291C", trim: "#FFFFFF", abbr: "MUN", code: 1 },
  Newcastle: { shirt: "#18181A", trim: "#111111", stripe: "#FFFFFF", abbr: "NEW", code: 4 },
  Norwich: { shirt: "#FFF200", trim: "#00A650", abbr: "NOR", code: 45 },
  "Nott'm Forest": { shirt: "#C8102E", trim: "#FFFFFF", abbr: "NFO", code: 17 },
  Sheffield: { shirt: "#EE2737", trim: "#111111", stripe: "#FFFFFF", abbr: "SHU", code: 49 },
  Southampton: { shirt: "#D71920", trim: "#111111", stripe: "#FFFFFF", abbr: "SOU", code: 20 },
  Spurs: { shirt: "#F3F3F1", trim: "#132257", abbr: "TOT", code: 6 },
  Sunderland: { shirt: "#E2231A", trim: "#111111", stripe: "#FFFFFF", abbr: "SUN", code: 56 },
  Watford: { shirt: "#FBEE23", trim: "#111111", abbr: "WAT", code: 57 },
  "West Ham": { shirt: "#7A263A", trim: "#FFFFFF", sleeve: "#1BB1E7", abbr: "WHU", code: 21 },
  Wolves: { shirt: "#FDB913", trim: "#231F20", abbr: "WOL", code: 39 },
};

const FALLBACK: Kit = { shirt: "#4A5A52", trim: "#F2F4F0", abbr: "—" };

export function kitFor(team: string | undefined): Kit {
  if (!team) return FALLBACK;
  if (KITS[team]) return KITS[team];
  // Tolerate small naming drifts ("Spurs" vs "Tottenham") without a crash.
  const loose = Object.keys(KITS).find(
    (k) => k.toLowerCase().startsWith(team.toLowerCase().slice(0, 4))
  );
  return loose ? KITS[loose] : { ...FALLBACK, abbr: team.slice(0, 3).toUpperCase() };
}

/** The club crest, from the Premier League's own image server: an SVG, then
 *  a PNG of the same badge if that fails. Empty for a club without a code,
 *  which then shows its kit colours instead (components/Crest.tsx). */
export function crestUrls(team: string | undefined): string[] {
  const code = kitFor(team).code;
  if (!code) return [];
  return [
    `https://resources.premierleague.com/premierleague25/badges/${code}.svg`,
    `https://resources.premierleague.com/premierleague/badges/100/t${code}@x2.png`,
  ];
}

/** A goalkeeper's shirt: yellow, or charcoal when the club already plays in
 *  something light, so the keeper never matches his outfield players. */
export function goalkeeperKit(team: string | undefined): Kit {
  const kit = kitFor(team);
  const hex = kit.shirt.replace("#", "");
  const [r, g, b] = [0, 2, 4].map((i) => parseInt(hex.slice(i, i + 2), 16));
  const light = (r * 299 + g * 587 + b * 114) / 1000 > 165;
  return light
    ? { ...kit, shirt: "#2B2D31", trim: "#E9C341", stripe: undefined, sleeve: undefined }
    : { ...kit, shirt: "#E9C341", trim: "#1A1A1A", stripe: undefined, sleeve: undefined };
}

/** White-ish shirts need a darker outline or they vanish on a dark pitch. */
export function needsOutline(kit: Kit): boolean {
  const hex = kit.shirt.replace("#", "");
  const r = parseInt(hex.slice(0, 2), 16);
  const g = parseInt(hex.slice(2, 4), 16);
  const b = parseInt(hex.slice(4, 6), 16);
  return (r * 299 + g * 587 + b * 114) / 1000 > 180;
}
