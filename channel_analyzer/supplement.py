from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import math

import numpy as np
import pandas as pd

from .analysis import (
    _keyword_sentiment_frame,
    _markdown_table,
    _sentiment_group_summary,
    build_report_payload,
    load_qwen_comment_sentiment,
)
from .config import AnalyzerConfig, output_slug
from .data import ChannelData
from .themes import label_video_themes


SUPPLEMENT_START = "<!-- BEGIN COMMENTER_DEEPER_ANALYSIS -->"
SUPPLEMENT_END = "<!-- END COMMENTER_DEEPER_ANALYSIS -->"


@dataclass(frozen=True)
class SupplementArtifacts:
    run_dir: Path
    tables_dir: Path
    report_en_path: Path
    report_zh_path: Path
    report_json_path: Path


def run_deeper_supplement(
    config: AnalyzerConfig,
    data: ChannelData,
    output_dir: Path | None = None,
) -> SupplementArtifacts:
    slug = output_slug(config, data.channel.get("title"))
    run_dir = output_dir or (Path(__file__).resolve().parents[1] / "runs" / slug)
    tables_dir = run_dir / "tables"
    tables_dir.mkdir(parents=True, exist_ok=True)

    videos = data.videos.copy()
    comments = data.comments.copy()
    qwen_path = tables_dir / "qwen_comment_sentiment.csv"
    sentiment, source = load_supplement_sentiment(comments, qwen_path)
    video_themes = label_video_themes(videos, qwen_path=tables_dir / "qwen_video_themes.csv")

    overview = build_reply_overview(comments, sentiment, source)
    reply_sentiment_summary = _sentiment_group_summary(sentiment, ["is_top_level_label"])
    thread_metrics = build_thread_metrics(comments, sentiment)
    video_summary = build_video_conflict_summary(thread_metrics, sentiment, videos, video_themes)
    theme_summary = build_theme_conflict_summary(thread_metrics, video_themes)

    _write_csv(tables_dir / "reply_thread_overview.csv", overview)
    _write_csv(tables_dir / "reply_sentiment_summary.csv", reply_sentiment_summary)
    _write_csv(tables_dir / "reply_thread_metrics.csv", thread_metrics)
    _write_csv(tables_dir / "reply_conflict_video_summary.csv", video_summary)
    _write_csv(tables_dir / "reply_conflict_theme_summary.csv", theme_summary)

    payload = build_report_payload(
        config=config,
        channel=data.channel,
        reply_thread_overview=overview,
        reply_sentiment_summary=reply_sentiment_summary,
        reply_conflict_video_summary=video_summary,
        reply_conflict_theme_summary=theme_summary,
    )
    payload["full_table_notes"] = {
        "reply_thread_metrics": "Thread-level metrics for every observed comment thread; no raw comment text is exported.",
        "reply_conflict_video_summary": "Video-level conflict and polarization proxy metrics.",
        "reply_conflict_theme_summary": "Theme-level aggregation of thread conflict metrics.",
    }

    report_en = render_supplement_section(payload, language="en")
    report_zh = render_supplement_section(payload, language="zh")
    report_en_path = run_dir / "report_en.md"
    report_zh_path = run_dir / "report_zh.md"
    report_json_path = run_dir / "report_supplement.json"
    _merge_section_into_report(
        report_en_path,
        report_en,
        title=f"Channel Community Report: {data.channel.get('title', 'Unknown Channel')}",
    )
    _merge_section_into_report(
        report_zh_path,
        report_zh,
        title=f"頻道社群統計報告：{data.channel.get('title', 'Unknown Channel')}",
    )
    (run_dir / "report.md").write_text(report_en_path.read_text(encoding="utf-8"), encoding="utf-8")
    _merge_supplement_json(run_dir / "report.json", payload)
    report_json_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    _remove_legacy_supplement_reports(run_dir)
    return SupplementArtifacts(
        run_dir=run_dir,
        tables_dir=tables_dir,
        report_en_path=report_en_path,
        report_zh_path=report_zh_path,
        report_json_path=report_json_path,
    )


