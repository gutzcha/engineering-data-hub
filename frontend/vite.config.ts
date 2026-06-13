/*
 * ===
 * File Summary
 * Path: frontend\vite.config.ts
 * Type: typescript
 * Purpose: Repository utility file supporting runtime, deployment, or documentation workflows.
 * Primary responsibilities:
 * - Domain behavior is summarized for fast onboarding and avoids full-file reread.
 * - Core symbols: inferred from domain responsibilities
 * Inputs:
 * - Downstream and upstream interactions in the same domain.
 * Outputs:
 * - API payloads, records, side effects, or UI views depending on file role.
 * Dependencies:
 * - Shared runtime services and adjacent domain modules.
 * Known risks:
 * - Validate behavior after migrations, dependency upgrades, or contract changes.
 * ===
 * 
 */

import react from "@vitejs/plugin-react";
import { configDefaults, defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react()],
  server: {
    allowedHosts: ["plastic-hub.local"],
    proxy: {
      "/api": {
        target: process.env.VITE_API_PROXY_TARGET ?? "http://backend:8000",
        changeOrigin: true
      }
    }
  },
  test: {
    environment: "jsdom",
    exclude: [...configDefaults.exclude, "e2e/**"],
    setupFiles: "./src/test/setup.ts"
  }
});

