/** Colours come from CSS variables (src/styles/index.css) so light/dark themes switch without rebuilding. */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        bg: 'var(--bg)', ink: 'var(--ink)', mut: 'var(--mut)', card: 'var(--card)', soft: 'var(--soft)', line: 'var(--line)',
        brand: 'var(--brand)', mint: 'var(--mint)', bad: 'var(--bad)', warn: 'var(--warn)', ok: 'var(--ok)',
      },
      fontFamily: { sans: ['"Plus Jakarta Sans"', 'ui-sans-serif', 'system-ui', '-apple-system', 'Segoe UI', 'Roboto', 'sans-serif'] },
    },
  },
  plugins: [],
}
