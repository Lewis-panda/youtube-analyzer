from __future__ import annotations

import json
import re

import pandas as pd


THEME_RULES: list[tuple[str, list[str]]] = [
    ("food_culture", ["美食", "食物", "餐廳", "料理", "吃", "food", "restaurant", "cooking"]),
    ("business_brand", ["創業", "品牌", "開店", "營運", "加盟", "business", "brand", "store"]),
    ("automotive_luxury", ["超跑", "跑車", "車", "法拉利", "保時捷", "benz", "bmw", "toyota", "car"]),
    ("controversy_response", ["回應", "爭議", "風波", "道歉", "聲明", "爆料", "controversy", "response"]),
    ("travel_exploration", ["旅遊", "旅行", "探索", "travel", "trip", "vlog", "country"]),
    ("city_lifestyle", ["城市", "生活", "city", "life", "living", "taiwan", "台灣", "america", "美國"]),
    ("physical_challenge", ["挑戰", "challenge", "ironman", "marathon", "race", "健身", "運動"]),
    ("survival_outdoor", ["荒島", "求生", "survival", "camping", "deserted", "outdoor"]),
    ("workplace_tech_career", ["工作", "職涯", "科技", "工程師", "apple", "engineer", "career", "tech", "office"]),
    ("education_advice", ["教學", "學", "如何", "建議", "advice", "learn", "education", "how to"]),
    ("personal_team_life", ["生日", "家人", "朋友", "團隊", "日常", "family", "team", "birthday", "personal"]),
    ("guest_relationship", ["來賓", "女友", "老婆", "訪問", "guest", "interview", "relationship"]),
    ("product_review", ["開箱", "評測", "review", "product", "買", "unbox"]),
    ("event_announcement", ["公告", "announcement", "重大", "宣布", "update"]),
]

THEME_LABELS = [theme for theme, _ in THEME_RULES] + ["other"]


def label_video_themes(
    videos: pd.DataFrame,
    qwen_path: object | None = None,
) -> pd.DataFrame:
    qwen = _load_qwen_themes(qwen_path, videos) if qwen_path else pd.DataFrame()
    if not qwen.empty:
        qwen_ids = set(qwen["video_id"])
        fallback = _label_video_themes_keyword(
            videos[~videos["video_id"].isin(qwen_ids)].copy()
        )
        out = pd.concat([qwen, fallback], ignore_index=True)
        order = videos[["video_id"]].reset_index().rename(columns={"index": "_order"})
        return (
            out.merge(order, on="video_id", how="left")
            .sort_values("_order")
            .drop(columns="_order")
            .reset_index(drop=True)
        )
    return _label_video_themes_keyword(videos)


