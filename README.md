# app-growth-teardown

一個 [Claude Code](https://claude.com/claude-code) skill：只用公開資料，拆解一個 App 是怎麼增長起來的——什麼時候開始爆、下載從哪來、自然流量和付費買量各佔多少、用戶在哪些國家、用了哪些傳播手段，最後產出一份有證據、有圖表的網頁報告。

核心原則：**每個結論至少要有兩種獨立證據，並主動找能推翻自己的證據。** 看到 TikTok 千萬播放就以為是自然爆紅，常常是錯的。

## 它會做什麼

1. 基本事實與時間線：新聞、融資、商店頁、改名／轉型歷史
2. 下載量曲線：用 Wayback 快照的 Google Play 評論數推估每月下載，iOS 看美區評分趨勢
3. 內容渠道：TikTok 官方帳號的發片、播放、爆款集中度、按讚率
4. 付費渠道：Google 廣告透明度中心、Meta 廣告資料庫、TikTok 影片頁的 `isAd` 標記
5. 用戶地區：Google Play 評論語言，以及英文評論的發文時區拆分
6. 網站與搜尋：Similarweb、Google Trends、承接搜尋流量的手法
7. 綜合判斷：自然 vs 付費的量級範圍、成本驗算
8. 產出 HTML 報告

範例成品：[`assets/example-report-sekai.html`](assets/example-report-sekai.html)（Sekai 的增長拆解，資料截至 2026-09-28）。

## 安裝

```bash
git clone https://github.com/WellyXY/app-growth-teardown.git ~/.claude/skills/app-growth-teardown
```

之後在 Claude Code 裡說「幫我拆解 XXX 這個 App 是怎麼紅的」或輸入 `/app-growth-teardown`。

Python 腳本需要的套件建議裝在獨立的虛擬環境：

```bash
python3 -m venv ~/.cache/app-growth-teardown/venv
~/.cache/app-growth-teardown/venv/bin/pip install google-play-scraper numpy scipy
```

`scripts/*.js` 要在瀏覽器裡執行（Claude Code 的內建瀏覽器或 Claude in Chrome），用法寫在每個檔案開頭。

## 檔案

| 路徑 | 內容 |
|---|---|
| `SKILL.md` | 分析流程與寫作原則 |
| `references/methods.md` | 每一步的做法、判斷門檻、限制 |
| `references/pitfalls.md` | 工具與資料來源踩過的坑 |
| `references/report-outline.md` | 報告結構 |
| `scripts/play_wayback_history.py` | Google Play 評論數歷史 → 每月下載推估 |
| `scripts/appstore_wayback_history.py` | App Store 評分數歷史 |
| `scripts/play_reviews_by_language.py` | Google Play 各語言每月評論數 |
| `scripts/play_reviews_timezone.py` | 依發文時區拆分評論者地區 |
| `scripts/tiktok_profile_collect.js` | 收集 TikTok 帳號／標籤頁影片 |
| `scripts/tiktok_ad_flags.py` | 讀 TikTok 影片頁的 `isAd` 等標記 |
| `scripts/tiktok_id_to_date.py` | TikTok 影片 ID 換算發文時間 |
| `scripts/google_ads_transparency.js` | 拉 Google 廣告主的所有素材與投放日期 |

## 注意

- 所有數字都是用公開資料推估的量級，不是官方數據；報告裡要寫清楚範圍和資料限制。
- 腳本會連到 Wayback Machine、Google Play、TikTok 等網站，請遵守各網站的使用條款，並保留腳本內建的請求間隔。
- 報告會點名公司並寫出推論（例如「很可能是付費推廣」），對外分享前請自行斟酌。
