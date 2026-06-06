# 專案更新給組員

日期：2026-05-13

## TL;DR

我把專案方向大幅調整了。

原本的方向是做 DoDoMen 的單一 case study；後來改成更 general 的
YouTube channel analyzer；現在又進一步補上 benchmark comparison layer：

> 給定一個 YouTube 頻道 URL，或給定已經存在於 shared SQLite DB 的頻道，
> 系統會產生一份可解讀的留言者社群健康報告，並進一步把該頻道放到台灣
> creator/media benchmark cohort 裡比較。

這次轉向不是一次跳到 benchmark，而是分成三個階段：

1. 原本只想做 DoDoMen 的單一 case study。
2. 後來發現單一頻道的分析不夠 general，所以先把專案改成「頻道分析工具」：
   給定任意 YouTube channel，就能從 DB 裡的影片、留言、Qwen 標註和
   audience/video network analysis 產出一份 report。
3. 再往下做時發現，很多 report 裡的指標如果沒有比較對象，其實很難解讀。
   例如 DoDoMen 的核心觀眾比例如果是 1%，單看可能覺得很低；但如果其他相近
   頻道平均只有 0.5%，那 1% 反而可能代表核心觀眾相對更強。因此現在又補上
   benchmark cohort：分析一批台灣頻道，建立 reference distribution，讓單一
   頻道的指標可以用 cohort average、median、range、percentile 來解讀。

## 新的專案定位

目前專案定位是：

> 一個 end-to-end Social Media Analytics tool，用 YouTube 影片 metadata、
> comments、Qwen 主題/情緒標註，以及 audience/video network analysis，
> 產生 YouTube 頻道的 commenter community health report。

輸入：

- YouTube channel URL，或已經存在 shared SQLite DB 的 channel。
- 目前 crawl scope 是 `2023-01-01` 之後的影片。
- 預設排除 Shorts，使用 180 秒以下當作 short-form threshold。

輸出：

- 英文與中文 Markdown report。
- 結構化 JSON。
- 詳細 CSV tables。
- 圖表與社群/時間序列分析結果。

報告主要回答：

- 頻道的核心留言者、回訪留言者、一次性留言者比例是多少？
- 觀眾社群是否集中在少數人或少數社群？
- 留言者 retention 是否穩定？
- 哪些影片主題吸引哪些留言者社群？
- 哪些影片或主題是負面情緒熱點？
- reply thread 是否有衝突或極化跡象？
- 這些指標相對於其他台灣頻道，是高、低，還是一般？

## Pipeline 概觀

系統分成兩層。

第一層是 crawler / database layer。

`youtube_graph_ingest` 會爬 YouTube metadata 和 comments，並正規化到 shared
SQLite DB：

- `channels`
- `videos`
- `actors`
- `comment_threads`
- `comments`

Crawler 有 queue，所以可以 resume。YouTube API quota 用完時，隔天可以從
queue 繼續，不需要整個重跑。

第二層是 analyzer / report layer。

`ChannelCommunityAnalyzer` 從 shared DB 讀資料，依 config 產生報告。

目前包含：

- channel/video metadata summary
- commenter activity tiers
- repeat-commenter retention
- actor-video network analysis：包含 commenter-commenter projection 和
  video-video shared-audience projection
- Qwen video-theme classification
- Qwen comment sentiment classification
- negative hotspot detection
- reply-thread conflict / polarization diagnostics
- bilingual report generation

重要設計原則：

- 保持 config-driven。
- 不 hard-code DoDoMen、Ian/Eric、特定事件或特定 split。
- DoDoMen 只保留作 demo 或 appendix，不再是整個 project 的唯一目標。

## 為什麼轉向

這個專案目前的轉向其實是兩次調整，不是直接從 DoDoMen 跳到 benchmark。

第一階段是 DoDoMen case study。最一開始，我是想針對 DoDoMen 做完整分析，
包含影片主題、留言者社群、核心觀眾、情緒和負面熱點。這個方向可以把
DoDoMen 這個頻道講得很細，但問題是 contribution 太像單一個案研究：很多
設計和解讀都會綁在 DoDoMen 身上，很難說它對其他頻道也有用。

