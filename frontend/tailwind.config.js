/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        ev: {
          bg: '#0a0f1e',
          surface: '#111827',
          card: '#161d2e',
          border: '#1e2d45',
          accent: '#00e5a0',
          accent2: '#00b4ff',
          accent3: '#7c3aed',
          text: '#e8f0fe',
          muted: '#6b7fa3',
          warn: '#f59e0b',
        }
      },
      fontFamily: {
        head: ['Syne', 'sans-serif'],
        body: ['DM Sans', 'sans-serif'],
      }
    }
  },
  plugins: []
}
