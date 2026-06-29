import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        bg: "#0b0e14",
        panel: "#141925",
        edge: "#232a3b",
        accent: "#3b82f6",
      },
    },
  },
  plugins: [],
};

export default config;
