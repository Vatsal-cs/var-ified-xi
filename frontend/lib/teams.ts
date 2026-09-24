// File: teams.ts
// Path: var-ified-xi/frontend/lib/teams.ts
//
// Club kit colours, so a player on the pitch reads as *someone* rather than
// as an anonymous grey disc. Shirt is the primary colour, trim is what sits
// on top of it (text, the ring around the badge).
//
// Keys match the `team` strings the backend emits, which are FPL's own short
// names. Anything unrecognised falls back to a neutral slate, so a promoted
// club nobody has added yet still renders correctly.

export interface Kit {
  /** Shirt body. */
  shirt: string;
  /** Readable on top of `shirt`. */
  trim: string;
  /** Short badge text, 3 letters. */
  abbr: string;
}

const KITS: Record<string, Kit> = {
  Arsenal: { shirt: "#EF0107", trim: "#FFFFFF", abbr: "ARS" },
  "Aston Villa": { shirt: "#95BFE5", trim: "#670E36", abbr: "AVL" },
  Bournemouth: { shirt: "#DA291C", trim: "#000000", abbr: "BOU" },
  Brentford: { shirt: "#E30613", trim: "#FFFFFF", abbr: "BRE" },
  Brighton: { shirt: "#0057B8", trim: "#FFCD00", abbr: "BHA" },
  Burnley: { shirt: "#6C1D45", trim: "#99D6EA", abbr: "BUR" },
  Chelsea: { shirt: "#034694", trim: "#FFFFFF", abbr: "CHE" },
  "Coventry City": { shirt: "#78D0F3", trim: "#1B1B1B", abbr: "COV" },
  "Crystal Palace": { shirt: "#1B458F", trim: "#C4122E", abbr: "CRY" },
  Everton: { shirt: "#003399", trim: "#FFFFFF", abbr: "EVE" },
  Fulham: { shirt: "#FFFFFF", trim: "#000000", abbr: "FUL" },
  "Hull City": { shirt: "#F18A01", trim: "#000000", abbr: "HUL" },
  "Ipswich Town": { shirt: "#3A64A3", trim: "#FFFFFF", abbr: "IPS" },
  Leeds: { shirt: "#FFFFFF", trim: "#1D428A", abbr: "LEE" },
  Leicester: { shirt: "#003090", trim: "#FDBE11", abbr: "LEI" },
  Liverpool: { shirt: "#C8102E", trim: "#F6EB61", abbr: "LIV" },
  Luton: { shirt: "#F78F1E", trim: "#002D62", abbr: "LUT" },
  "Man City": { shirt: "#6CABDD", trim: "#1C2C5B", abbr: "MCI" },
  "Man Utd": { shirt: "#DA291C", trim: "#FBE122", abbr: "MUN" },
  Newcastle: { shirt: "#241F20", trim: "#FFFFFF", abbr: "NEW" },
  Norwich: { shirt: "#FFF200", trim: "#00A650", abbr: "NOR" },
  "Nott'm Forest": { shirt: "#DD0000", trim: "#FFFFFF", abbr: "NFO" },
  Sheffield: { shirt: "#EE2737", trim: "#FFFFFF", abbr: "SHU" },
  Southampton: { shirt: "#D71920", trim: "#FFFFFF", abbr: "SOU" },
  Spurs: { shirt: "#FFFFFF", trim: "#132257", abbr: "TOT" },
  Sunderland: { shirt: "#EB172B", trim: "#FFFFFF", abbr: "SUN" },
  Watford: { shirt: "#FBEE23", trim: "#ED2127", abbr: "WAT" },
  "West Ham": { shirt: "#7A263A", trim: "#1BB1E7", abbr: "WHU" },
  Wolves: { shirt: "#FDB913", trim: "#231F20", abbr: "WOL" },
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

/** White-ish shirts need a darker outline or they vanish on a dark pitch. */
export function needsOutline(kit: Kit): boolean {
  const hex = kit.shirt.replace("#", "");
  const r = parseInt(hex.slice(0, 2), 16);
  const g = parseInt(hex.slice(2, 4), 16);
  const b = parseInt(hex.slice(4, 6), 16);
  return (r * 299 + g * 587 + b * 114) / 1000 > 180;
}
