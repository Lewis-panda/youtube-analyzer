#!/usr/bin/env python3
from __future__ import annotations

from argparse import ArgumentParser
from datetime import datetime, timezone
import json
import math
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DEMO_TARGET_RUN = ROOT / "case_studies" / "dodomen" / "dodomen-generic-demo"

KEY_BASELINE_METRICS = [
    "n_videos_in_scope",
    "top_level_comments",
    "top_level_commenters",
    "all_comments",
    "comments_per_video",
    "commenters_per_video",
    "comments_per_1k_views",
    "high_mid_tier_commenter_share",
    "high_mid_tier_comment_share",
    "continuity_return_rate_w4",
    "rolling_return_rate_latest",
    "commenter_network_density",
    "commenter_network_modularity",
    "largest_community_share",
    "top3_community_share",
    "community_hhi",
    "video_network_density",
    "video_network_modularity",
    "negative_rate",
    "positive_rate",
    "like_weighted_negative_rate",
    "like_weighted_positive_rate",
    "reply_share_all_comments",
    "pct_threads_with_replies",
    "reply_negative_rate",
    "max_video_conflict_score",
    "max_video_reply_count_weighted_conflict_score",
    "max_video_like_weighted_conflict_score",
]

METRIC_LABELS = {
    "n_videos_in_scope": "分析影片數",
    "top_level_comments": "一級留言數",
    "top_level_commenters": "一級留言者數",
    "all_comments": "全部留言數",
    "comments_per_video": "每支影片留言量",
    "commenters_per_video": "每支影片留言者數",
    "comments_per_1k_views": "每千觀看留言密度",
    "high_tier_commenter_share": "高頻留言者占比",
    "mid_tier_commenter_share": "中頻留言者占比",
    "low_tier_commenter_share": "低頻留言者占比",
    "high_mid_tier_commenter_share": "核心觀眾占比",
    "high_mid_tier_comment_share": "核心觀眾留言貢獻",
    "continuity_return_rate_w4": "四週留存率",
    "rolling_return_rate_mean": "平均滾動回訪率",
    "rolling_return_rate_latest": "近期滾動回訪率",
    "commenter_network_density": "留言者網路密度",
    "commenter_network_modularity": "留言者社群分隔度",
    "commenter_network_communities": "留言者社群數",
    "largest_community_share": "最大社群占比",
    "top3_community_share": "前三大社群占比",
    "community_hhi": "社群集中度 HHI",
    "top_bridge_participation_mean": "橋接觀眾參與度",
    "video_network_density": "影片共享觀眾密度",
    "video_network_modularity": "影片共享觀眾分群度",
    "video_network_clusters": "影片分群數",
    "negative_rate": "負面留言率",
    "positive_rate": "正面留言率",
    "like_weighted_negative_rate": "按讚加權負面率",
    "like_weighted_positive_rate": "按讚加權正面率",
    "max_video_negative_rate": "單支影片最高負面率",
    "top5_hotspot_negative_rate_mean": "前五負面熱點平均負面率",
    "max_video_like_weighted_negative_rate": "單支影片最高按讚加權負面率",
    "max_community_negative_rate": "最高社群負面率",
    "reply_share_all_comments": "回覆留言占比",
    "pct_threads_with_replies": "有回覆的留言串占比",
    "reply_negative_rate": "回覆區負面率",
    "max_video_conflict_score": "單支影片最高衝突分數",
    "max_video_reply_count_weighted_conflict_score": "回覆量加權衝突峰值",
    "max_video_like_weighted_conflict_score": "按讚加權衝突峰值",
    "max_video_conflict_thread_rate_replied": "最高衝突影片回覆串占比",
    "max_theme_conflict_score": "主題最高衝突分數",
    "max_theme_reply_count_weighted_conflict_score": "主題回覆量加權衝突峰值",
    "max_theme_like_weighted_conflict_score": "主題按讚加權衝突峰值",
}

METRIC_LABELS_EN = {
    "n_videos_in_scope": "Videos in scope",
    "top_level_comments": "Top-level comments",
    "top_level_commenters": "Top-level commenters",
    "all_comments": "All comments",
    "comments_per_video": "Comments per video",
    "commenters_per_video": "Commenters per video",
    "comments_per_1k_views": "Comments per 1k views",
    "high_tier_commenter_share": "High-tier commenter share",
    "mid_tier_commenter_share": "Mid-tier commenter share",
    "low_tier_commenter_share": "Low-tier commenter share",
    "high_mid_tier_commenter_share": "Core audience share",
    "high_mid_tier_comment_share": "Core audience comment share",
    "continuity_return_rate_w4": "4-week return rate",
    "rolling_return_rate_mean": "Mean rolling return rate",
    "rolling_return_rate_latest": "Latest rolling return rate",
    "commenter_network_density": "Commenter network density",
    "commenter_network_modularity": "Commenter network modularity",
    "commenter_network_communities": "Commenter network communities",
    "largest_community_share": "Largest community share",
    "top3_community_share": "Top-3 community share",
    "community_hhi": "Community concentration HHI",
    "top_bridge_participation_mean": "Bridge participation mean",
    "video_network_density": "Shared-audience video density",
    "video_network_modularity": "Shared-audience video modularity",
    "video_network_clusters": "Shared-audience video clusters",
    "negative_rate": "Negative comment rate",
    "positive_rate": "Positive comment rate",
    "like_weighted_negative_rate": "Like-weighted negative rate",
    "like_weighted_positive_rate": "Like-weighted positive rate",
    "max_video_negative_rate": "Max video negative rate",
    "top5_hotspot_negative_rate_mean": "Mean negative rate of top 5 hotspots",
    "max_video_like_weighted_negative_rate": "Max video like-weighted negative rate",
    "max_community_negative_rate": "Max community negative rate",
    "reply_share_all_comments": "Reply share",
    "pct_threads_with_replies": "Threads with replies",
    "reply_negative_rate": "Reply negative rate",
    "max_video_conflict_score": "Max video conflict score",
    "max_video_reply_count_weighted_conflict_score": "Max reply-weighted conflict",
    "max_video_like_weighted_conflict_score": "Max like-weighted conflict",
    "max_video_conflict_thread_rate_replied": "Max conflict video replied-thread rate",
    "max_theme_conflict_score": "Max theme conflict score",
    "max_theme_reply_count_weighted_conflict_score": "Max theme reply-weighted conflict",
    "max_theme_like_weighted_conflict_score": "Max theme like-weighted conflict",
}

METRIC_GROUP_INFO = {
    "scale": {
        "label_zh": "資料規模",
        "description_zh": "描述本次分析覆蓋的影片、留言與留言者數量；主要用來判斷樣本量，不直接代表頻道健康。",
    },
    "engagement": {
        "label_zh": "互動強度",
        "description_zh": "衡量觀看量轉化成留言與參與者的能力，適合用來比較留言區是否活躍。",
    },
    "retention": {
        "label_zh": "觀眾回訪",
        "description_zh": "衡量留言者是否跨影片或跨時間回來，接近社群黏著度與固定觀眾池。",
    },
    "commenter_network": {
        "label_zh": "留言者社群結構",
        "description_zh": "描述留言者是否集中在少數社群、社群之間是否分隔，以及是否存在橋接觀眾。",
    },
    "video_network": {
        "label_zh": "影片共享觀眾結構",
        "description_zh": "衡量不同影片是否吸引相同觀眾，適合找內容系列、跨題材連結與選題機會。",
    },
    "sentiment": {
        "label_zh": "情緒氣候",
        "description_zh": "描述留言區正負向比例，以及被按讚放大的情緒方向。",
    },
    "reply_conflict": {
        "label_zh": "回覆區衝突",
        "description_zh": "描述留言串裡的回覆、負面與互動衝突是否集中在特定影片或主題。",
    },
}

METRIC_GROUPS = {
    "scale": [
        "n_videos_in_scope",
        "top_level_comments",
        "top_level_commenters",
        "all_comments",
    ],
    "engagement": [
        "comments_per_video",
        "commenters_per_video",
        "comments_per_1k_views",
    ],
    "retention": [
        "high_mid_tier_commenter_share",
        "high_mid_tier_comment_share",
        "continuity_return_rate_w4",
        "rolling_return_rate_mean",
        "rolling_return_rate_latest",
    ],
    "commenter_network": [
        "commenter_network_density",
        "commenter_network_modularity",
        "commenter_network_communities",
        "largest_community_share",
        "top3_community_share",
        "community_hhi",
        "top_bridge_participation_mean",
    ],
    "video_network": [
        "video_network_density",
        "video_network_modularity",
        "video_network_clusters",
    ],
    "sentiment": [
        "negative_rate",
        "positive_rate",
        "like_weighted_negative_rate",
        "like_weighted_positive_rate",
        "max_video_negative_rate",
        "top5_hotspot_negative_rate_mean",
        "max_video_like_weighted_negative_rate",
        "max_community_negative_rate",
    ],
    "reply_conflict": [
        "reply_share_all_comments",
        "pct_threads_with_replies",
        "reply_negative_rate",
        "max_video_conflict_score",
        "max_video_reply_count_weighted_conflict_score",
        "max_video_like_weighted_conflict_score",
        "max_video_conflict_thread_rate_replied",
        "max_theme_conflict_score",
        "max_theme_reply_count_weighted_conflict_score",
        "max_theme_like_weighted_conflict_score",
    ],
}

LEADERBOARD_METRICS = [
    ("comments_per_1k_views", "留言密度最高"),
    ("high_mid_tier_commenter_share", "核心觀眾占比最高"),
    ("continuity_return_rate_w4", "四週留存最高"),
    ("community_hhi", "社群集中度最高"),
    ("negative_rate", "負面留言率最高"),
    ("like_weighted_negative_rate", "被按讚放大的負面最高"),
    ("reply_share_all_comments", "回覆互動最深"),
    ("max_video_like_weighted_conflict_score", "衝突峰值最高"),
]

COMPOSITE_INDICES = [
    {
        "id": "engagement_conversion",
        "label_zh": "互動轉換力",
        "short_label_zh": "互動",
        "question_zh": "觀看量與影片發布能不能轉成實際留言參與？",
        "metrics": ["comments_per_1k_views", "comments_per_video", "commenters_per_video"],
        "polarity": "benefit_high",
        "high_hint_zh": "觀眾不只是觀看，也願意留下意見；適合拆解高互動影片的題材與敘事方式。",
        "low_hint_zh": "觀看與留言之間的轉換偏弱；頻道可檢查 CTA、題材討論性與留言區互動回饋。",
    },
    {
        "id": "audience_stickiness",
        "label_zh": "核心黏著度",
        "short_label_zh": "黏著",
        "question_zh": "留言區是否有穩定回來的核心觀眾，而不是每支影片都重新開始？",
        "metrics": [
            "high_mid_tier_commenter_share",
            "high_mid_tier_comment_share",
            "continuity_return_rate_w4",
            "rolling_return_rate_latest",
        ],
        "polarity": "benefit_high",
        "high_hint_zh": "固定觀眾池厚，適合做系列、社群任務或會員感經營。",
        "low_hint_zh": "留言者偏一次性，應補強系列承接、回訪誘因與留言互動節奏。",
    },
    {
        "id": "conversation_quality",
        "label_zh": "討論品質",
        "short_label_zh": "品質",
        "question_zh": "高互動是否伴隨健康情緒，而不是靠負面或衝突撐起來？",
        "metrics": ["positive_rate", "negative_rate", "like_weighted_negative_rate", "reply_negative_rate"],
        "polarity": "benefit_high",
        "invert_metrics": ["negative_rate", "like_weighted_negative_rate", "reply_negative_rate"],
        "high_hint_zh": "討論較偏正向或中性，互動品質風險較低。",
        "low_hint_zh": "負面或回覆區負面拉低品質，需要回看熱點影片與主題脈絡。",
    },
    {
        "id": "risk_pressure",
        "label_zh": "情緒風險壓力",
        "short_label_zh": "風險",
        "question_zh": "留言區是否存在被按讚放大的負面或高衝突熱點？",
        "metrics": [
            "negative_rate",
            "like_weighted_negative_rate",
            "max_video_like_weighted_negative_rate",
            "max_video_like_weighted_conflict_score",
        ],
        "polarity": "risk_high",
        "high_hint_zh": "負面或衝突有被放大的跡象，應優先查熱點影片、事件時間與回覆串。",
        "low_hint_zh": "負面與衝突壓力低於同儕，留言區風險相對可控。",
    },
    {
        "id": "community_concentration",
        "label_zh": "社群集中度",
        "short_label_zh": "集中",
        "question_zh": "留言區是否被少數社群或核心圈層主導？",
        "metrics": ["largest_community_share", "top3_community_share", "community_hhi"],
        "polarity": "mixed_high",
        "high_hint_zh": "核心圈層明顯，利於動員，但也要避免少數聲音壓縮其他觀眾。",
        "low_hint_zh": "社群分散，多元性較高，但核心凝聚與可動員性可能較弱。",
    },
    {
        "id": "content_portfolio_linkage",
        "label_zh": "內容組合連通性",
        "short_label_zh": "連通",
        "question_zh": "不同影片與題材之間是否共享觀眾，能不能做跨題材承接？",
        "metrics": ["video_network_density", "video_network_modularity", "top_bridge_participation_mean"],
        "polarity": "mixed_high",
        "high_hint_zh": "影片之間觀眾連結或分群明確，適合找系列、橋接企劃與內容缺口。",
        "low_hint_zh": "影片觀眾連結較弱，題材之間可能各自吸引不同族群。",
    },
]

