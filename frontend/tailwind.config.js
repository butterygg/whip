module.exports = {
  purge: ["./src/**/*.{vue,js,ts,jsx,tsx}"],
  theme: {
    colors: {
      strawberry: "rgb(226,97,57)",
      biscuit: "rgb(225,183,109)",
      custard: "#FFFEF1",
    },
  },
  variants: {},
  plugins: [require("@tailwindcss/forms")],
};
