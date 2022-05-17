import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const API_URL = process.env.API_URL || "http://localhost";

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: "0.0.0.0",
    port: 3000,
    strictPort: true,
    hmr: {
      host: "0.0.0.0",
      port: 3010,
    },
    proxy: {
      "/api": {
        target: API_URL,
        changeOrigin: false,
        rewrite: (path) => path.replace(/^\/api/, ""),
      },
    },
  },
});
