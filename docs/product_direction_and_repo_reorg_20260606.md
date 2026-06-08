# 產品方向與 Repo 重整決策

日期：2026-06-06  
範圍：`ChannelCommunityAnalyzer/`

## 1. 產品定位

本專案要整理成一個 tool-oriented 的 YouTube channel analysis system。
核心目標不是研究筆記堆疊，也不是單純輸出一份 Markdown，而是：

> 輸入一個 YouTube channel URL，透過爬蟲、Qwen 語意/情緒分析、社群網路分析、baseline comparison、外部事件分析，產生一組可被 LLM 使用的冷資料報告，並由 LLM/API 轉成頻道主可讀的分析頁面。

實際 pipeline 可以跑 2-3 小時，且必須支援 resume。  
但期末展示的 Web demo 不會現場真的 crawl 或跑 Qwen，也不需要假的進度條。
Demo 會直接讀已完成的 runs / baseline artifacts，呈現像真正產品一樣的 dashboard。

## 2. Web Demo 定位

Web demo 是 read-only dashboard。

2026-06-07 demo adjustment:

- 後天展示先聚焦 DoDoMen 單一 case study，把 DoDoMen page 做清楚。
- 其他完成頻道可以在側欄保留少數可點選 reference，證明 dashboard 可切換案例。
- 目前跨頻道 percentile 只能稱為 broad benchmark / rough positioning。
- 不要把目前 48-channel benchmark 包裝成「同主題頻道比較」或「同類型排名」。
- 類似題材的 similar-channel comparison 是 future work。

不做：

- 不現場貼 URL 真的跑 crawl。
- 不現場跑 Qwen。
- 不顯示假的進度條。
- 不讓 demo 使用者觸發重型任務。

要做：

- 首頁乾淨，說明產品可分析 YouTube channel。
- 往下滑展示 completed channel examples。
- 每個 example 可進入 dashboard。
- Dashboard 有多個分頁，不是單頁報告。
- 讀本機已有 artifacts，例如 `report.json`、`report_zh.md`、`tables/*.csv`、`figures/*.png`、baseline outputs。
- 真 pipeline 保留在 CLI / runner / README 中，供非 demo 情境使用。

目前部署假設：

- Demo 可直接連到本機固定 IP。
- Cloudflare 不是核心執行環境；若使用，主要用途是 DNS / Tunnel / frontend hosting。
- Qwen、crawler、graph analysis 仍跑在本機或本機可控環境。

## 3. Dashboard 應包含的能力

別人有的基礎 YouTube analytics 也要有，但本專案要多做留言社群與外部事件層。

基礎層：

- channel overview
- video count、view count、like count、comment count
- upload cadence
- top videos
- time series
- theme/topic distribution
- sentiment overview

本專案差異化層：

- core audience / repeat commenter structure
- commenter tiers
- commenter-commenter network
- video shared-audience network
- community detection and community profiles
- bridge commenters / bridge videos
- reply conflict and pile-on diagnostics
- negative hotspots
- video link opportunities / content idea suggestions
- dynamic baseline percentile comparison
- external PTT event impact
- LLM-generated owner-facing report
- raw cold report / tables for deeper inspection

Figures 不能只是「把數字畫出來」。之後圖表設計要以分析問題為中心：

- 這個頻道相對 baseline 是高、低、還是典型？
- 事件前後是否有 audience / sentiment / conflict 變化？
- 哪些影片是風險或機會？
- 哪些社群群體貢獻了主要互動？
- 哪些內容主題在不同社群中有不同反應？

Audience / video segmentation display must be profile-oriented:

- Audience community 不應只顯示 community id、n_nodes、conductance。要轉成
  頻道主看得懂的 segment profile：群體大小、活躍程度、偏好影片/題材、
  常見討論關鍵字、主要情緒、負面來源、代表留言狀態、商業建議。
- Video shared-audience cluster 不應只顯示 cluster id、n_videos、top themes。
  要解釋每個 cluster 由哪些 evidence 形成：title/description/tags
  說明主題，comment keywords 說明觀眾討論什麼，sentiment 說明反應好壞，
  ABSA 說明稱讚/抱怨面向，metadata 說明表現輪廓，shared audience 說明
  共同觀眾結構。
- Current limitation: the 2026-06-07 dashboard JSON only has theme/title proxy
  keywords and ternary sentiment. It must label missing true comment keyword
  extraction, ABSA, and representative-comment sampling as future work rather
  than pretending those readings are already measured.

## 4. Pipeline 與 CLI

Web demo 讀完成品；真 pipeline 保留 CLI 任務。

建議核心任務拆分：

- crawl wrapper：呼叫外部 crawler project
- check/resume：檢查 DB/Qwen/report 完成度
- qwen video themes
- qwen comment sentiment
- analyzer report
- reply supplement
- external PTT crawl / external event analysis
- baseline builder
- LLM owner report generation

Qwen 預設會跑，但必須支援：

- `all`
- `existing`
- `none`
- resume incomplete rows
- retry parse errors

Crawler 工具來源：

