import { defineConfig, devices } from "@playwright/test";
import { resolve } from "node:path";
import { randomUUID } from "node:crypto";

const python = resolve("../backend/.venv", process.platform === "win32" ? "Scripts/python.exe" : "bin/python");
const record = resolve("../.codex-build", `acceptance-${randomUUID()}.json`);

export default defineConfig({
  testDir: "./e2e", fullyParallel: false, workers: 1, timeout: 240_000,
  expect: { timeout: 15_000 }, reporter: [["list"], ["html", { open: "never" }]],
  use: { baseURL: "http://127.0.0.1:5176", actionTimeout: 20_000, navigationTimeout: 30_000,
    trace: "retain-on-failure", screenshot: "only-on-failure" },
  projects: [{ name: "edge", use: { ...devices["Desktop Edge"], channel: "msedge" } }],
  globalTeardown: "./e2e/global-teardown.ts",
  metadata: { acceptancePython: python, acceptanceRecord: record },
  webServer: [
    { command: `"${python}" "${resolve("../backend/scripts/run_acceptance_server.py")}"`,
      url: "http://127.0.0.1:5016/health", timeout: 120_000, reuseExistingServer: false,
      env: { SCS360_ACCEPTANCE_RECORD: record } },
    { command: "npm run dev -- --host 127.0.0.1 --port 5176 --strictPort",
      url: "http://127.0.0.1:5176", timeout: 60_000, reuseExistingServer: false,
      env: { VITE_DEV_PROXY_TARGET: "http://127.0.0.1:5016", VITE_API_BASE_URL: "/api", VITE_ENABLE_DEMO_CREDENTIALS: "false" } },
  ],
});