def load_supplement_sentiment(comments: pd.DataFrame, qwen_path: Path) -> tuple[pd.DataFrame, str]:
    qwen = load_qwen_comment_sentiment(qwen_path, comments)
    if not qwen.empty:
        out = attach_thread_context(qwen, comments)
        out["is_top_level_label"] = np.where(out["is_top_level"], "top_level", "reply")
        return out, "qwen"

    fallback = _keyword_sentiment_frame(comments)
    out = attach_thread_context(fallback, comments)
    out["is_top_level_label"] = np.where(out["is_top_level"], "top_level", "reply")
    return out, "keyword_proxy"


def attach_thread_context(sentiments: pd.DataFrame, comments: pd.DataFrame) -> pd.DataFrame:
    meta = comments[
        ["comment_id", "thread_id", "parent_comment_id", "is_top_level"]
    ].copy()
    meta["is_top_level"] = meta["is_top_level"].astype(bool)
    sentiments = sentiments.drop(
        columns=[
            col
            for col in ["thread_id", "parent_comment_id", "is_top_level"]
            if col in sentiments.columns
        ]
    )
    out = sentiments.merge(meta, on="comment_id", how="left")
    out["is_top_level"] = out["is_top_level"].fillna(False).astype(bool)
    return out


def build_reply_overview(
    comments: pd.DataFrame,
    sentiment: pd.DataFrame,
    source: str,
) -> pd.DataFrame:
    n_comments = len(comments)
    n_top = int(comments["is_top_level"].astype(bool).sum())
    n_replies = n_comments - n_top
    thread_ids_with_replies = set(
        comments.loc[~comments["is_top_level"].astype(bool), "thread_id"].dropna()
    )
    scored = len(sentiment)
    scored_replies = int((~sentiment["is_top_level"]).sum()) if not sentiment.empty else 0
    return pd.DataFrame(
        [
            {
                "sentiment_source": source,
                "n_all_comments": n_comments,
                "n_top_level_comments": n_top,
                "n_replies": n_replies,
                "reply_share_all_comments": n_replies / n_comments if n_comments else math.nan,
                "n_threads": int(comments["thread_id"].nunique()),
                "n_threads_with_replies": len(thread_ids_with_replies),
                "pct_threads_with_replies": (
                    len(thread_ids_with_replies) / comments["thread_id"].nunique()
                    if comments["thread_id"].nunique()
                    else math.nan
                ),
                "n_commenters_all": int(comments["author_actor_id"].nunique()),
                "n_reply_commenters": int(
                    comments.loc[
                        ~comments["is_top_level"].astype(bool), "author_actor_id"
                    ].nunique()
                ),
                "n_scored_comments": scored,
                "n_scored_replies": scored_replies,
                "sentiment_coverage": scored / n_comments if n_comments else 0,
                "reply_sentiment_coverage": scored_replies / n_replies if n_replies else 0,
            }
        ]
    )


