# Project Update

日期：2026-05-13

## 專案方向大幅調整

原本的方向是做 DoDoMen 的單一 case study；現在改成更 general 的 YouTube channel community analyzer：

給定一個 YouTube 頻道 URL， 系統會產生一份可解讀的留言者社群健康報告，並進一步把該頻道放到台灣 creator/media benchmark cohort 裡比較。

## 轉向原因：

原本 DoDoMen-only 的 framing 太像單一 case study，contribution 不夠 general。 很多發現只能說明 DoDoMen 本身，很難推廣到其他頻道。

第一階段是 DoDoMen case study。問題是 contribution 太像單一個案研究：很多設計和解讀都會綁在 DoDoMen身上，很難說它對其他頻道也有用。

第二階段是 generic channel analyzer。為了讓 project 更 general，我把重點從「分析 DoDoMen」改成「做一個頻道分析工具」。

第三階段是 benchmark cohort。當頻道分析工具可以跑之後，我發現另一個問題：單一頻道的很多指標沒有比較基準時，很難判斷高低。比如核心觀眾比例 1% 是低、普通還是高；它需要跟其他相近頻道比較。所以現在新增的方向是建立 Taiwan creator/media benchmark cohort，跑多個頻道後建立各指標的 reference distribution，再用 cohort average、median、range、percentile 來解讀單一頻道的數值。

## 新的 contribution 是

- 一套可以重複套用在任意 YouTube 頻道的分析 pipeline。  
- 一個 benchmark cohort layer，用多頻道分布來解讀單頻道指標。  
- 一份適合後續 LLM 解讀的 statistical report packet。

## 新的專案定位

目前專案定位是：

一個 end-to-end Social Media Analytics tool，用 YouTube 影片 metadata、 comments、主題/情緒標註，以及 audience/video network analysis， 產生 YouTube 頻道的 commenter community health report。

輸入：

- YouTube channel URL。  
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

1. 抓取 YouTube 資料  
   給定 YouTube channel URL，系統會抓影片 metadata、留言、回覆和留言者資訊，並存進 shared SQLite DB。

2. 建立分析資料集  
   `ChannelCommunityAnalyzer` 從 DB 讀取指定頻道的資料，依 config 篩選分析範圍。目前預設分析 `2023-01-01` 之後的非 Shorts 影片。

3. 影片主題分類  
   使用 Qwen 對每支影片的 title、description、tags 做主題分類，讓後續可以分析不同內容主題吸引到哪些觀眾社群。

4. 留言情緒分類  
   使用 Qwen 對 comments 做 sentiment classification，產生 positive / neutral / negative 和對應分數。Top-level comments 主要用於觀眾結構分析；replies 會納入情緒、負面熱點與衝突分析。

5. 觀眾結構分析  
   根據留言行為分析 commenter tiers，例如核心留言者、回訪留言者、一次性留言者，並計算 retention、活躍度、留言集中度等指標。

6. Audience / video network analysis  
   系統會先建立「留言者 - 影片」的 bipartite graph，再做兩種 projection。第一種是 commenter-commenter graph：兩個留言者如果曾在同一支影片留言，就在兩人之間連邊，用來偵測 audience communities、bridge users 和社群集中度。第二種是 video-video shared-audience graph：兩支影片如果共享足夠多留言者，就在影片之間連邊，用來偵測 video clusters，也就是觀眾組成相近的影片群。這讓報告不只分析「誰跟誰像」，也分析「哪些影片吸引到同一批觀眾」。

7. Sentiment and hotspot analysis  
   結合 Qwen sentiment 和影片主題，找出整體情緒分布、不同主題的情緒差異，以及負面情緒特別集中的影片或主題。

8. Reply-thread deeper analysis  
   對 replies 做補充分析，觀察留言串中的衝突、對立、pile-on、極化等互動現象。這一層不取代核心觀眾分析，而是補充社群互動品質。

9. 產生單頻道報告  
   系統輸出中英文 Markdown report、JSON summary、CSV tables 和 figures。報告會整理頻道的觀眾結構、社群分群、影片群集、主題偏好、情緒分布、負面熱點與 reply-thread 診斷。

10. Benchmark cohort comparison  
   對多個台灣 creator/media channels 跑同一套 pipeline，建立各指標的 reference distribution。之後單一頻道的指標就可以用 cohort average、median、range、percentile 來解讀，而不是只看絕對值。

## 目前資料進度

截至 2026-05-13 00:46 ：

目前 shared DB 已經有 17 個頻道的資料：

| 頻道 | Videos | Top-level comments | Unique top-level commenters |
| :---- | ----: | ----: | ----: |
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
| The DoDo Men \- 嘟嘟人 | 347 | 242,955 | 110,802 |
| 中天新聞 | 572 | 276,686 | 105,905 |
| TVBS NEWS | 200 | 62,907 | 41,029 |
| 三立新聞網SETN | 23 | 6,972 | 6,143 |
| 上班不要看 NSFW | 152 | 41,459 | 20,110 |
| 反正我很閒 | 21 | 13,060 | 8,849 |
| 古娃娃WawaKu | 11 | 588 | 550 |

## 目前 Qwen 分析進度

以下頻道已完成 depth-all Qwen 分析，也就是 video themes、all-comment sentiment、base report、reply-thread supplement 都完成：

| 頻道 | Videos | Top-level comments | Qwen sentiment all comments | 狀態 |
| :---- | ----: | ----: | ----: | :---- |
| DoDoMen | 346 | 242,919 | 299,648 | complete |
| 錫蘭Ceylan | 112 | 171,175 | 250,589 | complete |
| Onion Man | 118 | 88,909 | 109,733 | complete |
| 喪屍老爸 | 473 | 72,735 | 88,414 | complete |

以下頻道 base Qwen 已完成，但 depth-all replies 還沒補完：

| 頻道 | Videos | Top-level comments | 待補 replies |
| :---- | ----: | ----: | ----: |
| Superpie | 602 | 73,117 | 27,054 |
| 课代表立正 | 526 | 14,062 | 8,056 |

## 下一步

短期：

- 等 YouTube API quota reset 後繼續 crawler。

中期：

- 建立 cohort distributions 和 percentiles。  
- 決定 final presentation 要用哪個 channel 當主案例。

主要風險：

- 完整 Qwen sentiment 對大型頻道很花時間。  
  - Onion Man：約 145 萬訂閱。這次 scope 是 118 支非 Shorts 影片、109,733 則 all comments，Qwen sentiment 跑了 11,844 秒，約 3 小時 17 分。  
  - 喪屍老爸：約 150 萬訂閱。這次 scope 是 473 支非 Shorts 影片、88,414 則 all comment，Qwen sentiment 跑了 9,141 秒， 約 2 小時 32 分。

- benchmark layer 需要足夠多 completed channels，percentile 解讀才有意義。

## 建議 final story

我目前建議 final project 可以這樣講：

我們建立了一個 YouTube channel community analyzer，結合 video metadata、comments、Qwen-assisted theme/sentiment labeling，以及 audience/video network analysis，產生頻道社群健康報告。為了讓單一頻道指標更可解讀，系統加入 benchmark cohort layer：把已完成的頻道分析結果聚合成 reference distributions，讓目標頻道的核心觀眾比例、retention、community concentration、sentiment 和 conflict metrics 可以比較。  
