import tailwindcss from "@tailwindcss/vite";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { fileURLToPath, URL } from "node:url";

export default defineConfig({
    plugins: [react(), tailwindcss()],
    resolve: {
        alias: {
            "@": fileURLToPath(new URL("./src", import.meta.url)),
        },
    },
    build: {
        rollupOptions: {
            output: {
                manualChunks(id) {
                    if (!id.includes("/node_modules/")) return;
                    if (/\/node_modules\/(react|react-dom|scheduler)\//.test(id)) return "react-vendor";
                    if (id.includes("/node_modules/react-router")) return "router-vendor";
                    if (id.includes("/node_modules/radix-ui/")) return "radix-vendor";
                    if (id.includes("/node_modules/lucide-react/")) return "icons";
                },
            },
        },
    },
    server: {
        host: "127.0.0.1",
        port: 3000
    }
});