// File: apple-icon.tsx
// Path: var-ified-xi/frontend/app/apple-icon.tsx
//
// The home-screen icon (iOS wants a PNG): the same mark as app/icon.svg —
// the referee's "check the screen" rectangle with a gold tick.

import { ImageResponse } from "next/og";

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
          background: "#131110",
        }}
      >
        <svg width="150" height="150" viewBox="0 0 32 32">
          <rect x="4.6" y="7.6" width="22.8" height="16.8" rx="2.6" fill="none" stroke="#F2EDE4" strokeWidth="2.3" />
          <path
            d="M10.4 16.4 L14.4 20.1 L21.8 12.2"
            fill="none"
            stroke="#E0A64A"
            strokeWidth="3.1"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      </div>
    ),
    size
  );
}
