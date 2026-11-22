import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig(({ command }) => ({
    plugins: [react()],
    base: command === "serve" ? "/" : "/static/frontend/",
    build: {
        outDir: "../backend/static/frontend",
        emptyOutDir: true,
        assetsDir: "assets",
        sourcemap: false,
    },
    server: {
        port: 5173,
        strictPort: true,
        proxy: {
            "/static": {
                target: "http://127.0.0.1:8000",
                changeOrigin: false,
            },
            "/api": {
                target: "http://127.0.0.1:8000",
                changeOrigin: false,
            },
            "/accounts": {
                target: "http://127.0.0.1:8000",
                changeOrigin: false,
            },
            "/management": {
                target: "http://127.0.0.1:8000",
                changeOrigin: false,
            },
            "/student": {
                target: "http://127.0.0.1:8000",
                changeOrigin: false,
            },
            "/lecturer": {
                target: "http://127.0.0.1:8000",
                changeOrigin: false,
            },
            "/healthz": {
                target: "http://127.0.0.1:8000",
                changeOrigin: false,
            },
            "/readyz": {
                target: "http://127.0.0.1:8000",
                changeOrigin: false,
            },
        },
    },
}));
