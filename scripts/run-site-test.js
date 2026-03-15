import { runWebsiteTest } from "../src/tools/websiteTestService.js";

const url = process.argv[2];

if (!url) {
  console.error("Usage: npm run test:site -- <url>");
  process.exit(1);
}

const result = await runWebsiteTest({ url });
console.log(JSON.stringify(result, null, 2));

if (!result.ok) {
  process.exit(1);
}
