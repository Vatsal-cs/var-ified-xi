/** @type {import('tailwindcss').Config} */
//
// "Kit room" — the dressing room rather than the dashboard.
//
// Every colour is a CSS variable (app/globals.css) so the same classes serve a
// warm stone light mode and a charcoal dark mode. Most are RGB triplets, which
// keeps Tailwind's opacity modifiers working (`bg-risk/10`, `text-pts/80`).
// One accent, a kit-room gold, plus muted semantics for gains, losses and
// chances. No glows, no gradients: the shirts and crests carry the colour.
const rgb = (v) => `rgb(var(${v}) / <alpha-value>)`;

module.exports = {
  content: ["./app/**/*.{js,ts,jsx,tsx}", "./components/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        base: rgb("--c-base"),
        surface: {
          DEFAULT: rgb("--c-surface"),
          raised: rgb("--c-raised"),
          sunk: rgb("--c-sunk"),
        },
        line: {
          DEFAULT: "var(--c-line)",
          strong: "var(--c-line-strong)",
        },
        gold: {
          DEFAULT: rgb("--c-gold"),
          deep: rgb("--c-gold-deep"),
          wash: "var(--c-gold-wash)",
        },
        pts: rgb("--c-pts"), // gains, points, good
        violet: rgb("--c-violet"), // chances and probabilities
        sky: rgb("--c-sky"), // information and fixtures
        coral: rgb("--c-coral"),
        warn: rgb("--c-warn"), // caution, chips
        risk: rgb("--c-risk"), // exposure, sold, loss
        grass: {
          DEFAULT: rgb("--c-grass"),
          dark: rgb("--c-grass-dark"),
        },
        plate: {
          DEFAULT: rgb("--c-plate"),
          text: rgb("--c-plate-text"),
        },
        ink: {
          100: rgb("--c-ink-100"), // headings
          200: rgb("--c-ink-200"), // body
          300: rgb("--c-ink-300"), // secondary
          400: rgb("--c-ink-400"), // captions
          500: rgb("--c-ink-500"), // faint labels
        },
      },
      fontFamily: {
        display: ["var(--font-display)", "var(--font-sans)", "sans-serif"],
        body: ["var(--font-sans)", "system-ui", "sans-serif"],
        mono: ["var(--font-mono)", "ui-monospace", "monospace"],
        // Shirt numbers and big figures: a condensed sports numeral.
        kit: ["var(--font-kit)", "var(--font-sans)", "sans-serif"],
      },
      boxShadow: {
        panel: "var(--shadow-panel)",
        raised: "var(--shadow-raised)",
      },
      keyframes: {
        rise: {
          "0%": { transform: "translateY(10px)", opacity: "0" },
          "100%": { transform: "translateY(0)", opacity: "1" },
        },
        pulseDot: {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0.3" },
        },
        // The VAR mark drawing itself: strokes with pathLength="1".
        draw: {
          "0%": { strokeDashoffset: "1" },
          "100%": { strokeDashoffset: "0" },
        },
        strike: {
          "0%": { transform: "scaleX(0)" },
          "100%": { transform: "scaleX(1)" },
        },
        grow: {
          "0%": { transform: "scaleX(0)" },
          "100%": { transform: "scaleX(1)" },
        },
        coin: {
          "0%": { transform: "rotateY(0deg)" },
          "100%": { transform: "rotateY(1080deg)" },
        },
        // A shirt dropping onto its peg and swinging to rest. Pivots on its
        // top edge (origin-top), like something hung up.
        hang: {
          "0%": { opacity: "0", transform: "translateY(-26px) rotate(-12deg)" },
          "45%": { opacity: "1", transform: "translateY(2px) rotate(6deg)" },
          "70%": { transform: "rotate(-3deg)" },
          "88%": { transform: "rotate(1deg)" },
          "100%": { opacity: "1", transform: "none" },
        },
        // The shirt swap: the old shirt is taken down, the new one swings on.
        outgo: {
          "0%": { opacity: "0", transform: "translateY(-14px)", filter: "none" },
          "25%": { opacity: "1", transform: "none", filter: "none" },
        },
        income: {
          "0%": { opacity: "0", transform: "translateX(70px) rotate(14deg)" },
          "55%": { opacity: "1", transform: "translateX(-4px) rotate(-5deg)" },
          "75%": { transform: "rotate(2.5deg)" },
          "100%": { opacity: "1", transform: "none" },
        },
        pop: {
          "0%": { opacity: "0", transform: "scale(.6)" },
          "70%": { opacity: "1", transform: "scale(1.12)" },
          "100%": { opacity: "1", transform: "scale(1)" },
        },
        // The seconds digit dropping into place each tick.
        tick: {
          "0%": { transform: "translateY(-35%)", opacity: "0.3" },
          "100%": { transform: "translateY(0)", opacity: "1" },
        },
      },
      animation: {
        rise: "rise 0.6s cubic-bezier(0.2,0.8,0.2,1) both",
        pulseDot: "pulseDot 2s ease-in-out infinite",
        draw: "draw 1.1s cubic-bezier(0.65,0,0.35,1) forwards",
        strike: "strike 0.45s cubic-bezier(0.65,0,0.35,1) both",
        grow: "grow 1.1s cubic-bezier(0.2,0.8,0.2,1) both",
        coin: "coin 1.4s cubic-bezier(0.45,0,0.2,1) both",
        hang: "hang 1s cubic-bezier(0.25,0.9,0.3,1.2) both",
        outgo: "outgo 1.3s cubic-bezier(0.3,0.7,0.3,1) both",
        income: "income 1.4s cubic-bezier(0.2,0.9,0.25,1) both",
        pop: "pop 0.5s cubic-bezier(0.3,1.5,0.5,1) both",
        tick: "tick 0.35s cubic-bezier(0.2,0.8,0.2,1) both",
      },
    },
  },
  plugins: [],
};
