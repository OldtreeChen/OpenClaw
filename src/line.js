import crypto from "node:crypto";
import { chatWithAssistant } from "./assistant.js";
import {
  formatDiagnosticsReport,
  runDiagnostics
} from "./diagnostics.js";
import {
  parseWebsiteTestCommand,
  runWebsiteTest
} from "./tools/websiteTestService.js";

function getLineConfig() {
  return {
    channelSecret: process.env.LINE_CHANNEL_SECRET,
    channelAccessToken: process.env.LINE_CHANNEL_ACCESS_TOKEN,
    adminLineUserId: process.env.ADMIN_LINE_USER_ID
  };
}

function verifyLineSignature(rawBody, signature, channelSecret) {
  if (!rawBody || !signature || !channelSecret) {
    return false;
  }

  const expected = crypto
    .createHmac("sha256", channelSecret)
    .update(rawBody)
    .digest("base64");

  const actualBuffer = Buffer.from(signature);
  const expectedBuffer = Buffer.from(expected);

  if (actualBuffer.length !== expectedBuffer.length) {
    return false;
  }

  return crypto.timingSafeEqual(actualBuffer, expectedBuffer);
}

async function replyLineMessage(replyToken, messages, channelAccessToken) {
  const response = await fetch("https://api.line.me/v2/bot/message/reply", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${channelAccessToken}`
    },
    body: JSON.stringify({
      replyToken,
      messages
    })
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(`LINE reply failed: ${response.status} ${text}`);
  }
}

function chunkText(text, size = 1800) {
  const result = [];
  for (let start = 0; start < text.length; start += size) {
    result.push(text.slice(start, start + size));
  }
  return result;
}

function buildReplyMessages(text) {
  const normalized =
    String(text || "").trim() ||
    "\u76ee\u524d\u6c92\u6709\u53ef\u56de\u8986\u7684\u5167\u5bb9\u3002";

  return chunkText(normalized).map((part) => ({
    type: "text",
    text: part
  }));
}

function getSessionIdFromEvent(event) {
  const userId = event.source?.userId;
  const groupId = event.source?.groupId;
  const roomId = event.source?.roomId;

  return userId || groupId || roomId || event.replyToken;
}

function isAdminEvent(event, adminLineUserId) {
  return Boolean(adminLineUserId) && event.source?.userId === adminLineUserId;
}

function isSelfCheckCommand(text) {
  const normalized = String(text || "").trim().toLowerCase();
  return normalized === "/self-check" || normalized === "自我檢查";
}

function isSelfRepairCommand(text) {
  const normalized = String(text || "").trim().toLowerCase();
  return normalized === "/self-repair" || normalized === "自我修正";
}

function isWebsiteTestCommand(text) {
  return parseWebsiteTestCommand(text) !== null;
}

async function replyDiagnostics(event, channelAccessToken) {
  const diagnostics = runDiagnostics();
  await replyLineMessage(
    event.replyToken,
    buildReplyMessages(formatDiagnosticsReport(diagnostics)),
    channelAccessToken
  );
}

async function replySelfRepairStatus(event, channelAccessToken) {
  const diagnostics = runDiagnostics();
  const text = diagnostics.selfHealing.enabled
    ? "自修正模式已啟用，但目前這版服務還沒有接上實際的 GitHub 修補流程。我可以先做自我檢查與回報狀態。"
    : "目前只能自我檢查，還不能永久自修正。原因是 Railway 線上容器的修改不會成為正式版本；要做到自修正，還需要 GitHub repo、寫入權限與自動重新部署流程。";

  await replyLineMessage(
    event.replyToken,
    buildReplyMessages(text),
    channelAccessToken
  );
}

async function replyWebsiteTestResult(event, channelAccessToken, command) {
  const result = await runWebsiteTest({
    url: command.url,
    expectedTitle: command.expectedTitle
  });

  await replyLineMessage(
    event.replyToken,
    buildReplyMessages(result.summary),
    channelAccessToken
  );
}

async function handleTextMessageEvent(event, channelAccessToken) {
  const userMessage = event.message?.text;
  const sessionId = getSessionIdFromEvent(event);
  const { adminLineUserId } = getLineConfig();
  const websiteTestCommand = parseWebsiteTestCommand(userMessage);

  if (isAdminEvent(event, adminLineUserId) && isSelfCheckCommand(userMessage)) {
    await replyDiagnostics(event, channelAccessToken);
    return;
  }

  if (isAdminEvent(event, adminLineUserId) && isSelfRepairCommand(userMessage)) {
    await replySelfRepairStatus(event, channelAccessToken);
    return;
  }

  if (
    websiteTestCommand &&
    (!adminLineUserId || isAdminEvent(event, adminLineUserId))
  ) {
    await replyWebsiteTestResult(
      event,
      channelAccessToken,
      websiteTestCommand
    );
    return;
  }

  const result = await chatWithAssistant({
    sessionId,
    message: userMessage
  });

  await replyLineMessage(
    event.replyToken,
    buildReplyMessages(result.text),
    channelAccessToken
  );
}

export async function handleLineWebhook(req, res) {
  const { channelSecret, channelAccessToken } = getLineConfig();

  if (!channelSecret || !channelAccessToken) {
    res.status(500).json({
      error: "LINE_CHANNEL_SECRET and LINE_CHANNEL_ACCESS_TOKEN are required."
    });
    return;
  }

  const signature = req.get("x-line-signature");
  const isValid = verifyLineSignature(req.rawBody, signature, channelSecret);

  if (!isValid) {
    res.status(401).json({ error: "Invalid LINE signature." });
    return;
  }

  const events = Array.isArray(req.body?.events) ? req.body.events : [];
  res.json({ ok: true });

  for (const event of events) {
    try {
      if (event.type === "message" && event.message?.type === "text") {
        await handleTextMessageEvent(event, channelAccessToken);
        continue;
      }

      if (event.type === "follow") {
        await replyLineMessage(
          event.replyToken,
          buildReplyMessages(
            "\u4f60\u597d\uff0c\u6211\u662f OpenClaw\u3002\u4f60\u53ef\u4ee5\u76f4\u63a5\u544a\u8a34\u6211\u60f3\u627e\u54ea\u4e00\u5340\u3001\u54ea\u7a2e\u6599\u7406\u3001\u5e7e\u4f4d\u3001\u54ea\u4e00\u5929\uff0c\u6211\u6703\u5e6b\u4f60\u67e5\u9910\u5ef3\u548c\u6574\u7406\u8a02\u4f4d\u9700\u6c42\u3002\u7ba1\u7406\u8005\u4e5f\u53ef\u4ee5\u50b3 /self-check \u6216 /test-site https://example.com"
          ),
          channelAccessToken
        );
      }
    } catch (error) {
      console.error("LINE webhook event failed:", error);
    }
  }
}
