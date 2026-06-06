# DoDoMen 頻道社群結論報告

本報告面向頻道主，整合 DoDoMen 完整頻道分析與 48 個台灣 creator/media benchmark cohort 比較。它不是只列指標，而是把「觀眾分群、留言者網路、影片 shared-audience 群集、Qwen semantic 主題、情緒與 reply conflict、外部事件」放在一起解讀。百分位數代表 cohort 中有多少比例的值低於或等於 DoDoMen，只表示相對位置，不直接代表好壞。DoDoMen 沒有被放進 baseline 分布。

## 1. 總結判斷

DoDoMen 是一個高觸及、高留言量、具有可觀重複參與核心的頻道，但留言區的結構不是「很多小社群自然互相討論」，而是「少數大型觀眾區塊主導，整體情緒正向，局部題材會出現高衝突」。因此，經營重點不應只是追求更多留言，而是提高觀看者留言轉換率、擴大跨社群橋接、並建立高風險題材的發布後監控。

## 2. 規模與互動效率

DoDoMen 分析範圍包含 351 支影片、245,544 則 top-level comments、111,537 位 top-level 留言者，以及 303,094 則含 replies 的情緒分析留言。留言數位於 benchmark 第 97.9 百分位，留言者數位於第 95.8 百分位，代表 DoDoMen 的留言母體遠大於多數可比頻道。

但這不等於留言轉換率特別高。DoDoMen 每千觀看留言數為 0.813，低於 benchmark 中位數 0.923，只在第 43.8 百分位。也就是說，高留言量主要來自頻道規模、觀看量與單片觸及，而不是每位觀看者更容易留言。

**經營含義**：DoDoMen 不缺留言規模，下一步應該優化留言轉換率。具體做法包括：影片中設計明確問題、二選一留言、下一站/下一集任務徵集、置頂留言投票，讓已觀看的人更容易留下可分析、可回覆的留言。

## 3. 核心觀眾與回流

DoDoMen 的高/中活躍留言者占 6.08%，高於 benchmark 中位數 2.60%，位於第 83.3 百分位。這群人雖然占比不大，但貢獻 36.1% 留言，高於 benchmark 中位數 18.0%，位於第 87.5 百分位。四窗留言者留存率為 24.8%，也高於 benchmark 中位數 14.5%，位於第 81.3 百分位。

這說明 DoDoMen 不只是「大頻道所以留言多」，而是確實有一批會跨影片、跨時間回來互動的觀眾。

**經營含義**：中高活躍留言者是可經營資產。可用系列企劃、社群貼文決策、直播 QA、會員投票、幕後企劃徵集，把他們從「常留言的人」轉成穩定回流與內容共創的一部分。

## 4. 留言者分群與網路結構

留言者共現網路包含 19,092 個節點、1,769,276 條邊，偵測出 3 個主要 audience communities。最大社群占 50.7%，第二大 31.0%，第三大 18.2%。社群集中度 HHI 為 0.387，高於 benchmark 中位數 0.276，位於第 89.4 百分位；主要社群數 3 則低於 benchmark 中位數 5，位於第 8.5 百分位。

這代表 DoDoMen 不是碎片化成很多小觀眾圈，而是由少數大型觀眾區塊主導。這有利於品牌定位，也代表不同內容線之間可能需要更主動的橋接。頂部橋接留言者 participation mean 為 0.614，低於 benchmark 中位數 0.692，位於第 19.1 百分位，支持「跨社群橋接偏弱」的判斷。

三個 audience communities 的內容偏好不同：

- Community 0：偏 `education_advice`、`workplace_tech_career`、`personal_team_life`，也是最大社群。
- Community 1：偏 `guest_relationship`、`food_culture`、`city_lifestyle`。
- Community 2：對 `survival_outdoor` 的 lift 最高，並偏 `guest_relationship`、`business_brand`、`controversy_response`。

**經營含義**：DoDoMen 可以針對不同社群設計不同入口。同一支影片不一定要服務所有人，但可在標題、開場、社群貼文或片尾問題中設計不同切角，讓旅遊、人物關係、職涯科技、戶外挑戰等觀眾群能交會。

