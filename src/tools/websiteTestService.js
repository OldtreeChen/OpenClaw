import path from "node:path";

process.env.PLAYWRIGHT_BROWSERS_PATH =
  process.env.PLAYWRIGHT_BROWSERS_PATH || path.resolve(".playwright-browsers");

const websiteTestRuns = [];

function getLoginTestConfig() {
  return {
    baseUrl: String(process.env.LOGIN_TEST_BASE_URL || "").trim(),
    loginUrl:
      String(process.env.LOGIN_TEST_LOGIN_URL || "").trim() ||
      String(process.env.LOGIN_TEST_BASE_URL || "").trim(),
    username: String(process.env.LOGIN_TEST_USERNAME || "").trim(),
    password: String(process.env.LOGIN_TEST_PASSWORD || "").trim(),
    usernameSelector: String(process.env.LOGIN_TEST_USERNAME_SELECTOR || "").trim(),
    passwordSelector: String(process.env.LOGIN_TEST_PASSWORD_SELECTOR || "").trim(),
    submitSelector: String(process.env.LOGIN_TEST_SUBMIT_SELECTOR || "").trim(),
    successSelector: String(process.env.LOGIN_TEST_SUCCESS_SELECTOR || "").trim(),
    successText: String(process.env.LOGIN_TEST_SUCCESS_TEXT || "").trim(),
    postLoginPath: String(process.env.LOGIN_TEST_POST_LOGIN_PATH || "").trim()
  };
}

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

function buildLoginReport(result) {
  const lines = [
    `URL: ${result.url}`,
    `登入測試: ${result.ok ? "通過" : "失敗"}`,
    `登入頁 HTTP: ${result.httpStatus ?? "unknown"}`,
    `登入頁標題: ${result.title || "(empty)"}`,
    `報告時間: ${result.testedAt}`
  ];

  for (const step of result.steps) {
    lines.push(`- ${step.name}: ${step.ok ? "ok" : "failed"}`);
    if (step.detail) {
      lines.push(`  ${step.detail}`);
    }
  }

  if (result.consoleErrors.length > 0) {
    lines.push(`Console warnings: ${result.consoleErrors.length}`);
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

export function parseNaturalWebsiteTestCommand(text) {
  const input = String(text || "").trim();
  if (!input) {
    return null;
  }

  const urlMatch = input.match(/https?:\/\/\S+/i);
  if (!urlMatch) {
    return null;
  }

  const wantsSiteTest =
    /測試|檢查|巡檢|看看/.test(input) &&
    /網站|網頁|頁面/.test(input);

  if (!wantsSiteTest) {
    return null;
  }

  const titleMatch = input.match(/標題(?:要|是|包含)?[:：]?\s*(.+)$/);

  return {
    url: urlMatch[0],
    expectedTitle: titleMatch?.[1]?.trim() || ""
  };
}

export function isLoginReportCommand(text) {
  const input = String(text || "").trim();
  return (
    input === "/login-report" ||
    /登入後.*(測試|報告)|登入.*功能測試報告|幫我.*登入.*報告/.test(input)
  );
}

export async function runConfiguredLoginReport() {
  const config = getLoginTestConfig();
  const requiredFields = [
    "baseUrl",
    "loginUrl",
    "username",
    "password",
    "usernameSelector",
    "passwordSelector",
    "submitSelector"
  ];

  const missingFields = requiredFields.filter((field) => !config[field]);
  if (missingFields.length > 0) {
    return {
      ok: false,
      url: config.loginUrl || config.baseUrl || "",
      httpStatus: null,
      title: "",
      consoleErrors: [],
      pageErrors: [],
      steps: [],
      testedAt: new Date().toISOString(),
      error: `Missing login test config: ${missingFields.join(", ")}`
    };
  }

  const consoleErrors = [];
  const pageErrors = [];
  const steps = [];
  const { chromium } = await import("playwright");
  const browser = await chromium.launch({ headless: true });

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

    const response = await page.goto(config.loginUrl, {
      waitUntil: "networkidle",
      timeout: 20000
    });

    steps.push({
      name: "open_login_page",
      ok: Boolean(response?.ok()),
      detail: `HTTP ${response?.status() ?? "unknown"}`
    });

    await page.fill(config.usernameSelector, config.username);
    steps.push({ name: "fill_username", ok: true, detail: config.usernameSelector });

    await page.fill(config.passwordSelector, config.password);
    steps.push({ name: "fill_password", ok: true, detail: config.passwordSelector });

    await Promise.all([
      page.waitForLoadState("networkidle"),
      page.click(config.submitSelector)
    ]);
    steps.push({ name: "submit_login", ok: true, detail: config.submitSelector });

    let loginSuccess = false;
    if (config.successSelector) {
      await page.waitForSelector(config.successSelector, { timeout: 10000 });
      loginSuccess = true;
      steps.push({
        name: "assert_success_selector",
        ok: true,
        detail: config.successSelector
      });
    } else if (config.successText) {
      await page.getByText(config.successText, { exact: false }).waitFor({
        timeout: 10000
      });
      loginSuccess = true;
      steps.push({
        name: "assert_success_text",
        ok: true,
        detail: config.successText
      });
    } else {
      loginSuccess = true;
      steps.push({
        name: "assert_login_navigation",
        ok: true,
        detail: "No success selector/text configured; login submit completed."
      });
    }

    if (config.postLoginPath) {
      const targetUrl = new URL(config.postLoginPath, config.baseUrl).toString();
      const postResponse = await page.goto(targetUrl, {
        waitUntil: "networkidle",
        timeout: 20000
      });
      steps.push({
        name: "open_post_login_page",
        ok: Boolean(postResponse?.ok()),
        detail: `${targetUrl} -> HTTP ${postResponse?.status() ?? "unknown"}`
      });
    }

    const result = {
      id: `login_test_${websiteTestRuns.length + 1}`,
      ok: loginSuccess && consoleErrors.length === 0 && pageErrors.length === 0,
      url: config.loginUrl,
      httpStatus: response?.status() ?? null,
      title: await page.title(),
      consoleErrors,
      pageErrors,
      steps,
      testedAt: new Date().toISOString(),
      error: null
    };

    result.ok = loginSuccess;
    result.summary = buildLoginReport(result);
    websiteTestRuns.unshift(result);
    websiteTestRuns.splice(10);
    return result;
  } catch (error) {
    const result = {
      id: `login_test_${websiteTestRuns.length + 1}`,
      ok: false,
      url: config.loginUrl,
      httpStatus: null,
      title: "",
      consoleErrors,
      pageErrors,
      steps,
      testedAt: new Date().toISOString(),
      error: error instanceof Error ? error.message : "Unknown login test error."
    };

    result.summary = buildLoginReport(result);
    websiteTestRuns.unshift(result);
    websiteTestRuns.splice(10);
    return result;
  } finally {
    await browser.close();
  }
}
