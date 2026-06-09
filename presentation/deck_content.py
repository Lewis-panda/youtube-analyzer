# -*- coding: utf-8 -*-
# Content spec for the deck. Consumed by build_deck.render().
NAMES = "郭宜蓁　林業語　趙翊宏　鄭兆恩　趙仲文"

SLIDES = [
    {"type":"title",
     "kicker":"社群媒體分析　·　期末報告",
     "title":["從頻道表現","到留言社群洞察"],
     "sub":"台灣 YouTube 頻道的 Audience Intelligence 分析",
     "sub2":"以 The DoDo Men－嘟嘟人為例",
     "authors":NAMES},

    {"type":"content",
     "kicker":"研究動機",
     "headline":["高留言、高互動，","不等於頻道健康"],
     "bullets":[
        ("觀看、訂閱、留言數，只回答「有沒有被看見、是否成長」",""),
        ("同樣是留言增加：可能是核心粉絲，也可能是爭議、負面、外部炎上",""),
        ("高互動可能是長期社群資產，也可能是潛在聲譽風險",""),
     ],
     "foot":"延伸 vanity metrics → critical analytics（Rogers, 2018）：從表面數字轉向互動品質。"},

    {"type":"content",
     "kicker":"研究缺口",
     "headline":["現有工具回答『表現』，","少回答『誰在互動、是資產還是風險』"],
     "bullets":[
        ("Performance（YouTube Studio／Social Blade）","追蹤觀看與成長，但不分析留言者社群"),
        ("Optimization（vidIQ／TubeBuddy）","優化曝光與點擊，少觸及發布後的社群反應"),
        ("Social listening（Brandwatch 等）","以品牌／關鍵字為主，少細看單一頻道留言生態"),
     ],
     "foot":"本研究補足 YouTube-native audience intelligence：留言社群、語意主體、互動衝突。"},

    {"type":"content",
     "kicker":"研究問題",
     "headline":["四個研究問題"],
     "gap":1.0,
     "bullets":[
        ("RQ1　留言社群整體是否健康？","來自穩定核心，還是較多一次性留言者？"),
        ("RQ2　是否存在不同觀眾社群？","偏好主題、情緒反應、負面主體是否不同？"),
        ("RQ3　正負面留言針對哪些主體／面向？","內容、創作者、合作對象，還是價值觀立場？"),
        ("RQ4　哪些影片不只負面多，而是引發衝突？","reply conflict／pile-on／parent opposition"),
     ]},

    {"type":"content",
     "kicker":"資料與對象",
     "headline":["The DoDo Men ─ 嘟嘟人"],
     "stats":[("351","分析影片（排除 Shorts）"),("247k","主留言（結構口徑）"),
              ("112k","不重複留言者"),("48","benchmark 頻道")],
     "stats_x":1.05,"stats_y":2.75,
     "foot":"情緒標註涵蓋約 200 萬則留言（個案＋cohort，含回覆）；ABSA 語意主體僅針對個案頻道。"},

    {"type":"flow",
     "kicker":"分析框架",
     "headline":["從資料到策略的分析流程"],
     "stages":[
        ("資料",["YouTube 公開","留言 + metadata"]),
        ("標註",["雙模型 + 人工審核","主題·情緒·ABSA"]),
        ("分析",["頻道健康","觀眾社群","情緒/衝突"]),
        ("策略",["內容·分眾溝通","炎上監測"]),
     ],
     "foot":"分析層含頻道健康、觀眾社群、情緒／衝突風險三個模組，最終整合為可執行策略。"},

    {"type":"content",
     "kicker":"RQ1　頻道健康",
     "headline":["互動來自穩定核心，","不是一次性流量"],
     "bw":5.1,"gap":0.98,
     "bullets":[
        ("回訪率明顯高於同儕","跨影片 PR 81、近期 rolling PR 91"),
        ("不依賴一次性流量","一次性留言者占比 PR 15（越低越好）"),
        ("整體情緒健康","負面率 7.5%，低於 cohort 平均"),
     ],
     "image":"ov_engagement.png","img_x":6.55,"img_y":2.7,"img_w":6.1,"img_h":4.1},

    {"type":"content",
     "kicker":"RQ2　觀眾社群",
     "headline":["頻道不是一群粉絲，而是三個觀眾社群"],
     "image":"aud_personas.png","img_x":1.05,"img_y":2.5,"img_w":11.23,"img_h":3.85,
     "foot":"co-commenter network + Louvain 社群偵測；modularity 0.31 → 軟性偏好傾向，非鐵票派系。"},

    {"type":"content",
     "kicker":"RQ3　情緒主體（ABSA）",
     "headline":["被讚的是人與內容，","被罵的是價值觀與真實性"],
     "bw":5.1,"gap":0.98,
     "bullets":[
        ("被稱讚的點","主持人 35%、內容品質 28%"),
        ("被批評的點","價值觀／政治 28%、真實性／造假 28%"),
        ("策略意義","負面屬聲譽層級風險，非單純內容問題"),
     ],
     "image":"sent_aspect_pos.png","img_x":6.7,"img_y":2.7,"img_w":5.95,"img_h":4.1},

    {"type":"bignum",
     "kicker":"RQ3　內容敏感度（控制題材）",
     "num":"8 pp",
     "caption":"同樣看「職場科技」，挑戰冒險型負面率 14% vs 知識職涯型 5%（p < 0.001）",
     "foot":"對照：荒野求生三群負面率一致（約 10%）— 差異來自社群本身，而非主題。"},

    {"type":"content",
     "kicker":"RQ4　留言衝突",
     "headline":["負面 ≠ 衝突：","少數影片真的「吵起來」"],
     "bw":5.4,"gap":0.98,
     "bullets":[
        ("衝突看回覆串結構","圍剿、對立母串，而非單純負面率"),
        ("多為「對立母串」","回覆與母留言唱反調；一面倒圍剿較少"),
        ("需優先關注的影片","如「建中教課」圍剿 8、對立母串 16"),
     ],
     "image":"sent_conflict.png","img_x":7.25,"img_y":2.35,"img_w":5.4,"img_h":4.75},

    {"type":"columns",
     "kicker":"策略",
     "headline":["把分析轉成可執行策略"],
     "cols":[
        ("內容策略",["核心題材維持黏著","爭議題材搭配風險監控","高互動企劃系統化複製"]),
        ("分眾溝通",["知識型：清楚證據與脈絡","冒險型：透明、即時、一致回應","敏感題材預備溝通素材"]),
        ("風險監測",["按讚加權負面率","衝突／圍剿／對立母串","各社群情緒變化"]),
     ]},

    {"type":"content",
     "kicker":"研究限制",
     "headline":["研究限制"],
     "gap":0.82,
     "bullets":[
        ("分析對象為 active commenting audience","只含留言者，非全體觀眾"),
        ("共同留言 ≠ 真實社交關係","僅代表共同參與相同內容"),
        ("benchmark 為廣義 cohort","非同題材 matched，百分位僅供相對參考"),
        ("ABSA 僅針對個案頻道","未與 cohort 對照"),
        ("情緒／語意為模型標註","非人工真值，需保守解讀"),
     ]},

    {"type":"content",
     "kicker":"結論",
     "headline":["從互動數量，到互動品質"],
     "bw":10.5,"gap":0.9,
     "bullets":[
        ("RQ1　健康","互動來自穩定核心與回訪觀眾，而非一次性流量"),
        ("RQ2　社群","三個觀眾社群，內容偏好與情緒特徵各不相同"),
        ("RQ3　主體","正面指向人與內容；負面指向價值觀與真實性"),
        ("RQ4　衝突","負面 ≠ 衝突，少數影片引發實質對立"),
     ]},

    {"type":"title",
     "kicker":"",
     "title":["謝謝聆聽"],
     "sub":"Q & A",
     "sub2":"",
     "authors":NAMES},
]
