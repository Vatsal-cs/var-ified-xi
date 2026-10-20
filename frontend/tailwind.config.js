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
        // Two more accents, used sparingly: chances and probabilities (violet),
        // information and fixtures (sky). Muted like the rest, never neon.
        violet: "#A48BE0",
        sky: "#7DB7D8",
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
        // The VAR mark drawing itself: strokes with pathLength="1".
        draw: {
          "0%": { strokeDashoffset: "1" },
          "100%": { strokeDashoffset: "0" },
        },
        // A review line sweeping across a panel once, left to right.
        scan: {
          "0%": { transform: "translateX(-10%)", opacity: "0" },
          "12%": { opacity: "1" },
          "88%": { opacity: "1" },
          "100%": { transform: "translateX(1000%)", opacity: "0" },
        },
        stamp: {
          "0%": { transform: "scale(1.8) rotate(-12deg)", opacity: "0" },
          "60%": { transform: "scale(0.94) rotate(-5deg)", opacity: "1" },
          "100%": { transform: "scale(1) rotate(-6deg)", opacity: "1" },
        },
        fromLeft: {
          "0%": { transform: "translateX(-18px)", opacity: "0" },
          "100%": { transform: "translateX(0)", opacity: "1" },
        },
        fromRight: {
          "0%": { transform: "translateX(18px)", opacity: "0" },
          "100%": { transform: "translateX(0)", opacity: "1" },
        },
        strike: {
          "0%": { transform: "scaleX(0)" },
          "100%": { transform: "scaleX(1)" },
        },
        dropIn: {
          "0%": { transform: "translate(-50%, -80%) scale(0.8)", opacity: "0" },
          "70%": { transform: "translate(-50%, -48%) scale(1.04)", opacity: "1" },
          "100%": { transform: "translate(-50%, -50%) scale(1)", opacity: "1" },
        },
        ring: {
          "0%": { boxShadow: "0 0 0 0 rgba(224,166,74,0.55)" },
          "70%": { boxShadow: "0 0 0 10px rgba(224,166,74,0)" },
          "100%": { boxShadow: "0 0 0 0 rgba(224,166,74,0)" },
        },
        grow: {
          "0%": { transform: "scaleX(0)" },
          "100%": { transform: "scaleX(1)" },
        },
        coin: {
          "0%": { transform: "rotateY(0deg)" },
          "100%": { transform: "rotateY(1080deg)" },
        },
        glow: {
          "0%, 100%": { opacity: "0.35" },
          "50%": { opacity: "0.7" },
        },
      },
      animation: {
        rise: "rise 0.45s cubic-bezier(0.22,1,0.36,1) forwards",
        pulseDot: "pulseDot 2.4s ease-in-out infinite",
        draw: "draw 1.1s cubic-bezier(0.65,0,0.35,1) forwards",
        scan: "scan 1.6s cubic-bezier(0.45,0,0.2,1) 0.25s both",
        stamp: "stamp 0.55s cubic-bezier(0.22,1,0.36,1) both",
        fromLeft: "fromLeft 0.55s cubic-bezier(0.22,1,0.36,1) both",
        fromRight: "fromRight 0.55s cubic-bezier(0.22,1,0.36,1) both",
        strike: "strike 0.45s cubic-bezier(0.65,0,0.35,1) both",
        dropIn: "dropIn 0.6s cubic-bezier(0.22,1,0.36,1) both",
        ring: "ring 2.2s cubic-bezier(0.22,1,0.36,1) infinite",
        grow: "grow 0.9s cubic-bezier(0.22,1,0.36,1) both",
        coin: "coin 1.4s cubic-bezier(0.45,0,0.2,1) both",
        glow: "glow 3.2s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};
