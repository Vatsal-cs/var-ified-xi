// File: Logo.tsx
// Path: var-ified-xi/frontend/components/Logo.tsx
//
// The VAR-ified XI crest: a club badge with a gold edge and "XI" across it.
// The letters are drawn as shapes, not text, so the mark looks the same in
// the header, the browser tab (app/icon.svg) and on a home screen
// (app/apple-icon.tsx) — keep all three in step.

export const CREST_OUTER = "M32 2 L58 9 L58 30 C58 46 47 56 32 62 C17 56 6 46 6 30 L6 9 Z";
export const CREST_INNER =
  "M32 6.2 L54.2 12 L54.2 30 C54.2 43.6 44.8 52.4 32 57.6 C19.2 52.4 9.8 43.6 9.8 30 L9.8 12 Z";
// X: two bars crossing, clipped to the letter height; I: one bar.
export const CREST_X = "M19.2 19 L33.6 46 M33.6 19 L19.2 46";
export const CREST_I = { x: 38.4, y: 19, width: 5.8, height: 27 };
export const CREST_GOLD = "#E3A93C";
export const CREST_DARK = "#14161A";

export default function LogoMark({ className = "" }: { className?: string }) {
  return (
    <svg viewBox="0 0 64 64" className={className} aria-hidden>
      <defs>
        <clipPath id="vx-crest-letters">
          <rect x="0" y={CREST_I.y} width="64" height={CREST_I.height} />
        </clipPath>
        <linearGradient id="vx-crest-sheen" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#fff" stopOpacity="0.14" />
          <stop offset="0.55" stopColor="#fff" stopOpacity="0" />
        </linearGradient>
      </defs>
      <path d={CREST_OUTER} fill={CREST_GOLD} />
      <path d={CREST_INNER} fill={CREST_DARK} />
      <path d={CREST_INNER} fill="url(#vx-crest-sheen)" />
      <path d={CREST_X} stroke={CREST_GOLD} strokeWidth="5.4" clipPath="url(#vx-crest-letters)" />
      <rect {...CREST_I} fill={CREST_GOLD} />
    </svg>
  );
}