第二階段是 generic channel analyzer。為了讓 project 更 general，我把重點
從「分析 DoDoMen」改成「做一個頻道分析工具」。也就是說，只要某個 YouTube
頻道已經被 crawler 寫進 shared SQLite DB，就可以透過 config 跑同一套流程，
產出包含 audience structure、retention、commenter communities、
video shared-audience clusters、Qwen video themes、Qwen comment sentiment、
negative hotspots 和 reply-thread diagnostics 的報告。這一步讓 DoDoMen
變成 demo，而不是 hard-coded target。

第三階段是 benchmark cohort。當頻道分析工具可以跑之後，我發現另一個問題：
單一頻道的很多指標沒有比較基準時，很難判斷高低。比如核心觀眾比例 1% 到底
是低、普通還是高，不能只靠直覺；它需要跟其他相近頻道比較。所以現在新增的
方向是建立 Taiwan creator/media benchmark cohort，跑多個頻道後建立各指標的
reference distribution，再用 cohort average、median、range、percentile 來
解讀單一頻道的數值。

所以現在的 contribution 變成：

- 一套可以重複套用在任意 YouTube 頻道的分析 pipeline。
- 一份 config-driven 的 channel community health report。
- 一個 cross-channel benchmark layer，用多頻道分布來解讀單頻道指標。

DoDoMen 仍然會保留，但定位會從「唯一研究對象」改成「示範案例或 appendix」。

## 目前實作進度

已完成：

- Generic analyzer pipeline 已可運作。
- 報告由 config 產生，不依賴 hard-coded channel logic。
- Qwen video-theme classification 已整合。
- Qwen comment sentiment classification 已整合。
- Qwen stages 可 resume：已有 CSV rows 的影片/留言會跳過，只補缺的部分。
- `--depth all` 的 reply-thread supplement 已完成。
- runtime estimation 和 completion check 已完成。
- benchmark candidate URL list 已整理並人工校正一輪。
- crawler queue 可以在 quota reset 後繼續跑。
- crawler 現在遇到單支影片的非 quota error 會跳過，不會讓整個 batch 停掉。

尚未完成：

- cross-channel benchmark percentile / average layer 還沒有真正寫進 final report。
- 新爬到的大多數 benchmark channels 還沒跑 Qwen。
- 需要決定最後 cohort 要用完整 50 個頻道，還是縮成比較乾淨的小 cohort。

## 目前資料進度

截至 2026-05-13 00:46 台灣時間：

Crawler queue 狀態：

- `graphed`: 4,141 videos
- `queued`: 1,179 videos
- `failed`: 4 videos
- `skipped`: 61 videos
- YouTube API quota 目前已用完；最後一次 crawl 在 2026-05-12 21:08 clean pause。

目前 shared DB 已經有 17 個頻道的資料：

| 頻道 | Videos | Top-level comments | Unique top-level commenters |
|---|---:|---:|---:|
| 欸你這週要幹嘛 | 76 | 17,079 | 10,043 |
| 喪屍老爸 | 473 | 72,735 | 26,978 |
| 見習網美小吳 | 343 | 391,623 | 163,792 |
| 阿慶師 | 335 | 19,871 | 11,388 |
| HahaTai 哈哈台 | 168 | 51,497 | 33,112 |
| 超派人生Superpie | 621 | 73,194 | 35,061 |
| 錫蘭Ceylan | 112 | 171,175 | 111,569 |
| Onion Man | 118 | 88,909 | 48,825 |
| 课代表立正 | 526 | 14,062 | 7,687 |
| 阿翰po影片 | 43 | 24,615 | 15,378 |
| The DoDo Men - 嘟嘟人 | 347 | 242,955 | 110,802 |
| 中天新聞 | 572 | 276,686 | 105,905 |
| TVBS NEWS | 200 | 62,907 | 41,029 |
| 三立新聞網SETN | 23 | 6,972 | 6,143 |
| 上班不要看 NSFW | 152 | 41,459 | 20,110 |
| 反正我很閒 | 21 | 13,060 | 8,849 |
| 古娃娃WawaKu | 11 | 588 | 550 |

## 目前 Qwen 分析進度

以下頻道已完成 depth-all Qwen 分析，也就是 video themes、all-comment
sentiment、base report、reply-thread supplement 都完成：

| 頻道 | Videos | Top-level comments | Qwen sentiment all comments | 狀態 |
|---|---:|---:|---:|---|
| DoDoMen | 346 | 242,919 | 299,648 | complete |
| 錫蘭Ceylan | 112 | 171,175 | 250,589 | complete |
| Onion Man | 118 | 88,909 | 109,733 | complete |
| 喪屍老爸 | 473 | 72,735 | 88,414 | complete |

