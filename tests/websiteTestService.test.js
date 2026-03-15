import test from "node:test";
import assert from "node:assert/strict";
import http from "node:http";
import {
  isLoginReportCommand,
  parseNaturalWebsiteTestCommand,
  parseWebsiteTestCommand,
  runWebsiteTest
} from "../src/tools/websiteTestService.js";

function createTestServer(handler) {
  return new Promise((resolve) => {
    const server = http.createServer(handler);
    server.listen(0, "127.0.0.1", () => {
      const address = server.address();
      resolve({
        server,
        url: `http://127.0.0.1:${address.port}`
      });
    });
  });
}

test("parseWebsiteTestCommand parses url and expected title", () => {
  const command = parseWebsiteTestCommand(
    "/test-site https://example.com title=Example Domain"
  );

  assert.deepEqual(command, {
    url: "https://example.com",
    expectedTitle: "Example Domain"
  });
});

test("parseNaturalWebsiteTestCommand parses Chinese request", () => {
  const command = parseNaturalWebsiteTestCommand(
    "幫我測試網站 https://example.com 標題 Example Domain"
  );

  assert.deepEqual(command, {
    url: "https://example.com",
    expectedTitle: "Example Domain"
  });
});

test("isLoginReportCommand matches natural language login report request", () => {
  assert.equal(isLoginReportCommand("幫我做登入後功能測試報告"), true);
  assert.equal(isLoginReportCommand("/login-report"), true);
  assert.equal(isLoginReportCommand("幫我測試網站 https://example.com"), false);
});

test("runWebsiteTest passes for a clean page", async () => {
  const fixture = await createTestServer((_req, res) => {
    res.writeHead(200, { "Content-Type": "text/html; charset=utf-8" });
    res.end(`
      <!doctype html>
      <html>
        <head><title>Smoke Test Page</title></head>
        <body><h1>ok</h1></body>
      </html>
    `);
  });

  try {
    const result = await runWebsiteTest({
      url: fixture.url,
      expectedTitle: "Smoke Test Page"
    });

    assert.equal(result.ok, true);
    assert.equal(result.httpStatus, 200);
    assert.equal(result.consoleErrors.length, 0);
    assert.equal(result.pageErrors.length, 0);
  } finally {
    await new Promise((resolve, reject) => {
      fixture.server.close((error) => {
        if (error) {
          reject(error);
          return;
        }
        resolve();
      });
    });
  }
});

test("runWebsiteTest fails when the page throws console and page errors", async () => {
  const fixture = await createTestServer((_req, res) => {
    res.writeHead(200, { "Content-Type": "text/html; charset=utf-8" });
    res.end(`
      <!doctype html>
      <html>
        <head><title>Broken Page</title></head>
        <body>
          <script>
            console.error("boom");
            throw new Error("page exploded");
          </script>
        </body>
      </html>
    `);
  });

  try {
    const result = await runWebsiteTest({
      url: fixture.url,
      expectedTitle: "Broken Page"
    });

    assert.equal(result.ok, false);
    assert.equal(result.httpStatus, 200);
    assert.ok(result.consoleErrors.length > 0);
    assert.ok(result.pageErrors.length > 0);
  } finally {
    await new Promise((resolve, reject) => {
      fixture.server.close((error) => {
        if (error) {
          reject(error);
          return;
        }
        resolve();
      });
    });
  }
});