def build_thread_metrics(comments: pd.DataFrame, sentiment: pd.DataFrame) -> pd.DataFrame:
    base = comments.copy()
    base["is_reply"] = ~base["is_top_level"].astype(bool)
    thread_base = (
        base.groupby("thread_id", dropna=False)
        .agg(
            video_id=("video_id", "first"),
            n_thread_comments=("comment_id", "count"),
            n_replies=("is_reply", "sum"),
            n_commenters=("author_actor_id", "nunique"),
            first_comment_at=("comment_published_at", "min"),
            last_comment_at=("comment_published_at", "max"),
        )
        .reset_index()
    )
    reply_commenters = (
        base[base["is_reply"]]
        .groupby("thread_id")["author_actor_id"]
        .nunique()
        .rename("n_reply_commenters")
        .reset_index()
    )
    thread_base = thread_base.merge(reply_commenters, on="thread_id", how="left")
    thread_base["n_reply_commenters"] = thread_base["n_reply_commenters"].fillna(0).astype(int)

    all_sent = prefix_sentiment_summary(
        _fast_sentiment_group_summary(sentiment, ["thread_id"]), "all"
    )
    replies = sentiment[~sentiment["is_top_level"]].copy()
    reply_sent = prefix_sentiment_summary(
        _fast_sentiment_group_summary(replies, ["thread_id"]), "reply"
    )
    top_sent = (
        sentiment[sentiment["is_top_level"]]
        .sort_values(["thread_id", "comment_published_at", "comment_id"])
        .groupby("thread_id", dropna=False)
        .agg(
            top_sentiment_label=("sentiment_label", "first"),
            top_score_neg=("score_neg", "first"),
            top_score_pos=("score_pos", "first"),
        )
        .reset_index()
    )

    out = (
        thread_base.merge(all_sent, on="thread_id", how="left")
        .merge(reply_sent, on="thread_id", how="left")
        .merge(top_sent, on="thread_id", how="left")
    )
    for col in out.columns:
        if col.startswith(("all_", "reply_")) and col not in {
            "all_avg_confidence",
            "reply_avg_confidence",
        }:
            out[col] = pd.to_numeric(out[col], errors="coerce").fillna(0)
    for col in ["all_avg_confidence", "reply_avg_confidence"]:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce")

    out["has_replies"] = out["n_replies"] > 0
    out["thread_bipolarity"] = 4 * out["all_positive_rate"] * out["all_negative_rate"]
    out["reply_bipolarity"] = 4 * out["reply_positive_rate"] * out["reply_negative_rate"]
    out["like_weighted_bipolarity"] = (
        4
        * out["all_like_weighted_positive_rate"]
        * out["all_like_weighted_negative_rate"]
    )
    out["conflict_thread"] = out["has_replies"] & (
        ((out["all_positive_rate"] >= 0.15) & (out["all_negative_rate"] >= 0.15))
        | ((out["reply_positive_rate"] >= 0.15) & (out["reply_negative_rate"] >= 0.15))
    )
    out["strict_reply_conflict_thread"] = (
        (out["n_replies"] >= 2)
        & (out["reply_n_positive"] >= 1)
        & (out["reply_n_negative"] >= 1)
    )
    out["pile_on_thread"] = (
        (out["n_replies"] >= 3)
        & (out["reply_negative_rate"] >= 0.60)
        & (out["reply_positive_rate"] < 0.15)
    )
    out["parent_opposition_thread"] = (
        (
            (out["top_sentiment_label"] == "positive")
            & (out["reply_negative_rate"] >= 0.25)
        )
        | (
            (out["top_sentiment_label"] == "negative")
            & (out["reply_positive_rate"] >= 0.25)
        )
        | (
            (out["top_sentiment_label"] == "neutral")
            & (out["reply_positive_rate"] >= 0.15)
            & (out["reply_negative_rate"] >= 0.15)
        )
    )
    out["negative_consensus_thread"] = (
        out["has_replies"]
        & (out["all_negative_rate"] >= 0.50)
        & (out["all_positive_rate"] < 0.10)
    )
    out["positive_consensus_thread"] = (
        out["has_replies"]
        & (out["all_positive_rate"] >= 0.50)
        & (out["all_negative_rate"] < 0.10)
    )

    out["conflict_intensity"] = np.where(
        out["conflict_thread"],
        np.maximum(out["thread_bipolarity"], out["reply_bipolarity"]),
        0.0,
    )
    out["conflict_reply_count_weight"] = np.where(
        out["conflict_thread"], out["n_replies"], 0
    )
    out["conflict_reply_like_weight"] = np.where(
        out["conflict_thread"], out["reply_total_like_w"], 0.0
    )
    out["conflict_reply_count_weighted_intensity"] = (
        out["conflict_intensity"] * out["n_replies"]
    )
    out["conflict_reply_like_weighted_intensity"] = (
        out["conflict_intensity"] * out["reply_total_like_w"]
    )
    return out.sort_values(
        [
            "conflict_thread",
            "conflict_reply_like_weighted_intensity",
            "thread_bipolarity",
            "n_replies",
        ],
        ascending=[False, False, False, False],
    )


def prefix_sentiment_summary(frame: pd.DataFrame, prefix: str) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame(columns=["thread_id"])
    rename = {
        col: f"{prefix}_{col}"
        for col in frame.columns
        if col != "thread_id"
    }
    out = frame.rename(columns=rename)
    return out


