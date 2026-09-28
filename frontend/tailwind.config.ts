import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        ink: "#151A21",
        paper: "#FAFAF8",
        panel: "#FFFFFF",
        line: "#E4E4E0",
        muted: "#6B7078",
        accent: "#3E5C8A",
        accentSoft: "#EAEFF7",
        good: "#2F7D5A",
        warn: "#B8862B",
        bad: "#B6432F",
      },
      fontFamily: {
        sans: ["Source Sans 3", "system-ui", "sans-serif"],
        mono: ["IBM Plex Mono", "ui-monospace", "monospace"],
      },
      boxShadow: {
        card: "0 1px 2px rgba(21,26,33,0.06)",
      },
      borderRadius: {
        card: "10px",
      },
    },
  },
  plugins: [],
};
export default config;
