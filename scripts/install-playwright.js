import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import path from "node:path";

const currentFile = fileURLToPath(import.meta.url);
const currentDir = path.dirname(currentFile);
const browsersPath = path.resolve(".playwright-browsers");
const cliPath = path.resolve(currentDir, "..", "node_modules", "playwright", "cli.js");

const result = spawnSync(
  process.execPath,
  [cliPath, "install", "chromium"],
  {
    stdio: "inherit",
    env: {
      ...process.env,
      PLAYWRIGHT_BROWSERS_PATH: browsersPath
    }
  }
);

if (result.status !== 0) {
  process.exit(result.status ?? 1);
}
