# 工具與資料來源的坑

都是實際踩過的。動手前先掃一遍。

## 瀏覽器

- **Reddit 對瀏覽器自動化是封鎖的**：內建瀏覽器和 Claude in Chrome（從 Claude Code 遠端操作）都會回「not allowed due to safety restrictions」，reddit.com 和 old.reddit.com 都一樣。不要嘗試繞過。改用其他論壇，或給使用者寫好的指令，請他在 Chrome 側邊欄的 Claude 擴充功能自己跑，再把結果貼回來。
- **Cloudflare 驗證**：等 5–10 秒，通常會自己通過（一畝三分地在使用者的 Chrome 會自動過）。跳出「確認你是真人」的勾選框時不要代點，換來源或請使用者自己處理。
- **TikTok**：
  - 視窗太矮（例如 263px）影片格子不會渲染，抓不到任何連結。先把視窗調到 1280×900。
  - 往下捲很多頁後可能跳登入牆，頁面標題變成「Log in」；已載入的資料仍可用。
  - 一次捲太多頁會讓 JS 執行超過 45 秒逾時，拆成每次約 18 次捲動。
  - 影片頁要先關掉「用方向鍵瀏覽」的提示才讀得到數字；讀不到就截圖看。
  - 被限流時個人頁的影片列表會是空的，等一下或換頁面再試。
  - 從瀏覽器頁面內用 fetch 連續抓影片頁（約 40 支、間隔不到 1 秒）會被限流：回應只剩約 400 bytes、沒有 `itemStruct`，持續 10 分鐘以上，之後直接打開影片頁還會出現「Access Denied」。這時從終端機用一般 HTTP 請求（`tiktok_ad_flags.py`）仍然抓得到。大量抓影片頁一律用腳本，每支間隔 2 秒。
  - 標籤頁（`/tag/<x>`）是模糊比對：#wayshot 會混進撞球、籃球「shot」的影片。統計創作者前先用文案過濾出真的提到產品的。
- **TikTok 廣告庫（library.tiktok.com）**：
  - 只收歐盟／英國／瑞士的廣告，美國投放看不到。
  - 網址一定要帶 `query_type=1`（廣告主名稱）或 `query_type=2`（關鍵字）。留空時不會篩選，會回傳全部廣告（約 1 億筆），很容易誤以為搜到了。
  - 打開網址後頁面不會自動搜尋，畫面上的「Total ads: 0」只是預設值。要點搜尋按鈕；瀏覽器面板隱藏時，用 JS 對文字是「Search」的元素 `.click()` 也有效。
  - 不要自己用腳本呼叫 `/api/v1/search`：少了頁面的簽章會回 HTTP 421「system busy」。讓頁面自己發請求。
  - 每次都先搜一個確定有投 TikTok 的品牌當對照組（例如 Runway，近 30 天約 3,000 筆），確認方法有效，再相信目標品牌的 0 筆。
- **TikTok Creative Center 熱門廣告**（ads.tiktok.com/business/creativecenter/inspiration/topads）：關鍵字搜尋要登入，不要代登入；請使用者自己查。
- **Google 廣告透明度中心找不到廣告主**很常見：App 安裝廣告導向商店，不會出現在官網網域底下；廣告主名稱可能是另一家公司。查不到不等於沒投，報告要寫「無法確認」。
- **JS 回傳值含網址查詢字串或 cookie 會被擋**（「BLOCKED: Cookie/query string data」）。只回傳需要的欄位，例如從 href 用正則抽出 ID，不要整串回傳。
- **Google 廣告透明度中心的日期篩選器**：在介面上輸入日期常常套用不上。直接用 `scripts/google_ads_transparency.js` 呼叫資料介面。
- **Meta 廣告資料庫**：頁面要等約 5 秒才有內容；第一次讀到空白很正常。
- **內建瀏覽器打不開本機 file:// 頁面的 JS 工具**；要檢查本機 HTML，用 headless Chromium 截圖。

## 資料來源

- **Wayback Machine**：
  - CDX 查詢：`https://web.archive.org/cdx/search/cdx?url=<網址>&matchType=prefix&output=txt&fl=timestamp,original&filter=statuscode:200&collapse=timestamp:6`（`collapse=timestamp:6` = 每月一份）。
  - 用 `id_` 取原始頁面：`https://web.archive.org/web/<timestamp>id_/<網址>`。很多回應是 gzip 壓縮，要先解壓；有些快照是非英文頁面，會解析不到數字。
  - 連續請求會被限流，每次間隔 3–4 秒。
  - App Store 網址含 App 名稱，改名後要用舊網址名稱分別查。
- **google-play-scraper（Python）**：
  - 回傳的 `at` 是「本機時區」的 naive datetime。要轉 UTC：`datetime.fromtimestamp(x['at'].timestamp(), timezone.utc)`。
  - `country` 參數不會篩選評論，只有 `lang` 有效。
  - 熱門語言（英文）一次抓 1,000 則可能還不到 30 天，記得翻頁直到超過要的日期。
- **iTunes Lookup API**（`itunes.apple.com/lookup?id=...&country=xx`）：曾經整批回傳空白，不要依賴它做各國評分統計。
- **一畝三分地**：頁面是 GBK 編碼，fetch 後要用 `new TextDecoder('gbk')` 解碼，否則中文是亂碼；訪客不能用站內搜尋，只能翻列表頁（`/bbs/forum-<版號>-<頁>.html`），討論串頁是 `/bbs/thread-<id>-<頁>-1.html`。關鍵字要同時涵蓋簡體和繁體。
- **Similarweb**：小網站不顯示訪問數，只有排名和流量來源比例。
- **Trackitt**：曾經整站打不開。
- **Blind**：沒登入只能看到很少搜尋結果。
- **Reddit 公開 JSON**（`reddit.com/search.json`）：用 curl 會被擋，回非 JSON。

## Shell 與環境

- 這台 Mac 的預設 shell 是 zsh：`set -- $x` 和 `for x in $var` 不會自動拆字，要用 `${=var}` 或改用 `while read a b`。
- Python 套件裝在獨立的虛擬環境，不要裝到系統 Python：
  ```bash
  python3 -m venv ~/.cache/app-growth-teardown/venv
  ~/.cache/app-growth-teardown/venv/bin/pip install google-play-scraper numpy scipy
  ```
  之後用 `~/.cache/app-growth-teardown/venv/bin/python scripts/xxx.py` 執行。
- 暫存檔放在 session 的 scratchpad，幾天後會被清掉。報告和重要資料要另存到使用者指定的位置，或發布成 Artifact。

## 判讀上的坑

- 不要把 TikTok 公開播放數直接當自然流量（見 methods.md 第 4 節）；按讚率高也不能證明沒投廣告，要查 `isAd`（第 7b 節）。
- 不要只用美國 CPI 算成本就下結論（見 methods.md 第 9 節）。
- 搜尋熱度、標籤頁會撞到同名的東西（遊戲、歌手），先確認內容是同一個產品。
- 廣告主名稱可能是完全不同的公司名，要點開廣告確認內容是目標 App。
