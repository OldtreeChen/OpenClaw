import { listReservations } from "./tools/restaurantService.js";

const startedAt = new Date();

function checkEnv(name, required = true) {
  const value = process.env[name];
  return {
    name,
    required,
    present: Boolean(value),
    status: value ? "ok" : required ? "missing" : "optional"
  };
}

export function runDiagnostics() {
  const envChecks = [
    checkEnv("OPENAI_API_KEY"),
    checkEnv("LINE_CHANNEL_SECRET"),
    checkEnv("LINE_CHANNEL_ACCESS_TOKEN"),
    checkEnv("ADMIN_LINE_USER_ID", false),
    checkEnv("GITHUB_REPO", false),
    checkEnv("GITHUB_TOKEN", false)
  ];

  const missingRequired = envChecks.filter(
    (item) => item.required && !item.present
  );

  const canSelfHeal =
    Boolean(process.env.GITHUB_REPO) && Boolean(process.env.GITHUB_TOKEN);

  return {
    ok: missingRequired.length === 0,
    timestamp: new Date().toISOString(),
    uptimeSeconds: Math.floor((Date.now() - startedAt.getTime()) / 1000),
    reservationCount: listReservations().length,
    envChecks,
    selfHealing: {
      enabled: canSelfHeal,
      reason: canSelfHeal
        ? "GitHub integration is configured."
        : "GitHub integration is not configured, so fixes cannot be persisted and redeployed automatically."
    }
  };
}

export function formatDiagnosticsReport(diagnostics) {
  const lines = [
    "OpenClaw 自我檢查結果",
    `時間: ${diagnostics.timestamp}`,
    `運行秒數: ${diagnostics.uptimeSeconds}`,
    `訂位請求數: ${diagnostics.reservationCount}`
  ];

  const requiredIssues = diagnostics.envChecks.filter(
    (item) => item.required && !item.present
  );

  if (requiredIssues.length === 0) {
    lines.push("必要環境變數: 正常");
  } else {
    lines.push(
      `必要環境變數缺少: ${requiredIssues.map((item) => item.name).join(", ")}`
    );
  }

  lines.push(
    diagnostics.selfHealing.enabled
      ? "自修正模式: 已啟用"
      : "自修正模式: 未啟用，需要 GitHub repo 與 GITHUB_TOKEN"
  );

  return lines.join("\n");
}
