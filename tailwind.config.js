/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./templates/**/*.html",
    "./financeapp/templates/**/*.html",
    "./allauth_ui/**/*.html",
  ],
  plugins: [require("daisyui")],
};