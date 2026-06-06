# DoDoMen 頻道社群詳細分析報告

這份報告面向頻道主與內容團隊。它不是單純列 benchmark 指標，而是把 DoDoMen 舊版完整報告中的核心模組重新串起來：Qwen semantic 主題、留言者共現網路、觀眾社群、影片 shared-audience 群集、link prediction 內容機會、情緒熱點、reply conflict、外部事件視窗，以及 48 個台灣 creator/media benchmark cohort 的相對位置。

重要讀法：

- Percentile 只代表 DoDoMen 在 cohort 中的相對位置，不代表高就是好或低就是壞。
- DoDoMen 沒有被放入 benchmark baseline 分布，baseline 只來自 48 個已完成分析的台灣 creator/media 頻道。
- Qwen video theme 是語意主題分類，不是情緒分類。
- Qwen sentiment 是模型分類，適合大樣本趨勢與風險篩查，不等同人工標註真值。
- 留言者社群是 co-commenter 行為網路，不是真實粉絲派系。
- 外部事件分析是事件視窗關聯，不是因果估計。

## 1. 資料範圍與模型輸出

DoDoMen 這次分析範圍包含：

| 項目 | 數值 |
| :-- | --: |
| 頻道 | The DoDo Men - 嘟嘟人 |
| 訂閱數 | 1,660,000 |
| 分析影片數 | 351 |
| 影片日期範圍 | 2020-02-02 到 2026-05-27 |
| Top-level comments | 245,544 |
| Top-level commenters | 111,537 |
| Sentiment-scope all comments | 303,094 |
| Top-level comments in sentiment scope | 245,544 |
| Replies in sentiment scope | 57,550 |
| 總觀看數 in scope | 302,183,499 |

這個範圍比多數 benchmark 頻道大：影片數第 79.2 百分位，top-level comments 第 97.9 百分位，top-level commenters 第 95.8 百分位。這表示 DoDoMen 有足夠大的留言資料支撐分群、情緒與事件視窗分析，但也代表總量指標會受到頻道規模影響，所以必須搭配每千觀看留言數、回流率、網路結構與情緒風險一起解讀。

## 2. 總體結論

DoDoMen 不是缺留言量的頻道。相反地，它有非常大的留言母體、可觀的重複留言觀眾，以及相對正向的整體情緒。真正需要看的問題是：

1. 觀看轉留言效率沒有特別高。每千觀看 top-level comments 為 0.813，低於 cohort 中位數 0.923，位於第 43.8 百分位。
2. 中高活躍留言者很有價值。6.08% 的中高活躍留言者貢獻 36.1% top-level comments，兩者都高於 cohort 多數頻道。
3. 觀眾社群不是很多小群，而是 3 個大型 audience communities。最大社群占圖上節點 50.7%，前三大社群合計 100%，集中度高。
4. 影片也形成 3 個 shared-audience 群集，代表內容線可以被切成幾個主要觀眾重疊區塊。
5. 整體情緒不差。negative rate 7.51%，低於 cohort 中位數 9.42%；positive rate 47.4%，高於中位數 33.8%。
6. 風險不是全頻道負面，而是局部題材與 reply conflict。travel、guest relationship、workplace/tech、survival/outdoor 等主題容易形成具體爭議點。
7. 外部事件可以當風險雷達，但不能當因果證明。部分 PTT/Dcard 討論窗口附近 YouTube 負面率確實高於 baseline。

## 3. Qwen Semantic 主題分析

Qwen video theme 顯示 DoDoMen 的內容主幹很清楚：`travel_exploration` 是最大軸，接著是團隊生活、來賓/人物關係、職涯科技與體能挑戰。

| 主題 | Top-level comments | Commenters | Videos | 解讀 |
| :-- | --: | --: | --: | :-- |
| `travel_exploration` | 70,490 | 41,548 | 112 | 頻道最大內容軸，也是 DoDoMen 品牌記憶最穩的主幹。 |
| `personal_team_life` | 48,001 | 34,676 | 58 | 團隊與主持人關係能帶來高正向情緒，是核心觀眾回流的重要材料。 |
| `guest_relationship` | 30,610 | 21,375 | 37 | 來賓、外國人、人物互動是高觸發內容，但也較容易引發界線與真實性討論。 |
| `workplace_tech_career` | 28,593 | 22,657 | 37 | 早期工程師、科技、職涯敘事仍有穩定受眾，且與最大社群有高 affinity。 |
| `physical_challenge` | 21,637 | 15,274 | 37 | 情緒偏正向，適合和旅遊、團隊生活混合。 |
| `survival_outdoor` | 13,606 | 9,601 | 8 | 影片數少但討論強，風險也高，需要更明確的規則與真實性說明。 |
| `city_lifestyle` | 8,156 | 6,682 | 10 | 城市/生活比較類內容有受眾，但容易牽涉文化與價值判斷。 |

