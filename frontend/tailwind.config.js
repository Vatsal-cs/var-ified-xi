/** @type {import('tailwindcss').Config} */
//
// "Matchday" — a night-match palette. Deep blue-black ground so the accents
// can be genuinely saturated without the page turning into a light show, glass
// surfaces that sit ON the ground rather than replacing it, and a violet-to-cyan
// gradient doing the work a single flat accent used to.
//
// Semantic colour is kept separate from the brand accent on purpose: points are
// always emerald, risk is always rose, caution is always amber, whatever the
// surrounding chrome is doing.
module.exports = {
  content: ["./app/**/*.{js,ts,jsx,tsx}", "./components/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        // Ground. Blue-biased rather than neutral grey, which is what stops
        // the whole page reading as "default dark mode".
        base: "#08080F",
        surface: {
          DEFAULT: "#101018",
          raised: "#16161F",
          sunk: "#0C0C13",
        },
        line: {
          DEFAULT: "rgba(255,255,255,0.09)",
          strong: "rgba(255,255,255,0.16)",
        },
        // Brand accent, used as a gradient far more often than flat.
        brand: {
          violet: "#8B5CF6",
          indigo: "#6366F1",
          cyan: "#22D3EE",
        },
        // Semantics. These never change meaning.
        pts: "#34D399", // points, gains, good
        warn: "#FBBF24", // caution, chips, watch this
        risk: "#FB7185", // exposure, losses, sold
        ink: {
          100: "#F5F6FA",
          200: "#D5D8E3",
          300: "#A2A7B8",
          400: "#767C90",
          500: "#575D70",
        },
      },
      fontFamily: {
        display: ["var(--font-display)", "system-ui", "sans-serif"],
        body: ["var(--font-body)", "system-ui", "sans-serif"],
        mono: ["var(--font-mono)", "ui-monospace", "monospace"],
      },
      backgroundImage: {
        "brand-gradient": "linear-gradient(110deg, #8B5CF6 0%, #6366F1 45%, #22D3EE 100%)",
        "brand-soft":
          "linear-gradient(110deg, rgba(139,92,246,0.16) 0%, rgba(34,211,238,0.10) 100%)",
      },
      boxShadow: {
        glass: "inset 0 1px 0 rgba(255,255,255,0.06), 0 12px 32px -20px rgba(0,0,0,0.9)",
        lift: "inset 0 1px 0 rgba(255,255,255,0.08), 0 20px 46px -24px rgba(0,0,0,0.95)",
        brand: "0 0 0 1px rgba(139,92,246,0.35), 0 18px 50px -24px rgba(139,92,246,0.55)",
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
        drift: {
          "0%, 100%": { transform: "translate3d(0,0,0) scale(1)" },
          "50%": { transform: "translate3d(2%, -3%, 0) scale(1.08)" },
        },
      },
      animation: {
        rise: "rise 0.45s cubic-bezier(0.22,1,0.36,1) forwards",
        pulseDot: "pulseDot 2.4s ease-in-out infinite",
        drift: "drift 18s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};
