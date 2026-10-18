/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        ink: { 950: '#05070D', 900: '#080B14', 800: '#0C111D', 700: '#131A2A' },
        fg: { DEFAULT: '#E9ECF6', muted: '#9BA4BA', subtle: '#69738C' },
        brand: { blue: '#5B7CFF', indigo: '#6B6FF5', violet: '#8B6CF6' },
        ok: '#3DD6A0',
        warn: '#F2B84B',
        bad: '#F0708A',
      },
      fontFamily: {
        sans: ['Geist', 'Inter', 'ui-sans-serif', 'system-ui', 'sans-serif'],
      },
      keyframes: {
        shimmer: { '100%': { transform: 'translateX(100%)' } },
        beacon: {
          '0%': { transform: 'scale(1)', opacity: '0.55' },
          '100%': { transform: 'scale(2.6)', opacity: '0' },
        },
        spin: { to: { transform: 'rotate(360deg)' } },
      },
      animation: {
        shimmer: 'shimmer 1.6s infinite',
        beacon: 'beacon 2.4s ease-out infinite',
        spin: 'spin 0.8s linear infinite',
      },
    },
  },
  plugins: [],
}