內容定位上，DoDoMen 不應被簡化成「旅遊頻道」。更精確的定位是：以旅遊與挑戰為主幹，結合人物關係、團隊生活與跨文化體驗。這也是後面網路分群與影片群集會反覆出現的結構。

## 4. 留言者共現網路與觀眾社群

留言者共現圖的定義是：兩位留言者如果曾在同一支影片留言，就可能形成 co-commenter edge；edge weight 是兩人共同留言過的影片數。本次圖上套用 `min_actor_videos=2` 與 `min_co_videos=3`，所以 111,537 位 top-level commenters 不會全部進入圖上節點，實際圖上節點為 19,092。這個設計是為了讓網路代表重複參與者與穩定共現關係，而不是一次性留言雜訊。

| 網路指標 | DoDoMen | Benchmark context | 解讀 |
| :-- | --: | :-- | :-- |
| Nodes | 19,092 | graph-only 指標 | 圖上代表較穩定參與者，不是全部留言者。 |
| Edges | 1,769,276 | graph-only 指標 | 共同留言關係非常多，足以做分群與橋接分析。 |
| Density | 0.00971 | 第 19.1 百分位 | 大頻道常見現象：觀眾很多，但任兩人共同出現在同一批影片的比例不高。 |
| Communities | 3 | 第 8.5 百分位 | 主要觀眾區塊少，不是碎片化成很多小圈。 |
| Modularity | 0.310 | 第 87.2 百分位 | 雖然只有 3 群，但邊界相對清楚。 |
| Largest community share | 50.7% | 第 78.7 百分位 | 最大社群非常大。 |
| Community HHI | 0.387 | 第 89.4 百分位 | 社群規模集中。 |
| Top bridge participation mean | 0.614 | 第 19.1 百分位 | 頂部橋接者跨社群程度偏低。 |

這裡的核心判斷是：DoDoMen 有大型核心觀眾區塊，但跨區塊橋接偏弱。對頻道經營來說，這不是單純的好壞，而是內容策略問題。若只服務最大社群，品牌一致性會強；若要擴張新題材或降低單一內容線依賴，就需要設計跨社群入口。

### 4.1 三個 audience communities

| Community | Commenters | 節點占比 | Comments | 觸及影片 | 主要主題 | 解讀 |
| :-- | --: | --: | --: | --: | :-- | :-- |
| 0 | 9,684 | 50.7% | 65,067 | 351 | travel, team life, workplace/tech, challenge, other | 最大社群，對早期工程師/職涯、團隊生活、教育建議相對更有 affinity。 |
| 2 | 5,926 | 31.0% | 42,415 | 348 | travel, guest relationship, team life, survival/outdoor, challenge | 對 survival/outdoor、爭議回應、人物合作更敏感，是風險與成長機會都較高的群。 |
| 1 | 3,482 | 18.2% | 27,200 | 349 | travel, guest relationship, team life, challenge, other | 較小但仍跨大量影片，人物與來賓內容是重要入口。 |

三個社群都觸及 348 支以上影片，代表它們不是只看單一系列的小群體，而是對整個頻道有不同偏好的大型觀眾區塊。分群價值在於：同一支影片的包裝與留言互動可以同時設計多個入口。例如旅遊主軸可以用「目的地與冒險」服務 travel 社群，用「人物互動」服務 guest 社群，用「幕後製作/職涯」服務 workplace/tech 社群。

### 4.2 社群主題 affinity

`lift = community_share / overall_share`。大於 1 代表該社群相對更偏好該主題。

| Community | 高 affinity 主題 | Lift | 解讀 |
| :-- | :-- | --: | :-- |
| 0 | `education_advice` | 1.63 | 最大社群對教育/建議類內容相對集中。 |
| 0 | `workplace_tech_career` | 1.41 | 工程師、科技、職涯敘事仍是最大社群的重要記憶。 |
| 0 | `personal_team_life` | 1.29 | 團隊生活能穩定服務核心群。 |
| 2 | `survival_outdoor` | 2.45 | 戶外/生存類高度集中於 Community 2。這是機會，也是風險點。 |
| 2 | `controversy_response` | 2.13 | Community 2 對爭議或回應型內容更敏感。 |
| 2 | `guest_relationship` | 1.34 | 來賓/人物關係是第二大社群的重要入口。 |
| 1 | `automotive_luxury` | 1.88 | 樣本小，適合當 appendix 觀察，不宜過度解讀。 |
| 1 | `food_culture` | 1.58 | Food/culture 在小社群有較強相對偏好。 |
| 1 | `guest_relationship` | 1.34 | 來賓/人物互動對小社群也重要。 |