```text
https://github.com/Lewis-panda/youtube-graph.git
```

本 repo 不搬 crawler 核心，只保留 integration wrapper / data contract。

## 5. Baseline 原則

Completed runs 是 baseline 的資料來源，不是垃圾，不能刪除。

Baseline 必須支援動態 cohort 篩選，例如：

- subscriber_count min/max
- video_count min/max
- time window
- Taiwan benchmark only / all completed runs
- exclude case studies

所有可 benchmark 的指標都應盡量納入 baseline，而不是只挑幾個容易展示的指標。

報告與 dashboard 必須標註：

- DB snapshot time
- subscriber_count snapshot
- cohort filter
- baseline sample size
- included channels
- excluded or incomplete channels

解讀原則：

> 指標本身通常沒有絕對意義；例如 core audience share = 1% 必須放進相似頻道 baseline 中看，才知道它是高、低、或典型。

Current demo caveat:

> 後天 demo 的 DoDoMen percentile 使用的是整體台灣 broad benchmark，不是 matched similar-channel cohort。它可以幫助觀眾理解「相對位置」這個產品概念，但不能被解讀成 DoDoMen 在相似旅遊/雙人創作者頻道中的排名。

Future matched-cohort approach:

1. 先建立台灣 YTR candidate pool，只抓輕量 channel / video metadata，不先抓留言。
2. 用 channel description、最近影片 title/description/tags、Qwen/embedding topic、訂閱/觀看/影片量、長短片比例、上片頻率、comment/view 與 like/view 建立初步相似度。
3. 對每個 target 選 Top 20-50 candidate comparable channels。
4. 只對這些候選頻道做深度留言爬蟲、Qwen sentiment、社群網路與 reply conflict。
5. 深度資料進來後，再用觀眾互動型態、回訪率、社群集中度、情緒/衝突模式、共同留言網路密度重算相似度。
6. Dashboard 再顯示真正的 Similar Channels 與 matched benchmark。

## 6. External Event Analysis

External events 要保留，並可和主分析平行進行。

第一版策略：

- PTT first，作為 core optional flow。
- Dcard 保留 interface，但先不阻塞主線，因為 browser workflow / anti-bot 風險較高。
- External source 必須 per channel，不可混用 DoDoMen 的外部貼文分析別的頻道。

Aliases 是必要功能：

- automatic aliases：channel title、handle、custom URL、基本名稱變體
- Qwen/API aliases：從 channel name、video titles、description 中推測人物、品牌、中文/英文別名
- manual aliases：config 補充，特別是 case study

## 7. DoDoMen Case Study

DoDoMen 拆夥分析是期末報告要回答的特例，不是 generic pipeline 的預設假設。

保留內容：

- 影片級 labels：`ian` / `eric` / `collab` / `other`
- DoDoMen appendix config / notes
- 必要 case study artifacts

不做：

- 不把 Ian/Eric/Collab 寫死在 generic analyzer。
- 不讓一般 channel analysis 預設讀 DoDoMen labels。
- 不把 DoDoMen 特例變成 generic analyzer 的預設邏輯。後天 demo 例外：首頁可以直接聚焦 DoDoMen，因為展示目標是完成一個清楚的 case-study page。

建議位置：

```text
case_studies/dodomen/
```

## 8. Repo 目標結構

第一階段只搬移，不刪除。

```text
channel_analyzer/
  Core Python package.

scripts/
  Thin task CLIs and runners.

dashboard/ or web/
  Read-only demo dashboard.

configs/
  Channel configs and examples.

runs/
  Active/current run outputs only.

baseline_runs/
  Completed full runs used by baseline and dashboard examples.

case_studies/
  Special appendices, currently DoDoMen.

legacy/
  Old logs, exports, qwen jobs, research experiments, notebooks, one-off scripts.

docs/
  Product direction, README support, runtime/baseline documentation.
```

## 9. Reorganization Rules

- Do not delete large completed runs.
- Do not delete DoDoMen case materials.
- Move first, delete only after verification and explicit approval.
- Keep baseline builder able to scan completed runs.
- Keep true pipeline runnable from CLI.
- Keep dashboard demo read-only.
- Keep DoDoMen case study separated from generic analysis.
- Keep external event data target-specific.

## 10. Immediate Step-by-Step Plan

1. Document product direction and repo rules.
2. Update `AGENTS.md` so future sessions follow this direction.
3. Create `baseline_runs/`, `case_studies/dodomen/`, and `legacy/`.
4. Move completed `runs/*-full` into `baseline_runs/`.
5. Move `runs/benchmark_baseline` to `baseline_runs/benchmark_baseline` and
   keep a compatibility symlink if existing scripts still read `runs/`.
6. Move DoDoMen custom labels and case notes into `case_studies/dodomen/`.
7. Move old logs, exports, qwen jobs, notebooks, and research-only folders to `legacy/`.
8. Update README / AGENTS path references.
9. Verify completion checks and baseline builder can still find expected artifacts.
10. Only after verification, discuss whether any legacy content should be deleted.
