import "dotenv/config";
import express from "express";
import { randomUUID } from "node:crypto";
import { chatWithAssistant } from "./assistant.js";
import { runDiagnostics } from "./diagnostics.js";
import { handleLineWebhook } from "./line.js";
import { listReservations } from "./tools/restaurantService.js";

const app = express();

app.post(
  "/line/webhook",
  express.json({
    verify: (req, _res, buffer) => {
      req.rawBody = buffer;
    }
  }),
  handleLineWebhook
);

app.use(express.json());

app.get("/health", (_req, res) => {
  res.json({ ok: true });
});

app.get("/diagnostics", (_req, res) => {
  res.json(runDiagnostics());
});

app.post("/chat", async (req, res) => {
  const { message, sessionId } = req.body || {};

  if (!message || typeof message !== "string") {
    res.status(400).json({ error: "message is required." });
    return;
  }

  try {
    const result = await chatWithAssistant({
      sessionId: sessionId || randomUUID(),
      message
    });

    res.json(result);
  } catch (error) {
    res.status(500).json({
      error: error instanceof Error ? error.message : "Unknown server error."
    });
  }
});

app.get("/reservations", (_req, res) => {
  res.json({
    count: listReservations().length,
    results: listReservations()
  });
});

const port = Number(process.env.PORT || 3000);
const host = process.env.HOST || "0.0.0.0";

app.listen(port, host, () => {
  console.log(`OpenClaw server listening on http://${host}:${port}`);
});