經營意義：不要把所有觀眾都當成同一種「DoDoMen 粉」。觀眾行為上至少有三個大型入口，內容包裝應該明確設計「旅遊冒險」「人物/來賓」「團隊與職涯/幕後」三種可進入角度。

## 5. 影片 Shared-Audience 群集

影片 shared-audience graph 的節點是影片，兩支影片若共享留言者達門檻就連邊。這和留言者共現圖相反：它問的是「哪些影片被同一批觀眾一起留言」。

| 指標 | DoDoMen | Benchmark context | 解讀 |
| :-- | --: | :-- | :-- |
| Video graph nodes | 350 | graph-only 指標 | 351 支影片中有 350 支進入影片圖。 |
| Edges | 52,470 | graph-only 指標 | 影片之間共享留言者關係非常密。 |
| Density | 0.859 | 第 68.8 百分位 | 大多數影片都和其他影片有共享留言者。 |
| Clusters | 3 | 第 60.4 百分位 | 影片內容形成 3 個主要 shared-audience 群。 |
| Modularity | 0.190 | 第 64.6 百分位 | 群集存在，但不是完全分裂。 |

### 5.1 三個影片群集

| Cluster | Videos | 日期範圍 | Comments | Unique commenters | Views | 主題與解讀 |
| :-- | --: | :-- | --: | --: | --: | :-- |
| 0 | 140 | 2023-11-15 到 2026-05-27 | 124,772 | 64,823 | 159,237,222 | 近期主群。旅遊、人物關係、城市生活、合作與團隊內容混合。代表現階段頻道主力。 |
| 1 | 158 | 2020-02-02 到 2023-01-04 | 97,553 | 49,480 | 98,456,012 | 早期主群。旅遊、團隊生活、職涯科技、教育建議與挑戰。保留早期品牌記憶。 |
| 2 | 52 | 2023-01-11 到 2024-03-27 | 23,205 | 15,400 | 44,443,218 | 過渡/小群。倉儲、跑步、YES MAN、挑戰、部分旅遊與職涯科技。較適合作為混合題材實驗場。 |

Cluster 0 和 Cluster 1 都很大，代表 DoDoMen 的近期內容與早期內容各有穩定共同觀眾。Cluster 2 較小且 conductance 較高，表示它和其他群集的邊界不穩，內容定位可能更混合或過渡。

### 5.2 影片群集主題 affinity

| Cluster | 高 affinity 主題 | Lift | 解讀 |
| :-- | :-- | --: | :-- |
| 0 | `city_lifestyle` | 1.85 | 近期內容更常結合城市、生活與人物互動。 |
| 0 | `survival_outdoor` | 1.82 | 近期也承接戶外/生存類的高討論內容。 |
| 0 | `food_culture` | 1.40 | 飲食文化可作為 travel/guest 的輔助入口。 |
| 1 | `education_advice` | 1.94 | 早期群集保留教育、職涯、工程師敘事。 |
| 1 | `personal_team_life` | 1.34 | 團隊生活與早期品牌連結很強。 |
| 1 | `workplace_tech_career` | 1.30 | 職涯科技是早期核心記憶。 |
| 2 | `controversy_response` | 3.37 | 過渡群較容易承接爭議/反應型內容。 |
| 2 | `guest_relationship` | 1.43 | 來賓內容可把過渡群帶回主流觀眾。 |

## 6. Link Prediction 與內容企劃機會

本專案的 link prediction 不是預測演算法推薦，而是在影片 shared-audience graph 上找「目前沒有強 shared-audience edge，但結構上接近」的影片對。使用 common neighbors、Jaccard、Adamic-Adar、resource allocation 等 explainable scores。這些候選代表可嘗試的跨群集、跨主題橋接方向。

高分機會範例：

