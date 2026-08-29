/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['var(--font-sans)', 'Inter', 'ui-sans-serif', 'system-ui', 'sans-serif'],
      },
      colors: {
        accent: {
          DEFAULT: '#0ea5e9',
          hover: '#38bdf8',
          soft: 'rgba(14, 165, 233, 0.12)',
        },
      },
      boxShadow: {
        card: '0 8px 30px rgba(0, 0, 0, 0.35)',
        glow: '0 0 0 1px rgba(14, 165, 233, 0.35), 0 8px 24px rgba(14, 165, 233, 0.12)',
      },
    },
  },
  plugins: [],
};
