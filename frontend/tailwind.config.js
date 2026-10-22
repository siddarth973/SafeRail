/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: {
          DEFAULT: '#080d19',
          secondary: '#0b1120',
          card: '#0d1527',
          cardHover: '#111b32',
          subtle: '#141e34'
        },
        border: {
          DEFAULT: '#19253d',
          light: '#233354',
          highlight: '#2a3d66'
        },
        saferail: {
          blue: {
            DEFAULT: '#1e40af',
            light: '#3b82f6',
            glow: '#60a5fa',
            dark: '#172554'
          },
          cyan: {
            DEFAULT: '#06b6d4',
            light: '#22d3ee',
            glow: '#67e8f9'
          },
          teal: {
            DEFAULT: '#0d9488',
            light: '#14b8a6',
            emerald: '#10b981'
          },
          amber: {
            DEFAULT: '#f59e0b',
            light: '#fbbf24',
            dark: '#b45309'
          },
          red: {
            DEFAULT: '#ef4444',
            light: '#f87171',
            dark: '#b91c1c'
          }
        }
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['JetBrains Mono', 'ui-monospace', 'monospace']
      },
      boxShadow: {
        'glow-cyan': '0 0 15px -3px rgba(6, 182, 212, 0.3)',
        'glow-teal': '0 0 15px -3px rgba(16, 185, 129, 0.3)',
        'glow-blue': '0 0 15px -3px rgba(37, 99, 235, 0.3)',
        'card': '0 4px 20px -2px rgba(0, 0, 0, 0.5)'
      }
    },
  },
  plugins: [],
}