| 橋接方向 | 範例影片對 | 解讀 |
| :-- | :-- | :-- |
| `travel_exploration` + `guest_relationship` | 美國最高城市雪上活動 -> 用耳機操控博恩、賀瓏搭訕路人 | 旅遊場景加人物互動，適合把旅遊主群和來賓互動觀眾接起來。 |
| `workplace_tech_career` + `travel_exploration` | Apple Watch Ultra 2 包裝開箱 -> 旅遊飛鏢射世界地圖 | 可測試「科技/工程師視角下的旅遊挑戰」或「旅遊中的設計/科技觀察」。 |
| `other` + `workplace_tech_career` | 100 小時不吃東西 -> 全英文面試考驗 | 身體極限/挑戰和職涯壓力測試可被包裝成能力測驗或壓力實驗。 |
| `physical_challenge` + `guest_relationship` | 高難度農耕挑戰 -> 從荷蘭帶小帥哥回台灣 | 體能任務加來賓文化體驗，能同時服務 challenge 與 guest 社群。 |
| `city_lifestyle` + `workplace_tech_career` | 洛杉磯住處開箱 -> 員工旅遊垂降瀑布 | 城市生活成本、工作選擇、團隊體驗可以混合成更有討論性的企劃。 |

實務上可把 link prediction 當成 idea generator，而不是保證成功的推薦系統。更好的用法是：每月挑 2 到 3 個高分橋接方向，做小型企劃測試，發布後追蹤新留言者比例、核心留言者回流、negative rate、reply conflict score。

## 7. 情緒與風險主題

整體情緒：

| Sentiment | Comments | 占比 | Like-weighted share | 解讀 |
| :-- | --: | --: | --: | :-- |
| Negative | 22,770 | 7.51% | 5.19% | 低於 cohort 中位數，且沒有被按讚特別放大。 |
| Neutral | 136,727 | 45.1% | 34.2% | 大量中性留言，常見於資訊、補充、簡短反應。 |
| Positive | 143,597 | 47.4% | 60.6% | 高於 cohort 中位數，正向留言也更常被按讚。 |

DoDoMen 的整體留言區不是高負面環境。風險應該看主題、影片與 reply thread，而不是只看全頻道平均。

### 7.1 主題情緒

| 主題 | Comments | Negative rate | Positive rate | Like-weighted negative | 解讀 |
| :-- | --: | --: | --: | --: | :-- |
| `personal_team_life` | 55,198 | 4.29% | 63.5% | 3.72% | 團隊生活是低風險高正向主題。 |
| `physical_challenge` | 25,239 | 3.75% | 59.0% | 1.26% | 挑戰類整體健康，可作為跨社群橋接材料。 |
| `travel_exploration` | 88,627 | 7.48% | 42.8% | 4.63% | 量最大，平均風險不高，但因量大會承接最多衝突。 |
| `guest_relationship` | 39,994 | 9.34% | 52.4% | 4.76% | 人物互動正向高，但也容易有界線、真實性或合作關係質疑。 |
| `workplace_tech_career` | 36,087 | 8.81% | 41.4% | 9.66% | Raw negative 不極端，但 like-weighted negative 偏高，代表負面意見較容易被認同。 |
| `survival_outdoor` | 16,895 | 11.9% | 23.4% | 10.5% | 高風險主題，需特別說明規則、真實性與安全邊界。 |
| `city_lifestyle` | 10,999 | 11.7% | 29.1% | 4.23% | 容易引發城市、文化或價值比較討論。 |
| `product_review` | 3,827 | 17.0% | 27.7% | 12.5% | 開箱/比較容易被專業觀眾檢視，需更嚴謹。 |

### 7.2 負面熱點影片

| 影片 | 主題 | Comments | Negative rate | Like-weighted negative | Reply share | 主要風險 |
| :-- | :-- | --: | --: | --: | --: | :-- |
| 一天內用十元硬幣換到兩張機票 | travel | 1,105 | 28.4% | 49.3% | 42.2% | 企劃公平性、真實性與觀眾認同。 |
| 帶 Enzo 體驗最道地的行程 | guest | 1,533 | 34.2% | 44.6% | 39.3% | 來賓關係、文化體驗、互動界線。 |
| 美國知名大學申請分享 | workplace/tech | 818 | 13.0% | 36.0% | 42.7% | 教育與升學資訊容易被專業檢視。 |
| 倉儲職業級高手開箱合作 | workplace/tech | 1,474 | 35.9% | 31.0% | 31.1% | 企劃規則、合作設定、期待落差。 |
| 深遊台灣邦交國 | travel | 703 | 14.7% | 30.4% | 41.8% | 跨文化呈現與資訊脈絡。 |
| 終於跟 Delaney 在美國重聚 | guest | 1,558 | 20.9% | 28.2% | 34.5% | 人物關係與觀眾投射。 |
| 蘋果 vs 三星開箱包裝 | product | 2,059 | 23.4% | 27.3% | 33.9% | 產品比較與專業期待。 |

