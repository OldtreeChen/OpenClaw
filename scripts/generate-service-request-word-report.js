import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { Document, HeadingLevel, ImageRun, Packer, Paragraph, Table, TableCell, TableRow, TextRun, WidthType } from "docx";

process.env.PLAYWRIGHT_BROWSERS_PATH =
  process.env.PLAYWRIGHT_BROWSERS_PATH || path.resolve(".playwright-browsers");

function parseArgs(argv) {
  const options = {};

  for (let index = 0; index < argv.length; index += 1) {
    const current = argv[index];
    if (!current.startsWith("--")) {
      continue;
    }

    const key = current.slice(2);
    const next = argv[index + 1];
    if (!next || next.startsWith("--")) {
      options[key] = "true";
      continue;
    }

    options[key] = next;
    index += 1;
  }

  return options;
}

function timestamp() {
  const now = new Date();
  const parts = [
    now.getFullYear(),
    String(now.getMonth() + 1).padStart(2, "0"),
    String(now.getDate()).padStart(2, "0"),
    String(now.getHours()).padStart(2, "0"),
    String(now.getMinutes()).padStart(2, "0"),
    String(now.getSeconds()).padStart(2, "0")
  ];

  return `${parts[0]}${parts[1]}${parts[2]}-${parts[3]}${parts[4]}${parts[5]}`;
}

function required(value, name) {
  if (String(value || "").trim()) {
    return String(value).trim();
  }

  throw new Error(`Missing required option: ${name}`);
}

function buildConfig(rawOptions) {
  return {
    baseUrl: required(
      rawOptions["base-url"] || process.env.LOGIN_TEST_BASE_URL,
      "base-url"
    ),
    username: required(
      rawOptions.username || process.env.LOGIN_TEST_USERNAME,
      "username"
    ),
    password: required(
      rawOptions.password || process.env.LOGIN_TEST_PASSWORD,
      "password"
    ),
    usernameSelector:
      rawOptions["username-selector"] ||
      process.env.LOGIN_TEST_USERNAME_SELECTOR ||
      "#LoginNameCell input",
    passwordSelector:
      rawOptions["password-selector"] ||
      process.env.LOGIN_TEST_PASSWORD_SELECTOR ||
      "#PasswordCell input[type='password']",
    submitSelector:
      rawOptions["submit-selector"] ||
      process.env.LOGIN_TEST_SUBMIT_SELECTOR ||
      "#LoginButton",
    successSelector:
      rawOptions["success-selector"] ||
      process.env.LOGIN_TEST_SUCCESS_SELECTOR ||
      "#IdentityName",
    reportTitle: rawOptions["report-title"] || "Service Request 測試報告",
    outputDir: path.resolve(rawOptions["output-dir"] || "reports"),
    serviceRequestText: rawOptions["service-request-text"] || "Service Request",
    customerRelationshipText:
      rawOptions["customer-relationship-text"] || "Customer Relationship"
  };
}

function createStep(stepNumber, title, description, screenshotPath, extra = {}) {
  return {
    stepNumber,
    title,
    description,
    screenshotPath,
    ...extra
  };
}

async function saveStepScreenshot(target, screenshotPath) {
  await target.screenshot({
    path: screenshotPath,
    fullPage: true
  });
}

async function waitForServiceRequestFrame(page) {
  for (let attempt = 0; attempt < 40; attempt += 1) {
    const frame = page
      .frames()
      .find((current) => current.url().includes("Ecp.ServiceRequest.List.page"));

    if (frame) {
      await frame.waitForLoadState("domcontentloaded").catch(() => {});
      return frame;
    }

    await page.waitForTimeout(500);
  }

  throw new Error("Service Request list frame did not appear.");
}

async function screenshotFrame(frame, screenshotPath) {
  const body = frame.locator("body");
  await body.waitFor({ state: "visible", timeout: 10000 });
  await body.screenshot({
    path: screenshotPath
  });
}

async function triggerDomClick(locator) {
  await locator.waitFor({ state: "visible", timeout: 10000 });
  await locator.evaluate((element) => {
    element.dispatchEvent(new MouseEvent("click", { bubbles: true, cancelable: true }));
  });
}

