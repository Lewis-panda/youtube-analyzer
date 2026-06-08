# CLAUDE.md — Dashboard worklog & resume guide

Active worklog/TODO for the read-only dashboard demo. Read `AGENTS.md` for full
project rules; read THIS for what's in-flight and what to do next. The user may
run out of tokens mid-task — this file lets any session resume cleanly.

## Run / verify

- Dashboard server (read-only static demo) runs in tmux on `0.0.0.0:8000`.
  Restart if down:
  `tmux new-session -d -s dash 'cd /home/lewis/NTU_Course/SMA/Youtube-Network/ChannelCommunityAnalyzer && python3 dashboard/server.py --host 0.0.0.0 --port 8000 > logs/dash.log 2>&1'`
  It sends `Cache-Control: no-store` and re-reads files per request, so a normal
  F5 (whole page, not just tab switch) picks up frontend edits.
- Frontend = `dashboard/static/app.js` (single file ~2400 lines) + `styles.css` + `index.html`.
  After edits: `node --check dashboard/static/app.js`.
- Demo channel: DoDoMen, slug `dodomen-generic-demo`. Channel data:
  `dashboard_data/channels/<slug>.json` (built by `scripts/build_dashboard_index.py`).
- Rebuild dashboard data (pandas only, ~1 min, NO Qwen/GPU): `python3 scripts/build_dashboard_index.py`
- Rebuild benchmark baseline: `python3 scripts/build_benchmark_baseline.py --target-run-dir runs/dodomen-generic-demo`

## Done this session (verify before changing; large UNCOMMITTED diff on `main`)

- Recovered `app.js` after another agent reverted it (restored from `~/.claude/file-history/*/e36f4c2289330b51@v5`).
- **Activity tiers redesigned** to coverage-based 4-tier (`one_time`/`returning`/`regular`/`core`),
  cross-channel normalized, cohort-calibrated. Code: `channel_analyzer/analysis.py:assign_commenter_tiers`
  + `config.py` (`core_coverage=0.05`, `regular_coverage=0.02`, `core_min_videos=3`).
  `benchmark.py` emits new tier metrics + keeps `high/mid/low/high_mid` aliases.
  Re-tier existing runs WITHOUT re-running analyzer: `python3 scripts/retier_commenter_activity.py`
  (then rebuild baseline + dashboard). `runs/*` symlink into `baseline_runs/*`.
- **Baseline comparisons show cohort MEAN, not median** (`tierComparisonBars`,
  `comparisonMetricBar`, `bulletMetric`; helper `valuePercentile`). `mean` is already
  in the baseline distribution, so switching display needs no rebuild.
- Sentiment 負面風險: per-video negative reasons (ABSA) in high-negative video cards via
  `video_aspect_summary`; the channel-level aspect overview panel was removed.
- Strategy page: grounded `strategy_brief` (source
  `case_studies/dodomen/dodomen-generic-demo/strategy_brief_zh.json`; builder hook
  `load_optional_strategy_brief` merges it into `analysis.strategy_brief`).
- External page focused on "does external discussion bring new audience" vs baseline.

## TODO QUEUE 2 — 2026-06-09 (ALL 4 DONE)

1. **[DONE]** 總覽 KPI 重複：訂閱/總觀看/總影片/分析留言 與 `channelReportCard` 重複 → 移除 KPI strip。
2. **[DONE]** 外部頁事件前後多指標同步變化（留言量倍率／負面率Δ＋顯著性／回覆衝突倍率／新留言者）— `naSyncBlock`，合併 `external_event_impact_diagnostics`。ABSA 負面主體事件窗變化仍為 future。
3. **[DONE]** 分群 content sensitivity（RQ3）：persona 卡加 觸及影片數／留言量／代表影片／特別投入(over-index lift)／特別負面(negative source)。
4. **[DONE]** 正面 ABSA：`generate_dashboard_video_absa.py` 產 `video_positive_aspect_summary.csv`；高正面影片卡顯示「被稱讚的點」。

<details><summary>原始需求（保留）</summary>

2. **外部頁：事件前後『同步變化』跨指標**（= 原 paused 事件 detail）。每個外部事件呈現
   事件前後是否同步變化：YouTube 留言量(`comment_volume_lift_vs_baseline`)、負面率
   (`delta_post_vs_baseline_negative_rate_pp`)、ABSA 負面主體（事件窗負面面向變化，較難；
   `external_events/comment_aspect_daily` 或先標 future）、reply conflict
   (`conflict_score_lift_vs_baseline`)、新留言者比例(已有)。資料：
   `runs/<slug>/external_events/external_event_impact_diagnostics.csv`（多數欄位都有；
   前端 fetchTableRows("external_event_impact_diagnostics")）。

