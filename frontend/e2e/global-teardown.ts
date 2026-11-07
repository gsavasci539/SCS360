import { execFileSync } from "node:child_process";
import { resolve } from "node:path";
import type { FullConfig } from "@playwright/test";

export default function teardown(config: FullConfig) {
  // Playwright terminates Windows web-server process trees before Python can
  // always run its finally block. Delete only this run's recorded test DB.
  execFileSync(String(config.metadata.acceptancePython), [resolve("../backend/scripts/cleanup_acceptance_database.py"),
    String(config.metadata.acceptanceRecord)], { stdio: "inherit", windowsHide: true });
}