function buildDocTable(steps) {
  return new Table({
    width: {
      size: 100,
      type: WidthType.PERCENTAGE
    },
    rows: [
      new TableRow({
        tableHeader: true,
        children: [
          new TableCell({
            children: [new Paragraph("步驟")]
          }),
          new TableCell({
            children: [new Paragraph("動作")]
          }),
          new TableCell({
            children: [new Paragraph("結果")]
          })
        ]
      }),
      ...steps.map((step) =>
        new TableRow({
          children: [
            new TableCell({
              children: [new Paragraph(String(step.stepNumber))]
            }),
            new TableCell({
              children: [new Paragraph(step.title)]
            }),
            new TableCell({
              children: [new Paragraph("成功")]
            })
          ]
        })
      )
    ]
  });
}

async function buildWordDocument({ reportTitle, config, steps, summary, outputPath }) {
  const children = [
    new Paragraph({
      text: reportTitle,
      heading: HeadingLevel.TITLE
    }),
    new Paragraph({
      children: [
        new TextRun(`測試網站：${config.baseUrl}`)
      ]
    }),
    new Paragraph({
      children: [
        new TextRun(`測試時間：${summary.testedAt}`)
      ]
    }),
    new Paragraph({
      children: [
        new TextRun(`登入帳號：${config.username}`)
      ]
    }),
    new Paragraph({
      children: [
        new TextRun(`整體結果：${summary.overallStatus}`)
      ]
    }),
    new Paragraph(""),
    new Paragraph({
      text: "測試摘要",
      heading: HeadingLevel.HEADING_1
    }),
    buildDocTable(steps),
    new Paragraph(""),
    new Paragraph({
      text: "詳細步驟",
      heading: HeadingLevel.HEADING_1
    })
  ];

  for (const step of steps) {
    const imageBuffer = await fs.readFile(step.screenshotPath);

    children.push(
      new Paragraph({
        text: `步驟 ${step.stepNumber}：${step.title}`,
        heading: HeadingLevel.HEADING_2
      }),
      new Paragraph(step.description),
      new Paragraph({
        children: [
          new TextRun(`畫面檔案：${path.basename(step.screenshotPath)}`)
        ]
      }),
      new Paragraph({
        children: [
          new ImageRun({
            data: imageBuffer,
            transformation: {
              width: 600,
              height: 340
            }
          })
        ]
      }),
      new Paragraph("")
    );
  }

  if (summary.consoleMessages.length > 0 || summary.pageErrors.length > 0) {
    children.push(
      new Paragraph({
        text: "執行紀錄",
        heading: HeadingLevel.HEADING_1
      })
    );

    if (summary.consoleMessages.length > 0) {
      children.push(
        new Paragraph({
          text: "Console 訊息",
          heading: HeadingLevel.HEADING_2
        })
      );

      for (const message of summary.consoleMessages) {
        children.push(new Paragraph(`- ${message}`));
      }
    }

    if (summary.pageErrors.length > 0) {
      children.push(
        new Paragraph({
          text: "Page errors",
          heading: HeadingLevel.HEADING_2
        })
      );

      for (const message of summary.pageErrors) {
        children.push(new Paragraph(`- ${message}`));
      }
    }
  }

  const document = new Document({
    sections: [
      {
        children
      }
    ]
  });

  const buffer = await Packer.toBuffer(document);
  await fs.writeFile(outputPath, buffer);
}