這些熱點不表示對應題材不能做。它們更像發布前 checklist：是否交代規則、是否避免誤導、合作關係是否清楚、文化呈現是否有脈絡、專業資訊是否可被檢驗。

## 8. 社群情緒差異

三個 audience communities 的情緒差異不大，但 Community 2 最高負面。

| Community | Comments | Negative rate | Positive rate | Like-weighted negative | 解讀 |
| :-- | --: | --: | --: | --: | :-- |
| 0 | 78,694 | 5.21% | 50.4% | 3.74% | 最大社群較穩定且正向，適合經營核心回流。 |
| 2 | 51,418 | 8.03% | 47.3% | 5.85% | 負面最高，且對 survival/outdoor、controversy、guest 較敏感。 |
| 1 | 32,435 | 6.62% | 51.3% | 3.75% | 小社群正向也高，人物與文化內容可作入口。 |

沒有看到某個大型社群整體高度負面。更準確的說法是：DoDoMen 有一個相對更敏感的 Community 2，當內容涉及 survival/outdoor、來賓關係、爭議或真實性時，應優先觀察這個社群在留言區的反應。

## 9. Reply Thread 與 Conflict

Reply analysis 使用 replies，不混入前面的 audience structure。原因是：觀眾社群、tiers、retention 應用 top-level comments 估計主動留言者行為；reply thread 則是另一種互動深度與衝突風險訊號。

| 指標 | DoDoMen | Benchmark context | 解讀 |
| :-- | --: | :-- | :-- |
| Replies | 57,550 | all-comments scope | 有足夠 reply 樣本可分析。 |
| Reply share of all comments | 19.0% | 第 29.2 百分位 | Reply 型互動偏少。 |
| Threads with replies | 6.49% | 第 12.5 百分位 | 很多留言是表態，不是討論串。 |
| Reply negative rate | 9.05% | 第 43.8 百分位 | Replies 並非整體高負面。 |
| Max video structural conflict score | 3.18 | 第 79.2 百分位 | 舊版 structural score，計算衝突 thread 數量與比例，但不含 reply 數或 like 權重。 |
| Max video reply-count weighted conflict score | 4.99 | 第 75.0 百分位 | 以衝突 replies 佔比加權後，單片高點仍高於多數 cohort。 |
| Max video like-weighted conflict score | 6.51 | 第 77.1 百分位 | 被按讚放大的衝突 replies 高點也偏高。 |
| Max theme conflict score | 11.77 | 第 75.0 百分位 | 主題層級風險值得追蹤。 |
| Max theme reply-count weighted conflict score | 14.64 | 第 75.0 百分位 | 主題層級的衝突 reply 佔比高點偏高。 |
| Max theme like-weighted conflict score | 17.82 | 第 77.1 百分位 | 主題層級被按讚放大的衝突高點偏高。 |

舊版 `conflict_score = n_conflict_threads * conflict_thread_rate_replied` 是 structural score；它能抓出「有多少 replied threads 呈現正負混合」，但沒有衡量這些衝突 thread 是否真的有大量 replies 或被按讚放大。因此新版 supplement 另外加入：

- `conflict_reply_share`：衝突 threads 佔該影片全部 replies 的比例。
- `like_weighted_conflict_reply_share`：衝突 threads 佔該影片 reply like weight 的比例。
- `reply_count_weighted_conflict_score = n_conflict_threads * conflict_reply_share`。
- `like_weighted_conflict_score = n_conflict_threads * like_weighted_conflict_reply_share`。

後續內容風險排序應同時看 structural score 與 weighted score；若要判斷「留言區是否真的被衝突主導」，weighted score 比舊 structural score 更重要。

### 9.1 Reply conflict 熱點影片

| 影片 | 主題 | Structural score | Like-weighted score | Conflict reply share | Like-weighted conflict share | Reply negative | 解讀 |
| :-- | :-- | --: | --: | --: | --: | --: | :-- |
| 荒島求生 Day1 | survival | 1.61 | 6.51 | 25.9% | 40.7% | 15.4% | 舊分數不最高，但衝突 replies 的 like weight 很高，代表被留言區放大。 |
| 巴拉圭人超愛台灣 | guest | 2.31 | 6.44 | 55.4% | 71.6% | 23.9% | replied threads 少，但衝突高度集中在 replies 與 like weight。 |
| 倉儲競標合作 | workplace/tech | 2.00 | 6.42 | 23.1% | 40.1% | 28.8% | 合作/競賽規則相關爭議被 replies 與按讚放大。 |
| 建中一日老師 | team/life + education | 1.68 | 5.21 | 17.4% | 30.6% | 29.6% | 不是 structural 第一名，但 weighted 後是高風險影片之一。 |
| 荷蘭小帥哥回台灣 | guest | 1.83 | 4.83 | 20.2% | 24.1% | 23.7% | 來賓/跨文化互動引發具體回覆討論。 |
| 賀瓏非洲行程 | guest | 1.81 | 4.61 | 15.4% | 18.4% | 18.8% | 大型事件式討論，衝突量和 reply 量都高。 |

