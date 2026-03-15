# OpenClaw 餐廳助理

這是一個最小可運作的餐廳查詢／訂位機器人範例。它使用 OpenAI Responses API 進行對話與工具呼叫，並透過本地工具層完成：

- 查詢餐廳
- 檢查指定日期／時段空位
- 建立訂位請求

目前的訂位能力是「建立請求」，不是直接對外部平台完成最終確認。你可以把工具層換成實際來源，例如：

- Google Places 或地圖資料
- inline / EZTABLE / OpenTable
- 你自己的後台訂位 API

## 快速開始

1. 安裝依賴

```bash
npm install
```

2. 建立環境變數

```bash
copy .env.example .env
```

3. 在 `.env` 放入 API key

```env
OPENAI_API_KEY=your_openai_api_key
MODEL=gpt-5
PORT=3000
LINE_CHANNEL_SECRET=your_line_channel_secret
LINE_CHANNEL_ACCESS_TOKEN=your_line_channel_access_token
```

4. 啟動服務

```bash
npm start
```

## API

### `POST /chat`

Request:

```json
{
  "sessionId": "demo-user-1",
  "message": "幫我找台北信義區適合約會的燒肉餐廳，明天晚上兩位"
}
```

Response:

```json
{
  "sessionId": "demo-user-1",
  "responseId": "resp_xxx",
  "text": "..."
}
```

### `GET /reservations`

列出目前 demo server 已建立的訂位請求。

### `POST /line/webhook`

LINE Messaging API webhook 入口。收到使用者文字訊息後，會：

1. 驗證 `x-line-signature`
2. 把文字送進 OpenClaw 助理
3. 用 LINE reply API 回覆結果

在 LINE Developers 後台把 webhook URL 設成：

```text
https://your-domain.example.com/line/webhook
```

如果你本機測試，可以先用 ngrok / Cloudflare Tunnel 暴露本機網址。

### `GET /diagnostics`

輸出目前服務的自我檢查結果，包含：

- 必要環境變數是否存在
- 服務運行時間
- 目前訂位請求數量
- 自修正模式是否已啟用

### LINE 管理指令

如果你有設定 `ADMIN_LINE_USER_ID`，該 LINE 使用者可以傳：

- `/self-check` 或 `自我檢查`
- `/self-repair` 或 `自我修正`

目前 `/self-check` 會回傳系統診斷結果。`/self-repair` 會回報是否已具備真正自動修補與重新部署的條件。

## 建議下一步

如果你要把它做成真的能用的機器人，下一步通常是：

1. 把 `src/data/restaurants.js` 換成真實餐廳來源。
2. 把 `createReservationRequest` 接到實際訂位平台。
3. 加入使用者驗證、聯絡資訊保護、資料庫儲存。
4. 把 `/chat` 接到 LINE、Telegram、網頁聊天介面。

## Git 同步

目前專案可以用這個指令快速同步到 Git remote：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\git-sync.ps1 -Message "your commit message"
```

這會依序執行：

- `git add .`
- `git commit -m "..."`
- `git push`

前提是你已經設定好 git repository 與 remote。

## AI QA / DevOps

這個 repo 現在包含第一版 AI QA / DevOps 骨架：

- `agents/codex_tasks.md`
- `.github/workflows/ci.yml`
- `.github/workflows/railway-deploy.yml`
- `tests/`
- `docs/system-overview.md`

本地檢查指令：

```bash
npm run ci:check
```

GitHub Actions 需要的 secrets：

- `RAILWAY_TOKEN`
- `RAILWAY_PROJECT_ID`
- `RAILWAY_SERVICE_ID`

目前 Railway deploy workflow 只有在 secrets 存在時才會執行。

## 參考

- OpenAI 官方建議新專案使用 Responses API：[Migrate to the Responses API](https://platform.openai.com/docs/guides/responses-vs-chat-completions)
- OpenAI JavaScript SDK：[Libraries - JavaScript](https://platform.openai.com/docs/libraries/javascript)
- OpenAI 函式工具呼叫：[Function calling](https://platform.openai.com/docs/guides/function-calling)
