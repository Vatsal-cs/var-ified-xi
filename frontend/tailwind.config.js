/** @type {import('tailwindcss').Config} */
//
// "Programme" — the palette of good football print rather than of a dashboard.
//
// Warm near-black instead of blue-black, bone instead of white, and ONE accent:
// a brass gold that appears on perhaps five things per screen. No gradients, no
// glass, no glow. Hierarchy is carried by type size, weight and whitespace,
// which is what actually makes a page look expensive — colour spent everywhere
// is colour that says nothing.
//
// Semantic colours are muted on purpose. A sage green reads as "good" without
// the page turning into a set of traffic lights, and it sits with the gold
// instead of fighting it.
module.exports = {
  content: ["./app/**/*.{js,ts,jsx,tsx}", "./components/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        // Warm blacks. The red bias is slight but it is what stops this
        // reading as default dark mode.
        base: "#0B0A09",
        surface: {
          DEFAULT: "#131110",
          raised: "#1B1816",
          sunk: "#080706",
        },
        line: {
          DEFAULT: "rgba(240,235,226,0.11)",
          strong: "rgba(240,235,226,0.2)",
        },
        // The only accent. Brass, not neon.
        gold: {
          DEFAULT: "#E0A64A",
          deep: "#B8832F",
          wash: "rgba(224,166,74,0.10)",
        },
        // Semantics, deliberately muted to sit beside the gold.
        pts: "#8FBF7A", // gains, points, good
        warn: "#D9A441", // caution, chips
        risk: "#C96A5C", // exposure, sold, loss
        ink: {
          100: "#F2EDE4", // bone — headings
          200: "#D9D2C6", // body
          300: "#A8A093", // secondary
          400: "#7D766B", // captions
          500: "#5C564E", // faint labels
        },
      },
      fontFamily: {
        display: ["var(--font-display)", "Georgia", "serif"],
        body: ["var(--font-body)", "system-ui", "sans-serif"],
        mono: ["var(--font-mono)", "ui-monospace", "monospace"],
      },
      boxShadow: {
        panel: "0 1px 0 rgba(240,235,226,0.04) inset",
        raised: "0 24px 60px -40px rgba(0,0,0,0.9)",
      },
      keyframes: {
        rise: {
          "0%": { transform: "translateY(8px)", opacity: "0" },
          "100%": { transform: "translateY(0)", opacity: "1" },
        },
        pulseDot: {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0.25" },
        },
      },
      animation: {
        rise: "rise 0.45s cubic-bezier(0.22,1,0.36,1) forwards",
        pulseDot: "pulseDot 2.4s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};
