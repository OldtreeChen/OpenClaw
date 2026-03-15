import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";

const outputDir = path.resolve("docs");
const outputFile = path.join(outputDir, "system-overview.md");

const content = `# OpenClaw System Overview

## Purpose

OpenClaw is a restaurant concierge service that:

- receives user messages from LINE
- uses the OpenAI Responses API to plan replies
- searches local restaurant data
- checks reservation availability
- creates reservation requests
- exposes diagnostics for operator checks

## Runtime Endpoints

### \`GET /health\`

Simple service health endpoint.

### \`GET /diagnostics\`

Returns runtime diagnostics, including required environment variable presence and whether self-healing prerequisites are configured.

### \`POST /chat\`

Direct chat endpoint for web or API integrations.

### \`GET /reservations\`

Lists reservation requests stored in the running process.

### \`POST /line/webhook\`

Verifies LINE signatures, accepts LINE text messages, forwards them to the assistant, and replies through the LINE Messaging API.

## Assistant Tools

The assistant can call these internal tools:

- \`search_restaurants\`
- \`check_availability\`
- \`create_reservation_request\`
- \`list_reservations\`

## Operator Commands

If \`ADMIN_LINE_USER_ID\` is configured, the matching LINE account can send:

- \`/self-check\` or \`自我檢查\`
- \`/self-repair\` or \`自我修正\`

## CI Expectations

The repository should run these checks in CI:

1. Install dependencies with \`npm ci\`
2. Run tests with \`npm test\`
3. Generate docs with \`npm run docs:generate\`

## Deployment Notes

Railway deploys this service as a long-running Node.js process. Production secrets should be stored in Railway variables, not committed to the repository.
`;

await mkdir(outputDir, { recursive: true });
await writeFile(outputFile, content, "utf8");

console.log(`Generated ${outputFile}`);