ANALYSIS_LENSES = [
    {
        "id": "executive",
        "label_zh": "決策摘要",
        "question_zh": "這個頻道最值得先處理的社群問題是什麼？",
        "indices": ["engagement_conversion", "audience_stickiness", "conversation_quality", "risk_pressure"],
    },
    {
        "id": "audience",
        "label_zh": "觀眾與回訪",
        "question_zh": "留言者是廣泛加入，還是靠少數核心觀眾支撐？",
        "indices": ["engagement_conversion", "audience_stickiness", "community_concentration"],
    },
    {
        "id": "content",
        "label_zh": "內容策略",
        "question_zh": "哪些題材與影片群可以形成下一波選題或跨題材連結？",
        "indices": ["content_portfolio_linkage", "engagement_conversion", "audience_stickiness"],
    },
    {
        "id": "risk",
        "label_zh": "情緒與衝突",
        "question_zh": "負面、按讚放大與回覆衝突是否需要介入？",
        "indices": ["risk_pressure", "conversation_quality", "community_concentration"],
    },
]

METRIC_DETAIL_OVERRIDES = {
    "n_videos_in_scope": {
        "unit": "count",
        "polarity": "scale",
        "question_zh": "這次分析涵蓋多少非 Shorts 影片？",
        "high_hint_zh": "影片覆蓋量較大，結論通常較穩，但也可能混入更多不同時期的頻道策略。",
        "low_hint_zh": "影片樣本較少，極端影片比較容易影響整體判讀。",
    },
    "top_level_comments": {
        "unit": "count",
        "polarity": "scale",
        "question_zh": "主要留言樣本量有多大？",
        "high_hint_zh": "留言樣本充足，適合做分群、情緒與熱點比較。",
        "low_hint_zh": "留言樣本較少，應避免過度解讀細分主題或小社群。",
    },
    "top_level_commenters": {
        "unit": "count",
        "polarity": "scale",
        "question_zh": "有多少不同觀眾參與一級留言？",
        "high_hint_zh": "參與者基數大，代表留言區能吸引較廣泛觀眾表態。",
        "low_hint_zh": "參與者基數小，頻道互動可能集中在少數熟面孔。",
    },
    "all_comments": {
        "unit": "count",
        "polarity": "scale",
        "question_zh": "包含回覆後的總留言量是多少？",
        "high_hint_zh": "留言串互動量大，適合進一步看回覆區是否是討論或衝突來源。",
        "low_hint_zh": "回覆互動較少，reply conflict 指標的解釋力可能有限。",
    },
    "comments_per_video": {
        "unit": "per_video",
        "polarity": "benefit_high",
        "question_zh": "平均每支影片帶來多少留言？",
        "high_hint_zh": "影片通常能引發討論，適合拆解哪些主題或格式最能促進留言。",
        "low_hint_zh": "每支影片留言量偏低，可檢查題材、CTA 或社群互動設計。",
    },
    "commenters_per_video": {
        "unit": "per_video",
        "polarity": "benefit_high",
        "question_zh": "平均每支影片吸引多少不同留言者？",
        "high_hint_zh": "互動不是只靠少數人灌留言，擴散到較多觀眾。",
        "low_hint_zh": "留言區可能由少數人支撐，需確認新觀眾是否容易加入討論。",
    },
    "comments_per_1k_views": {
        "unit": "per_1k_views",
        "polarity": "benefit_high",
        "question_zh": "觀看量轉換成留言的效率如何？",
        "high_hint_zh": "觀眾更願意留下意見，代表題材有討論性或社群參與門檻低。",
        "low_hint_zh": "觀看量未有效轉成留言，可檢查影片是否偏消費型內容或缺少互動入口。",
    },
    "high_mid_tier_commenter_share": {
        "unit": "rate",
        "polarity": "benefit_high",
        "question_zh": "核心與中頻留言者占整體留言者多少？",
        "high_hint_zh": "固定觀眾池較厚，適合經營會員感、系列內容與社群任務。",
        "low_hint_zh": "留言者多半是一次性參與，應檢查回訪誘因與系列內容承接。",
    },
    "high_mid_tier_comment_share": {
        "unit": "rate",
        "polarity": "mixed_high",
        "question_zh": "核心與中頻留言者貢獻了多少留言？",
        "high_hint_zh": "核心觀眾影響力高，但也要防止留言區被少數聲音主導。",
        "low_hint_zh": "留言來源分散，利於多元參與，但核心社群黏著可能較弱。",
    },
    "continuity_return_rate_w4": {
        "unit": "rate",
        "polarity": "benefit_high",
        "question_zh": "留言者在四週視窗內回來的比例如何？",
        "high_hint_zh": "觀眾連續回訪能力強，表示頻道有較穩定的社群節奏。",
        "low_hint_zh": "回訪較弱，需檢查內容系列性、發布節奏與留言互動回饋。",
    },
    "rolling_return_rate_mean": {
        "unit": "rate",
        "polarity": "benefit_high",
        "question_zh": "長期平均回訪率如何？",
        "high_hint_zh": "平均來看留言者回訪穩定，頻道具有持續互動基礎。",
        "low_hint_zh": "平均回訪偏低，互動可能受單支熱門影片帶動而非穩定社群。",
    },
    "rolling_return_rate_latest": {
        "unit": "rate",
        "polarity": "benefit_high",
        "question_zh": "近期留言者回訪是否仍維持？",
        "high_hint_zh": "近期社群黏著度仍強，可觀察近期題材是否形成正循環。",
        "low_hint_zh": "近期回訪偏弱，可能代表題材更換、發布節奏或社群情緒改變。",
    },
    "commenter_network_density": {
        "unit": "density",
        "polarity": "mixed_high",
        "question_zh": "留言者是否常出現在相同影片中？",
        "high_hint_zh": "觀眾之間重疊高，社群感可能強，但也可能代表受眾較集中。",
        "low_hint_zh": "觀眾分散在不同影片，內容可能觸及多個族群但彼此連結弱。",
    },
    "commenter_network_modularity": {
        "unit": "score",
        "polarity": "mixed_high",
        "question_zh": "留言者社群是否分成清楚群落？",
        "high_hint_zh": "受眾分群明顯，適合辨識不同內容族群與橋接者。",
        "low_hint_zh": "留言者混合度高，代表社群較整體，也可能缺少可辨識子社群。",
    },
    "largest_community_share": {
        "unit": "rate",
        "polarity": "concentration_high",
        "question_zh": "最大留言者社群占比有多高？",
        "high_hint_zh": "最大社群主導性強，需確認是否壓縮其他觀眾族群的參與。",
        "low_hint_zh": "沒有單一社群明顯主導，留言區較分散。",
    },
    "top3_community_share": {
        "unit": "rate",
        "polarity": "concentration_high",
        "question_zh": "前三大留言者社群合計占比多高？",
        "high_hint_zh": "留言區集中在少數社群，適合經營核心圈層但要注意多元性。",
        "low_hint_zh": "社群分布較平均，需看是否因此降低核心凝聚。",
    },
    "community_hhi": {
        "unit": "score",
        "polarity": "concentration_high",
        "question_zh": "留言者社群集中程度如何？",
        "high_hint_zh": "社群集中度高，核心圈層明確，但對單一族群情緒波動較敏感。",
        "low_hint_zh": "社群較分散，抗單一群體波動較佳，但核心動員力可能較弱。",
    },
    "top_bridge_participation_mean": {
        "unit": "score",
        "polarity": "benefit_high",
        "question_zh": "橋接觀眾是否能跨社群參與？",
        "high_hint_zh": "跨圈層觀眾活躍，適合做跨題材連結與系列企劃。",
        "low_hint_zh": "橋接力量較弱，不同觀眾群可能各看各的。",
    },
    "video_network_density": {
        "unit": "density",
        "polarity": "mixed_high",
        "question_zh": "不同影片是否共享相同觀眾？",
        "high_hint_zh": "影片之間共享觀眾多，內容宇宙連續性較強。",
        "low_hint_zh": "影片之間觀眾重疊少，可能代表題材切分清楚，也可能代表系列承接弱。",
    },
    "video_network_modularity": {
        "unit": "score",
        "polarity": "mixed_high",
        "question_zh": "影片是否形成清楚的共享觀眾分群？",
        "high_hint_zh": "內容族群分明，適合用來找系列、子品牌或跨群橋接企劃。",
        "low_hint_zh": "影片觀眾混合度高，內容線可能較一致。",
    },
    "negative_rate": {
        "unit": "rate",
        "polarity": "risk_high",
        "question_zh": "留言區整體負面比例有多高？",
        "high_hint_zh": "負面氣候偏強，應回看負面熱點與引發負面主題。",
        "low_hint_zh": "整體負面比例偏低，留言區情緒風險較小。",
    },
    "positive_rate": {
        "unit": "rate",
        "polarity": "benefit_high",
        "question_zh": "留言區整體正面比例有多高？",
        "high_hint_zh": "正向回饋明顯，可拆解哪些題材或角色帶來支持。",
        "low_hint_zh": "正向回饋偏少，不一定代表負面高，也可能是中性討論較多。",
    },
    "like_weighted_negative_rate": {
        "unit": "rate",
        "polarity": "risk_high",
        "question_zh": "負面留言是否被更多按讚放大？",
        "high_hint_zh": "負面聲音不只存在，還被觀眾支持或共鳴，需優先檢查。",
        "low_hint_zh": "負面留言即使存在，也較少被按讚放大。",
    },
    "like_weighted_positive_rate": {
        "unit": "rate",
        "polarity": "benefit_high",
        "question_zh": "正面留言是否被更多按讚放大？",
        "high_hint_zh": "正向留言具有擴散與共鳴，可作為內容優勢線索。",
        "low_hint_zh": "正向留言較少被放大，需看是否缺少能讓觀眾互相認同的表述。",
    },
    "max_video_negative_rate": {
        "unit": "rate",
        "polarity": "risk_high",
        "question_zh": "是否有單支影片負面率特別高？",
        "high_hint_zh": "存在明顯負面熱點，應單獨檢查該影片題材、事件與留言脈絡。",
        "low_hint_zh": "即使在最負面的影片，負面比例也不算突出。",
    },
    "top5_hotspot_negative_rate_mean": {
        "unit": "rate",
        "polarity": "risk_high",
        "question_zh": "前五個負面熱點平均是否偏高？",
        "high_hint_zh": "負面不是單一偶發影片，可能有一組反覆出現的風險題材。",
        "low_hint_zh": "負面熱點平均不高，負面問題較可能是零星事件。",
    },
    "max_video_like_weighted_negative_rate": {
        "unit": "rate",
        "polarity": "risk_high",
        "question_zh": "是否有影片的負面留言被高度按讚放大？",
        "high_hint_zh": "特定影片中負面共鳴強，需優先看該片留言與外部事件。",
        "low_hint_zh": "最嚴重影片的負面按讚放大程度也相對低。",
    },
    "max_community_negative_rate": {
        "unit": "rate",
        "polarity": "risk_high",
        "question_zh": "是否有特定留言者社群特別負面？",
        "high_hint_zh": "負面情緒可能集中在某群觀眾，需看該社群關注題材。",
        "low_hint_zh": "各社群負面差異不明顯，風險較不像集中在單一族群。",
    },
    "reply_share_all_comments": {
        "unit": "rate",
        "polarity": "mixed_high",
        "question_zh": "回覆占全部留言多少？",
        "high_hint_zh": "留言串互動深，可能是健康討論，也可能提高衝突風險。",
        "low_hint_zh": "回覆互動較少，留言區比較像單向留言牆。",
    },
    "pct_threads_with_replies": {
        "unit": "rate",
        "polarity": "mixed_high",
        "question_zh": "多少一級留言會引發回覆？",
        "high_hint_zh": "較多留言能引發互動，需搭配 reply negative/conflict 判斷品質。",
        "low_hint_zh": "留言串互動擴展有限，社群對話性較弱。",
    },
    "reply_negative_rate": {
        "unit": "rate",
        "polarity": "risk_high",
        "question_zh": "回覆區負面比例是否偏高？",
        "high_hint_zh": "衝突或反駁可能集中在回覆區，而不是一級留言表面。",
        "low_hint_zh": "回覆區負面比例低，深層互動風險較小。",
    },
    "max_video_conflict_score": {
        "unit": "score",
        "polarity": "risk_high",
        "question_zh": "單支影片最高回覆衝突強度如何？",
        "high_hint_zh": "特定影片引發明顯回覆衝突，需看留言串結構與負面理由。",
        "low_hint_zh": "沒有明顯高衝突影片。",
    },
    "max_video_reply_count_weighted_conflict_score": {
        "unit": "score",
        "polarity": "risk_high",
        "question_zh": "回覆量加權後的影片衝突峰值如何？",
        "high_hint_zh": "衝突伴隨大量回覆，代表討論規模也大，不只是少數留言。",
        "low_hint_zh": "即使有衝突，也較少擴成大規模回覆串。",
    },
    "max_video_like_weighted_conflict_score": {
        "unit": "score",
        "polarity": "risk_high",
        "question_zh": "按讚加權後的影片衝突峰值如何？",
        "high_hint_zh": "衝突留言受到較多按讚支持，代表觀眾對立或不滿有共鳴。",
        "low_hint_zh": "衝突留言較少被按讚放大。",
    },
    "max_video_conflict_thread_rate_replied": {
        "unit": "rate",
        "polarity": "risk_high",
        "question_zh": "最高衝突影片中，有回覆的留言串比例多高？",
        "high_hint_zh": "高衝突影片中互動擴散廣，應看留言管理與回覆脈絡。",
        "low_hint_zh": "高衝突影片的回覆擴散面有限。",
    },
    "max_theme_conflict_score": {
        "unit": "score",
        "polarity": "risk_high",
        "question_zh": "是否有主題層級的高衝突？",
        "high_hint_zh": "衝突可能不是單支影片，而是與某類題材或主題長期相關。",
        "low_hint_zh": "主題層級未出現明顯衝突集中。",
    },
    "max_theme_reply_count_weighted_conflict_score": {
        "unit": "score",
        "polarity": "risk_high",
        "question_zh": "主題衝突是否伴隨大量回覆？",
        "high_hint_zh": "某類主題容易引發大規模回覆衝突，適合做題材風險標記。",
        "low_hint_zh": "主題衝突未明顯擴大成大量回覆。",
    },
    "max_theme_like_weighted_conflict_score": {
        "unit": "score",
        "polarity": "risk_high",
        "question_zh": "主題衝突是否被按讚放大？",
        "high_hint_zh": "某類主題中的衝突留言有觀眾共鳴，需謹慎解讀題材風險。",
        "low_hint_zh": "主題層級衝突較少被按讚放大。",
    },
}

