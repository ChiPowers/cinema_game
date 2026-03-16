import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        cinema: {
          black: "#0a0a0a",
          dark: "#111111",
          card: "#1a1a1a",
          gold: "#f5c518",
          silver: "#9ca3af",
        },
      },
      fontFamily: {
        mono: ["var(--font-mono)", "monospace"],
      },
    },
  },
  plugins: [],
};

export default config;
