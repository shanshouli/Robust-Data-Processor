/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/**/*.{html,ts}"
  ],
  theme: {
    extend: {
      colors: {
        midnight: {
          50: "#f5f7ff",
          100: "#e6ebff",
          200: "#c7d3ff",
          300: "#a4b4ff",
          400: "#7d8fff",
          500: "#596bff",
          600: "#3f52e6",
          700: "#2f3fb4",
          800: "#232f82",
          900: "#1a235c"
        },
        graphite: {
          50: "#f5f6f8",
          100: "#e6e8ec",
          200: "#c9ced8",
          300: "#a9b0be",
          400: "#8a93a6",
          500: "#6d768b",
          600: "#555d6f",
          700: "#424857",
          800: "#2f3340",
          900: "#1e2129"
        }
      },
      fontFamily: {
        display: ["Space Grotesk", "system-ui", "sans-serif"],
        body: ["IBM Plex Sans", "system-ui", "sans-serif"]
      },
      boxShadow: {
        "soft-xl": "0 20px 50px -20px rgba(7, 9, 24, 0.6)",
        "soft-md": "0 12px 24px -12px rgba(7, 9, 24, 0.4)"
      }
    }
  },
  plugins: []
};