STATISTICAL_PRINCIPLES = [
    "百分位是相對於目前完成的台灣 benchmark cohort；不是絕對好壞，也不是因果證明。",
    "每個比較都應同時看 cohort_n、median、IQR。樣本數太小或分布長尾時，不應只看平均值。",
    "高互動、高集中或高回覆不必然代表健康；需搭配情緒、衝突與影片主題一起判讀。",
    "負面率與衝突分數只能說明留言區表現或事件窗口關聯，不能單獨推論外部事件造成結果。",
    "影片數、留言數、留言者數屬於資料規模指標，主要用於可信度與覆蓋率，不作為頻道品質排名。",
]

DASHBOARD_TABS = [
    {
        "id": "overview",
        "title": "總覽",
        "tables": ["channel_overview", "diagnostics", "video_metrics"],
        "figures": ["channel_activity"],
    },
    {
        "id": "videos",
        "title": "影片與時間序列",
        "tables": ["video_metrics", "rolling_retention", "continuity_summary", "continuity_sensitivity"],
        "figures": ["channel_activity", "rolling_retention"],
    },
    {
        "id": "themes",
        "title": "主題與情緒",
        "tables": [
            "theme_summary",
            "sentiment_summary",
            "sentiment_theme_summary",
            "sentiment_hotspots",
            "theme_video_labels",
            "comment_aspect_summary",
            "comment_aspect_daily",
        ],
        "figures": [],
    },
    {
        "id": "community",
        "title": "社群與網路",
        "tables": [
            "commenter_tiers",
            "network_summary",
            "community_summary",
            "community_profiles",
            "bridge_actors",
            "actor_communities",
        ],
        "figures": ["commenter_tiers", "community_sizes"],
    },
    {
        "id": "video_network",
        "title": "影片共享觀眾網路",
        "tables": [
            "video_network_summary",
            "video_cluster_summary",
            "video_clusters",
            "video_network_metrics",
            "video_link_opportunities",
        ],
        "figures": ["video_cluster_sizes"],
    },
    {
        "id": "reply_conflict",
        "title": "回覆區衝突",
        "tables": [
            "reply_thread_overview",
            "reply_sentiment_summary",
            "reply_conflict_video_summary",
            "reply_conflict_theme_summary",
        ],
        "figures": [],
    },
    {
        "id": "baseline",
        "title": "基準比較",
        "tables": [],
        "figures": [],
    },
    {
        "id": "external_events",
        "title": "外部事件",
        "tables": [
            "external_event_summary",
            "external_event_windows",
            "external_event_audience_windows",
            "external_event_impact_diagnostics",
        ],
        "figures": [],
    },
    {
        "id": "cold_report",
        "title": "冷冰冰統計報告",
        "tables": [],
        "figures": [],
    },
    {
        "id": "owner_report",
        "title": "頻道主可讀報告",
        "tables": [],
        "figures": [],
    },
]


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(description="Build read-only dashboard index artifacts from completed runs.")
    parser.add_argument(
        "--runs-dir",
        type=Path,
        default=ROOT / "baseline_runs",
        help="Directory containing completed run directories.",
    )
    parser.add_argument(
        "--baseline-dir",
        type=Path,
        default=ROOT / "baseline_runs" / "benchmark_baseline",
        help="Directory containing benchmark baseline CSVs.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "dashboard_data",
        help="Directory to write dashboard JSON artifacts.",
    )
    parser.add_argument(
        "--include-run",
        action="append",
        default=[],
        help="Extra completed run directory to include, e.g. a case study. Can be repeated.",
    )
    parser.add_argument(
        "--skip-default-demo-target",
        action="store_true",
        help="Do not include the default DoDoMen case-study run in dashboard_data.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    runs_dir = args.runs_dir.expanduser().resolve()
    baseline_dir = args.baseline_dir.expanduser().resolve()
    output_dir = args.output_dir.expanduser().resolve()
    channels_dir = output_dir / "channels"
    channels_dir.mkdir(parents=True, exist_ok=True)

    baseline = load_baseline(baseline_dir)
    run_dirs = discover_run_dirs(runs_dir)
    if not args.skip_default_demo_target and DEFAULT_DEMO_TARGET_RUN.exists():
        run_dirs.append(DEFAULT_DEMO_TARGET_RUN.resolve())
    run_dirs.extend(Path(item).expanduser().resolve() for item in args.include_run)
    run_dirs = sorted(set(run_dirs), key=lambda path: path.name)

    generated_at = datetime.now(timezone.utc).isoformat()
    examples: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []

    for run_dir in run_dirs:
        try:
            channel_doc = build_channel_doc(run_dir, baseline, generated_at)
        except Exception as exc:  # Keep one broken run from hiding the whole dashboard.
            errors.append({"run_dir": display_path(run_dir), "error": str(exc)})
            continue
        channel_path = channels_dir / f"{channel_doc['slug']}.json"
        write_json(channel_path, channel_doc)
        examples.append(build_index_entry(channel_doc, channel_path))

    examples.sort(
        key=lambda item: (
            item.get("subscriber_count") is None,
            -(item.get("subscriber_count") or 0),
            item.get("title") or item.get("slug") or "",
        )
    )
    index = {
        "schema_version": 1,
        "generated_at": generated_at,
        "product_mode": "read_only_demo",
        "notes": [
            "Dashboard demo reads completed artifacts only.",
            "It must not trigger crawler, Qwen inference, or fake progress bars.",
            "DoDoMen split labels are case-study material and excluded by default.",
        ],
        "source_dirs": {
            "runs_dir": display_path(runs_dir),
            "baseline_dir": display_path(baseline_dir),
            "output_dir": display_path(output_dir),
        },
        "demo_target_slug": "dodomen-generic-demo",
        "demo_focus": {
            "slug": "dodomen-generic-demo",
            "scope_zh": "後天 demo 聚焦 DoDoMen 單一 case study；其他頻道目前只作為 broad reference 與 future work 背景。",
            "comparison_caution_zh": "目前 percentile 是相對整體台灣 benchmark cohort，尚未完成類似主題頻道的 matched cohort；因此只可作為粗略相對位置，不應包裝成同類型頻道排名。",
            "future_work_zh": "下一階段應先用輕量 metadata 建立台灣 YTR candidate pool，依題材、規模、內容型態與互動強度選出相似候選，再對 Top 20-50 做深度留言與網路分析。",
        },
        "baseline": build_baseline_summary(baseline, baseline_dir),
        "dashboard_statistics": build_index_statistics(examples, baseline),
        "n_examples": len(examples),
        "examples": examples,
        "errors": errors,
    }
    write_json(output_dir / "index.json", index)
    write_readme(output_dir, index)

    print(f"Dashboard index: {display_path(output_dir / 'index.json')}")
    print(f"Channel JSON files: {display_path(channels_dir)} ({len(examples)})")
    if errors:
        print(f"Errors: {len(errors)}")


def discover_run_dirs(runs_dir: Path) -> list[Path]:
    if not runs_dir.exists():
        return []
    out: list[Path] = []
    for path in runs_dir.iterdir():
        if not path.is_dir():
            continue
        if path.name == "benchmark_baseline":
            continue
        if (path / "report.json").exists():
            out.append(path.resolve())
    return out


def load_baseline(baseline_dir: Path) -> dict[str, pd.DataFrame]:
    paths = {
        "members": baseline_dir / "cohort_members.csv",
        "metrics": baseline_dir / "channel_metrics.csv",
        "percentiles": baseline_dir / "metric_percentiles.csv",
        "distributions": baseline_dir / "metric_distributions.csv",
        "target_percentiles": baseline_dir / "target_metric_percentiles.csv",
    }
    data: dict[str, pd.DataFrame] = {}
    for key, path in paths.items():
        data[key] = pd.read_csv(path) if path.exists() else pd.DataFrame()
    return data


def build_channel_doc(run_dir: Path, baseline: dict[str, pd.DataFrame], generated_at: str) -> dict[str, Any]:
    report_path = run_dir / "report.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    run_summary = read_json_if_exists(run_dir / "run_summary.json")
    resolved_config = read_json_if_exists(run_dir / "resolved_config.json")

    slug = run_dir.name
    channel = report.get("channel") or {}
    overview = first_row(report.get("channel_overview"))
    channel_id = str(channel.get("channel_id") or overview.get("channel_id") or "")
    title = str(channel.get("title") or overview.get("channel_title") or slug)

    tables = [
        *list_artifacts(run_dir / "tables", suffix=".csv", source_dir="tables"),
        *list_artifacts(run_dir / "external_events", suffix=".csv", source_dir="external_events"),
        *list_artifacts(run_dir / "absa", suffix=".csv", source_dir="absa"),
    ]
    figures = list_artifacts(run_dir / "figures", suffix=".png")
    reports = {
        "report_md": path_if_exists(run_dir / "report.md"),
        "report_en_md": path_if_exists(run_dir / "report_en.md"),
        "report_zh_md": path_if_exists(run_dir / "report_zh.md"),
        "report_json": path_if_exists(run_dir / "report.json"),
        "report_supplement_json": path_if_exists(run_dir / "report_supplement.json"),
    }

    baseline_doc = build_channel_baseline(channel_id, title, slug, run_dir, baseline)
    dashboard_summary = build_dashboard_summary(report)
    analysis_doc = build_channel_analysis(title, dashboard_summary, baseline_doc)
    strategy_brief = load_optional_strategy_brief(run_dir)
    if strategy_brief:
        analysis_doc["strategy_brief"] = strategy_brief
    tabs = build_tabs(run_dir, tables, figures, baseline_doc)

    return clean_json(
        {
            "schema_version": 1,
            "generated_at": generated_at,
            "slug": slug,
            "title": title,
            "channel_id": channel_id or None,
            "run_dir": display_path(run_dir),
            "source_type": "baseline_completed_run",
            "channel": summarize_channel(channel, overview),
            "overview": overview,
            "run_summary": summarize_run_summary(run_summary),
            "config": summarize_config(report.get("config") or resolved_config),
            "reports": reports,
            "artifacts": {
                "tables": tables,
                "figures": figures,
            },
            "tabs": tabs,
            "dashboard_summary": dashboard_summary,
            "baseline": baseline_doc,
            "analysis": analysis_doc,
        }
    )


def summarize_channel(channel: dict[str, Any], overview: dict[str, Any]) -> dict[str, Any]:
    return {
        "channel_id": channel.get("channel_id") or overview.get("channel_id"),
        "title": channel.get("title") or overview.get("channel_title"),
        "custom_url": channel.get("custom_url"),
        "country": channel.get("country"),
        "subscriber_count": as_number(channel.get("subscriber_count") or overview.get("subscriber_count")),
        "video_count_api": as_number(channel.get("video_count") or overview.get("channel_video_count_api")),
        "view_count_api": as_number(channel.get("view_count") or overview.get("channel_view_count_api")),
        "crawl_time": channel.get("crawl_time"),
        "date_min": overview.get("date_min"),
        "date_max": overview.get("date_max"),
        "n_videos_in_scope": as_number(overview.get("n_videos_in_scope")),
        "n_comments_in_scope": as_number(overview.get("n_comments_in_scope")),
        "n_commenters_in_scope": as_number(overview.get("n_commenters_in_scope")),
        "total_views_in_scope": as_number(overview.get("total_views_in_scope")),
    }


def summarize_config(config: Any) -> dict[str, Any]:
    if not isinstance(config, dict):
        return {}
    return {
        "project_name": config.get("project_name"),
        "channel_url": config.get("channel_url"),
        "channel_handle": config.get("channel_handle"),
        "date_start": config.get("date_start"),
        "date_end": config.get("date_end"),
        "exclude_shorts": config.get("exclude_shorts"),
        "short_threshold_seconds": config.get("short_threshold_seconds"),
        "outputs": config.get("outputs") or {},
        "external_analysis": config.get("external_analysis") or {},
    }


def summarize_run_summary(run_summary: dict[str, Any]) -> dict[str, Any]:
    if not run_summary:
        return {}
    stages = run_summary.get("stages") if isinstance(run_summary.get("stages"), list) else []
    return {
        "started_at": run_summary.get("started_at"),
        "finished_at": run_summary.get("finished_at"),
        "total_seconds": as_number(run_summary.get("total_seconds")),
        "qwen_mode": run_summary.get("qwen_mode"),
        "n_stages": len(stages),
        "stages": [
            {
                "stage": stage.get("stage"),
                "status": stage.get("status"),
                "elapsed_seconds": as_number(stage.get("elapsed_seconds")),
            }
            for stage in stages
            if isinstance(stage, dict)
        ],
    }


def build_dashboard_summary(report: dict[str, Any]) -> dict[str, Any]:
    sentiment = list_rows(report.get("sentiment_summary"), limit=5)
    sentiment_by_label = {
        str(row.get("sentiment_label")): row
        for row in sentiment
        if row.get("sentiment_label") is not None
    }
    deeper = report.get("commenter_deeper_analysis") or {}
    reply_overview = first_row(deeper.get("reply_thread_overview") if isinstance(deeper, dict) else None)
    return {
        "top_themes": list_rows(report.get("theme_summary"), limit=8),
        "sentiment_summary": sentiment,
        "negative_rate": nested_number(sentiment_by_label, "negative", "pct_comments"),
        "positive_rate": nested_number(sentiment_by_label, "positive", "pct_comments"),
        "like_weighted_negative_rate": nested_number(sentiment_by_label, "negative", "like_weighted_share"),
        "commenter_tiers": list_rows(report.get("commenter_tiers"), limit=5),
        "network_summary": first_row(report.get("network_summary")),
        "community_summary": list_rows(report.get("community_summary"), limit=8),
        "audience_segment_profiles": build_audience_segment_profiles(report),
        "audience_segment_profile_contract": audience_segment_profile_contract(),
        "video_network_summary": first_row(report.get("video_network_summary")),
        "video_clusters": list_rows(report.get("video_cluster_summary"), limit=8),
        "video_cluster_profiles": build_video_cluster_profiles(report),
        "video_cluster_explanation_contract": video_cluster_explanation_contract(),
        "negative_hotspots": list_rows(report.get("sentiment_hotspots"), limit=8),
        "reply_overview": reply_overview,
        "reply_conflict_hotspots": list_rows(
            deeper.get("reply_conflict_video_summary") if isinstance(deeper, dict) else None,
            limit=8,
        ),
    }


def audience_segment_profile_contract() -> list[dict[str, str]]:
    return [
        {
            "aspect": "群體大小",
            "meaning": "這個 segment 佔 active commenters 的比例，以及有多少留言者。",
            "source": "community_profiles.n_commenters / pct_nodes",
        },
        {
            "aspect": "活躍程度",
            "meaning": "平均每人留言次數、觸及影片數，判斷是核心型還是輕度參與型。",
            "source": "community_profiles.n_comments / n_commenters / n_videos_touched",
        },
        {
            "aspect": "偏好影片",
            "meaning": "這群觀眾最常出現在哪些影片，可反推內容吸引力。",
            "source": "community_profiles.top_comment_videos",
        },
        {
            "aspect": "常見關鍵字",
            "meaning": "理想上應由留言文字抽取；目前 dashboard 只提供 theme/title proxy，不能當成真正留言關鍵字。",
            "source": "future: comment keyword extraction over raw comments",
        },
        {
            "aspect": "主要情緒",
            "meaning": "這群觀眾的正/中/負向留言結構。",
            "source": "community_sentiment_summary",
        },
        {
            "aspect": "負面來源",
            "meaning": "哪些主題在這群觀眾中較容易產生負面或被按讚放大的負面。",
            "source": "community_theme_sentiment",
        },
        {
            "aspect": "代表留言",
            "meaning": "理想上應從 raw comments 選具代表性的中性/正面/負面留言；目前冷資料不輸出留言原文，避免誤植或隱私風險。",
            "source": "future: representative comment sampler",
        },
        {
            "aspect": "商業建議",
            "meaning": "由偏好主題、情緒與負面來源推導可嘗試的內容/合作方向。",
            "source": "derived from profile evidence; not causal proof",
        },
    ]


def video_cluster_explanation_contract() -> list[dict[str, str]]:
    return [
        {
            "source": "title / description / tags",
            "explains": "這群影片的主題、格式與內容定位。",
            "current_status": "available via qwen_video_themes / theme labels",
        },
        {
            "source": "comment keywords",
            "explains": "觀眾在這群影片下實際討論什麼。",
            "current_status": "partial only; current artifact uses theme/title proxy until raw-comment keyword extraction is added",
        },
        {
            "source": "sentiment",
            "explains": "這群影片的觀眾反應是否偏正、偏中性或偏負。",
            "current_status": "available via video_cluster_sentiment_summary",
        },
        {
            "source": "ABSA",
            "explains": "觀眾稱讚或抱怨的具體面向，例如價格、可信度、節奏、來賓、企劃設計。",
            "current_status": "missing; ternary sentiment is not enough and must not be presented as ABSA",
        },
        {
            "source": "metadata",
            "explains": "觀看數、留言數、like 數、影片長度與發布時間等表現輪廓。",
            "current_status": "partially available; current summary has views/comments/date, duration/likes need cluster aggregation",
        },
        {
            "source": "shared audience",
            "explains": "這群影片是否吸引同一批觀眾，以及是否和其他影片群有橋接關係。",
            "current_status": "available via video shared-audience graph metrics",
        },
    ]


def build_audience_segment_profiles(report: dict[str, Any]) -> list[dict[str, Any]]:
    profiles = list_rows(report.get("community_profiles"), limit=12)
    sentiments = by_key(list_rows(report.get("community_sentiment_summary"), limit=50), "community")
    theme_sentiments = group_by_key(list_rows(report.get("community_theme_sentiment"), limit=80), "community")
    affinity = group_by_key(list_rows(report.get("community_theme_affinity"), limit=80), "community")

    out = []
    for row in profiles:
        community = row.get("community")
        sentiment = sentiments.get(str(community), {})
        themes = parse_ranked_items(row.get("top_primary_themes"))
        top_videos = parse_ranked_items(row.get("top_comment_videos"))
        top_affinity = sorted(
            affinity.get(str(community), []),
            key=lambda item: (as_number(item.get("lift")) or 0, as_number(item.get("n_actor_video_pairs")) or 0),
            reverse=True,
        )[:3]
        negative_sources = top_negative_sources(theme_sentiments.get(str(community), []))
        n_commenters = as_number(row.get("n_commenters"))
        n_comments = as_number(row.get("n_comments"))
        avg_comments = (float(n_comments) / float(n_commenters)) if n_commenters else None
        keywords = segment_keywords_from_themes(themes, top_videos)
        out.append(
            clean_json(
                {
                    "community": community,
                    "segment_label": f"Audience segment {community}",
                    "group_size": {
                        "n_commenters": n_commenters,
                        "pct_active_commenters": as_number(row.get("pct_nodes")),
                        "summary_zh": f"{format_percent(row.get('pct_nodes'))} of active commenters",
                    },
                    "activity": {
                        "n_comments": n_comments,
                        "avg_comments_per_commenter": avg_comments,
                        "n_videos_touched": as_number(row.get("n_videos_touched")),
                        "summary_zh": (
                            f"平均留言 {avg_comments:.1f} 次 / 人"
                            if avg_comments is not None
                            else "缺少活躍程度資料"
                        ),
                    },
                    "preferred_videos": top_videos[:5],
                    "preferred_themes": themes[:5],
                    "over_indexed_themes": [
                        {
                            "theme": item.get("theme_label"),
                            "lift": as_number(item.get("lift")),
                            "n_commenters": as_number(item.get("n_commenters")),
                        }
                        for item in top_affinity
                    ],
                    "common_keywords": {
                        "values": keywords,
                        "source": "theme/title proxy",
                        "limitation_zh": "目前不是從留言文字直接抽出；未來應新增 comment keyword extraction。",
                    },
                    "main_sentiment": sentiment_profile(sentiment),
                    "negative_sources": negative_sources,
                    "representative_comments": {
                        "values": [],
                        "status": "missing_current_artifact",
                        "limitation_zh": "目前冷資料不輸出留言原文；未來應由 raw comments 取樣代表留言。",
                    },
                    "business_advice": business_advice_for_themes(themes, sentiment, negative_sources),
                    "evidence_fields": [
                        "community_profiles",
                        "community_theme_affinity",
                        "community_sentiment_summary",
                        "community_theme_sentiment",
                    ],
                }
            )
        )
    return out


def build_video_cluster_profiles(report: dict[str, Any]) -> list[dict[str, Any]]:
    clusters = list_rows(report.get("video_cluster_summary"), limit=12)
    sentiments = by_key(list_rows(report.get("video_cluster_sentiment_summary"), limit=50), "video_cluster")
    affinity = group_by_key(list_rows(report.get("video_cluster_theme_affinity"), limit=80), "video_cluster")

    out = []
    for row in clusters:
        cluster = row.get("video_cluster")
        sentiment = sentiments.get(str(cluster), {})
        themes = parse_ranked_items(row.get("top_theme_labels"))
        top_videos = parse_ranked_items(row.get("top_videos"))
        top_affinity = sorted(
            affinity.get(str(cluster), []),
            key=lambda item: (as_number(item.get("lift")) or 0, as_number(item.get("n_videos")) or 0),
            reverse=True,
        )[:4]
        keywords = segment_keywords_from_themes(themes, top_videos)
        metadata_evidence = (
            f"{format_number(row.get('n_videos'))} 支影片；"
            f"{format_number(row.get('total_views'))} views；"
            f"{format_number(row.get('total_observed_comments'))} observed comments；"
            f"{format_number(row.get('unique_commenters'))} unique commenters"
        )
        shared_evidence = (
            f"internal_edges={format_number(row.get('internal_edges'))}, "
            f"external_edges={format_number(row.get('external_edges'))}, "
            f"conductance={format_decimal(row.get('conductance'))}"
        )
        out.append(
            clean_json(
                {
                    "video_cluster": cluster,
                    "cluster_label": f"Video cluster {cluster}",
                    "size": {
                        "n_videos": as_number(row.get("n_videos")),
                        "date_min": row.get("date_min"),
                        "date_max": row.get("date_max"),
                        "pct_graph_videos": as_number(row.get("pct_graph_videos")),
                    },
                    "topic_from_title_description_tags": {
                        "top_themes": themes[:5],
                        "over_indexed_themes": [
                            {
                                "theme": item.get("theme_label"),
                                "lift": as_number(item.get("lift")),
                                "n_videos": as_number(item.get("n_videos")),
                            }
                            for item in top_affinity
                        ],
                        "top_videos": top_videos[:5],
                    },
                    "comment_keywords": {
                        "values": keywords,
                        "source": "theme/title proxy",
                        "limitation_zh": "目前不是從留言文字直接抽出；未來要補 comment keyword table 才能回答觀眾實際討論什麼。",
                    },
                    "sentiment": sentiment_profile(sentiment),
                    "absa": {
                        "status": "missing_current_pipeline",
                        "limitation_zh": "目前 Qwen comment sentiment 是三元情緒，沒有 aspect-based sentiment；不能宣稱已知道觀眾稱讚/抱怨哪些具體面向。",
                    },
                    "metadata": {
                        "total_views": as_number(row.get("total_views")),
                        "total_observed_comments": as_number(row.get("total_observed_comments")),
                        "unique_commenters": as_number(row.get("unique_commenters")),
                        "median_observed_commenters": as_number(row.get("median_observed_commenters")),
                        "evidence_zh": metadata_evidence,
                    },
                    "shared_audience": {
                        "internal_edges": as_number(row.get("internal_edges")),
                        "external_edges": as_number(row.get("external_edges")),
                        "conductance": as_number(row.get("conductance")),
                        "interpretation_zh": shared_audience_interpretation(row),
                        "evidence_zh": shared_evidence,
                    },
                    "explanation_sources": [
                        {
                            "source": "title / description / tags",
                            "available": True,
                            "explains": "這群影片的主題。",
                            "evidence_zh": row.get("top_theme_labels"),
                        },
                        {
                            "source": "comment keywords",
                            "available": False,
                            "explains": "觀眾在這群影片下討論什麼。",
                            "evidence_zh": "目前只有 theme/title proxy。",
                        },
                        {
                            "source": "sentiment",
                            "available": bool(sentiment),
                            "explains": "這群影片的觀眾反應好不好。",
                            "evidence_zh": (sentiment_profile(sentiment) or {}).get("summary_zh"),
                        },
                        {
                            "source": "ABSA",
                            "available": False,
                            "explains": "觀眾稱讚 / 抱怨哪些面向。",
                            "evidence_zh": "目前 pipeline 尚未輸出。",
                        },
                        {
                            "source": "metadata",
                            "available": True,
                            "explains": "觀看數、留言數、like 數、影片長度與發布時間。",
                            "evidence_zh": metadata_evidence,
                        },
                        {
                            "source": "shared audience",
                            "available": True,
                            "explains": "這群影片吸引哪些共同觀眾與跨群連結程度。",
                            "evidence_zh": shared_evidence,
                        },
                    ],
                    "business_read": business_advice_for_themes(themes, sentiment, []),
                }
            )
        )
    return out


def by_key(rows: list[dict[str, Any]], key: str) -> dict[str, dict[str, Any]]:
    return {str(row.get(key)): row for row in rows if row.get(key) is not None}


def group_by_key(rows: list[dict[str, Any]], key: str) -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        value = row.get(key)
        if value is None:
            continue
        out.setdefault(str(value), []).append(row)
    return out


def parse_ranked_items(value: Any) -> list[dict[str, Any]]:
    text = str(value or "").strip()
    if not text:
        return []
    out = []
    for raw in text.split(";"):
        item = raw.strip()
        if not item:
            continue
        label = item
        count = None
        if item.endswith(")") and "(" in item:
            label, suffix = item.rsplit("(", 1)
            label = label.strip()
            count = as_number(suffix.rstrip(")").replace(",", ""))
        out.append({"label": label, "count": count})
    return out


THEME_KEYWORDS_ZH = {
    "travel_exploration": ["旅遊", "目的地", "探索", "在地體驗"],
    "personal_team_life": ["團隊", "近況", "生日", "生活"],
    "guest_relationship": ["來賓", "合作", "外國人", "跨圈層"],
    "physical_challenge": ["挑戰", "體能", "極限", "任務"],
    "survival_outdoor": ["戶外", "求生", "荒島", "挑戰"],
    "workplace_tech_career": ["職涯", "科技", "矽谷", "工作"],
    "education_advice": ["知識", "教學", "建議", "解釋"],
    "food_culture": ["美食", "文化", "夜市", "在地"],
    "city_lifestyle": ["城市", "街訪", "生活風格", "台灣"],
    "business_brand": ["品牌", "業配", "商業", "合作"],
    "automotive_luxury": ["車", "精品", "生活風格", "高價產品"],
    "controversy_response": ["爭議", "回應", "澄清", "輿論"],
}


def segment_keywords_from_themes(
    themes: list[dict[str, Any]], top_videos: list[dict[str, Any]]
) -> list[str]:
    out: list[str] = []
    for item in themes[:4]:
        label = str(item.get("label") or "")
        mapped = THEME_KEYWORDS_ZH.get(label)
        if mapped:
            out.extend(mapped[:3])
        elif label and label != "other":
            out.append(label)
    title_text = " ".join(str(item.get("label") or "") for item in top_videos[:3])
    for token in ["比較", "開箱", "實測", "挑戰", "旅遊", "外國人", "分開", "工程師", "荒島", "生日"]:
        if token in title_text:
            out.append(token)
    seen = set()
    deduped = []
    for item in out:
        if item in seen:
            continue
        seen.add(item)
        deduped.append(item)
    return deduped[:8]


def sentiment_profile(row: dict[str, Any]) -> dict[str, Any]:
    if not row:
        return {}
    neg = as_number(row.get("negative_rate"))
    neu = as_number(row.get("neutral_rate"))
    pos = as_number(row.get("positive_rate"))
    weighted_neg = as_number(row.get("like_weighted_negative_rate"))
    weighted_pos = as_number(row.get("like_weighted_positive_rate"))
    values = {"negative": neg, "neutral": neu, "positive": pos}
    dominant = max(
        ((key, value) for key, value in values.items() if value is not None),
        key=lambda item: item[1],
        default=("unknown", None),
    )[0]
    if dominant == "positive" and (neg or 0) < 0.1:
        label = "中性偏正，正向討論較多"
    elif dominant == "positive":
        label = "正向為主，但仍需看負面來源"
    elif dominant == "neutral":
        label = "中性討論為主"
    elif dominant == "negative":
        label = "負面討論偏高"
    else:
        label = "缺少情緒資料"
    return {
        "dominant": dominant,
        "negative_rate": neg,
        "neutral_rate": neu,
        "positive_rate": pos,
        "like_weighted_negative_rate": weighted_neg,
        "like_weighted_positive_rate": weighted_pos,
        "summary_zh": (
            f"{label}；負面 {format_percent_rate(neg)}，正面 {format_percent_rate(pos)}，"
            f"按讚加權負面 {format_percent_rate(weighted_neg)}"
        ),
    }


def top_negative_sources(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    candidates = []
    for row in rows:
        n_comments = as_number(row.get("n_comments")) or 0
        if n_comments < 50:
            continue
        score = as_number(row.get("like_weighted_negative_rate"))
        if score is None:
            score = as_number(row.get("negative_rate")) or 0
        candidates.append((score, n_comments, row))
    candidates.sort(reverse=True, key=lambda item: (item[0], item[1]))
    out = []
    for _, _, row in candidates[:3]:
        out.append(
            {
                "theme": row.get("primary_theme"),
                "negative_rate": as_number(row.get("negative_rate")),
                "like_weighted_negative_rate": as_number(row.get("like_weighted_negative_rate")),
                "n_comments": as_number(row.get("n_comments")),
                "summary_zh": (
                    f"{row.get('primary_theme')}：負面 {format_percent_rate(row.get('negative_rate'))}，"
                    f"按讚加權負面 {format_percent_rate(row.get('like_weighted_negative_rate'))}"
                ),
            }
        )
    return out


def business_advice_for_themes(
    themes: list[dict[str, Any]], sentiment: dict[str, Any], negative_sources: list[dict[str, Any]]
) -> str:
    labels = [str(item.get("label") or "") for item in themes[:3]]
    label_set = set(labels)
    if "travel_exploration" in label_set:
        base = "適合目的地合作、行程設計、體驗型業配與系列企劃。"
    elif "workplace_tech_career" in label_set or "education_advice" in label_set:
        base = "適合產品教育、比較型內容、職涯/知識型合作與高資訊密度腳本。"
    elif "guest_relationship" in label_set:
        base = "適合跨圈層來賓合作、人物故事與互相導流的聯名企劃。"
    elif "physical_challenge" in label_set or "survival_outdoor" in label_set:
        base = "適合挑戰型企劃、戶外品牌合作與高記憶點系列內容。"
    elif "food_culture" in label_set:
        base = "適合餐飲、城市體驗、在地文化與消費導購合作。"
    else:
        base = "適合把高偏好主題整理成系列內容，並用留言反應檢查可複製性。"
    if negative_sources:
        return base + " 但需先檢查負面來源主題，避免合作訊息被價格、可信度或敘事爭議稀釋。"
    profile = sentiment_profile(sentiment)
    if profile.get("dominant") == "positive":
        return base + " 此 segment 情緒偏正，可優先測試轉換型 CTA。"
    return base


def shared_audience_interpretation(row: dict[str, Any]) -> str:
    conductance = as_number(row.get("conductance"))
    if conductance is None:
        return "缺少 shared-audience conductance。"
    if conductance < 0.4:
        return "群內共享觀眾相對緊密，適合作為系列內容或同題材延伸。"
    if conductance < 0.7:
        return "群內外都有共享觀眾，可檢查跨主題橋接企劃。"
    return "群集邊界較鬆散，可能是過渡型內容或與其他題材高度混合。"


def format_number(value: Any) -> str:
    number = as_number(value)
    if number is None:
        return "-"
    return f"{number:,.0f}"


def format_decimal(value: Any) -> str:
    number = as_number(value)
    if number is None:
        return "-"
    return f"{number:.3f}"


def format_percent(value: Any) -> str:
    number = as_number(value)
    if number is None:
        return "-"
    return f"{number:.1f}%"


def format_percent_rate(value: Any) -> str:
    number = as_number(value)
    if number is None:
        return "-"
    return f"{number * 100:.1f}%" if abs(number) <= 1 else f"{number:.1f}%"


def build_channel_baseline(
    channel_id: str,
    title: str,
    slug: str,
    run_dir: Path,
    baseline: dict[str, pd.DataFrame],
) -> dict[str, Any]:
    metrics = baseline.get("metrics", pd.DataFrame())
    percentiles = baseline.get("percentiles", pd.DataFrame())
    target_percentiles = baseline.get("target_percentiles", pd.DataFrame())
    distributions = baseline.get("distributions", pd.DataFrame())
    members = baseline.get("members", pd.DataFrame())

    metric_row = find_channel_row(metrics, channel_id, title, slug, run_dir)
    member_row = find_channel_row(members, channel_id, title, slug, run_dir)
    percentile_rows = find_percentile_rows(percentiles, channel_id, title, slug, run_dir)
    comparison_source = "baseline_member_percentiles"
    if percentile_rows.empty and not target_percentiles.empty:
        percentile_rows = normalize_target_percentile_rows(
            find_percentile_rows(target_percentiles, channel_id, title, slug, run_dir)
        )
        if not percentile_rows.empty:
            comparison_source = "target_vs_broad_benchmark"

    distribution_by_metric = {
        str(row["metric"]): row.to_dict()
        for _, row in distributions.iterrows()
        if "metric" in distributions.columns and pd.notna(row.get("metric"))
    }

    key_metrics: list[dict[str, Any]] = []
    all_metrics: list[dict[str, Any]] = []
    if not percentile_rows.empty:
        percentile_rows = percentile_rows.assign(
            _sort_key=percentile_rows["metric"].astype(str).map(metric_sort_key)
        ).sort_values("_sort_key")
        for _, row in percentile_rows.iterrows():
            metric = str(row.get("metric"))
            distribution = compact_distribution(distribution_by_metric.get(metric, {}))
            value = as_number(row.get("value"))
            percentile = as_number(row.get("percentile"))
            cohort_n = as_number(row.get("n_cohort"))
            meta = metric_metadata(metric)
            item = {
                "metric": metric,
                "label": meta["label_zh"],
                "label_en": meta["label_en"],
                "group": meta["group"],
                "group_label": meta["group_label_zh"],
                "unit": meta["unit"],
                "polarity": meta["polarity"],
                "value": value,
                "percentile": percentile,
                "percentile_band": percentile_band(percentile),
                "n_cohort": cohort_n,
                "cohort_n": cohort_n,
                "distribution": distribution,
                "comparison": metric_comparison(metric, value, percentile, distribution),
                "interpretation_hint_zh": owner_hint(metric, percentile),
                "risk_opportunity_label": metric_risk_opportunity_label(metric, percentile),
                "statistical_caution_zh": metric_caution(metric),
            }
            all_metrics.append(item)
            if metric in KEY_BASELINE_METRICS:
                key_metrics.append(item)

    return clean_json(
        {
            "is_baseline_member": not metric_row.empty,
            "membership": first_df_row(member_row),
            "comparison_source": comparison_source,
            "comparison_caution_zh": (
                "此比較使用整體台灣 benchmark cohort，不是相似題材 matched cohort；適合 demo 粗略定位，不應視為同類型頻道排名。"
                if comparison_source == "target_vs_broad_benchmark"
                else "此頻道在 baseline cohort 內，百分位表示相對目前完成 cohort 的位置。"
            ),
            "key_metrics": key_metrics,
            "all_metrics": all_metrics,
            "n_metrics": len(all_metrics),
            "percentile_takeaways": build_percentile_takeaways(key_metrics),
            "risk_opportunity_summary": build_risk_opportunity_summary(key_metrics),
        }
    )


def load_optional_strategy_brief(run_dir: Path) -> dict[str, Any] | None:
    """Optional per-run authored strategy brief.

    If ``run_dir/strategy_brief_zh.json`` exists it is merged into the channel
    ``analysis`` doc as ``strategy_brief``. This lets a completed run ship an
    interpreted, source-cited owner strategy without hard-coding channel
    specifics into the generic builder. Returns ``None`` when absent or invalid.
    """
    brief = read_json_if_exists(run_dir / "strategy_brief_zh.json")
    items = brief.get("items") if isinstance(brief, dict) else None
    if not isinstance(items, list) or not items:
        return None
    return clean_json(brief)


def build_channel_analysis(
    title: str,
    dashboard_summary: dict[str, Any],
    baseline_doc: dict[str, Any],
) -> dict[str, Any]:
    metrics = {
        str(item.get("metric")): item
        for item in baseline_doc.get("all_metrics", [])
        if item.get("metric")
    }
    indices = [build_composite_index(spec, metrics) for spec in COMPOSITE_INDICES]
    indices = [item for item in indices if item]
    index_by_id = {item["id"]: item for item in indices}
    story_cards = build_story_cards(title, dashboard_summary, baseline_doc, index_by_id)
    return clean_json(
        {
            "interface_version": 2,
            "purpose_zh": "把完成的頻道 artifact 轉成頻道主能快速理解的社群健康、內容策略與風險判讀。",
            "archetype": infer_channel_archetype(index_by_id),
            "indices": indices,
            "lenses": build_analysis_lenses(index_by_id, metrics),
            "story_cards": story_cards,
            "decision_queue": build_decision_queue(story_cards),
            "benchmark_maps": build_benchmark_maps(metrics, index_by_id),
            "method_notes_zh": [
                "Composite index 使用 component metrics 的 benchmark percentile 平均；沒有新增未觀測資料。",
                "risk 類 index 越高代表壓力越大；quality 類 index 已把負面/衝突 component 反向後再合成。",
                "所有判讀都是相對目前 48 個 ready benchmark channel，不是因果推論。",
            ],
        }
    )


def build_composite_index(spec: dict[str, Any], metrics: dict[str, dict[str, Any]]) -> dict[str, Any]:
    components = []
    invert_metrics = set(spec.get("invert_metrics") or [])
    for metric in spec.get("metrics", []):
        item = metrics.get(metric)
        if not item:
            continue
        percentile = as_number(item.get("percentile"))
        if percentile is None:
            continue
        contribution = 100 - percentile if metric in invert_metrics else percentile
        components.append(
            {
                "metric": metric,
                "label": item.get("label") or METRIC_LABELS.get(metric, metric),
                "value": item.get("value"),
                "percentile": percentile,
                "contribution": contribution,
                "direction": "inverted" if metric in invert_metrics else "direct",
                "hint_zh": item.get("interpretation_hint_zh"),
            }
        )
    if not components:
        return {}
    score = sum(float(item["contribution"]) for item in components) / len(components)
    return {
        "id": spec["id"],
        "label": spec["label_zh"],
        "short_label": spec["short_label_zh"],
        "question_zh": spec["question_zh"],
        "score": score,
        "band": score_band(score, spec.get("polarity")),
        "polarity": spec.get("polarity"),
        "interpretation_zh": composite_hint(spec, score),
        "components": components,
    }


def score_band(score: float | int | None, polarity: str | None = None) -> str:
    value = as_number(score)
    if value is None:
        return "未知"
    if value >= 80:
        return "非常高"
    if value >= 65:
        return "偏高"
    if value >= 40:
        return "中段"
    if value >= 25:
        return "偏低"
    return "非常低"


def composite_hint(spec: dict[str, Any], score: float | int | None) -> str:
    value = as_number(score)
    if value is None:
        return "缺少足夠 component metrics。"
    if value >= 65:
        return str(spec.get("high_hint_zh") or "")
    if value <= 35:
        return str(spec.get("low_hint_zh") or "")
    return "位於同儕中段，建議從 component metrics 與影片/主題細節找具體原因。"


def infer_channel_archetype(indices: dict[str, dict[str, Any]]) -> dict[str, Any]:
    engagement = index_score(indices, "engagement_conversion")
    stickiness = index_score(indices, "audience_stickiness")
    quality = index_score(indices, "conversation_quality")
    risk = index_score(indices, "risk_pressure")
    concentration = index_score(indices, "community_concentration")
    linkage = index_score(indices, "content_portfolio_linkage")

    if engagement >= 65 and risk >= 65:
        label = "高互動高風險型"
        summary = "留言區很能引發討論，但負面或衝突也容易被放大；管理重點是把討論能量導向可控議題。"
    elif engagement >= 65 and stickiness >= 60 and risk < 60:
        label = "穩定討論引擎型"
        summary = "互動與回訪都強，且風險壓力未明顯偏高；適合擴大系列內容與核心觀眾經營。"
    elif stickiness >= 65 and concentration >= 65:
        label = "核心圈層驅動型"
        summary = "固定觀眾與集中社群明顯；優勢是凝聚力，風險是留言區可能被少數族群主導。"
    elif linkage >= 65 and engagement >= 50:
        label = "內容組合可擴張型"
        summary = "影片之間存在可利用的共享觀眾結構；適合找跨題材連結、系列企劃與內容缺口。"
    elif quality >= 65 and engagement < 45:
        label = "低噪音潛力型"
        summary = "留言氣候相對健康，但互動轉換不足；重點是提升留言入口與題材討論性。"
    elif engagement < 40 and stickiness < 40:
        label = "低參與待啟動型"
        summary = "留言互動與回訪都偏弱；應先檢查內容系列、社群互動節奏與觀眾加入門檻。"
    else:
        label = "均衡觀察型"
        summary = "多數指標落在同儕中段；需要透過影片熱點、主題與時間序列找具體突破口。"

    return {
        "label_zh": label,
        "summary_zh": summary,
        "scores": {
            "engagement_conversion": engagement,
            "audience_stickiness": stickiness,
            "conversation_quality": quality,
            "risk_pressure": risk,
            "community_concentration": concentration,
            "content_portfolio_linkage": linkage,
        },
    }


def build_story_cards(
    title: str,
    dashboard_summary: dict[str, Any],
    baseline_doc: dict[str, Any],
    indices: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    cards = []
    cards.extend(story_cards_from_indices(indices))
    for row in baseline_doc.get("percentile_takeaways", [])[:6]:
        cards.append(
            {
                "id": f"metric_{row.get('metric')}",
                "kind": row.get("risk_opportunity_label") or "context",
                "priority": story_priority(row.get("risk_opportunity_label"), row.get("percentile")),
                "title_zh": row.get("headline_zh"),
                "body_zh": row.get("interpretation_hint_zh"),
                "evidence_zh": f"{row.get('label')}：{format_metric_value(row.get('value'), row.get('metric'))}，PR {as_number(row.get('percentile')):.1f}",
                "metrics": [row.get("metric")],
                "next_step_zh": next_step_for_metric(str(row.get("metric") or "")),
            }
        )
    hotspot = first_hotspot(dashboard_summary)
    if hotspot:
        cards.append(hotspot)
    cards = [card for card in cards if card.get("title_zh")]
    cards.sort(key=lambda item: item.get("priority", 50), reverse=True)
    return cards[:9]


def story_cards_from_indices(indices: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    risk = indices.get("risk_pressure")
    engagement = indices.get("engagement_conversion")
    stickiness = indices.get("audience_stickiness")
    quality = indices.get("conversation_quality")
    linkage = indices.get("content_portfolio_linkage")
    if risk and (risk.get("score") or 0) >= 65:
        out.append(
            {
                "id": "risk_pressure",
                "kind": "risk",
                "priority": 95,
                "title_zh": "先處理被放大的負面與衝突",
                "body_zh": risk.get("interpretation_zh"),
                "evidence_zh": f"情緒風險壓力 {as_number(risk.get('score')):.1f}/100",
                "metrics": [item["metric"] for item in risk.get("components", [])],
                "next_step_zh": "先看情緒與衝突頁，找出負面/衝突最高的影片與主題。",
            }
        )
    if engagement and (engagement.get("score") or 0) >= 65:
        out.append(
            {
                "id": "engagement_conversion",
                "kind": "opportunity",
                "priority": 88,
                "title_zh": "高互動不是偶然，應拆解可複製題材",
                "body_zh": engagement.get("interpretation_zh"),
                "evidence_zh": f"互動轉換力 {as_number(engagement.get('score')):.1f}/100",
                "metrics": [item["metric"] for item in engagement.get("components", [])],
                "next_step_zh": "切到內容策略頁，對照高留言影片、主題與共享觀眾群。",
            }
        )
    if stickiness and (stickiness.get("score") or 0) >= 65:
        out.append(
            {
                "id": "audience_stickiness",
                "kind": "opportunity",
                "priority": 82,
                "title_zh": "核心觀眾可被系統化經營",
                "body_zh": stickiness.get("interpretation_zh"),
                "evidence_zh": f"核心黏著度 {as_number(stickiness.get('score')):.1f}/100",
                "metrics": [item["metric"] for item in stickiness.get("components", [])],
                "next_step_zh": "檢查哪些主題讓核心觀眾跨影片回來，作為系列內容候選。",
            }
        )
    if quality and (quality.get("score") or 0) <= 35:
        out.append(
            {
                "id": "conversation_quality",
                "kind": "risk",
                "priority": 80,
                "title_zh": "互動品質低於同儕，需要分辨負面來源",
                "body_zh": quality.get("interpretation_zh"),
                "evidence_zh": f"討論品質 {as_number(quality.get('score')):.1f}/100",
                "metrics": [item["metric"] for item in quality.get("components", [])],
                "next_step_zh": "看情緒分布與負面熱點，分辨是單支影片、主題或整體語氣問題。",
            }
        )
    if linkage and (linkage.get("score") or 0) >= 65:
        out.append(
            {
                "id": "content_portfolio_linkage",
                "kind": "opportunity",
                "priority": 76,
                "title_zh": "影片共享觀眾結構可用來想新企劃",
                "body_zh": linkage.get("interpretation_zh"),
                "evidence_zh": f"內容組合連通性 {as_number(linkage.get('score')):.1f}/100",
                "metrics": [item["metric"] for item in linkage.get("components", [])],
                "next_step_zh": "看影片共享觀眾網路與 link opportunities，找相近但尚未連接的題材。",
            }
        )
    return out


def build_analysis_lenses(
    indices: dict[str, dict[str, Any]], metrics: dict[str, dict[str, Any]]
) -> list[dict[str, Any]]:
    out = []
    for lens in ANALYSIS_LENSES:
        lens_indices = [indices[item] for item in lens["indices"] if item in indices]
        related_metrics = []
        for item in lens_indices:
            related_metrics.extend(component.get("metric") for component in item.get("components", []))
        metric_rows = [metrics[name] for name in dict.fromkeys(related_metrics) if name in metrics]
        out.append(
            {
                "id": lens["id"],
                "label": lens["label_zh"],
                "question_zh": lens["question_zh"],
                "indices": lens_indices,
                "metrics": metric_rows[:10],
                "read_order_zh": "先看 composite score，再看 component percentile，最後鑽到影片/主題表。",
            }
        )
    return out


def build_decision_queue(cards: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for idx, card in enumerate(cards[:5], start=1):
        out.append(
            {
                "rank": idx,
                "kind": card.get("kind"),
                "title_zh": card.get("title_zh"),
                "why_zh": card.get("body_zh"),
                "evidence_zh": card.get("evidence_zh"),
                "next_step_zh": card.get("next_step_zh"),
            }
        )
    return out


def build_benchmark_maps(
    metrics: dict[str, dict[str, Any]], indices: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    return {
        "engagement_vs_risk": {
            "x": "engagement_conversion",
            "y": "risk_pressure",
            "x_label_zh": "互動轉換力",
            "y_label_zh": "情緒風險壓力",
            "selected": {
                "x": index_score(indices, "engagement_conversion"),
                "y": index_score(indices, "risk_pressure"),
            },
            "quadrant_hints_zh": {
                "high_x_high_y": "高互動但高風險：先做留言與主題風險控管。",
                "high_x_low_y": "高互動且低風險：可擴大成功題材。",
                "low_x_high_y": "低互動但高風險：少數負面可能主導觀感。",
                "low_x_low_y": "低互動低風險：先提高討論入口。",
            },
        },
        "stickiness_vs_concentration": {
            "x": "audience_stickiness",
            "y": "community_concentration",
            "x_label_zh": "核心黏著度",
            "y_label_zh": "社群集中度",
            "selected": {
                "x": index_score(indices, "audience_stickiness"),
                "y": index_score(indices, "community_concentration"),
            },
        },
    }


def first_hotspot(dashboard_summary: dict[str, Any]) -> dict[str, Any] | None:
    hotspots = dashboard_summary.get("negative_hotspots") or []
    if not hotspots:
        return None
    row = hotspots[0]
    title = row.get("title")
    neg = as_number(row.get("negative_rate"))
    if not title or neg is None:
        return None
    return {
        "id": "top_negative_hotspot",
        "kind": "risk",
        "priority": 72,
        "title_zh": "最負面影片需要單獨檢查",
        "body_zh": "整體平均會稀釋單支影片的風險；最高負面影片常是事件、題材或敘事轉折的線索。",
        "evidence_zh": f"{title}，負面率 {neg * 100:.1f}%",
        "metrics": ["negative_rate", "max_video_negative_rate"],
        "next_step_zh": "在情緒與衝突頁檢查該影片是否同時有按讚加權負面或高回覆衝突。",
    }


def index_score(indices: dict[str, dict[str, Any]], key: str) -> float:
    return float(as_number((indices.get(key) or {}).get("score")) or 0)


def story_priority(kind: Any, percentile: Any) -> float:
    pct = as_number(percentile) or 50
    base = abs(pct - 50)
    if kind == "risk":
        return 70 + base
    if kind == "opportunity":
        return 64 + base
    if kind == "watch":
        return 58 + base
    return 40 + base


def next_step_for_metric(metric: str) -> str:
    group = metric_group(metric)
    if group == "sentiment" or group == "reply_conflict":
        return "切到情緒與衝突頁，查看熱點影片、回覆串與按讚加權負面。"
    if group == "retention":
        return "切到觀眾與回訪視角，確認核心觀眾是否集中在特定主題或系列。"
    if group == "video_network":
        return "切到內容策略頁，查看共享觀眾分群與可連結的影片組合。"
    if group == "commenter_network":
        return "切到社群網路頁，檢查最大社群、橋接觀眾與集中度。"
    return "先看同儕比較，再鑽到影片與主題細表確認來源。"


def format_metric_value(value: Any, metric: str | None = None) -> str:
    number = as_number(value)
    if number is None:
        return "-"
    if metric and infer_metric_unit(metric) in {"rate", "density"}:
        return f"{number * 100:.1f}%" if abs(number) <= 1 else f"{number:.1f}%"
    if abs(number) >= 1000:
        return f"{number:,.0f}"
    if float(number).is_integer():
        return f"{number:.0f}"
    return f"{number:.2f}"


def find_channel_row(df: pd.DataFrame, channel_id: str, title: str, slug: str, run_dir: Path) -> pd.DataFrame:
    if df.empty:
        return df
    masks = []
    if channel_id and "channel_id" in df.columns:
        masks.append(df["channel_id"].astype(str) == channel_id)
    if "run_dir" in df.columns:
        run_values = df["run_dir"].astype(str)
        masks.append(run_values == f"runs/{slug}")
        masks.append(run_values == display_path(run_dir))
        masks.append(run_values.str.endswith(f"/{slug}"))
    if title and "run_channel_title" in df.columns:
        masks.append(df["run_channel_title"].astype(str) == title)
    if not masks:
        return df.iloc[0:0]
    mask = masks[0]
    for extra in masks[1:]:
        mask = mask | extra
    return df[mask].head(1)


def find_percentile_rows(df: pd.DataFrame, channel_id: str, title: str, slug: str, run_dir: Path) -> pd.DataFrame:
    if df.empty:
        return df
    masks = []
    if channel_id and "channel_id" in df.columns:
        masks.append(df["channel_id"].astype(str) == channel_id)
    if "run_dir" in df.columns:
        run_values = df["run_dir"].astype(str)
        masks.append(run_values == f"runs/{slug}")
        masks.append(run_values == display_path(run_dir))
        masks.append(run_values.str.endswith(f"/{slug}"))
    if title and "run_channel_title" in df.columns:
        masks.append(df["run_channel_title"].astype(str) == title)
    if not masks:
        return df.iloc[0:0]
    mask = masks[0]
    for extra in masks[1:]:
        mask = mask | extra
    return df[mask].copy()


def normalize_target_percentile_rows(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    out = df.copy()
    if "percentile" not in out.columns and "percentile_at_or_below" in out.columns:
        out["percentile"] = out["percentile_at_or_below"]
    if "n_cohort" not in out.columns and "cohort_n" in out.columns:
        out["n_cohort"] = out["cohort_n"]
    return out


def compact_distribution(row: dict[str, Any]) -> dict[str, Any]:
    keys = ["n", "mean", "median", "std", "min", "p10", "p25", "p75", "p90", "max"]
    out = {key: as_number(row.get(key)) for key in keys if key in row}
    p25 = as_number(row.get("p25"))
    p75 = as_number(row.get("p75"))
    if p25 is not None and p75 is not None:
        out["iqr"] = p75 - p25
    return out


def describe_series(values: pd.Series) -> dict[str, Any]:
    numeric = pd.to_numeric(values, errors="coerce").dropna()
    if numeric.empty:
        return {}
    out = {
        "n": int(numeric.shape[0]),
        "mean": float(numeric.mean()),
        "median": float(numeric.median()),
        "std": float(numeric.std(ddof=1)) if numeric.shape[0] > 1 else 0.0,
        "min": float(numeric.min()),
        "p10": float(numeric.quantile(0.10)),
        "p25": float(numeric.quantile(0.25)),
        "p75": float(numeric.quantile(0.75)),
        "p90": float(numeric.quantile(0.90)),
        "max": float(numeric.max()),
    }
    out["iqr"] = out["p75"] - out["p25"]
    return clean_json(out)


def metric_metadata(metric: str) -> dict[str, Any]:
    detail = METRIC_DETAIL_OVERRIDES.get(metric, {})
    group = metric_group(metric)
    group_info = METRIC_GROUP_INFO.get(group, METRIC_GROUP_INFO["scale"])
    return {
        "metric": metric,
        "label_zh": METRIC_LABELS.get(metric, metric),
        "label_en": METRIC_LABELS_EN.get(metric, metric),
        "group": group,
        "group_label_zh": group_info["label_zh"],
        "group_description_zh": group_info["description_zh"],
        "unit": detail.get("unit") or infer_metric_unit(metric),
        "polarity": detail.get("polarity") or infer_metric_polarity(metric),
        "question_zh": detail.get("question_zh") or f"{METRIC_LABELS.get(metric, metric)}在 cohort 中的位置如何？",
        "high_hint_zh": detail.get("high_hint_zh") or "高於多數 benchmark 頻道，需結合主題、受眾與情緒脈絡判讀。",
        "low_hint_zh": detail.get("low_hint_zh") or "低於多數 benchmark 頻道，需確認這是策略選擇、資料不足，還是社群弱點。",
    }


def infer_metric_unit(metric: str) -> str:
    if metric.startswith("n_") or metric.endswith("_comments") or metric.endswith("_commenters"):
        return "count"
    if any(part in metric for part in ["rate", "share", "pct"]):
        return "rate"
    if "density" in metric:
        return "density"
    if "score" in metric or metric.endswith("_hhi") or "modularity" in metric:
        return "score"
    if "per_video" in metric:
        return "per_video"
    if "per_1k_views" in metric:
        return "per_1k_views"
    return "value"


def infer_metric_polarity(metric: str) -> str:
    if any(part in metric for part in ["negative", "conflict"]):
        return "risk_high"
    if any(part in metric for part in ["positive", "return", "bridge"]):
        return "benefit_high"
    if any(part in metric for part in ["largest_community", "top3_community", "community_hhi"]):
        return "concentration_high"
    if metric.startswith("n_") or metric in {"top_level_comments", "top_level_commenters", "all_comments"}:
        return "scale"
    return "mixed_high"


def metric_comparison(
    metric: str,
    value: int | float | None,
    percentile: int | float | None,
    distribution: dict[str, Any],
) -> dict[str, Any]:
    median = as_number(distribution.get("median"))
    p25 = as_number(distribution.get("p25"))
    p75 = as_number(distribution.get("p75"))
    iqr = as_number(distribution.get("iqr"))
    relative_to_iqr = None
    if value is not None and median is not None and iqr not in (None, 0):
        relative_to_iqr = (value - median) / iqr
    if value is None or p25 is None or p75 is None:
        iqr_position = "unknown"
    elif value < p25:
        iqr_position = "below_iqr"
    elif value > p75:
        iqr_position = "above_iqr"
    else:
        iqr_position = "inside_iqr"
    return clean_json(
        {
            "percentile_band": percentile_band(percentile),
            "iqr_position": iqr_position,
            "relative_to_iqr": relative_to_iqr,
            "value_vs_median": None if value is None or median is None else value - median,
            "summary_zh": metric_comparison_sentence(metric, value, percentile, distribution, iqr_position),
        }
    )


def metric_comparison_sentence(
    metric: str,
    value: int | float | None,
    percentile: int | float | None,
    distribution: dict[str, Any],
    iqr_position: str,
) -> str:
    label = METRIC_LABELS.get(metric, metric)
    band = percentile_band(percentile)
    median = as_number(distribution.get("median"))
    n = as_number(distribution.get("n"))
    parts = [f"{label}位於 benchmark 的{band}區間"]
    if median is not None:
        parts.append(f"cohort 中位數為 {median:g}")
    if iqr_position == "above_iqr":
        parts.append("高於 IQR 上緣")
    elif iqr_position == "below_iqr":
        parts.append("低於 IQR 下緣")
    elif iqr_position == "inside_iqr":
        parts.append("落在 IQR 內")
    if n is not None:
        parts.append(f"比較樣本 n={int(n)}")
    if value is None:
        return f"{label}缺少可比較數值。"
    return "，".join(parts) + "。"


def percentile_band(percentile: int | float | None) -> str:
    pct = as_number(percentile)
    if pct is None:
        return "未知"
    if pct >= 90:
        return "極高"
    if pct >= 75:
        return "偏高"
    if pct > 25:
        return "典型"
    if pct > 10:
        return "偏低"
    return "極低"


def owner_hint(metric: str, percentile: int | float | None) -> str:
    meta = metric_metadata(metric)
    pct = as_number(percentile)
    if pct is None:
        return "缺少 percentile，暫不做高低判讀。"
    if pct >= 75:
        return meta["high_hint_zh"]
    if pct <= 25:
        return meta["low_hint_zh"]
    return "位於 cohort 中段，單獨看不是突出的異常；建議搭配時間序列、主題與影片熱點判讀。"


def metric_risk_opportunity_label(metric: str, percentile: int | float | None) -> str:
    pct = as_number(percentile)
    if pct is None:
        return "context"
    polarity = metric_metadata(metric)["polarity"]
    if polarity == "scale":
        return "context"
    if polarity == "risk_high":
        if pct >= 75:
            return "risk"
        if pct <= 25:
            return "opportunity"
        return "context"
    if polarity == "benefit_high":
        if pct >= 75:
            return "opportunity"
        if pct <= 25:
            return "risk"
        return "context"
    if polarity in {"concentration_high", "mixed_high"}:
        return "watch" if pct >= 75 or pct <= 25 else "context"
    return "context"


def takeaway_headline(metric: str, percentile: int | float | None) -> str:
    label = METRIC_LABELS.get(metric, metric)
    risk_label = metric_risk_opportunity_label(metric, percentile)
    band = percentile_band(percentile)
    if risk_label == "risk":
        prefix = "需要注意"
    elif risk_label == "opportunity":
        prefix = "可放大優勢"
    elif risk_label == "watch":
        prefix = "結構異常"
    else:
        prefix = "相對位置"
    return f"{prefix}：{label}{band}"


def metric_caution(metric: str) -> str:
    meta = metric_metadata(metric)
    if meta["polarity"] == "scale":
        return "這是資料覆蓋量或樣本規模，不應直接解讀為頻道表現好壞。"
    if meta["polarity"] == "risk_high":
        return "高風險指標只代表留言區相對更負面或衝突，不能單獨證明原因。"
    if meta["polarity"] == "benefit_high":
        return "高百分位通常是有利訊號，但仍需確認是否由少數爆款或特殊事件造成。"
    return "此指標高低沒有單一好壞方向，必須搭配內容主題、情緒與時間變化解讀。"


def metric_sort_key(metric: str) -> tuple[int, int, str]:
    group = metric_group(metric)
    group_order = list(METRIC_GROUPS).index(group) if group in METRIC_GROUPS else len(METRIC_GROUPS)
    metrics = METRIC_GROUPS.get(group, [])
    metric_order = metrics.index(metric) if metric in metrics else len(metrics)
    return (group_order, metric_order, metric)


def path_slug(value: Any) -> str:
    text = str(value or "").strip().rstrip("/")
    return Path(text).name if text else ""


def build_tabs(
    run_dir: Path,
    tables: list[dict[str, Any]],
    figures: list[dict[str, Any]],
    baseline_doc: dict[str, Any],
) -> list[dict[str, Any]]:
    table_names = {item["name"] for item in tables}
    figure_names = {item["name"] for item in figures}
    has_reports = any((run_dir / name).exists() for name in ["report.md", "report_en.md", "report_zh.md"])
    has_owner_report = any(run_dir.glob("*owner*report*.md"))
    out = []
    for tab in DASHBOARD_TABS:
        required_tables = set(tab["tables"])
        required_figures = set(tab["figures"])
        available_tables = sorted(required_tables & table_names)
        available_figures = sorted(required_figures & figure_names)
        available = bool(available_tables or available_figures)
        if tab["id"] == "baseline":
            available = bool(baseline_doc.get("n_metrics"))
        elif tab["id"] == "external_events":
            available = (run_dir / "external_events").exists()
        elif tab["id"] == "cold_report":
            available = has_reports
        elif tab["id"] == "owner_report":
            available = has_owner_report
        out.append(
            {
                "id": tab["id"],
                "title": tab["title"],
                "available": available,
                "tables": available_tables,
                "figures": available_figures,
            }
        )
    return out


def build_index_entry(channel_doc: dict[str, Any], channel_path: Path) -> dict[str, Any]:
    channel = channel_doc.get("channel") or {}
    summary = channel_doc.get("dashboard_summary") or {}
    baseline = channel_doc.get("baseline") or {}
    analysis = channel_doc.get("analysis") or {}
    risk_summary = baseline.get("risk_opportunity_summary") or {}
    return clean_json(
        {
            "slug": channel_doc.get("slug"),
            "title": channel_doc.get("title"),
            "channel_id": channel_doc.get("channel_id"),
            "subscriber_count": channel.get("subscriber_count"),
            "n_videos_in_scope": channel.get("n_videos_in_scope"),
            "n_comments_in_scope": channel.get("n_comments_in_scope"),
            "n_commenters_in_scope": channel.get("n_commenters_in_scope"),
            "date_min": channel.get("date_min"),
            "date_max": channel.get("date_max"),
            "json_path": display_path(channel_path),
            "run_dir": channel_doc.get("run_dir"),
            "negative_rate": summary.get("negative_rate"),
            "positive_rate": summary.get("positive_rate"),
            "baseline_metrics": baseline.get("n_metrics", 0),
            "percentile_takeaways": baseline.get("percentile_takeaways", [])[:3],
            "archetype": (analysis.get("archetype") or {}).get("label_zh"),
            "analysis_scores": (analysis.get("archetype") or {}).get("scores") or {},
            "risk_flag_count": len(risk_summary.get("risk_flags") or []),
            "opportunity_flag_count": len(risk_summary.get("opportunity_flags") or []),
            "watch_flag_count": len(risk_summary.get("watch_flags") or []),
            "available_tabs": [
                tab["id"]
                for tab in channel_doc.get("tabs", [])
                if tab.get("available")
            ],
        }
    )


def build_baseline_summary(baseline: dict[str, pd.DataFrame], baseline_dir: Path) -> dict[str, Any]:
    members = baseline.get("members", pd.DataFrame())
    metrics = baseline.get("metrics", pd.DataFrame())
    distributions = baseline.get("distributions", pd.DataFrame())
    percentiles = baseline.get("percentiles", pd.DataFrame())
    return {
        "baseline_dir": display_path(baseline_dir),
        "cohort_n_ready": int((members.get("status") == "ready").sum()) if "status" in members.columns else len(members),
        "channel_metric_rows": len(metrics),
        "metric_count": int(distributions["metric"].nunique()) if "metric" in distributions.columns else 0,
        "percentile_rows": len(percentiles),
        "paths": {
            "cohort_members": path_if_exists(baseline_dir / "cohort_members.csv"),
            "channel_metrics": path_if_exists(baseline_dir / "channel_metrics.csv"),
            "metric_distributions": path_if_exists(baseline_dir / "metric_distributions.csv"),
            "metric_percentiles": path_if_exists(baseline_dir / "metric_percentiles.csv"),
        },
        "key_metrics": KEY_BASELINE_METRICS,
        "statistical_principles": STATISTICAL_PRINCIPLES,
    }


def build_index_statistics(examples: list[dict[str, Any]], baseline: dict[str, pd.DataFrame]) -> dict[str, Any]:
    metrics = baseline.get("metrics", pd.DataFrame())
    percentiles = baseline.get("percentiles", pd.DataFrame())
    distributions = baseline.get("distributions", pd.DataFrame())
    return clean_json(
        {
            "totals": {
                "examples": len(examples),
                "videos": sum_number(examples, "n_videos_in_scope"),
                "comments": sum_number(examples, "n_comments_in_scope"),
                "commenters": sum_number(examples, "n_commenters_in_scope"),
            },
            "subscriber_bands": build_subscriber_bands(examples),
            "subscriber_band_distributions": build_subscriber_band_distributions(examples, metrics),
            "metric_labels": METRIC_LABELS,
            "metric_labels_en": METRIC_LABELS_EN,
            "metric_groups": METRIC_GROUPS,
            "metric_group_labels": {
                group: info["label_zh"] for group, info in METRIC_GROUP_INFO.items()
            },
            "metric_group_descriptions": {
                group: info["description_zh"] for group, info in METRIC_GROUP_INFO.items()
            },
            "metric_catalog": build_metric_catalog(distributions),
            "baseline_distributions": build_baseline_distributions(distributions),
            "cohort_position_maps": build_cohort_position_maps(percentiles),
            "leaderboards": build_leaderboards(metrics),
            "metric_spotlight": build_metric_spotlight(metrics, distributions),
            "statistical_principles": STATISTICAL_PRINCIPLES,
        }
    )


def build_subscriber_bands(examples: list[dict[str, Any]]) -> list[dict[str, Any]]:
    bands = [
        ("全部完成案例", 0),
        ("50萬訂閱以上", 500_000),
        ("100萬訂閱以上", 1_000_000),
    ]
    out = []
    for label, min_subs in bands:
        rows = [row for row in examples if (row.get("subscriber_count") or 0) >= min_subs]
        out.append(
            {
                "label": label,
                "min_subscriber_count": min_subs,
                "n_channels": len(rows),
                "videos": sum_number(rows, "n_videos_in_scope"),
                "comments": sum_number(rows, "n_comments_in_scope"),
                "commenters": sum_number(rows, "n_commenters_in_scope"),
            }
        )
    return out


def build_subscriber_band_distributions(
    examples: list[dict[str, Any]], metrics: pd.DataFrame
) -> list[dict[str, Any]]:
    if metrics.empty or not examples:
        return []
    subs_by_slug = {
        str(row.get("slug")): as_number(row.get("subscriber_count")) or 0
        for row in examples
        if row.get("slug")
    }
    rows = metrics.copy()
    if "run_dir" not in rows.columns:
        return []
    rows["_slug"] = rows["run_dir"].astype(str).map(path_slug)
    rows["_subscriber_count"] = rows["_slug"].map(subs_by_slug)
    bands = [
        ("all", "全部完成案例", 0),
        ("subs_500k_plus", "50萬訂閱以上", 500_000),
        ("subs_1m_plus", "100萬訂閱以上", 1_000_000),
    ]
    out = []
    for band_id, label, min_subs in bands:
        band_rows = rows[rows["_subscriber_count"].fillna(0) >= min_subs]
        metric_rows = []
        for metric in KEY_BASELINE_METRICS:
            if metric not in band_rows.columns:
                continue
            dist = describe_series(band_rows[metric])
            if dist.get("n"):
                meta = metric_metadata(metric)
                metric_rows.append(
                    {
                        "metric": metric,
                        "label": meta["label_zh"],
                        "group": meta["group"],
                        "unit": meta["unit"],
                        "distribution": dist,
                        "interpretation_hint_zh": meta["question_zh"],
                    }
                )
        out.append(
            {
                "id": band_id,
                "label": label,
                "min_subscriber_count": min_subs,
                "n_channels": int(len(band_rows)),
                "metrics": metric_rows,
            }
        )
    return clean_json(out)


def build_leaderboards(metrics: pd.DataFrame) -> list[dict[str, Any]]:
    if metrics.empty:
        return []
    boards = []
    for metric, title in LEADERBOARD_METRICS:
        if metric not in metrics.columns:
            continue
        rows = metrics[["run_channel_title", "cohort_channel_name", "run_dir", metric]].copy()
        rows[metric] = pd.to_numeric(rows[metric], errors="coerce")
        rows = rows.dropna(subset=[metric])
        if rows.empty:
            continue
        top = rows.sort_values(metric, ascending=False).head(5)
        bottom = rows.sort_values(metric, ascending=True).head(5)
        meta = metric_metadata(metric)
        boards.append(
            {
                "metric": metric,
                "label": meta["label_zh"],
                "label_en": meta["label_en"],
                "title": title,
                "group": meta["group"],
                "group_label": meta["group_label_zh"],
                "polarity": meta["polarity"],
                "owner_question_zh": meta["question_zh"],
                "high_interpretation_zh": meta["high_hint_zh"],
                "low_interpretation_zh": meta["low_hint_zh"],
                "top": leaderboard_rows(top, metric),
                "bottom": leaderboard_rows(bottom, metric),
                "caution_zh": metric_caution(metric),
            }
        )
    return boards


def build_metric_spotlight(metrics: pd.DataFrame, distributions: pd.DataFrame) -> list[dict[str, Any]]:
    if metrics.empty or distributions.empty:
        return []
    distribution_by_metric = {
        str(row["metric"]): row.to_dict()
        for _, row in distributions.iterrows()
        if "metric" in distributions.columns and pd.notna(row.get("metric"))
    }
    out = []
    for metric in KEY_BASELINE_METRICS:
        if metric not in metrics.columns:
            continue
        values = metrics[["run_channel_title", "cohort_channel_name", "run_dir", metric]].copy()
        values[metric] = pd.to_numeric(values[metric], errors="coerce")
        values = values.dropna(subset=[metric])
        if values.empty:
            continue
        high = values.sort_values(metric, ascending=False).head(3)
        low = values.sort_values(metric, ascending=True).head(3)
        meta = metric_metadata(metric)
        distribution = compact_distribution(distribution_by_metric.get(metric, {}))
        out.append(
            {
                "metric": metric,
                "label": meta["label_zh"],
                "label_en": meta["label_en"],
                "group": meta["group"],
                "group_label": meta["group_label_zh"],
                "unit": meta["unit"],
                "polarity": meta["polarity"],
                "distribution": distribution,
                "cohort_n": distribution.get("n"),
                "owner_question_zh": meta["question_zh"],
                "high_interpretation_zh": meta["high_hint_zh"],
                "low_interpretation_zh": meta["low_hint_zh"],
                "caution_zh": metric_caution(metric),
                "top_high": leaderboard_rows(high, metric),
                "top_low": leaderboard_rows(low, metric),
            }
        )
    return out


def build_cohort_position_maps(percentiles: pd.DataFrame) -> dict[str, Any]:
    if percentiles.empty or "run_dir" not in percentiles.columns or "metric" not in percentiles.columns:
        return {}
    points = []
    for run_dir, rows in percentiles.groupby("run_dir", dropna=True):
        metric_rows = {}
        for _, row in rows.iterrows():
            metric = str(row.get("metric") or "")
            if not metric:
                continue
            metric_rows[metric] = {
                "metric": metric,
                "label": METRIC_LABELS.get(metric, metric),
                "value": as_number(row.get("value")),
                "percentile": as_number(row.get("percentile")),
            }
        indices = {
            item["id"]: item
            for item in (build_composite_index(spec, metric_rows) for spec in COMPOSITE_INDICES)
            if item
        }
        first = rows.iloc[0].to_dict()
        points.append(
            {
                "run_dir": run_dir,
                "slug": path_slug(run_dir),
                "channel": first.get("run_channel_title") or first.get("cohort_channel_name"),
                "channel_id": first.get("channel_id"),
                "scores": {key: as_number(value.get("score")) for key, value in indices.items()},
                "archetype": infer_channel_archetype(indices).get("label_zh"),
            }
        )
    return {
        "points": clean_json(points),
        "maps": [
            {
                "id": "engagement_vs_risk",
                "title_zh": "互動轉換力 × 情緒風險壓力",
                "x": "engagement_conversion",
                "y": "risk_pressure",
                "x_label_zh": "互動轉換力",
                "y_label_zh": "情緒風險壓力",
            },
            {
                "id": "stickiness_vs_concentration",
                "title_zh": "核心黏著度 × 社群集中度",
                "x": "audience_stickiness",
                "y": "community_concentration",
                "x_label_zh": "核心黏著度",
                "y_label_zh": "社群集中度",
            },
        ],
    }


def leaderboard_rows(rows: pd.DataFrame, metric: str) -> list[dict[str, Any]]:
    return [
        {
            "rank": int(idx + 1),
            "channel": row.get("run_channel_title") or row.get("cohort_channel_name"),
            "run_dir": row.get("run_dir"),
            "value": as_number(row.get(metric)),
        }
        for idx, (_, row) in enumerate(rows.iterrows())
    ]


def build_percentile_takeaways(metrics: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for item in metrics:
        pct = as_number(item.get("percentile"))
        metric = str(item.get("metric") or "")
        if pct is None or not metric:
            continue
        if pct <= 25 or pct >= 75:
            label = metric_risk_opportunity_label(metric, pct)
            meta = metric_metadata(metric)
            out.append(
                {
                    "metric": metric,
                    "label": meta["label_zh"],
                    "label_en": meta["label_en"],
                    "group": meta["group"],
                    "group_label": meta["group_label_zh"],
                    "value": item.get("value"),
                    "percentile": pct,
                    "percentile_band": percentile_band(pct),
                    "direction": "high" if pct >= 75 else "low",
                    "risk_opportunity_label": label,
                    "headline_zh": takeaway_headline(metric, pct),
                    "interpretation_hint_zh": owner_hint(metric, pct),
                    "distribution": item.get("distribution") or {},
                    "caution_zh": metric_caution(metric),
                }
            )
    return sorted(out, key=lambda row: abs((row.get("percentile") or 50) - 50), reverse=True)[:8]


def build_risk_opportunity_summary(metrics: list[dict[str, Any]]) -> dict[str, Any]:
    buckets = {"risk": [], "opportunity": [], "watch": [], "context": []}
    for item in metrics:
        label = item.get("risk_opportunity_label")
        if label in buckets:
            buckets[label].append(item)
    for key, rows in buckets.items():
        rows.sort(key=lambda row: abs((row.get("percentile") or 50) - 50), reverse=True)
        buckets[key] = rows[:5]
    return clean_json(
        {
            "risk_flags": buckets["risk"],
            "opportunity_flags": buckets["opportunity"],
            "watch_flags": buckets["watch"],
            "context_flags": buckets["context"],
            "principle_zh": "這些標籤只表示相對 benchmark 的統計位置，不能單獨推論因果或頻道品質。",
        }
    )


def build_metric_catalog(distributions: pd.DataFrame) -> dict[str, Any]:
    metrics = set(METRIC_LABELS)
    if not distributions.empty and "metric" in distributions.columns:
        metrics.update(str(value) for value in distributions["metric"].dropna().tolist())
    distribution_by_metric = {
        str(row["metric"]): row.to_dict()
        for _, row in distributions.iterrows()
        if "metric" in distributions.columns and pd.notna(row.get("metric"))
    }
    out = {}
    for metric in sorted(metrics, key=metric_sort_key):
        meta = metric_metadata(metric)
        out[metric] = {
            **meta,
            "distribution": compact_distribution(distribution_by_metric.get(metric, {})),
            "caution_zh": metric_caution(metric),
        }
    return clean_json(out)


def build_baseline_distributions(distributions: pd.DataFrame) -> list[dict[str, Any]]:
    if distributions.empty or "metric" not in distributions.columns:
        return []
    out = []
    for _, row in distributions.iterrows():
        metric = str(row.get("metric"))
        if not metric or metric == "nan":
            continue
        meta = metric_metadata(metric)
        dist = compact_distribution(row.to_dict())
        out.append(
            {
                "metric": metric,
                "label": meta["label_zh"],
                "label_en": meta["label_en"],
                "group": meta["group"],
                "group_label": meta["group_label_zh"],
                "unit": meta["unit"],
                "polarity": meta["polarity"],
                "distribution": dist,
                "cohort_n": dist.get("n"),
                "owner_question_zh": meta["question_zh"],
                "high_interpretation_zh": meta["high_hint_zh"],
                "low_interpretation_zh": meta["low_hint_zh"],
                "caution_zh": metric_caution(metric),
            }
        )
    return sorted(out, key=lambda item: metric_sort_key(item["metric"]))


def metric_group(metric: str) -> str:
    for group, names in METRIC_GROUPS.items():
        if metric in names:
            return group
    return "scale"


def sum_number(rows: list[dict[str, Any]], key: str) -> int | float:
    total = 0.0
    for row in rows:
        value = as_number(row.get(key))
        if value is not None:
            total += value
    return int(total) if total.is_integer() else total


def list_artifacts(directory: Path, suffix: str, source_dir: str | None = None) -> list[dict[str, Any]]:
    if not directory.exists():
        return []
    out = []
    for path in sorted(directory.glob(f"*{suffix}")):
        out.append(
            {
                "name": path.stem,
                "path": display_path(path),
                "bytes": path.stat().st_size,
                "source_dir": source_dir,
            }
        )
    return out


def first_row(value: Any) -> dict[str, Any]:
    rows = list_rows(value, limit=1)
    return rows[0] if rows else {}


def list_rows(value: Any, limit: int) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    rows = [row for row in value if isinstance(row, dict)]
    return clean_json(rows[:limit])


def first_df_row(df: pd.DataFrame) -> dict[str, Any]:
    if df.empty:
        return {}
    return clean_json(df.iloc[0].to_dict())


def read_json_if_exists(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def path_if_exists(path: Path) -> str | None:
    return display_path(path) if path.exists() else None


def nested_number(data: dict[str, Any], key: str, subkey: str) -> float | int | None:
    value = data.get(key)
    if not isinstance(value, dict):
        return None
    return as_number(value.get(subkey))


def as_number(value: Any) -> int | float | None:
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except TypeError:
        pass
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if math.isfinite(value) and value.is_integer():
            return int(value)
        return value if math.isfinite(value) else None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number):
        return None
    return int(number) if number.is_integer() else number


def clean_json(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): clean_json(val) for key, val in value.items()}
    if isinstance(value, list):
        return [clean_json(item) for item in value]
    if isinstance(value, tuple):
        return [clean_json(item) for item in value]
    if isinstance(value, Path):
        return display_path(value)
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if hasattr(value, "item"):
        try:
            return clean_json(value.item())
        except Exception:
            pass
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    try:
        if pd.isna(value):
            return None
    except TypeError:
        pass
    return value


def display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(clean_json(data), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def write_readme(output_dir: Path, index: dict[str, Any]) -> None:
    text = f"""# dashboard_data

Generated read-only dashboard artifacts.

- `index.json`: dashboard example index.
- `channels/*.json`: one dashboard data packet per completed channel run.

Generated at: `{index['generated_at']}`

Examples: `{index['n_examples']}`

Mode: read-only demo. These files do not trigger crawler, Qwen inference, or
fake progress bars.
"""
    (output_dir / "README.md").write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
