import { defineConfig } from "vite";
import { vitePlugin as remix } from "@remix-run/dev";
import tsconfigPaths from "vite-tsconfig-paths";
import { resolve } from "path";

export default defineConfig({
    server: {
        port: 4000,
        host: true,
        hmr: true
    },
    plugins: [
        remix({
            ignoredRouteFiles: ["**/.*"]
        }),
        tsconfigPaths()
    ],
    resolve: {
        alias: {
            "~": resolve(__dirname, "./app")
        }
    },
    build: {
        sourcemap: true,
        outDir: "public/build",
        rollupOptions: {
            output: {
                manualChunks: {
                    vendor: [
                        "react",
                        "react-dom",
                        "@remix-run/react"
                    ]
                }
            }
        }
    },
    optimizeDeps: {
        include: ["react", "react-dom"]
    },
    css: {
        devSourcemap: true,
        postcss: true
    }
}); 