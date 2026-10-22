// File: apple-icon.tsx
// Path: var-ified-xi/frontend/app/apple-icon.tsx
//
// The home-screen icon (iOS wants a PNG): the crest from components/Logo.tsx
// on the site's dark ground. Keep it in step with app/icon.svg.

import { ImageResponse } from "next/og";
import { CREST_DARK, CREST_GOLD, CREST_I, CREST_INNER, CREST_OUTER, CREST_X } from "@/components/Logo";

export const size = { width: 180, height: 180 };
export const contentType = "image/png";

export default function AppleIcon() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          background: "#0E0F11",
        }}
      >
        <svg width="136" height="136" viewBox="0 0 64 64">
          <defs>
            <clipPath id="l">
              <rect x="0" y={CREST_I.y} width="64" height={CREST_I.height} />
            </clipPath>
          </defs>
          <path d={CREST_OUTER} fill={CREST_GOLD} />
          <path d={CREST_INNER} fill={CREST_DARK} />
          <path d={CREST_X} stroke={CREST_GOLD} strokeWidth="5.4" clipPath="url(#l)" />
          <rect x={CREST_I.x} y={CREST_I.y} width={CREST_I.width} height={CREST_I.height} fill={CREST_GOLD} />
        </svg>
      </div>
    ),
    size
  );
}