### 9.2 主題 conflict

| 主題 | Replied threads | Conflict threads | Structural score | Like-weighted score | Like-weighted conflict share | 解讀 |
| :-- | --: | --: | --: | --: | --: | :-- |
| `workplace_tech_career` | 2,431 | 125 | 6.43 | 17.82 | 14.3% | Weighted 後最高，表示職涯/科技/規則型爭議較容易被按讚放大。 |
| `travel_exploration` | 4,732 | 236 | 11.77 | 17.67 | 7.49% | Structural 最高主要因量大；weighted 後仍高，但不是唯一重點。 |
| `guest_relationship` | 2,195 | 152 | 10.53 | 16.09 | 10.6% | 來賓/人物關係同時有衝突量與 weighted impact。 |
| `personal_team_life` | 2,086 | 99 | 4.70 | 10.11 | 10.2% | 團隊/生活類平均正向，但特定事件仍會被放大。 |
| `survival_outdoor` | 984 | 66 | 4.43 | 8.87 | 13.4% | 樣本較小，但 weighted conflict share 偏高。 |

DoDoMen 的 reply 問題不是「留言區吵到失控」，而是「大部分留言不展開討論，但少數高風險題材會形成集中衝突」。Weighted 修正後，應特別注意不是所有 structural top videos 都同樣重要；真正需要優先處理的是衝突 replies 佔比高、或衝突 replies 被大量按讚放大的影片。

## 10. 外部事件分析

外部事件分析把 PTT/Dcard 外部討論日期和 YouTube 留言視窗對齊。DoDoMen 目前這份 appendix 使用舊外部資料，包含 168 篇外部貼文、165 篇 relevant posts、18 個事件群、baseline 90 天、pre/post 各 28 天。

請注意：這是事件視窗關聯，不是因果。外部討論、影片主題、演算法推薦、發布節奏和社群既有情緒都可能同時影響 YouTube 留言。

較強訊號事件：

| Event | Topic | 日期 | External posts | Post comments | Delta negative vs baseline | 診斷 |
| :-- | :-- | :-- | --: | --: | --: | :-- |
| external_event_018 | staff_or_host_change | 2026-04-23 | 2 | 3,581 | +10.26 pp | 負面率明顯高於 baseline，新留言者更負面，且有 spillover 訊號。 |
| external_event_013 | content_quality_criticism | 2025-10-10 | 1 | 15,141 | +5.09 pp | PTT 內容品質批評窗口，負面反應高於 baseline。 |
| external_event_015 | content_authenticity_question | 2025-10-24 | 1 | 15,933 | +4.85 pp | 荒島真實性質疑，負面與 reply conflict 都有訊號。 |
| external_event_014 | mixed_external_discussion | 2025-10-12 | 2 | 15,492 | +4.73 pp | 負面、新觀眾進入、reply conflict、spillover 同時出現。 |
| external_event_016 | general | 2025-10-28 到 2025-10-29 | 2 | 12,619 | +4.13 pp | 荒野求生相關討論，負面高於 baseline。 |
| external_event_009 | content_quality_criticism | 2025-02-05 | 1 | 2,235 | +3.19 pp | 阿滴致敬 DoDoMen 相關討論，負面高於 baseline。 |

對頻道主的用法：不要把外部事件當成「外部貼文造成留言變差」的證據；應把它當成早期警示。如果外部討論升溫，頻道應提前準備置頂留言、社群貼文、補充 FAQ、幕後說明，避免 YouTube 留言區只由猜測和片段資訊主導。

## 11. Benchmark 指標附錄

以下保留所有 target-vs-baseline 指標，讓前面模組化分析可以回溯到可比較數值。