3. **分群頁 content sensitivity (RQ3)**：每個觀眾社群顯示 群體大小/留言量/活躍程度/觸及影片數/
   偏好影片主題/theme affinity lift/情緒分布/高負面主題/代表影片/商業角色+策略。多數已在
   `audience_segment_profiles`（`preferred_themes`、`over_indexed_themes[lift]`、`negative_sources`、
   `preferred_videos`、`main_sentiment`、`business_advice`、`group_size`）。檢查是否有
   `community_theme_affinity.csv` 可補 affinity lift。重點：呈現「哪一群對哪一類內容特別正/負/易互動」。

4. **正面 ABSA**：positive ABSA 已完成（`runs/dodomen-generic-demo/tables/qwen_comment_absa_positive.csv`，
   144,503 列、0 parse error）。擴充 `scripts/generate_dashboard_video_absa.py` 也產
   `video_positive_aspect_summary.csv`（per-video 正面面向，讀 positive csv），rebuild dashboard，
   前端「正面亮點」加 per-video 正面原因（analog 現有負面的 `videoAspectReasons`）。

</details>

## TODO QUEUE — ALL 6 DONE 2026-06-08 (frontend only, no rebuild needed; kept for reference)

Minor remaining cleanup (harmless): after removing the 共享觀眾 tab, these helpers
are now dead and can be deleted: `videoClusterCards`, `videoPortfolioSummary`,
`affinityBars`, `opportunityCards` (and any sub-helpers only they used).

1. **總覽 KPI 去重**: `renderOverview()` 的 `metric-strip` 目前 8 個 tile，**只保留 4**：
   訂閱數、頻道總觀看次數、頻道總影片數、分析留言數（主留言數）。移除其餘重複的
   （分析範圍影片/觀看次數、主留言者數、YouTube 顯示留言數）。`channelReportCard` 若也重複這些要一起精簡。

2. **移除「共享觀眾」分頁**: `pages` 陣列拿掉 `{id:"video_network"}`；移除 `renderVideoNetwork()`
   與 `renderPage()` 的 dispatch。連結機會（`opportunityCards`/`video_link_opportunities`）目前只在這頁，一併移除。

3. **正負面留言排名依 ABSA「對頻道真的有負面影響」呈現**：負面排名要排除無行動性面向
   （`other`/`unclear`，`videoAspectReasons` 已 skip），但「排名」本身應依*真的有影響*的面向篩選/加權。
   `comment_aspect_summary` 有 `aspect_negative_lift_vs_scored_channel_negative_rate` /
   `negative_aspect_prevalence_lift_vs_full_channel_negative_rate` 可判斷。定義「真的有負面影響」≈
   lift>1 且非 other/unclear。套到 `themeRiskBars` / 負面排名 / per-video aspects。

4. **近期影片留言量（`videoTimeline`）雙軸圖**：加圖標題、兩軸的座標軸標題、刻度與刻度值（目前是簡化 SVG）。

5. **重新命名「四週回訪率」**：實際是「**4 個影片窗**」（`continuity_windows=4`），不是 4 週。
   UI 改成「**跨影片回訪率**」＋「近期回訪率」。app.js 搜 `四週`/`回訪`；`continuity_return_rate_w4`
   的 label、`audienceBaselineBars`、相關 infoTip 都要改。**只改顯示文字，不要動計算**。

6. **HHI / modularity 搬到觀眾頁、從相對定位移除、圖重做**：
   - `renderAudience()`：在 `communityPersonaCards` **上方**加兩張「白話判讀」卡：
     - HHI → 標題「**觀眾集中度**」+ band（偏高/中/低）+ 文案：「偏高，你的活躍留言者主要集中在少數幾個共同留言群。建議優先理解主力觀眾群偏好的內容與敏感主題。」
     - modularity → 標題「**分群清晰度**」+ band（高/中/低）+ 文案：「高，你的留言者可以被清楚分成幾個內容參與群，代表不同觀眾群可能有不同內容偏好。」
   - band 門檻可用 cohort 分布或固定。資料：`dashboard_summary.network_summary`（modularity）+ community 指標（`community_hhi`）。
   - `renderBenchmark()`：`selectedMetrics`/scatter/bullet **移除**社群網路分群指標
     （`community_hhi`、`largest_community_share`、`top3_community_share`、`commenter_network_modularity` 等），圖重做。

## Paused (do NOT start unless user says)

- 外部頁「粗時間窗重跑」(`merge_cross_topic`): `config.py`/`external_events.py` 已有半成品（default off）。
- 外部頁「清單→點選→各指標 detail」重設計。
