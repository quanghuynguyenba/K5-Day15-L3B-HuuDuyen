import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Dev: frontend :5173, API Python :8000 — proxy để gọi /api, /audio không vướng CORS
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": "http://localhost:8000",
      "/audio": "http://localhost:8000",
    },
  },
});
