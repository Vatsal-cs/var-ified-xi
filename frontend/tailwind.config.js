/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./app/**/*.{js,ts,jsx,tsx}", "./components/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        pitch: {
          night: "#0A0E0C", // page background
          panel: "#131917", // card surface
          panel2: "#1A211E", // nested surface
          line: "#283430", // borders / dividers
        },
        var: {
          green: "#22E38A", // primary accent (slightly softened from #00FF87)
          greendim: "#0F7F4E",
          greensoft: "#0E1E17", // green-tinted fill for highlighted cards
          crimson: "#FF5C7A",
          amber: "#FFC24B",
        },
        ink: {
          100: "#F2F4F0", // headings / strong emphasis
          200: "#D3DBD6", // body copy
          300: "#A7B2AC", // secondary text
          400: "#7E8A83", // muted / captions
          500: "#5D6862", // faint labels
        },
      },
      fontFamily: {
        display: ["var(--font-oswald)", "sans-serif"],
        mono: ["var(--font-jbmono)", "ui-monospace", "monospace"],
        body: ["var(--font-inter)", "system-ui", "sans-serif"],
      },
      boxShadow: {
        card: "0 1px 0 rgba(255,255,255,0.02) inset, 0 8px 24px -16px rgba(0,0,0,0.6)",
        glow: "0 0 0 1px rgba(34,227,138,0.25), 0 8px 30px -12px rgba(34,227,138,0.25)",
      },
      keyframes: {
        sweep: {
          "0%": { transform: "translateX(-100%)" },
          "100%": { transform: "translateX(100%)" },
        },
        rise: {
          "0%": { transform: "translateY(6px)", opacity: "0" },
          "100%": { transform: "translateY(0)", opacity: "1" },
        },
        pulseDot: {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0.3" },
        },
      },
      animation: {
        sweep: "sweep 2s ease-in-out 1",
        rise: "rise 0.4s ease-out forwards",
        pulseDot: "pulseDot 2s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};
