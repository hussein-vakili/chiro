import path from "node:path";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  base: "/static/react-portal/",
  build: {
    outDir: path.resolve(__dirname, "../static/react-portal"),
    emptyOutDir: true,
    rollupOptions: {
      output: {
        entryFileNames: "portal.js",
        assetFileNames: (assetInfo) => {
          if ((assetInfo.name || "").endsWith(".css")) {
            return "portal.css";
          }
          return "assets/[name]-[hash][extname]";
        },
      },
    },
  },
});
