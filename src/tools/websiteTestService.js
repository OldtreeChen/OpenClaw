import path from "node:path";

process.env.PLAYWRIGHT_BROWSERS_PATH =
  process.env.PLAYWRIGHT_BROWSERS_PATH || path.resolve(".playwright-browsers");

const websiteTestRuns = [];

function normalizeUrl(url) {
  const value = String(url || "").trim();
  if (!value) {
    return "";
  }

  if (value.startsWith("http://") || value.startsWith("https://")) {
    return value;
  }

  return `https://${value}`;
}

function buildSummary(result) {
  const lines = [
    `URL: ${result.url}`,
    `狀態: ${result.ok ? "通過" : "失敗"}`,
    `HTTP: ${result.httpStatus ?? "unknown"}`,
    `標題: ${result.title || "(empty)"}`
  ];

  if (result.consoleErrors.length > 0) {
    lines.push(`Console errors: ${result.consoleErrors.length}`);
  }

  if (result.pageErrors.length > 0) {
    lines.push(`Page errors: ${result.pageErrors.length}`);
  }

  if (result.error) {
    lines.push(`錯誤: ${result.error}`);
  }

  return lines.join("\n");
}

export async function runWebsiteTest({
  url,
  expectedTitle,
  timeoutMs = 15000
}) {
  const normalizedUrl = normalizeUrl(url);
  if (!normalizedUrl) {
    return {
      ok: false,
      error: "url is required."
    };
  }

  const consoleErrors = [];
  const pageErrors = [];
  const { chromium } = await import("playwright");

  const browser = await chromium.launch({
    headless: true
  });

  try {
    const page = await browser.newPage();

    page.on("console", (message) => {
      if (message.type() === "error") {
        consoleErrors.push(message.text());
      }
    });

    page.on("pageerror", (error) => {
      pageErrors.push(error.message);
    });

    const response = await page.goto(normalizedUrl, {
      waitUntil: "networkidle",
      timeout: timeoutMs
    });

    const title = await page.title();
    const httpStatus = response?.status() ?? null;

    const matchesExpectedTitle = expectedTitle
      ? title.includes(expectedTitle)
      : true;

    const ok =
      Boolean(response?.ok()) &&
      matchesExpectedTitle &&
      consoleErrors.length === 0 &&
      pageErrors.length === 0;

    const result = {
      id: `site_test_${websiteTestRuns.length + 1}`,
      ok,
      url: normalizedUrl,
      expectedTitle: expectedTitle || null,
      title,
      httpStatus,
      consoleErrors,
      pageErrors,
      error: matchesExpectedTitle
        ? null
        : `Title did not include expected text: ${expectedTitle}`,
      testedAt: new Date().toISOString()
    };

    result.summary = buildSummary(result);
    websiteTestRuns.unshift(result);
    websiteTestRuns.splice(10);

    return result;
  } catch (error) {
    const result = {
      id: `site_test_${websiteTestRuns.length + 1}`,
      ok: false,
      url: normalizedUrl,
      expectedTitle: expectedTitle || null,
      title: "",
      httpStatus: null,
      consoleErrors,
      pageErrors,
      error: error instanceof Error ? error.message : "Unknown website test error.",
      testedAt: new Date().toISOString()
    };

    result.summary = buildSummary(result);
    websiteTestRuns.unshift(result);
    websiteTestRuns.splice(10);

    return result;
  } finally {
    await browser.close();
  }
}

export function listWebsiteTestRuns() {
  return websiteTestRuns;
}

export function parseWebsiteTestCommand(text) {
  const input = String(text || "").trim();
  const match = input.match(/^\/test-site\s+(\S+)(?:\s+title=(.+))?$/i);

  if (!match) {
    return null;
  }

  return {
    url: match[1],
    expectedTitle: match[2]?.trim() || ""
  };
}