以下頻道 base Qwen 已完成，但 depth-all replies 還沒補完：

| 頻道 | Videos | Top-level comments | 待補 replies |
|---|---:|---:|---:|
| Superpie | 602 | 73,117 | 27,054 |
| 课代表立正 | 526 | 14,062 | 8,056 |

重要 caveat：

- 見習網美小吳原本在 89 支影片 scope 時已完成 Qwen。
- 但後來 crawler 又補到更多影片，目前 DB scope 擴到 343 支影片、
  419,394 all comments，所以需要再 resume Qwen 補新資料。

## 我希望組員給 feedback 的地方

1. Project contribution 是否夠清楚

目前我想把 contribution 寫成：

> generic channel analyzer + benchmark cohort comparison layer

這樣是否夠強？還是應該收斂成比較保守的：

> YouTube channel community health diagnostics

2. Benchmark cohort 怎麼定義

可能選項：

- 完整 50 個台灣 creator/media channels。
- 只留 150 萬訂閱以下的頻道。
- 只留 creator channels，排除新聞媒體。
- 按類型 stratify，例如 creator、commentary、food/lifestyle、news/media。

我需要大家判斷哪一種比較適合作為 final report 的比較基準。

3. 哪些指標應該放進 benchmark

我目前認為最需要跨頻道比較的是：

- core-audience share
- repeat-commenter retention
- community concentration
- bridge / community structure
- negative sentiment rate
- negative hotspot amplification
- reply-thread conflict rate

想請大家幫忙判斷：這些指標是否足夠？是否有些應該刪掉或新增？

4. Comment scope 是否合理

目前設計是：

- top-level comments 用於核心觀眾、留言者分層、retention、commenter network
  和 video shared-audience network
- all comments，包括 replies，用於 sentiment、negative hotspots、reply-thread conflict

這樣可以避免把 reply 行為混進 audience structure，但又能在衝突/情緒問題上
利用 replies。想請大家確認這個切分是否合理。

5. Final deliverable 要怎麼收斂

可能 final deliverables：

- single-channel report generator
- benchmark cohort summary table/dashboard
- 用 DoDoMen 或錫蘭做一個主 demo
- methodology appendix，說明 crawler、Qwen、network metrics 和 benchmark 方法

需要一起決定 deadline 前最 realistic 的版本。

## 下一步

短期：

- 等 YouTube API quota reset 後繼續 crawler。
- 跑完剩下 1,179 queued videos。
- 幫新完成的頻道產生 configs。
- resume 見習網美小吳的 Qwen，補新增資料。
- 對更多 benchmark channels 跑 Qwen。

中期：

- 實作 benchmark aggregation layer，從 `runs/` 裡 completed channel reports 讀
  指標。
- 建立 cohort distributions 和 percentiles。
- 把 benchmark interpretation 寫進 Markdown report。
- 決定 final presentation 要用哪個 channel 當主案例。

主要風險：

- YouTube API quota 是目前最大瓶頸。
- 完整 Qwen sentiment 對大型頻道很花時間。實測例子：錫蘭Ceylan 約 155 萬
  訂閱，這次 scope 是 112 支非 Shorts 影片、250,589 則 all comments
  （171,175 top-level + 79,414 replies），Qwen sentiment 跑了 29,832 秒，
  約 8 小時 17 分；Onion Man 約 145 萬訂閱、118 支影片、109,733 則 all
  comments，跑了 11,844 秒，約 3 小時 17 分；喪屍老爸約 150 萬訂閱、473
  支影片、88,414 則 all comments，跑了 9,141 秒，約 2 小時 32 分。
- benchmark layer 需要足夠多 completed channels，percentile 解讀才有意義。

## 建議 final story

我目前建議 final project 可以這樣講：

> 我們建立了一個 config-driven 的 YouTube channel community analyzer，結合
> video metadata、comments、Qwen-assisted theme/sentiment labeling，以及
> audience/video network analysis，產生雙語的頻道社群健康報告。為了讓單一頻道
> 指標更可解讀，系統加入 benchmark cohort layer：把已完成的頻道分析結果
> 聚合成 reference distributions，讓目標頻道的核心觀眾比例、retention、
> community concentration、sentiment 和 conflict metrics 可以跟相似頻道比較。
