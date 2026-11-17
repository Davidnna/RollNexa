/** @type {import('tailwindcss').Config} */
export default {
    content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
    theme: {
        extend: {
            colors: {
                ink: "#101b35",
                teal: "#0da99a",
                mist: "#f4f7fa",
                slate: "#62708a",
            },
            fontFamily: {
                sans: ["DM Sans", "sans-serif"],
                display: ["Manrope", "sans-serif"],
            },
            boxShadow: {
                soft: "0 18px 50px rgba(16, 27, 53, 0.08)",
            },
        },
    },
    plugins: [],
};