def _fast_sentiment_group_summary(
    sentiments: pd.DataFrame,
    group_cols: list[str],
) -> pd.DataFrame:
    if sentiments.empty:
        return pd.DataFrame(columns=group_cols)

    frame = sentiments.copy()
    frame["_is_negative"] = (frame["sentiment_label"] == "negative").astype(int)
    frame["_is_neutral"] = (frame["sentiment_label"] == "neutral").astype(int)
    frame["_is_positive"] = (frame["sentiment_label"] == "positive").astype(int)
    frame["_negative_like_w"] = np.where(
        frame["sentiment_label"] == "negative", frame["like_w"], 0.0
    )
    frame["_positive_like_w"] = np.where(
        frame["sentiment_label"] == "positive", frame["like_w"], 0.0
    )

    out = (
        frame.groupby(group_cols, dropna=False)
        .agg(
            n_comments=("comment_id", "count"),
            n_negative=("_is_negative", "sum"),
            n_neutral=("_is_neutral", "sum"),
            n_positive=("_is_positive", "sum"),
            total_like_w=("like_w", "sum"),
            negative_like_w=("_negative_like_w", "sum"),
            positive_like_w=("_positive_like_w", "sum"),
            avg_score_neg=("score_neg", "mean"),
            avg_score_neu=("score_neu", "mean"),
            avg_score_pos=("score_pos", "mean"),
            avg_confidence=("sentiment_confidence", "mean"),
        )
        .reset_index()
    )
    out["negative_rate"] = out["n_negative"] / out["n_comments"]
    out["neutral_rate"] = out["n_neutral"] / out["n_comments"]
    out["positive_rate"] = out["n_positive"] / out["n_comments"]
    out["like_weighted_negative_rate"] = np.divide(
        out["negative_like_w"],
        out["total_like_w"],
        out=np.zeros(len(out), dtype=float),
        where=out["total_like_w"].to_numpy() != 0,
    )
    out["like_weighted_positive_rate"] = np.divide(
        out["positive_like_w"],
        out["total_like_w"],
        out=np.zeros(len(out), dtype=float),
        where=out["total_like_w"].to_numpy() != 0,
    )
    ordered = [
        *group_cols,
        "n_comments",
        "n_negative",
        "n_neutral",
        "n_positive",
        "negative_rate",
        "neutral_rate",
        "positive_rate",
        "total_like_w",
        "negative_like_w",
        "positive_like_w",
        "like_weighted_negative_rate",
        "like_weighted_positive_rate",
        "avg_score_neg",
        "avg_score_neu",
        "avg_score_pos",
        "avg_confidence",
    ]
    return out[ordered]


