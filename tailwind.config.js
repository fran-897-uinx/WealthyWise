/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './templates/**/*.html',
    './financeapp/templates/**/*.html',
    './allauth_ui/**/*.html'
  ],
  theme: {
    extend: {},
  },
  plugins: [
    require('daisyui')
  ],
}