## 5. Qwen semantic 主題與內容定位

Qwen video theme 分類顯示，DoDoMen 最大內容軸是 `travel_exploration`：112 支影片、70,490 則 top-level comments、41,548 位留言者。其次是 `personal_team_life`、`guest_relationship`、`workplace_tech_career`、`physical_challenge`。

這些主題不是單純的分類標籤，而是用來理解「哪類內容吸引哪類留言者、哪類內容風險較高」。例如 `travel_exploration` 是最大流量與最大討論主軸；`personal_team_life` 正向率高；`survival_outdoor`、`product_review`、`city_lifestyle` 的負面率較高，需要更謹慎的設定說明。

**經營含義**：DoDoMen 的內容核心仍是旅遊探索，但成長機會不只在更多旅遊，而在於旅遊如何與人物關係、職涯科技、團隊生活、戶外挑戰做結構性混合。

## 6. 影片 shared-audience 群集與內容橋接

影片 shared-audience 圖有 350 支影片、3 個影片群集。Cluster 0 以 2023-2026 的旅遊、人物、城市生活與近期合作內容為主；Cluster 1 偏 2020-2023 的早期旅遊、團隊生活、職涯科技與教育建議；Cluster 2 較小，包含跑步、倉儲、挑戰、部分旅遊與職涯科技內容。

影片網路密度為 0.859，高於 benchmark 中位數 0.466，代表 DoDoMen 不同影片之間共享留言者程度高。這表示內容之間有明顯共同觀眾，但也可能代表觀眾圈高度重疊。

Link prediction 產出的內容橋接機會多為 `cross_cluster_theme_bridge`，例如：

- `travel_exploration + guest_relationship`
- `workplace_tech_career + travel_exploration`
- `physical_challenge + guest_relationship`
- `city_lifestyle + workplace_tech_career`
- `travel_exploration + personal_team_life`

**經營含義**：這些不是保證成功的企劃，而是「目前 shared-audience 還未強連結，但結構上有橋接潛力」的題材組合。適合做 A/B 式企劃測試。

## 7. 情緒與風險

整體情緒上，DoDoMen negative rate 為 7.51%，低於 benchmark 中位數 9.42%；positive rate 為 47.4%，高於 benchmark 中位數 33.8%；like-weighted negative rate 為 5.19%，低於 benchmark 中位數 9.69%；like-weighted positive rate 為 60.6%，高於 benchmark 中位數 41.8%。這代表全頻道層級的留言情緒相對健康，負面留言沒有被按讚明顯放大。

但局部題材有風險。主題情緒顯示：

- `product_review` negative rate 17.0%，相對高。
- `survival_outdoor` negative rate 11.9%，且正向率較低。
- `city_lifestyle` negative rate 11.7%。
- `guest_relationship` negative rate 9.3%，但留言量大、reply 較多。
- `personal_team_life`、`physical_challenge`、`event_announcement` 相對正向。

負面熱點影片包含硬幣換機票、Enzo 行程、倉儲競標、蘋果 vs 三星開箱、巫術島、澳洲打工等。這些熱點的共同風險通常不是「內容類型不能做」，而是觀眾可能質疑真實性、合作界線、企劃公平性、文化呈現、或工作/旅遊敘事是否過度簡化。

**經營含義**：DoDoMen 不需要把整個頻道視為高負面風險，但要建立「題材級」監控。Product review、戶外/荒島、城市比較、來賓合作、職涯科技、工作體驗類影片發布前應預先準備說明框架。

## 8. Reply 深度與衝突

DoDoMen replies 共 57,550 則，占 all comments 19.0%；有 replies 的 threads 為 15,925 / 245,544，占 6.49%。這兩個數字都低於 benchmark 中位數，代表留言區多數互動停留在單層表態，觀眾彼此深入討論的比例偏低。