def build_video_conflict_summary(
    thread_metrics: pd.DataFrame,
    sentiment: pd.DataFrame,
    videos: pd.DataFrame,
    video_themes: pd.DataFrame,
) -> pd.DataFrame:
    if thread_metrics.empty:
        return pd.DataFrame()
    rows = []
    for video_id, group in thread_metrics.groupby("video_id", dropna=False):
        replied = group[group["has_replies"]]
        denom_replied = len(replied)
        total_replies = float(group["n_replies"].sum())
        total_reply_like_w = float(group["reply_total_like_w"].sum())
        conflict_reply_count = float(group["conflict_reply_count_weight"].sum())
        conflict_reply_like_w = float(group["conflict_reply_like_weight"].sum())
        conflict_intensity = float(group["conflict_intensity"].sum())
        reply_count_weighted_intensity = float(
            group["conflict_reply_count_weighted_intensity"].sum()
        )
        reply_like_weighted_intensity = float(
            group["conflict_reply_like_weighted_intensity"].sum()
        )
        conflict_reply_share = divide_zero(conflict_reply_count, total_replies)
        like_weighted_conflict_reply_share = divide_zero(
            conflict_reply_like_w, total_reply_like_w
        )
        reply_count_weighted_conflict_intensity = divide_zero(
            reply_count_weighted_intensity, total_replies
        )
        like_weighted_conflict_intensity = divide_zero(
            reply_like_weighted_intensity, total_reply_like_w
        )
        rows.append(
            {
                "video_id": video_id,
                "n_threads": len(group),
                "n_threads_with_replies": denom_replied,
                "n_replies": int(group["n_replies"].sum()),
                "n_conflict_threads": int(group["conflict_thread"].sum()),
                "conflict_thread_rate_all": group["conflict_thread"].mean(),
                "conflict_thread_rate_replied": (
                    replied["conflict_thread"].mean() if denom_replied else 0
                ),
                "n_strict_reply_conflict_threads": int(
                    group["strict_reply_conflict_thread"].sum()
                ),
                "n_pile_on_threads": int(group["pile_on_thread"].sum()),
                "n_parent_opposition_threads": int(
                    group["parent_opposition_thread"].sum()
                ),
                "avg_thread_bipolarity": group["thread_bipolarity"].mean(),
                "max_thread_bipolarity": group["thread_bipolarity"].max(),
                "avg_reply_bipolarity": replied["reply_bipolarity"].mean()
                if denom_replied
                else 0,
                "max_reply_bipolarity": group["reply_bipolarity"].max(),
                "conflict_intensity_sum": conflict_intensity,
                "conflict_reply_count": conflict_reply_count,
                "conflict_reply_share": conflict_reply_share,
                "conflict_reply_like_weight": conflict_reply_like_w,
                "like_weighted_conflict_reply_share": like_weighted_conflict_reply_share,
                "reply_count_weighted_conflict_intensity": (
                    reply_count_weighted_conflict_intensity
                ),
                "like_weighted_conflict_intensity": like_weighted_conflict_intensity,
            }
        )
    out = pd.DataFrame(rows)
    reply_sent = sentiment[~sentiment["is_top_level"]]
    if not reply_sent.empty:
        reply_video = _sentiment_group_summary(reply_sent, ["video_id"])
        reply_video = reply_video.rename(
            columns={
                "n_comments": "n_scored_replies",
                "negative_rate": "reply_negative_rate",
                "positive_rate": "reply_positive_rate",
                "like_weighted_negative_rate": "reply_like_weighted_negative_rate",
                "like_weighted_positive_rate": "reply_like_weighted_positive_rate",
            }
        )
        keep = [
            "video_id",
            "n_scored_replies",
            "reply_negative_rate",
            "reply_positive_rate",
            "reply_like_weighted_negative_rate",
            "reply_like_weighted_positive_rate",
        ]
        out = out.merge(reply_video[keep], on="video_id", how="left")
    for col in [
        "n_scored_replies",
        "reply_negative_rate",
        "reply_positive_rate",
        "reply_like_weighted_negative_rate",
        "reply_like_weighted_positive_rate",
    ]:
        if col not in out.columns:
            out[col] = 0
        out[col] = pd.to_numeric(out[col], errors="coerce").fillna(0)
    out["conflict_score"] = (
        out["n_conflict_threads"] * out["conflict_thread_rate_replied"]
    )
    out["reply_count_weighted_conflict_score"] = (
        out["n_conflict_threads"] * out["conflict_reply_share"]
    )
    out["like_weighted_conflict_score"] = (
        out["n_conflict_threads"] * out["like_weighted_conflict_reply_share"]
    )
    out["opposition_score"] = (
        out["n_parent_opposition_threads"] * out["conflict_thread_rate_replied"]
    )
    video_meta = videos[["video_id", "title", "published_at", "view_count", "comment_count"]]
    theme_meta = video_themes[["video_id", "primary_theme"]]
    return (
        out.merge(theme_meta, on="video_id", how="left")
        .merge(video_meta, on="video_id", how="left")
        .sort_values(
            [
                "like_weighted_conflict_score",
                "reply_count_weighted_conflict_score",
                "conflict_score",
                "n_conflict_threads",
                "conflict_thread_rate_replied",
                "max_thread_bipolarity",
                "n_replies",
            ],
            ascending=False,
        )
    )