def _label_video_themes_keyword(videos: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for row in videos.itertuples(index=False):
        tags = _parse_tags(getattr(row, "tags_json", ""))
        text = " ".join(
            [
                str(getattr(row, "title", "") or ""),
                str(getattr(row, "description", "") or ""),
                tags,
            ]
        ).lower()
        theme, labels, hits = classify_theme(text)
        rows.append(
            {
                "video_id": row.video_id,
                "title": row.title,
                "published_at": row.published_at,
                "primary_theme": theme,
                "theme_labels": ";".join(labels),
                "n_theme_labels": len(labels),
                "theme_source": "keyword",
                "secondary_themes": "",
                "format": "unclear",
                "setting": "unknown",
                "audience_intent": "unknown",
                "entities": "",
                "theme_confidence": None,
                "theme_reason": "",
                "theme_keyword_hits": ";".join(hits[:12]),
                "view_count": row.view_count,
                "comment_count": row.comment_count,
            }
        )
    return pd.DataFrame(rows)


def _load_qwen_themes(qwen_path: object, videos: pd.DataFrame) -> pd.DataFrame:
    path = getattr(qwen_path, "exists", None)
    if path is None or not qwen_path.exists():
        return pd.DataFrame()
    raw = pd.read_csv(qwen_path)
    if raw.empty or "video_id" not in raw.columns:
        return pd.DataFrame()
    current = videos[
        ["video_id", "title", "published_at", "view_count", "comment_count"]
    ].copy()
    raw = raw.drop_duplicates("video_id", keep="last")
    raw = raw[raw["video_id"].isin(set(current["video_id"]))].copy()
    if raw.empty:
        return pd.DataFrame()

    if "primary_theme" not in raw.columns:
        raw["primary_theme"] = "other"
    if "theme_labels" not in raw.columns:
        raw["theme_labels"] = raw.apply(_theme_labels_from_qwen_row, axis=1)

    out = current.merge(raw, on="video_id", how="inner", suffixes=("", "_qwen"))
    for col in ["title", "published_at", "view_count", "comment_count"]:
        qcol = f"{col}_qwen"
        if qcol in out.columns:
            out = out.drop(columns=qcol)

    out["primary_theme"] = out["primary_theme"].map(_clean_theme)
    out["theme_labels"] = out["theme_labels"].map(_clean_theme_labels)
    out["n_theme_labels"] = out["theme_labels"].map(lambda value: len(str(value).split(";")))
    out["theme_source"] = "qwen"

    defaults = {
        "secondary_themes": "",
        "format": "unclear",
        "setting": "unknown",
        "audience_intent": "unknown",
        "entities": "",
        "theme_confidence": None,
        "theme_reason": "",
        "theme_keyword_hits": "",
    }
    for col, value in defaults.items():
        if col not in out.columns:
            out[col] = value
    return out[
        [
            "video_id",
            "title",
            "published_at",
            "primary_theme",
            "theme_labels",
            "n_theme_labels",
            "theme_source",
            "secondary_themes",
            "format",
            "setting",
            "audience_intent",
            "entities",
            "theme_confidence",
            "theme_reason",
            "theme_keyword_hits",
            "view_count",
            "comment_count",
        ]
    ]


def summarize_theme_sources(video_themes: pd.DataFrame) -> pd.DataFrame:
    if video_themes.empty or "theme_source" not in video_themes.columns:
        return pd.DataFrame()
    return (
        video_themes.groupby("theme_source")
        .agg(n_videos=("video_id", "count"))
        .reset_index()
        .sort_values("n_videos", ascending=False)
    )


def classify_theme(text: str) -> tuple[str, list[str], list[str]]:
    best_theme = "other"
    best_hits: list[str] = []
    labels: list[str] = []
    all_hits: list[str] = []
    for theme, keywords in THEME_RULES:
        hits = [kw for kw in keywords if re.search(re.escape(kw.lower()), text)]
        if hits:
            labels.append(theme)
            all_hits.extend(f"{theme}:{kw}" for kw in hits)
        if len(hits) > len(best_hits):
            best_theme = theme
            best_hits = hits
    if not labels:
        labels = ["other"]
    return best_theme, labels, all_hits or best_hits


def _theme_labels_from_qwen_row(row: pd.Series) -> str:
    labels = [_clean_theme(row.get("primary_theme"))]
    secondary = row.get("secondary_themes", row.get("secondary_theme", ""))
    if isinstance(secondary, str):
        parts = re.split(r"[;,|]", secondary)
    elif isinstance(secondary, list):
        parts = secondary
    else:
        parts = []
    labels.extend(_clean_theme(part) for part in parts)
    labels = [label for label in labels if label and label != "other"]
    return ";".join(dict.fromkeys(labels)) or "other"


def _clean_theme(value: object) -> str:
    text = str(value or "other").strip()
    return text if text in THEME_LABELS else "other"


def _clean_theme_labels(value: object) -> str:
    labels = []
    for part in re.split(r"[;,|]", str(value or "")):
        label = _clean_theme(part)
        if label:
            labels.append(label)
    labels = [label for label in labels if label != "other"]
    return ";".join(dict.fromkeys(labels)) or "other"


def summarize_themes(video_themes: pd.DataFrame, comments: pd.DataFrame) -> pd.DataFrame:
    merged = comments[["comment_id", "video_id", "author_actor_id"]].merge(
        video_themes[["video_id", "primary_theme"]], on="video_id", how="inner"
    )
    if merged.empty:
        return pd.DataFrame()
    theme_video_counts = video_themes.groupby("primary_theme").size().rename("n_videos")
    out = (
        merged.groupby("primary_theme")
        .agg(
            n_comments=("comment_id", "count"),
            n_commenters=("author_actor_id", "nunique"),
        )
        .join(theme_video_counts, how="outer")
        .fillna(0)
        .reset_index()
        .sort_values(["n_commenters", "n_comments"], ascending=False)
    )
    return out


def _parse_tags(raw: object) -> str:
    if not raw:
        return ""
    try:
        tags = json.loads(str(raw))
    except Exception:
        return str(raw)
    if isinstance(tags, list):
        return " ".join(str(tag) for tag in tags)
    return str(raw)