| # | Metric | DoDoMen | Benchmark median | Percentile | 解釋 |
| --: | :-- | --: | --: | --: | :-- |
| 1 | `n_videos_in_scope` | 351 | 162 | 79.2 | 分析影片數高於多數 cohort，統計樣本大，但總量指標會受規模影響。 |
| 2 | `top_level_comments` | 245,544 | 23,159.5 | 97.9 | 主留言量遠高於多數頻道，代表留言觸及大。 |
| 3 | `top_level_commenters` | 111,537 | 15,502 | 95.8 | 留言者母體非常大，有足夠資料做分眾與回流分析。 |
| 4 | `all_comments` | 303,094 | 37,166.5 | 97.9 | 含 replies 後仍是高樣本量，可支持情緒與 conflict 分析。 |
| 5 | `comments_per_video` | 699.6 | 164.3 | 91.7 | 單支影片平均留言數高。 |
| 6 | `commenters_per_video` | 317.8 | 90.3 | 79.2 | 平均每支影片吸引的不重複留言者偏高。 |
| 7 | `comments_per_1k_views` | 0.813 | 0.923 | 43.8 | 相對觀看量後，留言轉換率不高，這是主要改善點。 |
| 8 | `high_tier_commenter_share` | 1.11% | 0.32% | 85.4 | 高活躍留言者比例高，核心觀眾存在。 |
| 9 | `mid_tier_commenter_share` | 4.97% | 2.13% | 87.5 | 中活躍者比例高，是可轉成核心觀眾的池子。 |
| 10 | `low_tier_commenter_share` | 93.92% | 97.40% | 16.7 | 低活躍者比例低於多數頻道，表示重複參與較強。 |
| 11 | `high_mid_tier_commenter_share` | 6.08% | 2.60% | 83.3 | 中高活躍留言者合計比例高。 |
| 12 | `high_mid_tier_comment_share` | 36.1% | 18.0% | 87.5 | 少數中高活躍者貢獻大量留言，是經營資產。 |
| 13 | `continuity_return_rate_w4` | 24.8% | 14.5% | 81.3 | 跨時間窗回流高於多數頻道。 |
| 14 | `rolling_return_rate_mean` | 25.6% | 16.4% | 79.4 | Rolling 回流也偏高，非單一切窗假象。 |
| 15 | `rolling_return_rate_latest` | 30.1% | 15.6% | 91.2 | 近期回流特別高，可能與近期內容或事件相關。 |
| 16 | `commenter_network_density` | 0.00971 | 0.02739 | 19.1 | 大頻道觀眾池廣，任兩人共同留言比例偏低。 |
| 17 | `commenter_network_modularity` | 0.310 | 0.218 | 87.2 | 分群邊界清楚。 |
| 18 | `commenter_network_communities` | 3 | 5 | 8.5 | 主要社群少，結構集中。 |
| 19 | `largest_community_share` | 50.7% | 38.8% | 78.7 | 最大社群占比高。 |
| 20 | `top3_community_share` | 100.0% | 82.4% | 91.5 | 三大社群涵蓋圖上全部主要觀眾。 |
| 21 | `community_hhi` | 0.387 | 0.276 | 89.4 | 社群集中度高，需要主動橋接。 |
| 22 | `top_bridge_participation_mean` | 0.614 | 0.692 | 19.1 | 頂部橋接者跨社群程度偏低。 |
| 23 | `video_network_density` | 0.859 | 0.466 | 68.8 | 影片之間共享留言者程度高。 |
| 24 | `video_network_modularity` | 0.190 | 0.135 | 64.6 | 影片群集存在但不極端分裂。 |
| 25 | `video_network_clusters` | 3 | 3 | 60.4 | 影片可視為三個主要 shared-audience 群。 |
| 26 | `negative_rate` | 7.51% | 9.42% | 37.5 | 整體負面率低於中位數。 |
| 27 | `positive_rate` | 47.4% | 33.8% | 72.9 | 整體正向率高於中位數。 |
| 28 | `like_weighted_negative_rate` | 5.19% | 9.69% | 35.4 | 負面留言沒有被按讚顯著放大。 |
| 29 | `like_weighted_positive_rate` | 60.6% | 41.8% | 81.3 | 正向留言被按讚放大程度高。 |
| 30 | `max_video_negative_rate` | 35.9% | 40.6% | 41.7 | 最負面單片仍低於中位數。 |
| 31 | `top5_hotspot_negative_rate_mean` | 29.0% | 30.7% | 47.9 | 前五負面熱點接近但略低於中位數。 |
| 32 | `max_video_like_weighted_negative_rate` | 49.3% | 54.7% | 41.7 | 最被按讚放大的負面影片低於中位數。 |
| 33 | `max_community_negative_rate` | 8.03% | 10.7% | 38.3 | 最負面社群也不算高。 |
| 34 | `reply_share_all_comments` | 19.0% | 26.7% | 29.2 | Reply 型互動偏少。 |
| 35 | `pct_threads_with_replies` | 6.49% | 13.46% | 12.5 | 留言串展開率低，是社群深度弱點。 |
| 36 | `reply_negative_rate` | 9.05% | 10.04% | 43.8 | Replies 負面率略低於中位數。 |
| 37 | `max_video_conflict_score` | 3.18 | 1.82 | 79.2 | 少數影片的 reply conflict 偏高。 |
| 38 | `max_video_reply_count_weighted_conflict_score` | 4.99 | 2.40 | 75.0 | 以衝突 replies 佔比加權後，單片高點仍高於多數 cohort。 |
| 39 | `max_video_like_weighted_conflict_score` | 6.51 | 2.55 | 77.1 | 被按讚放大的單片 conflict 高點偏高。 |
| 40 | `max_video_conflict_thread_rate_replied` | 25.7% | 33.3% | 41.7 | 最高風險影片的衝突 thread 比例不高，但 conflict thread 數量與 weighted score 讓總風險偏高。 |
| 41 | `max_theme_conflict_score` | 11.77 | 3.03 | 75.0 | 主題層級 conflict 明顯高於中位數。 |
| 42 | `max_theme_reply_count_weighted_conflict_score` | 14.64 | 4.50 | 75.0 | 主題層級以衝突 replies 佔比加權後仍偏高。 |
| 43 | `max_theme_like_weighted_conflict_score` | 17.82 | 7.32 | 77.1 | 主題層級被按讚放大的 conflict 高點偏高。 |