def build_theme_conflict_summary(
    thread_metrics: pd.DataFrame,
    video_themes: pd.DataFrame,
) -> pd.DataFrame:
    if thread_metrics.empty or video_themes.empty:
        return pd.DataFrame()
    labeled = thread_metrics.merge(
        video_themes[["video_id", "primary_theme"]], on="video_id", how="left"
    )
    rows = []
    for theme, group in labeled.groupby("primary_theme", dropna=False):
        replied = group[group["has_replies"]]
        n_conflict_threads = int(group["conflict_thread"].sum())
        conflict_rate_replied = replied["conflict_thread"].mean() if len(replied) else 0
        total_replies = float(group["n_replies"].sum())
        total_reply_like_w = float(group["reply_total_like_w"].sum())
        conflict_reply_count = float(group["conflict_reply_count_weight"].sum())
        conflict_reply_like_w = float(group["conflict_reply_like_weight"].sum())
        conflict_reply_share = divide_zero(conflict_reply_count, total_replies)
        like_weighted_conflict_reply_share = divide_zero(
            conflict_reply_like_w, total_reply_like_w
        )
        reply_count_weighted_intensity = float(
            group["conflict_reply_count_weighted_intensity"].sum()
        )
        reply_like_weighted_intensity = float(
            group["conflict_reply_like_weighted_intensity"].sum()
        )
        rows.append(
            {
                "primary_theme": theme,
                "n_threads": len(group),
                "n_threads_with_replies": len(replied),
                "n_replies": int(group["n_replies"].sum()),
                "n_conflict_threads": n_conflict_threads,
                "conflict_thread_rate_all": group["conflict_thread"].mean(),
                "conflict_thread_rate_replied": conflict_rate_replied,
                "conflict_score": n_conflict_threads * conflict_rate_replied,
                "reply_count_weighted_conflict_score": (
                    n_conflict_threads * conflict_reply_share
                ),
                "like_weighted_conflict_score": (
                    n_conflict_threads * like_weighted_conflict_reply_share
                ),
                "conflict_reply_count": conflict_reply_count,
                "conflict_reply_share": conflict_reply_share,
                "conflict_reply_like_weight": conflict_reply_like_w,
                "like_weighted_conflict_reply_share": (
                    like_weighted_conflict_reply_share
                ),
                "reply_count_weighted_conflict_intensity": divide_zero(
                    reply_count_weighted_intensity, total_replies
                ),
                "like_weighted_conflict_intensity": divide_zero(
                    reply_like_weighted_intensity, total_reply_like_w
                ),
                "n_pile_on_threads": int(group["pile_on_thread"].sum()),
                "n_parent_opposition_threads": int(
                    group["parent_opposition_thread"].sum()
                ),
                "avg_thread_bipolarity": group["thread_bipolarity"].mean(),
                "max_thread_bipolarity": group["thread_bipolarity"].max(),
                "avg_reply_bipolarity": replied["reply_bipolarity"].mean()
                if len(replied)
                else 0,
            }
        )
    return pd.DataFrame(rows).sort_values(
        [
            "like_weighted_conflict_score",
            "reply_count_weighted_conflict_score",
            "conflict_score",
            "n_conflict_threads",
            "conflict_thread_rate_replied",
        ],
        ascending=False,
    )