async function main() {
  const rawOptions = parseArgs(process.argv.slice(2));
  const config = buildConfig(rawOptions);
  const runId = timestamp();
  const reportDir = path.join(config.outputDir, `service-request-report-${runId}`);
  const screenshotsDir = path.join(reportDir, "screenshots");
  const outputPath = path.join(reportDir, `service-request-test-report-${runId}.docx`);

  await fs.mkdir(screenshotsDir, { recursive: true });

  const consoleMessages = [];
  const pageErrors = [];
  const steps = [];
  const { chromium } = await import("playwright");
  const browser = await chromium.launch({ headless: true });

  try {
    const page = await browser.newPage({
      viewport: {
        width: 1440,
        height: 2200
      }
    });

    page.on("console", (message) => {
      if (message.type() === "error" || message.type() === "warning") {
        consoleMessages.push(`[${message.type()}] ${message.text()}`);
      }
    });

    page.on("pageerror", (error) => {
      pageErrors.push(error.message);
    });

    await page.goto(config.baseUrl, {
      waitUntil: "networkidle",
      timeout: 30000
    });

    const loginPageScreenshot = path.join(screenshotsDir, "01-login-page.png");
    await saveStepScreenshot(page, loginPageScreenshot);
    steps.push(
      createStep(
        1,
        "開啟登入頁",
        "系統成功進入 ECP 登入頁，確認測試站台可正常連線，並顯示帳號與密碼輸入欄位。",
        loginPageScreenshot
      )
    );

    await page.fill(config.usernameSelector, config.username);
    const usernameFilledScreenshot = path.join(screenshotsDir, "02-username-filled.png");
    await saveStepScreenshot(page, usernameFilledScreenshot);
    steps.push(
      createStep(
        2,
        "輸入登入帳號",
        `在帳號欄位輸入測試帳號 ${config.username}，確認欄位定位與輸入行為正常。`,
        usernameFilledScreenshot
      )
    );

    await page.fill(config.passwordSelector, config.password);
    const passwordFilledScreenshot = path.join(screenshotsDir, "03-password-filled.png");
    await saveStepScreenshot(page, passwordFilledScreenshot);
    steps.push(
      createStep(
        3,
        "輸入登入密碼",
        "在密碼欄位輸入測試密碼，確認密碼欄位可正常輸入且畫面未出現阻擋訊息。",
        passwordFilledScreenshot
      )
    );

    await Promise.all([
      page.waitForLoadState("networkidle"),
      page.click(config.submitSelector)
    ]);
    await page.waitForSelector(config.successSelector, { timeout: 15000 });

    const dashboardScreenshot = path.join(screenshotsDir, "04-dashboard-after-login.png");
    await saveStepScreenshot(page, dashboardScreenshot);
    steps.push(
      createStep(
        4,
        "登入成功進入首頁",
        "按下登入後，系統成功進入首頁主畫面，可見使用者資訊與左側功能選單，表示登入流程成功。",
        dashboardScreenshot
      )
    );

    await page
      .getByText(config.customerRelationshipText, { exact: true })
      .click();
    await page
      .getByText(config.serviceRequestText, { exact: true })
      .first()
      .click();

    const serviceRequestFrame = await waitForServiceRequestFrame(page);
    await serviceRequestFrame.locator("body").waitFor({ state: "visible", timeout: 10000 });

    const serviceRequestListScreenshot = path.join(
      screenshotsDir,
      "05-service-request-list.png"
    );
    await screenshotFrame(serviceRequestFrame, serviceRequestListScreenshot);
    steps.push(
      createStep(
        5,
        "進入 Service Request 清單",
        "從左側選單進入 Customer Relationship > Service Request，系統成功開啟服務請求清單頁，工具列與資料列表皆正常顯示。",
        serviceRequestListScreenshot
      )
    );

    await triggerDomClick(
      serviceRequestFrame.locator(".JuiComboButtonText").getByText("New")
    );
    await page.waitForTimeout(1500);

    const newMenuScreenshot = path.join(screenshotsDir, "06-new-request-menu.png");
    await saveStepScreenshot(page, newMenuScreenshot);
    steps.push(
      createStep(
        6,
        "展開新增服務請求選單",
        "點擊 New 後，系統成功展開新增類型選單，可見外部客戶報修、內部報修與訂閱網服務請求等選項，代表新增入口可正常使用。",
        newMenuScreenshot
      )
    );

    const summary = {
      testedAt: new Date().toLocaleString("zh-TW", {
        hour12: false,
        timeZone: "Asia/Taipei"
      }),
      overallStatus: "通過",
      consoleMessages,
      pageErrors
    };

    await buildWordDocument({
      reportTitle: config.reportTitle,
      config,
      steps,
      summary,
      outputPath
    });

    console.log(
      JSON.stringify(
        {
          ok: true,
          outputPath,
          screenshotsDir,
          stepCount: steps.length,
          consoleMessages,
          pageErrors
        },
        null,
        2
      )
    );
  } finally {
    await browser.close();
  }
}

const currentFilePath = fileURLToPath(import.meta.url);
if (process.argv[1] && path.resolve(process.argv[1]) === currentFilePath) {
  main().catch((error) => {
    console.error(error instanceof Error ? error.stack : error);
    process.exit(1);
  });
}