## 12. 給頻道主的具體建議

1. 提高觀看轉留言效率。  
   DoDoMen 已經有大量留言，但每千觀看留言數不高。每支影片應設計一個清楚、容易回答、可被置頂延伸的留言題目，例如下一站選擇、規則投票、觀眾任務、二選一判斷。

2. 經營中高活躍留言者。  
   6.08% 中高活躍留言者貢獻 36.1% 留言。這群人適合透過社群貼文、直播 QA、企劃投票、會員內容、片尾徵集轉成穩定回流與內容共創。

3. 用混合題材橋接三個大型 audience communities。  
   優先測試 travel + guest、travel + team life、workplace/tech + travel、survival/outdoor + clear rules、physical challenge + guest。每次測試後比較新留言者、回流留言者、核心留言者占比與 sentiment。

4. 對高風險題材建立發布前 checklist。  
   Product review、survival/outdoor、跨文化、來賓關係、職涯/教育資訊、合作競賽類內容，發布前應檢查規則、資訊來源、合作界線、文化脈絡、是否容易被認為誤導。

5. 建立發布後 24 到 72 小時監控。  
   監控 `negative_rate`、`like_weighted_negative_rate`、`reply_share`、`conflict_score`、高讚負面留言與置頂留言下的反駁。這比只看總留言數更有經營價值。

6. 增加健康 reply，不只在爭議時回覆。  
   DoDoMen reply 展開率低。頻道可以主動回覆具體問題、補充資訊、整理 FAQ，讓 reply thread 成為資訊補充與社群參與，而不是只在爭議時才活躍。

7. 把外部事件當雷達，不當因果證據。  
   外部討論升溫時，提早準備資訊補充與回應節奏。目標不是反駁所有外部評論，而是避免 YouTube 留言區被不完整資訊主導。

## 13. 來源檔案

- `runs/dodomen-generic-demo/report_zh.md`
- `runs/dodomen-generic-demo/report.json`
- `runs/dodomen-generic-demo/tables/theme_summary.csv`
- `runs/dodomen-generic-demo/tables/community_profiles.csv`
- `runs/dodomen-generic-demo/tables/community_theme_affinity.csv`
- `runs/dodomen-generic-demo/tables/community_sentiment_summary.csv`
- `runs/dodomen-generic-demo/tables/video_cluster_summary.csv`
- `runs/dodomen-generic-demo/tables/video_cluster_theme_affinity.csv`
- `runs/dodomen-generic-demo/tables/video_link_opportunities.csv`
- `runs/dodomen-generic-demo/tables/sentiment_theme_summary.csv`
- `runs/dodomen-generic-demo/tables/sentiment_hotspots.csv`
- `runs/dodomen-generic-demo/tables/reply_conflict_video_summary.csv`
- `runs/dodomen-generic-demo/tables/reply_conflict_theme_summary.csv`
- `runs/dodomen-generic-demo/external_events/external_event_impact_diagnostics.csv`
- `runs/benchmark_baseline/target_metric_percentiles.csv`
- `runs/benchmark_baseline/metric_distributions.csv`
- `runs/benchmark_baseline/cohort_members.csv`