def render_supplement_section(payload: dict, language: str = "en") -> str:
    zh = language == "zh"
    channel = payload["channel"]
    overview = payload["reply_thread_overview"][0] if payload.get("reply_thread_overview") else {}
    if zh:
        lines = [
            "## 留言互動深度分析",
            "",
            "### 用途",
            "",
            "本章專門分析 reply thread 中的互動品質、衝突與極化 proxy。前面章節仍只用 top-level comments 估計頻道整體社群結構；本章不要拿來取代核心留言者、co-commenter network 或 benchmark 指標。",
            "",
            "### 分析範圍",
            "",
            f"- 全部留言：{overview.get('n_all_comments', 0):,}",
            f"- Top-level comments：{overview.get('n_top_level_comments', 0):,}",
            f"- Replies：{overview.get('n_replies', 0):,}",
            f"- Reply share：{_pct(overview.get('reply_share_all_comments'))}",
            f"- 有 replies 的 threads：{overview.get('n_threads_with_replies', 0):,} / {overview.get('n_threads', 0):,}",
            f"- Sentiment source：`{overview.get('sentiment_source')}`，coverage={_pct(overview.get('sentiment_coverage'))}",
            "",
            "### 指標定義",
            "",
            "- `thread_bipolarity = 4 * positive_rate * negative_rate`，正負情緒同時高時接近 1；單邊負面或單邊正面時較低。",
            "- `reply_bipolarity`：只在 replies 中計算的 bipolarity。",
            "- `conflict_thread`：有 replies，且整串或 replies 中正負比例都達到可觀門檻的 thread；這是極化 proxy，不等於人工判定吵架。",
            "- `conflict_score = n_conflict_threads * conflict_thread_rate_replied`；這是 structural score，兼顧衝突 thread 數量與 replied threads 中的衝突比例，但不含 reply 數或 like 權重。",
            "- `reply_count_weighted_conflict_score = n_conflict_threads * conflict_reply_share`；用 replies 數量加權，避免少量 replies 的小衝突被高估。",
            "- `like_weighted_conflict_score = n_conflict_threads * like_weighted_conflict_reply_share`；用 reply like weight 加權，衡量衝突是否被留言區按讚放大。",
            "- `strict_reply_conflict_thread`：replies 中同時至少有一則 positive 和一則 negative。",
            "- `pile_on_thread`：replies 至少 3 則，且負面 replies 明顯集中；代表圍攻/集體負面 proxy。",
            "- `parent_opposition_thread`：top-level 留言與 replies 的主要情緒方向相反；代表回嘴/反駁 proxy。",
            "",
            "### 核心表格",
        ]
    else:
        lines = [
            "## Commenter Deeper Analysis",
            "",
            "### Purpose",
            "",
            "This section measures reply-thread interaction quality, conflict, and polarization proxies. Earlier sections remain top-level-only for audience structure, co-commenter networks, and benchmarkable community metrics.",
            "",
            "### Scope",
            "",
            f"- All comments: {overview.get('n_all_comments', 0):,}",
            f"- Top-level comments: {overview.get('n_top_level_comments', 0):,}",
            f"- Replies: {overview.get('n_replies', 0):,}",
            f"- Reply share: {_pct(overview.get('reply_share_all_comments'))}",
            f"- Threads with replies: {overview.get('n_threads_with_replies', 0):,} / {overview.get('n_threads', 0):,}",
            f"- Sentiment source: `{overview.get('sentiment_source')}`, coverage={_pct(overview.get('sentiment_coverage'))}",
            "",
            "### Metric Definitions",
            "",
            "- `thread_bipolarity = 4 * positive_rate * negative_rate`; it approaches 1 when both positive and negative comments are substantial.",
            "- `reply_bipolarity`: the same metric computed only inside replies.",
            "- `conflict_thread`: a thread with replies where positive and negative sentiment both pass meaningful thresholds. This is a polarization proxy, not human-coded argument detection.",
            "- `conflict_score = n_conflict_threads * conflict_thread_rate_replied`; a structural score based on conflict-thread count and conflict rate among replied threads. It does not include reply volume or like weight.",
            "- `reply_count_weighted_conflict_score = n_conflict_threads * conflict_reply_share`; reply-count weighted conflict impact.",
            "- `like_weighted_conflict_score = n_conflict_threads * like_weighted_conflict_reply_share`; like-weighted conflict impact inside replies.",
            "- `strict_reply_conflict_thread`: replies include at least one positive and one negative comment.",
            "- `pile_on_thread`: at least 3 replies and negative replies are highly concentrated; a pile-on proxy.",
            "- `parent_opposition_thread`: top-level sentiment and reply sentiment point in opposite directions; a pushback proxy.",
            "",
            "### Core Tables",
        ]

    table_specs = [
        (
            "Reply Overview" if not zh else "Reply 總覽",
            "reply_thread_overview",
            [
                "sentiment_source",
                "n_all_comments",
                "n_top_level_comments",
                "n_replies",
                "reply_share_all_comments",
                "n_threads",
                "n_threads_with_replies",
                "pct_threads_with_replies",
                "n_reply_commenters",
                "sentiment_coverage",
                "reply_sentiment_coverage",
            ],
            5,
        ),
        (
            "Reply Sentiment" if not zh else "Top-level vs Reply 情緒",
            "reply_sentiment_summary",
            [
                "is_top_level_label",
                "n_comments",
                "negative_rate",
                "like_weighted_negative_rate",
                "positive_rate",
                "like_weighted_positive_rate",
            ],
            5,
        ),
        (
            "Conflict Hotspot Videos" if not zh else "影片衝突熱點",
            "reply_conflict_video_summary",
            [
                "video_id",
                "primary_theme",
                "conflict_score",
                "reply_count_weighted_conflict_score",
                "like_weighted_conflict_score",
                "conflict_reply_share",
                "like_weighted_conflict_reply_share",
                "n_threads_with_replies",
                "n_replies",
                "n_conflict_threads",
                "conflict_thread_rate_replied",
                "n_pile_on_threads",
                "n_parent_opposition_threads",
                "max_thread_bipolarity",
                "reply_negative_rate",
                "reply_positive_rate",
                "title",
            ],
            12,
        ),
        (
            "Theme Conflict" if not zh else "主題衝突摘要",
            "reply_conflict_theme_summary",
            [
                "primary_theme",
                "conflict_score",
                "reply_count_weighted_conflict_score",
                "like_weighted_conflict_score",
                "conflict_reply_share",
                "like_weighted_conflict_reply_share",
                "n_threads_with_replies",
                "n_replies",
                "n_conflict_threads",
                "conflict_thread_rate_replied",
                "n_pile_on_threads",
                "n_parent_opposition_threads",
                "avg_thread_bipolarity",
            ],
            12,
        ),
    ]
    for title, key, cols, limit in table_specs:
        lines.extend(["", f"#### {title}", "", _markdown_table(payload.get(key, []), limit=limit, keys=cols)])

    if zh:
        lines.extend([
            "",
            "### 補充檔案",
            "",
            "- `tables/reply_thread_metrics.csv` 含每個 thread 的 thread-level 指標，不含原始留言文字。",
            "- `tables/reply_conflict_video_summary.csv` 和 `tables/reply_conflict_theme_summary.csv` 是主要下游分析表。",
        ])
    else:
        lines.extend([
            "",
            "### Supplemental Files",
            "",
            "- `tables/reply_thread_metrics.csv` contains thread-level metrics for every thread, without raw comment text.",
            "- `tables/reply_conflict_video_summary.csv` and `tables/reply_conflict_theme_summary.csv` are the main downstream analysis tables.",
        ])
    return "\n".join(lines) + "\n"