Reply 情緒中，replies negative rate 為 9.1%，top-level negative rate 為 7.2%。Reply 不是全面失控，但比 top-level 更容易出現負面或反駁。舊版 structural conflict score 只看衝突 thread 數量與 replied-thread 比例；新版另加入 reply-count weighted 與 like-weighted conflict，避免少量 replies 的小衝突被高估，也能看出哪些衝突被按讚放大。重建 baseline 後，DoDoMen 的 max video like-weighted conflict score 位於第 77.1 百分位，max theme like-weighted conflict score 也位於第 77.1 百分位，屬於高於多數 cohort 的局部風險。Weighted 後，荒島 Day1、巴拉圭、倉儲競標、建中一日老師、荷蘭小帥哥回台灣、賀瓏非洲行程都屬於需要優先檢查的 reply conflict 熱點。主題層級則以 `workplace_tech_career`、`travel_exploration`、`guest_relationship`、`personal_team_life`、`survival_outdoor` 較值得監控。

**經營含義**：DoDoMen 的問題不是「reply 太吵」，而是「健康 reply 不夠多，但少數題材會有明顯衝突」。頻道應主動回覆具體問題、誤解澄清、高讚建議，把 reply thread 變成補充資訊與共同參與，而不是只在爭議時爆發。

## 9. 外部事件

外部事件分析對齊 PTT/Dcard 討論與 YouTube 留言反應。這是事件視窗關聯，不是因果估計。分析中有 168 篇外部貼文、18 個事件群。部分事件窗口附近 YouTube 負面率高於 baseline，例如：

- 2025-10 內容品質批評與真實性討論。
- 2025-10 荒島求生真實性質疑。
- 2026-04 主持/人員變動討論。
- 2024-08 賀瓏/非洲行程相關討論。

**經營含義**：外部討論不應被當成因果證明，但可以作為風險雷達。外部討論升溫時，頻道應準備置頂留言、社群貼文、後續影片補充或 FAQ，避免 YouTube 留言區只由猜測與片段資訊主導。

## 10. 可執行建議

1. **提高留言轉換率，而不是只看留言總量。**  
   每千觀看留言數低於中位數。每支影片設計一個明確互動點，讓已觀看者更容易留言。

2. **把中高活躍留言者納入固定回流機制。**  
   這群人占 6.08%，貢獻 36.1% 留言，是頻道可經營的核心社群資產。

3. **用混合題材做跨社群橋接。**  
   優先測試旅遊 + 人物關係、職涯科技 + 旅遊、團隊生活 + 戶外挑戰、產品/開箱 + 旅遊情境。

4. **建立發布後 24-72 小時風險監控。**  
   追蹤 negative rate、like-weighted negative rate、reply conflict score、置頂留言下的反駁比例。

5. **對高風險題材預先說明設定與邊界。**  
   Product review、戶外挑戰、城市比較、來賓合作、職涯科技、工作體驗要更清楚說明合作關係、拍攝限制、真實性與安全安排。

6. **增加健康 reply thread。**  
   主動回覆高讚問題、誤解澄清、具體建議，並把優質留言帶進後續影片或社群貼文。

7. **把外部事件當監控訊號，不當因果結論。**  
   外部討論升溫時，提前準備回應節奏與資訊補充。

## 11. 不能下的結論

- 不能說 DoDoMen 「比其他頻道更健康」。只能說不同指標在 cohort 中相對高或低。
- 不能把 percentile 高當成好、低當成壞。高留言量、高社群集中度、高衝突分數意義完全不同。
- 不能把共留言社群當成真實粉絲派系。它是共同留言行為形成的網路分群。
- 不能把 Qwen sentiment 當人工標註真值。它適合大樣本趨勢與風險篩查。
- 不能從外部事件推論因果。外部討論、影片題材、演算法推薦、發布節奏都可能同時影響留言。

## 來源

- `runs/dodomen-generic-demo/report_zh.md`
- `runs/benchmark_baseline/target_metric_percentiles.csv`
- `runs/benchmark_baseline/metric_distributions.csv`
- `runs/benchmark_baseline/cohort_members.csv`
