# Restaurant Agent MVP

這個服務已支援你要的流程：
- 輸入餐廳類型（火鍋/燒肉/串燒/生魚片）
- AI 搜尋推薦餐廳
- 批次查詢可能可預約時段（inline / EZTABLE 網頁探測）
- 查不到就自動回退半自動預約連結
- 可直接給 LINE webhook 或 LINE(OpenClaw) 呼叫
- OpenClaw response 會附 `booking_intents[]`，可直接拿來做按鈕、卡片或後續訂位 action

## 1) 安裝

```bash
python -m venv .venv
.venv\\Scripts\\activate
pip install -r requirements.txt
copy .env.example .env
playwright install chromium
```

## 2) 啟動

```bash
uvicorn app.main:app --reload
```

## 2.1) Render 雲端部署

這個專案已包含：
- `Dockerfile`
- `render.yaml`
- `/health` 健康檢查

建議直接用 Render 建立 Web Service，讓它讀取 repo 根目錄的 `Dockerfile`。

部署步驟：
1. 把這個專案推到 GitHub
2. 到 Render 建立 `Web Service`
3. 連接你的 GitHub repo
4. Render 會自動偵測 `Dockerfile`
5. 在 Environment Variables 填入：
   - `LINE_CHANNEL_SECRET`
   - `LINE_CHANNEL_ACCESS_TOKEN`
   - `GOOGLE_MAPS_API_KEY`
6. 部署完成後，將 LINE webhook URL 設為：
   - `https://<你的-render-網域>/line/webhook`

如果你想用 Blueprint，也可以直接讓 Render 讀根目錄的 `render.yaml`

## 2.2) Railway 雲端部署

這個專案已包含：
- `Dockerfile`
- `railway.json`
- `/health` 健康檢查

部署時至少要設定這些環境變數：
- `LINE_CHANNEL_SECRET`
- `LINE_CHANNEL_ACCESS_TOKEN`
- `GOOGLE_MAPS_API_KEY`

部署完成後，將 LINE webhook URL 設為：
- `https://<你的-railway-網域>/line/webhook`

## 3) 核心 API

- `POST /agent/search-and-probe`
  - 一次完成：搜尋 + 批次探測 + 排序
- `POST /line/webhook`
  - 給 LINE Messaging API 直接打 webhook，會驗證 `x-line-signature` 並自動回覆使用者
- `POST /line/openclaw-query`
  - 給 OpenClaw 呼叫，回傳可直接發給 LINE 使用者的文字與連結 actions
- `POST /availability/probe-batch`
  - 只做批次探測
- `POST /booking/assist`
  - 只做半自動訂位連結整理

## 4) /agent/search-and-probe 範例

```bash
curl -X POST http://127.0.0.1:8000/agent/search-and-probe \\
  -H "Content-Type: application/json" \\
  -d '{
    "message": "想吃燒肉",
    "location": "台北市信義區",
    "party_size": 4,
    "reservation_date": "2026-03-21",
    "preferred_time": "19:00",
    "limit": 8,
    "max_parallel": 3,
    "probe_timeout_sec": 10
  }'
```

## 5) LINE 官方 webhook 串接方式

在 LINE Developers Console 設定：
- Webhook URL: `https://<你的網域>/line/webhook`
- 啟用 `Use webhook`
- 可以先用 Console 的 `Verify` 測試

你的 `.env` 需要有：
- `LINE_CHANNEL_SECRET`
- `LINE_CHANNEL_ACCESS_TOKEN`

目前 webhook 行為：
- 收到使用者文字訊息
- 自動跑搜尋 + 批次查時段
- 用 LINE reply API 回覆推薦結果

## 6) LINE(OpenClaw) 串接方式

在 OpenClaw 建一個 action（或 webhook 節點）呼叫：
- URL: `POST https://<你的網域>/line/openclaw-query`
- Request body：

```json
{
  "user_id": "{{line.userId}}",
  "message": "{{line.text}}",
  "location": "台北市",
  "party_size": 2,
  "reservation_date": "2026-03-21",
  "preferred_time": "19:00",
  "limit": 6
}
```

把 response 的這兩個欄位映射回 LINE：
- `reply_text` -> 文字訊息
- `actions[]` -> 按鈕/快速選單 URL

另外建議在 OpenClaw 讀取這些欄位：
- `booking_intents[]`
  - `restaurant_name`
  - `provider`
  - `url`
  - `party_size`
  - `reservation_date`
  - `preferred_time`
  - `availability_status`
  - `available_times[]`
  - `booking_summary_text`

這樣 OpenClaw 不需要再從 `reply_text` 反解析訂位資訊。

## 6.1) inline / EZTABLE live booking

`POST /booking/create` 與 `POST /booking/cancel` 現在都支援：
- `provider=inline`
- `provider=eztable`

但這兩條 live integration 都是「可配置 provider adapter」：
- 你需要有對應平台提供的 API endpoint / partner endpoint
- 把 base URL、auth header、path 寫進 `.env`
- 如果沒有官方/合作 API，請維持 `dry_run=true`，並使用 `/line/openclaw-query` 回傳的訂位連結做半自動流程

## 7) 測試

```bash
pytest -q
```