def _merge_section_into_report(path: Path, section: str, *, title: str) -> None:
    if path.exists():
        base = path.read_text(encoding="utf-8")
    else:
        base = f"# {title}\n\n"
    base = _remove_existing_section(base)
    merged = (
        base.rstrip()
        + "\n\n"
        + SUPPLEMENT_START
        + "\n"
        + section.rstrip()
        + "\n"
        + SUPPLEMENT_END
        + "\n"
    )
    path.write_text(merged, encoding="utf-8")


def _remove_existing_section(text: str) -> str:
    if SUPPLEMENT_START not in text or SUPPLEMENT_END not in text:
        return text
    before, rest = text.split(SUPPLEMENT_START, 1)
    _, after = rest.split(SUPPLEMENT_END, 1)
    return (before.rstrip() + "\n\n" + after.lstrip()).rstrip() + "\n"


def _merge_supplement_json(path: Path, supplement_payload: dict) -> None:
    if path.exists() and path.stat().st_size > 0:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            payload = {}
    else:
        payload = {}
    payload["commenter_deeper_analysis"] = supplement_payload
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )


def _remove_legacy_supplement_reports(run_dir: Path) -> None:
    for name in ["report_supplement_en.md", "report_supplement_zh.md"]:
        path = run_dir / name
        if path.exists():
            path.unlink()


def _pct(value: object) -> str:
    try:
        numeric = float(value)
    except Exception:
        return "n/a"
    if math.isnan(numeric):
        return "n/a"
    return f"{numeric * 100:.1f}%"


def divide_zero(numerator: float, denominator: float) -> float:
    if denominator == 0 or math.isnan(denominator):
        return 0.0
    return numerator / denominator


def _write_csv(path: Path, df: pd.DataFrame) -> None:
    df.to_csv(path, index=False)
