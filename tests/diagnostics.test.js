import test from "node:test";
import assert from "node:assert/strict";
import {
  formatDiagnosticsReport,
  runDiagnostics
} from "../src/diagnostics.js";

test("runDiagnostics reports missing required variables when unset", () => {
  const originalOpenAiKey = process.env.OPENAI_API_KEY;
  const originalLineSecret = process.env.LINE_CHANNEL_SECRET;
  const originalLineToken = process.env.LINE_CHANNEL_ACCESS_TOKEN;

  delete process.env.OPENAI_API_KEY;
  delete process.env.LINE_CHANNEL_SECRET;
  delete process.env.LINE_CHANNEL_ACCESS_TOKEN;

  const diagnostics = runDiagnostics();

  assert.equal(diagnostics.ok, false);
  assert.ok(
    diagnostics.envChecks.some(
      (item) => item.name === "OPENAI_API_KEY" && item.present === false
    )
  );

  process.env.OPENAI_API_KEY = originalOpenAiKey;
  process.env.LINE_CHANNEL_SECRET = originalLineSecret;
  process.env.LINE_CHANNEL_ACCESS_TOKEN = originalLineToken;
});

test("formatDiagnosticsReport includes self-healing status", () => {
  const report = formatDiagnosticsReport({
    timestamp: "2026-03-15T00:00:00.000Z",
    uptimeSeconds: 10,
    reservationCount: 0,
    envChecks: [],
    selfHealing: {
      enabled: false
    }
  });

  assert.match(report, /OpenClaw 自我檢查結果/);
  assert.match(report, /自修正模式/);
});
