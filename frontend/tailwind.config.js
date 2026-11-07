/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        ink: '#142a33',
        paper: '#f5f6f2',
        sea: '#177d70',
        amber: '#c98730',
      },
    },
  },
  plugins: [],
}
