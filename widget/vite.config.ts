import { defineConfig } from "vite";

export default defineConfig({
  build: {
    lib: {
      entry: "src/widget.ts",
      name: "DocuPilotWidget",
      formats: ["iife"],
      fileName: () => "widget.js",
    },
    minify: "esbuild",
    sourcemap: false,
    target: "es2019",
  },
});
