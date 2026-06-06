from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import json
import math

import numpy as np
import pandas as pd

from .config import AnalyzerConfig, output_slug
from .data import ChannelData
from .network_analysis import build_network_outputs, build_video_cluster_outputs
from .themes import label_video_themes, summarize_theme_sources, summarize_themes


NEGATIVE_KEYWORDS = [
    "失望",
    "難看",
    "爛",
    "討厭",
    "噁",
    "尷尬",
    "退訂",
    "不好笑",
    "批評",
    "disappointed",
    "boring",
    "bad",
    "terrible",
    "hate",
    "cringe",
    "unsubscribe",
]


@dataclass(frozen=True)
class RunArtifacts:
    run_dir: Path
    tables_dir: Path
    figures_dir: Path
    report_path: Path
    report_en_path: Path
    report_zh_path: Path
    report_json_path: Path


def run_analysis(
    config: AnalyzerConfig,
    data: ChannelData,
    output_dir: Path | None = None,
    sentiment_data: ChannelData | None = None,
) -> RunArtifacts:
    slug = output_slug(config, data.channel.get("title"))
    run_dir = output_dir or (Path(__file__).resolve().parents[1] / "runs" / slug)
    tables_dir = run_dir / "tables"
    figures_dir = run_dir / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    videos = data.videos.copy()
    comments = data.comments.copy()
    sentiment_comments = (
        sentiment_data.comments.copy() if sentiment_data is not None else comments.copy()
    )

    channel_overview = build_channel_overview(data.channel, videos, comments)
    video_metrics = build_video_metrics(videos, comments)
    sentiment_video_metrics = build_video_metrics(videos, sentiment_comments)
    commenter_activity = build_commenter_activity(comments)
    commenter_tiers = assign_commenter_tiers(commenter_activity, config)
    continuity = build_continuity_summary(videos, comments, config)
    continuity_sensitivity = build_continuity_sensitivity(videos, comments, config)
    rolling_retention = build_rolling_retention(videos, comments, config)
    (
        network_summary,
        community_summary,
        bridge_actors,
        actor_communities,
        network_actor_metrics,
    ) = build_network_outputs(comments, config)
    bridge_actors = attach_actor_profiles(bridge_actors, commenter_activity)
    actor_communities = attach_actor_profiles(actor_communities, commenter_activity)
    network_actor_metrics = attach_actor_profiles(
        network_actor_metrics, commenter_activity
    )
    qwen_theme_path = tables_dir / "qwen_video_themes.csv"
    video_themes = label_video_themes(videos, qwen_path=qwen_theme_path)
    video_theme_labels = explode_video_theme_labels(video_themes)
    theme_summary = summarize_themes(video_themes, comments)
    theme_source_summary = summarize_theme_sources(video_themes)
    community_profiles = build_community_profiles(
        actor_communities, comments, video_themes, community_summary
    )
    community_theme_affinity = build_community_theme_affinity(
        actor_communities, comments, video_theme_labels
    )
    (
        video_network_summary,
        video_cluster_summary,
        video_clusters,
        video_cluster_theme_affinity,
        video_network_metrics,
        video_link_opportunities,
    ) = build_video_cluster_outputs(videos, comments, video_themes, video_theme_labels, config)
    qwen_sentiment_path = tables_dir / "qwen_comment_sentiment.csv"
    (
        sentiment_source_summary,
        sentiment_summary,
        sentiment_theme_summary,
        sentiment_hotspots,
        community_sentiment_summary,
        community_theme_sentiment,
        video_cluster_sentiment_summary,
    ) = build_sentiment_outputs(
        sentiment_video_metrics,
        sentiment_comments,
        video_themes,
        qwen_sentiment_path,
        actor_communities,
        video_clusters,
    )
    diagnostics = build_diagnostics(
        channel_overview=channel_overview,
        commenter_tiers=commenter_tiers,
        continuity_sensitivity=continuity_sensitivity,
        rolling_retention=rolling_retention,
        network_summary=network_summary,
        community_summary=community_summary,
        community_theme_affinity=community_theme_affinity,
        video_network_summary=video_network_summary,
        video_cluster_summary=video_cluster_summary,
        video_cluster_theme_affinity=video_cluster_theme_affinity,
    )

    _write_csv(tables_dir / "channel_overview.csv", channel_overview)
    _write_csv(tables_dir / "diagnostics.csv", diagnostics)
    _write_csv(tables_dir / "video_metrics.csv", video_metrics)
    _write_csv(tables_dir / "commenter_activity.csv", commenter_activity)
    _write_csv(tables_dir / "commenter_tiers.csv", commenter_tiers)
    _write_csv(tables_dir / "continuity_summary.csv", continuity)
    _write_csv(tables_dir / "continuity_sensitivity.csv", continuity_sensitivity)
    _write_csv(tables_dir / "rolling_retention.csv", rolling_retention)
    _write_csv(tables_dir / "network_summary.csv", network_summary)
    _write_csv(tables_dir / "community_summary.csv", community_summary)
    _write_csv(tables_dir / "community_profiles.csv", community_profiles)
    _write_csv(tables_dir / "community_theme_affinity.csv", community_theme_affinity)
    _write_csv(tables_dir / "bridge_actors.csv", bridge_actors)
    _write_csv(tables_dir / "actor_communities.csv", actor_communities)
    _write_csv(tables_dir / "network_actor_metrics.csv", network_actor_metrics)
    _write_csv(tables_dir / "theme_video_labels.csv", video_themes)
    _write_csv(tables_dir / "theme_video_labels_long.csv", video_theme_labels)
    _write_csv(tables_dir / "theme_source_summary.csv", theme_source_summary)
    _write_csv(tables_dir / "theme_summary.csv", theme_summary)
    _write_csv(tables_dir / "video_network_summary.csv", video_network_summary)
    _write_csv(tables_dir / "video_cluster_summary.csv", video_cluster_summary)
    _write_csv(tables_dir / "video_clusters.csv", video_clusters)
    _write_csv(tables_dir / "video_cluster_theme_affinity.csv", video_cluster_theme_affinity)
    _write_csv(tables_dir / "video_network_metrics.csv", video_network_metrics)
    _write_csv(tables_dir / "video_link_opportunities.csv", video_link_opportunities)
    _write_csv(tables_dir / "sentiment_source_summary.csv", sentiment_source_summary)
    _write_csv(tables_dir / "sentiment_summary.csv", sentiment_summary)
    _write_csv(tables_dir / "sentiment_theme_summary.csv", sentiment_theme_summary)
    _write_csv(tables_dir / "sentiment_hotspots.csv", sentiment_hotspots)
    _write_csv(tables_dir / "community_sentiment_summary.csv", community_sentiment_summary)
    _write_csv(tables_dir / "community_theme_sentiment.csv", community_theme_sentiment)
    _write_csv(tables_dir / "video_cluster_sentiment_summary.csv", video_cluster_sentiment_summary)

    write_figures(
        figures_dir,
        video_metrics,
        commenter_tiers,
        community_summary,
        rolling_retention,
        video_cluster_summary,
    )

    report_data = build_report_payload(
        config=config,
        channel=data.channel,
        channel_overview=channel_overview,
        diagnostics=diagnostics,
        continuity=continuity,
        continuity_sensitivity=continuity_sensitivity,
        rolling_retention=rolling_retention,
        commenter_tiers=commenter_tiers,
        network_summary=network_summary,
        community_summary=community_summary,
        community_profiles=community_profiles,
        community_theme_affinity=community_theme_affinity,
        bridge_actors=bridge_actors,
        network_actor_metrics=network_actor_metrics,
        theme_source_summary=theme_source_summary,
        theme_summary=theme_summary,
        video_network_summary=video_network_summary,
        video_cluster_summary=video_cluster_summary,
        video_cluster_theme_affinity=video_cluster_theme_affinity,
        video_network_metrics=video_network_metrics,
        video_link_opportunities=video_link_opportunities,
        sentiment_source_summary=sentiment_source_summary,
        sentiment_summary=sentiment_summary,
        sentiment_theme_summary=sentiment_theme_summary,
        sentiment_hotspots=sentiment_hotspots,
        community_sentiment_summary=community_sentiment_summary,
        community_theme_sentiment=community_theme_sentiment,
        video_cluster_sentiment_summary=video_cluster_sentiment_summary,
    )
    report_path = run_dir / "report.md"
    report_en_path = run_dir / "report_en.md"
    report_zh_path = run_dir / "report_zh.md"
    report_json_path = run_dir / "report.json"
    report_en = render_report(report_data, language="en")
    report_zh = render_report(report_data, language="zh")
    report_path.write_text(report_en, encoding="utf-8")
    report_en_path.write_text(report_en, encoding="utf-8")
    report_zh_path.write_text(report_zh, encoding="utf-8")
    for stale_name in ["report_base.md", "report_base_en.md", "report_base_zh.md"]:
        stale_path = run_dir / stale_name
        if stale_path.exists():
            stale_path.unlink()
    report_json_path.write_text(
        json.dumps(report_data, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    (run_dir / "resolved_config.json").write_text(
        json.dumps(asdict(config), ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    return RunArtifacts(
        run_dir=run_dir,
        tables_dir=tables_dir,
        figures_dir=figures_dir,
        report_path=report_path,
        report_en_path=report_en_path,
        report_zh_path=report_zh_path,
        report_json_path=report_json_path,
    )


def build_channel_overview(
    channel: dict,
    videos: pd.DataFrame,
    comments: pd.DataFrame,
) -> pd.DataFrame:
    row = {
        "channel_id": channel.get("channel_id"),
        "channel_title": channel.get("title"),
        "subscriber_count": channel.get("subscriber_count"),
        "channel_video_count_api": channel.get("video_count"),
        "channel_view_count_api": channel.get("view_count"),
        "n_videos_in_scope": len(videos),
        "n_comments_in_scope": len(comments),
        "n_commenters_in_scope": comments["author_actor_id"].nunique(),
        "date_min": videos["published_at"].min(),
        "date_max": videos["published_at"].max(),
        "total_views_in_scope": videos["view_count"].fillna(0).sum(),
        "total_video_comment_count_api": videos["comment_count"].fillna(0).sum(),
    }
    return pd.DataFrame([row])


def build_video_metrics(videos: pd.DataFrame, comments: pd.DataFrame) -> pd.DataFrame:
    cstats = (
        comments.groupby("video_id")
        .agg(
            observed_comments=("comment_id", "count"),
            observed_commenters=("author_actor_id", "nunique"),
            observed_comment_likes=("like_count", "sum"),
        )
        .reset_index()
    )
    out = videos.merge(cstats, on="video_id", how="left")
    for col in ["observed_comments", "observed_commenters", "observed_comment_likes"]:
        out[col] = out[col].fillna(0).astype(int)
    out["published_month"] = (
        out["published_at"].dt.tz_convert(None).dt.to_period("M").astype(str)
    )
    return out[
        [
            "video_id",
            "title",
            "published_at",
            "published_month",
            "view_count",
            "like_count",
            "comment_count",
            "observed_comments",
            "observed_commenters",
            "observed_comment_likes",
        ]
    ]


def build_commenter_activity(comments: pd.DataFrame) -> pd.DataFrame:
    agg = {
        "n_comments": ("comment_id", "count"),
        "n_videos": ("video_id", "nunique"),
        "comment_likes_received": ("like_count", "sum"),
        "first_comment_at": ("comment_published_at", "min"),
        "last_comment_at": ("comment_published_at", "max"),
    }
    if "author_display_name" in comments.columns:
        agg["author_display_name"] = ("author_display_name", _first_non_null)
    if "author_channel_url" in comments.columns:
        agg["author_channel_url"] = ("author_channel_url", _first_non_null)
    return (
        comments.groupby("author_actor_id")
        .agg(**agg)
        .reset_index()
        .sort_values(["n_videos", "n_comments"], ascending=False)
    )


def _first_non_null(values: pd.Series) -> object:
    non_null = values.dropna()
    if non_null.empty:
        return None
    return non_null.iloc[0]


def assign_commenter_tiers(
    activity: pd.DataFrame,
    config: AnalyzerConfig,
) -> pd.DataFrame:
    out = activity.copy()
    high = config.analysis.high_activity_min_videos
    mid = config.analysis.mid_activity_min_videos
    out["activity_tier"] = np.select(
        [out["n_videos"] >= high, out["n_videos"] >= mid],
        ["high", "mid"],
        default="low",
    )
    summary = (
        out.groupby("activity_tier")
        .agg(
            n_commenters=("author_actor_id", "count"),
            avg_videos=("n_videos", "mean"),
            median_videos=("n_videos", "median"),
            total_comments=("n_comments", "sum"),
            total_likes_received=("comment_likes_received", "sum"),
        )
        .reset_index()
    )
    total = summary["n_commenters"].sum()
    summary["pct_commenters"] = summary["n_commenters"] / total * 100 if total else 0
    order = pd.Categorical(summary["activity_tier"], ["high", "mid", "low"], ordered=True)
    return summary.assign(_order=order).sort_values("_order").drop(columns="_order")


def build_continuity_summary(
    videos: pd.DataFrame,
    comments: pd.DataFrame,
    config: AnalyzerConfig,
) -> pd.DataFrame:
    n_windows = max(2, config.analysis.continuity_windows)
    return _build_window_continuity(videos, comments, n_windows)


def _build_window_continuity(
    videos: pd.DataFrame,
    comments: pd.DataFrame,
    n_windows: int,
) -> pd.DataFrame:
    ordered = videos.sort_values("published_at").reset_index(drop=True)
    splits = np.array_split(ordered.index.to_numpy(), n_windows)
    video_window = {}
    window_rows = []
    for i, idxs in enumerate(splits):
        if len(idxs) == 0:
            continue
        sub = ordered.loc[idxs]
        for video_id in sub["video_id"]:
            video_window[video_id] = i
        window_rows.append(
            {
                "window": i,
                "start": sub["published_at"].min(),
                "end": sub["published_at"].max(),
                "n_videos": len(sub),
            }
        )

    c = comments[["author_actor_id", "video_id"]].drop_duplicates().copy()
    c["window"] = c["video_id"].map(video_window)
    c = c.dropna(subset=["window"])
    actor_sets = {
        int(window): set(group["author_actor_id"])
        for window, group in c.groupby("window")
    }
    rows = []
    for i in range(len(window_rows) - 1):
        base = actor_sets.get(i, set())
        nxt = actor_sets.get(i + 1, set())
        returned = base & nxt
        rows.append(
            {
                "transition": f"{i}->{i + 1}",
                "from_start": window_rows[i]["start"],
                "from_end": window_rows[i]["end"],
                "to_start": window_rows[i + 1]["start"],
                "to_end": window_rows[i + 1]["end"],
                "from_n_videos": window_rows[i]["n_videos"],
                "to_n_videos": window_rows[i + 1]["n_videos"],
                "n_base_commenters": len(base),
                "n_returned_next_window": len(returned),
                "return_rate": len(returned) / len(base) if base else math.nan,
                "non_return_rate": 1 - len(returned) / len(base) if base else math.nan,
            }
        )
    return pd.DataFrame(rows)


def build_continuity_sensitivity(
    videos: pd.DataFrame,
    comments: pd.DataFrame,
    config: AnalyzerConfig,
) -> pd.DataFrame:
    rows = []
    for n_windows in _parse_window_options(config.analysis.continuity_window_options):
        continuity = _build_window_continuity(videos, comments, n_windows)
        if continuity.empty:
            continue
        total_base = continuity["n_base_commenters"].sum()
        total_returned = continuity["n_returned_next_window"].sum()
        weighted_return = total_returned / total_base if total_base else math.nan
        rows.append(
            {
                "n_windows": n_windows,
                "n_transitions": len(continuity),
                "total_base_commenters_across_transitions": total_base,
                "weighted_return_rate": weighted_return,
                "weighted_non_return_rate": 1 - weighted_return if total_base else math.nan,
                "median_return_rate": continuity["return_rate"].median(),
                "min_return_rate": continuity["return_rate"].min(),
                "max_return_rate": continuity["return_rate"].max(),
            }
        )
    return pd.DataFrame(rows)


def build_rolling_retention(
    videos: pd.DataFrame,
    comments: pd.DataFrame,
    config: AnalyzerConfig,
) -> pd.DataFrame:
    pre_n = max(1, config.analysis.rolling_window_videos)
    post_n = max(1, config.analysis.rolling_horizon_videos)
    step = max(1, config.analysis.rolling_step_videos)
    ordered = videos.sort_values("published_at").reset_index(drop=True)
    if len(ordered) < pre_n + post_n:
        return pd.DataFrame()

    actor_video = comments[["author_actor_id", "video_id"]].drop_duplicates()
    actors_by_video = {
        video_id: set(group["author_actor_id"])
        for video_id, group in actor_video.groupby("video_id")
    }
    rows = []
    max_start = len(ordered) - pre_n - post_n
    for start in range(0, max_start + 1, step):
        pre = ordered.iloc[start : start + pre_n]
        post = ordered.iloc[start + pre_n : start + pre_n + post_n]
        base = _union_actor_sets(pre["video_id"], actors_by_video)
        future = _union_actor_sets(post["video_id"], actors_by_video)
        returned = base & future
        rows.append(
            {
                "cutoff_video_index": start + pre_n,
                "pre_start": pre["published_at"].min(),
                "pre_end": pre["published_at"].max(),
                "post_start": post["published_at"].min(),
                "post_end": post["published_at"].max(),
                "pre_n_videos": len(pre),
                "post_n_videos": len(post),
                "n_base_commenters": len(base),
                "n_returned": len(returned),
                "return_rate": len(returned) / len(base) if base else math.nan,
                "non_return_rate": 1 - len(returned) / len(base) if base else math.nan,
            }
        )
    return pd.DataFrame(rows)


def _union_actor_sets(video_ids: pd.Series, actors_by_video: dict[str, set[str]]) -> set[str]:
    actors: set[str] = set()
    for video_id in video_ids:
        actors.update(actors_by_video.get(video_id, set()))
    return actors


def _parse_window_options(raw: str) -> list[int]:
    values = []
    for part in str(raw).split(","):
        part = part.strip()
        if not part:
            continue
        try:
            value = int(part)
        except ValueError:
            continue
        if value >= 2:
            values.append(value)
    return sorted(set(values)) or [3, 4, 6, 8]


def attach_actor_profiles(
    frame: pd.DataFrame,
    commenter_activity: pd.DataFrame,
) -> pd.DataFrame:
    if frame.empty or "author_actor_id" not in frame.columns:
        return frame
    cols = ["author_actor_id"]
    for col in ["author_display_name", "author_channel_url", "n_comments", "n_videos"]:
        if col in commenter_activity.columns:
            cols.append(col)
    return frame.merge(commenter_activity[cols], on="author_actor_id", how="left")


def explode_video_theme_labels(video_themes: pd.DataFrame) -> pd.DataFrame:
    if video_themes.empty:
        return pd.DataFrame()
    rows = []
    for row in video_themes.itertuples(index=False):
        labels = str(getattr(row, "theme_labels", "") or "other").split(";")
        for label in labels:
            label = label.strip()
            if not label:
                continue
            rows.append(
                {
                    "video_id": row.video_id,
                    "title": row.title,
                    "published_at": row.published_at,
                    "primary_theme": row.primary_theme,
                    "theme_label": label,
                }
            )
    return pd.DataFrame(rows)


def build_community_profiles(
    actor_communities: pd.DataFrame,
    comments: pd.DataFrame,
    video_themes: pd.DataFrame,
    community_summary: pd.DataFrame,
) -> pd.DataFrame:
    if actor_communities.empty:
        return pd.DataFrame()
    c = comments.merge(
        actor_communities[["author_actor_id", "community"]],
        on="author_actor_id",
        how="inner",
    )
    if c.empty:
        return pd.DataFrame()
    video_cols = ["video_id", "title", "primary_theme"]
    c = c.merge(video_themes[video_cols], on="video_id", how="left")
    rows = []
    for comm, group in c.groupby("community"):
        top_videos = (
            group.groupby(["video_id", "title"])
            .agg(n_comments=("comment_id", "count"), n_commenters=("author_actor_id", "nunique"))
            .reset_index()
            .sort_values(["n_commenters", "n_comments"], ascending=False)
            .head(5)
        )
        top_themes = (
            group.groupby("primary_theme")
            .agg(n_comments=("comment_id", "count"), n_commenters=("author_actor_id", "nunique"))
            .reset_index()
            .sort_values(["n_commenters", "n_comments"], ascending=False)
            .head(5)
        )
        rows.append(
            {
                "community": comm,
                "n_commenters": group["author_actor_id"].nunique(),
                "n_comments": len(group),
                "n_videos_touched": group["video_id"].nunique(),
                "top_primary_themes": _join_ranked(
                    top_themes, "primary_theme", "n_commenters"
                ),
                "top_comment_videos": _join_ranked(top_videos, "title", "n_commenters"),
            }
        )
    out = pd.DataFrame(rows)
    if not community_summary.empty:
        out = out.merge(
            community_summary[["community", "n_nodes", "pct_nodes"]],
            on="community",
            how="left",
        )
    return out.sort_values("n_commenters", ascending=False)


def build_community_theme_affinity(
    actor_communities: pd.DataFrame,
    comments: pd.DataFrame,
    video_theme_labels: pd.DataFrame,
) -> pd.DataFrame:
    if actor_communities.empty or video_theme_labels.empty:
        return pd.DataFrame()
    actor_video = comments[["author_actor_id", "video_id"]].drop_duplicates()
    actor_video = actor_video.merge(
        actor_communities[["author_actor_id", "community"]],
        on="author_actor_id",
        how="inner",
    )
    if actor_video.empty:
        return pd.DataFrame()
    labeled = actor_video.merge(
        video_theme_labels[["video_id", "theme_label"]],
        on="video_id",
        how="inner",
    )
    if labeled.empty:
        return pd.DataFrame()

    community_totals = actor_video.groupby("community").size().rename("community_pairs")
    overall_total = len(actor_video)
    overall_counts = labeled.groupby("theme_label").size().rename("overall_label_pairs")
    rows = (
        labeled.groupby(["community", "theme_label"])
        .agg(
            n_actor_video_pairs=("video_id", "count"),
            n_commenters=("author_actor_id", "nunique"),
            n_videos=("video_id", "nunique"),
        )
        .reset_index()
        .merge(community_totals.reset_index(), on="community", how="left")
        .merge(overall_counts.reset_index(), on="theme_label", how="left")
    )
    rows["community_share"] = rows["n_actor_video_pairs"] / rows["community_pairs"]
    rows["overall_share"] = rows["overall_label_pairs"] / overall_total
    rows["lift"] = rows["community_share"] / rows["overall_share"].replace(0, np.nan)
    return rows.sort_values(
        ["community_pairs", "community", "lift", "n_actor_video_pairs"],
        ascending=[False, True, False, False],
    )


def build_diagnostics(
    channel_overview: pd.DataFrame,
    commenter_tiers: pd.DataFrame,
    continuity_sensitivity: pd.DataFrame,
    rolling_retention: pd.DataFrame,
    network_summary: pd.DataFrame,
    community_summary: pd.DataFrame,
    community_theme_affinity: pd.DataFrame,
    video_network_summary: pd.DataFrame,
    video_cluster_summary: pd.DataFrame,
    video_cluster_theme_affinity: pd.DataFrame,
) -> pd.DataFrame:
    rows = []
    overview = channel_overview.iloc[0].to_dict() if not channel_overview.empty else {}

    low = _tier_row(commenter_tiers, "low")
    high = _tier_row(commenter_tiers, "high")
    if low:
        rows.append(
            {
                "area": "audience_mix",
                "metric": "low_tier_share",
                "value": low.get("pct_commenters"),
                "diagnosis": (
                    "Commenting audience is casual-heavy; interpret raw commenter counts as reach, "
                    "not loyal community size."
                    if float(low.get("pct_commenters") or 0) >= 80
                    else "Commenting audience has a substantial repeat-participant base."
                ),
            }
        )
    if high:
        rows.append(
            {
                "area": "audience_mix",
                "metric": "high_tier_commenters",
                "value": high.get("n_commenters"),
                "diagnosis": (
                    f"Core repeat commenters are a small but measurable segment "
                    f"({high.get('n_commenters')} actors)."
                ),
            }
        )

    if not continuity_sensitivity.empty:
        ret_min = continuity_sensitivity["weighted_return_rate"].min()
        ret_max = continuity_sensitivity["weighted_return_rate"].max()
        rows.append(
            {
                "area": "retention",
                "metric": "window_sensitivity_return_range",
                "value": f"{ret_min:.3f}-{ret_max:.3f}",
                "diagnosis": (
                    "Fixed-window retention is stable across tested window counts."
                    if ret_max - ret_min <= 0.08
                    else "Retention depends on window choice; use rolling retention before making trend claims."
                ),
            }
        )
    if not rolling_retention.empty:
        ret_min = rolling_retention["return_rate"].min()
        ret_max = rolling_retention["return_rate"].max()
        rows.append(
            {
                "area": "retention",
                "metric": "rolling_return_range",
                "value": f"{ret_min:.3f}-{ret_max:.3f}",
                "diagnosis": "Rolling retention shows when repeat-commenter continuity strengthens or weakens over the channel timeline.",
            }
        )

    if not network_summary.empty and not community_summary.empty:
        net = network_summary.iloc[0]
        largest = community_summary.sort_values("n_nodes", ascending=False).iloc[0]
        rows.append(
            {
                "area": "audience_structure",
                "metric": "audience_communities",
                "value": int(net.get("n_communities", 0)),
                "diagnosis": (
                    f"The commenter graph separates into {int(net.get('n_communities', 0))} communities; "
                    f"largest community contains {largest.get('pct_nodes'):.1f}% of graph actors."
                ),
            }
        )
        rows.append(
            {
                "area": "audience_structure",
                "metric": "community_concentration_hhi",
                "value": f"{float(net.get('community_concentration_hhi') or 0):.3f}",
                "diagnosis": (
                    f"Community-size concentration HHI is {float(net.get('community_concentration_hhi') or 0):.3f}; "
                    f"effective communities are about {float(net.get('effective_communities') or 0):.1f}."
                ),
            }
        )
        rows.append(
            {
                "area": "audience_structure",
                "metric": "max_k_core",
                "value": int(net.get("max_core_number") or 0),
                "diagnosis": (
                    f"The co-commenter graph has max k-core {int(net.get('max_core_number') or 0)}; "
                    "interpret this as structural embeddedness, not commenter loyalty."
                ),
            }
        )

    major_affinity = _top_major_affinity(
        community_theme_affinity,
        group_col="community",
        size_col="community_pairs",
        label_col="theme_label",
    )
    if major_affinity:
        rows.append(
            {
                "area": "audience_structure",
                "metric": "top_audience_affinity",
                "value": major_affinity["value"],
                "diagnosis": major_affinity["diagnosis"],
            }
        )

    if not video_network_summary.empty and not video_cluster_summary.empty:
        net = video_network_summary.iloc[0]
        largest = video_cluster_summary.sort_values("n_videos", ascending=False).iloc[0]
        n_videos = float(overview.get("n_videos_in_scope") or 0)
        share = float(largest.get("n_videos") or 0) / n_videos * 100 if n_videos else math.nan
        rows.append(
            {
                "area": "content_portfolio",
                "metric": "video_shared_audience_clusters",
                "value": int(net.get("n_video_clusters", 0)),
                "diagnosis": (
                    f"Videos form {int(net.get('n_video_clusters', 0))} shared-audience clusters; "
                    f"largest cluster covers {share:.1f}% of in-scope videos."
                ),
            }
        )

    cluster_affinity = _top_major_affinity(
        video_cluster_theme_affinity,
        group_col="video_cluster",
        size_col="cluster_videos",
        label_col="theme_label",
    )
    if cluster_affinity:
        rows.append(
            {
                "area": "content_portfolio",
                "metric": "top_video_cluster_affinity",
                "value": cluster_affinity["value"],
                "diagnosis": cluster_affinity["diagnosis"],
            }
        )

    return pd.DataFrame(rows)


def _tier_row(commenter_tiers: pd.DataFrame, tier: str) -> dict | None:
    if commenter_tiers.empty:
        return None
    match = commenter_tiers[commenter_tiers["activity_tier"] == tier]
    if match.empty:
        return None
    return match.iloc[0].to_dict()


def _top_major_affinity(
    affinity: pd.DataFrame,
    group_col: str,
    size_col: str,
    label_col: str,
) -> dict | None:
    if affinity.empty or size_col not in affinity.columns:
        return None
    max_size = affinity[size_col].max()
    if not max_size:
        return None
    major = affinity[affinity[size_col] >= max_size * 0.25].copy()
    major = major[major[label_col] != "other"]
    major = major[major["lift"] >= 1.2]
    if major.empty:
        return None
    row = major.sort_values(["lift", size_col], ascending=False).iloc[0]
    group = row.get(group_col)
    label = row.get(label_col)
    lift = row.get("lift")
    return {
        "value": f"{group}:{label} lift={lift:.2f}",
        "diagnosis": (
            f"{group_col} {group} over-indexes on `{label}` "
            f"(lift {lift:.2f}); use this as a segment/content-positioning clue, not as causal proof."
        ),
    }


def _join_ranked(frame: pd.DataFrame, label_col: str, value_col: str) -> str:
    values = []
    for row in frame.itertuples(index=False):
        label = str(getattr(row, label_col, "") or "")
        value = getattr(row, value_col, None)
        if not label:
            continue
        values.append(f"{label[:48]} ({value})")
    return "; ".join(values)


def build_sentiment_outputs(
    video_metrics: pd.DataFrame,
    comments: pd.DataFrame,
    video_themes: pd.DataFrame,
    qwen_sentiment_path: Path,
    actor_communities: pd.DataFrame,
    video_clusters: pd.DataFrame,
) -> tuple[
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
]:
    qwen = load_qwen_comment_sentiment(qwen_sentiment_path, comments)
    if not qwen.empty:
        return build_qwen_sentiment_outputs(
            video_metrics, comments, video_themes, qwen, actor_communities, video_clusters
        )
    return build_keyword_sentiment_outputs(
        video_metrics, comments, video_themes, actor_communities, video_clusters
    )


def load_qwen_comment_sentiment(path: Path, comments: pd.DataFrame) -> pd.DataFrame:
    if not path.exists() or path.stat().st_size <= 0:
        return pd.DataFrame()
    raw = pd.read_csv(path, low_memory=False)
    if raw.empty or "comment_id" not in raw.columns:
        return pd.DataFrame()
    for col in ["sentiment_label", "score_neg", "score_neu", "score_pos"]:
        if col not in raw.columns:
            return pd.DataFrame()
    if "sentiment_parse_error" in raw.columns:
        raw["sentiment_parse_error"] = _bool_series(raw["sentiment_parse_error"])
    else:
        raw["sentiment_parse_error"] = False
    raw_rows = len(raw)
    parse_errors = int(raw["sentiment_parse_error"].sum())
    raw = raw[~raw["sentiment_parse_error"]].copy()
    if raw.empty:
        return pd.DataFrame()

    meta_cols = ["comment_id", "video_id", "author_actor_id", "like_count", "comment_published_at"]
    for col in ["thread_id", "parent_comment_id", "is_top_level"]:
        if col in comments.columns:
            meta_cols.append(col)
    comment_meta = comments[meta_cols].copy()
    if "is_top_level" in comment_meta.columns:
        comment_meta["is_top_level"] = comment_meta["is_top_level"].astype(bool)
    keep_cols = [
        "comment_id",
        "sentiment_label",
        "score_neg",
        "score_neu",
        "score_pos",
        "target",
        "emotion_tags",
        "toxicity",
        "sentiment_confidence",
        "model",
    ]
    for col in keep_cols:
        if col not in raw.columns:
            raw[col] = None
    out = comment_meta.merge(raw[keep_cols], on="comment_id", how="inner")
    out["sentiment_label"] = out["sentiment_label"].map(_clean_sentiment_label)
    for col in ["score_neg", "score_neu", "score_pos", "toxicity", "sentiment_confidence"]:
        out[col] = pd.to_numeric(out[col], errors="coerce")
    out[["score_neg", "score_neu", "score_pos"]] = out[
        ["score_neg", "score_neu", "score_pos"]
    ].fillna(0.0)
    out["like_w"] = out["like_count"].fillna(0).astype(float) + 1.0
    out.attrs["raw_rows"] = raw_rows
    out.attrs["parse_errors"] = parse_errors
    return out


def build_qwen_sentiment_outputs(
    video_metrics: pd.DataFrame,
    comments: pd.DataFrame,
    video_themes: pd.DataFrame,
    sentiments: pd.DataFrame,
    actor_communities: pd.DataFrame,
    video_clusters: pd.DataFrame,
) -> tuple[
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
]:
    source = pd.DataFrame(
        [
            _sentiment_source_row(
                source="qwen",
                comments=comments,
                sentiments=sentiments,
                parse_errors=int(sentiments.attrs.get("parse_errors", 0)),
                notes="Qwen comment-level ternary sentiment over the sentiment scope.",
            )
        ]
    )
    return (
        source,
        _sentiment_summary(sentiments),
        _sentiment_theme_summary(sentiments, video_themes),
        _qwen_sentiment_hotspots(video_metrics, sentiments, video_themes),
        build_community_sentiment_summary(sentiments, actor_communities),
        build_community_theme_sentiment(sentiments, actor_communities, video_themes),
        build_video_cluster_sentiment_summary(sentiments, video_clusters),
    )


def build_keyword_sentiment_outputs(
    video_metrics: pd.DataFrame,
    comments: pd.DataFrame,
    video_themes: pd.DataFrame,
    actor_communities: pd.DataFrame,
    video_clusters: pd.DataFrame,
) -> tuple[
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
]:
    c = _keyword_sentiment_frame(comments)
    source = pd.DataFrame(
        [
            {
                **_sentiment_source_row(
                    source="keyword_proxy",
                    comments=comments,
                    sentiments=c,
                    parse_errors=0,
                    notes="Transparent negative-keyword proxy over the sentiment scope; not calibrated sentiment.",
                ),
            }
        ]
    )
    return (
        source,
        _sentiment_summary(c),
        _sentiment_theme_summary(c, video_themes),
        _keyword_sentiment_hotspots(video_metrics, c, video_themes),
        build_community_sentiment_summary(c, actor_communities),
        build_community_theme_sentiment(c, actor_communities, video_themes),
        build_video_cluster_sentiment_summary(c, video_clusters),
    )


def _keyword_sentiment_frame(comments: pd.DataFrame) -> pd.DataFrame:
    cols = [
        "comment_id",
        "video_id",
        "author_actor_id",
        "text_plain",
        "like_count",
        "comment_published_at",
    ]
    for col in ["thread_id", "parent_comment_id", "is_top_level"]:
        if col in comments.columns:
            cols.append(col)
    c = comments[cols].copy()
    if "is_top_level" in c.columns:
        c["is_top_level"] = c["is_top_level"].astype(bool)
    pattern = "|".join(re_escape(k) for k in NEGATIVE_KEYWORDS)
    c["risk_keyword_hit"] = c["text_plain"].fillna("").str.lower().str.contains(
        pattern, regex=True
    )
    c["sentiment_label"] = np.where(c["risk_keyword_hit"], "negative", "neutral")
    c["score_neg"] = np.where(c["risk_keyword_hit"], 0.80, 0.10)
    c["score_neu"] = np.where(c["risk_keyword_hit"], 0.10, 0.80)
    c["score_pos"] = 0.10
    c["target"] = "unclear"
    c["emotion_tags"] = np.where(c["risk_keyword_hit"], "criticism", "")
    c["toxicity"] = np.where(c["risk_keyword_hit"], 0.30, 0.0)
    c["sentiment_confidence"] = np.where(c["risk_keyword_hit"], 0.55, 0.35)
    c["like_w"] = c["like_count"].fillna(0).astype(float) + 1.0
    return c


def _sentiment_source_row(
    *,
    source: str,
    comments: pd.DataFrame,
    sentiments: pd.DataFrame,
    parse_errors: int,
    notes: str,
) -> dict:
    if "is_top_level" in comments.columns:
        n_top = int(comments["is_top_level"].astype(bool).sum())
        n_replies = int((~comments["is_top_level"].astype(bool)).sum())
    else:
        n_top = len(comments)
        n_replies = 0
    scope_label = "all_comments" if n_replies else "top_level_comments"
    return {
        "sentiment_source": source,
        "comment_scope": scope_label,
        "n_scope_comments": len(comments),
        "n_scope_top_level_comments": n_top,
        "n_scope_replies": n_replies,
        "n_scored_comments": len(sentiments),
        "coverage_rate": len(sentiments) / len(comments) if len(comments) else 0,
        "parse_errors": parse_errors,
        "notes": notes,
    }


def _sentiment_summary(sentiments: pd.DataFrame) -> pd.DataFrame:
    if sentiments.empty:
        return pd.DataFrame()
    total = len(sentiments)
    total_like_w = sentiments["like_w"].sum()
    rows = []
    for label, group in sentiments.groupby("sentiment_label"):
        like_w = group["like_w"].sum()
        row = {
            "sentiment_label": label,
            "n_comments": len(group),
            "pct_comments": len(group) / total if total else 0,
            "like_w": like_w,
            "like_weighted_share": like_w / total_like_w if total_like_w else 0,
            "avg_score_neg": group["score_neg"].mean(),
            "avg_score_neu": group["score_neu"].mean(),
            "avg_score_pos": group["score_pos"].mean(),
            "avg_confidence": group["sentiment_confidence"].mean(),
        }
        if "is_top_level" in group.columns:
            n_replies = int((~group["is_top_level"].astype(bool)).sum())
            row["n_replies"] = n_replies
            row["reply_share"] = n_replies / len(group) if len(group) else 0
        rows.append(row)
    order = {"negative": 0, "neutral": 1, "positive": 2}
    out = pd.DataFrame(rows)
    return out.assign(_order=out["sentiment_label"].map(order)).sort_values("_order").drop(columns="_order")


def _sentiment_theme_summary(
    sentiments: pd.DataFrame,
    video_themes: pd.DataFrame,
) -> pd.DataFrame:
    if sentiments.empty or video_themes.empty:
        return pd.DataFrame()
    labeled = sentiments.merge(
        video_themes[["video_id", "primary_theme"]], on="video_id", how="left"
    )
    return _sentiment_group_summary(labeled, ["primary_theme"]).sort_values(
        ["n_comments", "negative_rate"], ascending=False
    )


def build_community_sentiment_summary(
    sentiments: pd.DataFrame,
    actor_communities: pd.DataFrame,
) -> pd.DataFrame:
    if sentiments.empty or actor_communities.empty:
        return pd.DataFrame()
    labeled = sentiments.merge(
        actor_communities[["author_actor_id", "community"]].drop_duplicates(),
        on="author_actor_id",
        how="inner",
    )
    if labeled.empty:
        return pd.DataFrame()
    out = _sentiment_group_summary(labeled, ["community"])
    extras = (
        labeled.groupby("community")
        .agg(
            n_commenters=("author_actor_id", "nunique"),
            n_videos=("video_id", "nunique"),
        )
        .reset_index()
    )
    return (
        out.merge(extras, on="community", how="left")
        .sort_values(["n_comments", "like_weighted_negative_rate"], ascending=False)
    )


def build_community_theme_sentiment(
    sentiments: pd.DataFrame,
    actor_communities: pd.DataFrame,
    video_themes: pd.DataFrame,
) -> pd.DataFrame:
    if sentiments.empty or actor_communities.empty or video_themes.empty:
        return pd.DataFrame()
    labeled = sentiments.merge(
        actor_communities[["author_actor_id", "community"]].drop_duplicates(),
        on="author_actor_id",
        how="inner",
    ).merge(video_themes[["video_id", "primary_theme"]], on="video_id", how="left")
    if labeled.empty:
        return pd.DataFrame()
    out = _sentiment_group_summary(labeled, ["community", "primary_theme"])
    extras = (
        labeled.groupby(["community", "primary_theme"], dropna=False)
        .agg(
            n_commenters=("author_actor_id", "nunique"),
            n_videos=("video_id", "nunique"),
        )
        .reset_index()
    )
    return (
        out.merge(extras, on=["community", "primary_theme"], how="left")
        .sort_values(["n_comments", "like_weighted_negative_rate"], ascending=False)
    )


def build_video_cluster_sentiment_summary(
    sentiments: pd.DataFrame,
    video_clusters: pd.DataFrame,
) -> pd.DataFrame:
    if sentiments.empty or video_clusters.empty:
        return pd.DataFrame()
    labeled = sentiments.merge(
        video_clusters[["video_id", "video_cluster"]].drop_duplicates(),
        on="video_id",
        how="inner",
    )
    if labeled.empty:
        return pd.DataFrame()
    out = _sentiment_group_summary(labeled, ["video_cluster"])
    extras = (
        labeled.groupby("video_cluster")
        .agg(
            n_commenters=("author_actor_id", "nunique"),
            n_videos=("video_id", "nunique"),
        )
        .reset_index()
    )
    return (
        out.merge(extras, on="video_cluster", how="left")
        .sort_values(["n_comments", "like_weighted_negative_rate"], ascending=False)
    )


def _qwen_sentiment_hotspots(
    video_metrics: pd.DataFrame,
    sentiments: pd.DataFrame,
    video_themes: pd.DataFrame,
) -> pd.DataFrame:
    out = _sentiment_group_summary(sentiments, ["video_id"])
    out = (
        out.merge(video_metrics[["video_id", "title", "published_at", "view_count"]], on="video_id")
        .merge(video_themes[["video_id", "primary_theme"]], on="video_id", how="left")
        .assign(sentiment_source="qwen")
        .sort_values(["like_weighted_negative_rate", "n_negative"], ascending=False)
    )
    return out


def _keyword_sentiment_hotspots(
    video_metrics: pd.DataFrame,
    keyword_sentiments: pd.DataFrame,
    video_themes: pd.DataFrame,
) -> pd.DataFrame:
    agg = _sentiment_group_summary(keyword_sentiments, ["video_id"])
    agg["n_risk_keyword_comments"] = agg["n_negative"]
    agg["risk_keyword_rate"] = agg["negative_rate"]
    agg["like_weighted_risk_rate"] = agg["like_weighted_negative_rate"]
    out = (
        agg.merge(video_metrics[["video_id", "title", "published_at", "view_count"]], on="video_id")
        .merge(video_themes[["video_id", "primary_theme"]], on="video_id", how="left")
        .assign(sentiment_source="keyword_proxy")
        .sort_values(["like_weighted_risk_rate", "n_risk_keyword_comments"], ascending=False)
    )
    return out


def _sentiment_group_summary(sentiments: pd.DataFrame, group_cols: list[str]) -> pd.DataFrame:
    if sentiments.empty:
        return pd.DataFrame()
    rows = []
    for key, group in sentiments.groupby(group_cols, dropna=False):
        if not isinstance(key, tuple):
            key = (key,)
        total_like_w = group["like_w"].sum()
        neg = group[group["sentiment_label"] == "negative"]
        neu = group[group["sentiment_label"] == "neutral"]
        pos = group[group["sentiment_label"] == "positive"]
        row = {col: value for col, value in zip(group_cols, key)}
        row.update(
            {
                "n_comments": len(group),
                "n_negative": len(neg),
                "n_neutral": len(neu),
                "n_positive": len(pos),
                "negative_rate": len(neg) / len(group) if len(group) else 0,
                "neutral_rate": len(neu) / len(group) if len(group) else 0,
                "positive_rate": len(pos) / len(group) if len(group) else 0,
                "total_like_w": total_like_w,
                "negative_like_w": neg["like_w"].sum(),
                "positive_like_w": pos["like_w"].sum(),
                "like_weighted_negative_rate": (
                    neg["like_w"].sum() / total_like_w if total_like_w else 0
                ),
                "like_weighted_positive_rate": (
                    pos["like_w"].sum() / total_like_w if total_like_w else 0
                ),
                "avg_score_neg": group["score_neg"].mean(),
                "avg_score_neu": group["score_neu"].mean(),
                "avg_score_pos": group["score_pos"].mean(),
                "avg_confidence": group["sentiment_confidence"].mean(),
            }
        )
        if "is_top_level" in group.columns:
            n_replies = int((~group["is_top_level"].astype(bool)).sum())
            row["n_replies"] = n_replies
            row["reply_share"] = n_replies / len(group) if len(group) else 0
        rows.append(row)
    return pd.DataFrame(rows)


def _clean_sentiment_label(value: object) -> str:
    text = str(value or "").strip()
    return text if text in {"negative", "neutral", "positive"} else "neutral"


def _bool_series(values: object) -> pd.Series:
    if isinstance(values, pd.Series):
        return values.astype(str).str.lower().isin({"true", "1", "yes"})
    return pd.Series([bool(values)])


def re_escape(value: str) -> str:
    import re

    return re.escape(value.lower())


def write_figures(
    figures_dir: Path,
    video_metrics: pd.DataFrame,
    commenter_tiers: pd.DataFrame,
    community_summary: pd.DataFrame,
    rolling_retention: pd.DataFrame,
    video_cluster_summary: pd.DataFrame,
) -> None:
    import os
    import matplotlib

    mpl_config_dir = figures_dir.parent / ".matplotlib"
    mpl_config_dir.mkdir(parents=True, exist_ok=True)
    os.environ["MPLCONFIGDIR"] = str(mpl_config_dir)
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    monthly = (
        video_metrics.groupby("published_month")
        .agg(n_videos=("video_id", "count"), observed_comments=("observed_comments", "sum"))
        .reset_index()
    )
    fig, ax1 = plt.subplots(figsize=(12, 4))
    ax1.bar(monthly["published_month"], monthly["n_videos"], color="#4C78A8", alpha=0.8)
    ax1.set_ylabel("Videos")
    ax1.tick_params(axis="x", rotation=60, labelsize=7)
    ax2 = ax1.twinx()
    ax2.plot(monthly["published_month"], monthly["observed_comments"], color="#F58518", linewidth=1.5)
    ax2.set_ylabel("Observed comments")
    ax1.set_title("Channel Activity")
    fig.tight_layout()
    fig.savefig(figures_dir / "channel_activity.png", dpi=150)
    plt.close(fig)

    if not commenter_tiers.empty:
        fig, ax = plt.subplots(figsize=(6, 4))
        ax.bar(commenter_tiers["activity_tier"], commenter_tiers["n_commenters"], color="#54A24B")
        ax.set_title("Commenter Activity Tiers")
        ax.set_ylabel("Commenters")
        fig.tight_layout()
        fig.savefig(figures_dir / "commenter_tiers.png", dpi=150)
        plt.close(fig)

    if not community_summary.empty:
        top = community_summary.head(15)
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.bar(top["community"].astype(str), top["n_nodes"], color="#B279A2")
        ax.set_title("Top Community Sizes")
        ax.set_xlabel("Community")
        ax.set_ylabel("Nodes")
        fig.tight_layout()
        fig.savefig(figures_dir / "community_sizes.png", dpi=150)
        plt.close(fig)

    if not rolling_retention.empty:
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.plot(
            rolling_retention["cutoff_video_index"],
            rolling_retention["return_rate"],
            color="#E45756",
            marker="o",
            linewidth=1.5,
            markersize=3,
        )
        ax.set_title("Rolling Commenter Retention")
        ax.set_xlabel("Cutoff video index")
        ax.set_ylabel("Return rate")
        ax.set_ylim(0, min(1.0, max(rolling_retention["return_rate"].max() * 1.15, 0.1)))
        fig.tight_layout()
        fig.savefig(figures_dir / "rolling_retention.png", dpi=150)
        plt.close(fig)

    if not video_cluster_summary.empty:
        top = video_cluster_summary.head(15)
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.bar(top["video_cluster"].astype(str), top["n_videos"], color="#72B7B2")
        ax.set_title("Video Shared-Audience Cluster Sizes")
        ax.set_xlabel("Video cluster")
        ax.set_ylabel("Videos")
        fig.tight_layout()
        fig.savefig(figures_dir / "video_cluster_sizes.png", dpi=150)
        plt.close(fig)


def build_report_payload(**kwargs) -> dict:
    payload = {}
    for key, value in kwargs.items():
        if isinstance(value, pd.DataFrame):
            payload[key] = value.head(20).replace({np.nan: None}).to_dict(orient="records")
        elif isinstance(value, AnalyzerConfig):
            payload[key] = asdict(value)
        else:
            payload[key] = value
    return payload


def render_report(payload: dict, language: str = "en") -> str:
    zh = language == "zh"
    channel = payload["channel"]
    overview = payload["channel_overview"][0] if payload["channel_overview"] else {}
    network = payload["network_summary"][0] if payload["network_summary"] else {}
    video_network = payload["video_network_summary"][0] if payload.get("video_network_summary") else {}
    source_rows = payload.get("sentiment_source_summary") or []
    sentiment_source = source_rows[0].get("sentiment_source", "") if source_rows else ""
    sentiment_scope = source_rows[0] if source_rows else {}

    if zh:
        lines = [
            f"# 頻道社群統計報告：{channel.get('title', 'Unknown Channel')}",
            "",
            "## 給 LLM 的使用說明",
            "",
            "這份報告是給下游 LLM 做分析用的統計資料包，不是完整敘事稿。請根據下列表格比較內容主題、留言者社群、影片群集與情緒風險；避免把共現、情緒或主題關聯解讀為因果。",
            "",
            "## 分析範圍",
            "",
            f"- 頻道 ID：`{channel.get('channel_id')}`",
            f"- 影片數：{overview.get('n_videos_in_scope', 0):,}",
            f"- 留言數：{overview.get('n_comments_in_scope', 0):,}",
            f"- 不重複留言者：{overview.get('n_commenters_in_scope', 0):,}",
            f"- 影片日期範圍：{overview.get('date_min')} 到 {overview.get('date_max')}",
        ]
        if sentiment_scope:
            sentiment_comments = int(sentiment_scope.get("n_scope_comments") or 0)
            sentiment_replies = int(sentiment_scope.get("n_scope_replies") or 0)
            if sentiment_replies or sentiment_comments != int(overview.get("n_comments_in_scope") or 0):
                lines.append(
                    f"- 情緒/風險分析留言數：{sentiment_comments:,} "
                    f"（top-level {int(sentiment_scope.get('n_scope_top_level_comments') or 0):,} + replies {sentiment_replies:,}）"
                )
        if network:
            lines.extend([
                f"- 留言者共現圖：{network.get('n_nodes', 0):,} 節點、{network.get('n_edges', 0):,} 邊、{network.get('n_communities', 0):,} 個社群",
                f"- 留言者社群偵測：{network.get('community_method')}，modularity={_fmt(network.get('modularity'))}，max k-core={network.get('max_core_number')}",
            ])
        if video_network:
            lines.append(
                f"- 影片 shared-audience 圖：{video_network.get('n_nodes', 0):,} 支影片、{video_network.get('n_video_clusters', 0):,} 個影片群集"
            )
        lines.extend([
            "",
            "## 指標定義與計算方式",
            "",
            "- `co-commenter edge`：兩個留言者曾在同一支影片留言即形成共現；邊權重為共同留言影片數，並套用 `min_co_videos` 門檻。",
            "- `audience community`：在 co-commenter graph 上偵測出的留言者社群；不是創作者預先標籤。",
            "- `video shared-audience cluster`：兩支影片共享留言者達門檻時連邊，再在影片圖上偵測群集。",
            "- `community_concentration_hhi = sum(community_share^2)`；越高表示社群規模越集中，`effective_communities=1/HHI`。",
            "- `k-core`：圖中每個節點至少連到 k 個同核心節點的最大 k 值；用來標示結構核心，不等同於忠誠觀眾分層。",
            "- `betweenness_centrality`：以固定 seed 抽樣的近似 betweenness；用於找可能連接不同區塊的橋接節點。",
            "- `participation_coefficient = 1 - sum((跨各社群邊權重 / 總邊權重)^2)`；越高表示鄰居分布越跨社群。",
            "- `conductance = external_edge_weight / min(community_volume, rest_volume)`；越低表示該社群和外部越分離。",
            "- `degree_assortativity`：相近 degree 節點互連的傾向；`community_assortativity` 是偵測社群 label 的連邊同質性。",
            "- `video_link_opportunities`：在尚未形成 shared-audience edge 的影片對上做 link prediction；用 common neighbors、Jaccard、Adamic-Adar 與 resource allocation 排出可嘗試的內容橋接/混合企劃。",
            "- `theme_label`：影片主題。若有 `qwen_video_themes.csv` 使用 Qwen 分類，否則使用 keyword fallback。",
            "- `community_share = 該社群中某主題 actor-video pairs / 該社群所有 actor-video pairs`。",
            "- `overall_share = 全頻道該主題 actor-video pairs / 全頻道所有 actor-video pairs`。",
            "- `lift = community_share / overall_share`；大於 1 表示該社群相對更偏好該主題。",
            "- `negative_rate = negative 留言數 / 該表 sentiment-scope 留言總數`；`positive_rate` 同理。若本報告有 replies，影片/主題/熱點情緒會納入 replies。",
            "- `like_weighted_negative_rate = negative 留言的 (like_count+1) 加總 / 該表 sentiment-scope 全部留言的 (like_count+1) 加總`；用來估計被社群按讚放大的負面程度。",
            "- `commenter tier`：依留言者參與過的不重複影片數分層；預設 high>=16、mid>=6、low<6。",
            "- `return_rate`：前一時間窗留言者中，下一時間窗仍留言的比例；`non_return_rate=1-return_rate`。",
            f"- `sentiment_source`：目前為 `{sentiment_source}`。若為 qwen，三元情緒與 score 由 Qwen 產生；若為 keyword_proxy，僅代表透明關鍵字近似。實際留言範圍請看 `comment_scope`。",
            "- 表格欄位名與分類 label 保留英文，方便和 `tables/*.csv` 欄位對照。",
            "",
            "## 核心統計表",
        ])
    else:
        lines = [
            f"# Channel Community Statistical Report: {channel.get('title', 'Unknown Channel')}",
            "",
            "## How To Use This Report With An LLM",
            "",
            "This report is a compact statistical packet for downstream LLM analysis, not a narrative memo. Use the tables to compare content themes, audience communities, video clusters, and sentiment risks. Do not interpret co-commenting, sentiment, or content affinity as causal evidence.",
            "",
            "## Scope",
            "",
            f"- Channel ID: `{channel.get('channel_id')}`",
            f"- Videos: {overview.get('n_videos_in_scope', 0):,}",
            f"- Comments: {overview.get('n_comments_in_scope', 0):,}",
            f"- Unique commenters: {overview.get('n_commenters_in_scope', 0):,}",
            f"- Video date range: {overview.get('date_min')} to {overview.get('date_max')}",
        ]
        if sentiment_scope:
            sentiment_comments = int(sentiment_scope.get("n_scope_comments") or 0)
            sentiment_replies = int(sentiment_scope.get("n_scope_replies") or 0)
            if sentiment_replies or sentiment_comments != int(overview.get("n_comments_in_scope") or 0):
                lines.append(
                    f"- Sentiment/risk comments: {sentiment_comments:,} "
                    f"(top-level {int(sentiment_scope.get('n_scope_top_level_comments') or 0):,} + replies {sentiment_replies:,})"
                )
        if network:
            lines.extend([
                f"- Co-commenter graph: {network.get('n_nodes', 0):,} nodes, {network.get('n_edges', 0):,} edges, {network.get('n_communities', 0):,} communities",
                f"- Audience community detection: {network.get('community_method')}, modularity={_fmt(network.get('modularity'))}, max k-core={network.get('max_core_number')}",
            ])
        if video_network:
            lines.append(
                f"- Video shared-audience graph: {video_network.get('n_nodes', 0):,} videos, {video_network.get('n_video_clusters', 0):,} video clusters"
            )
        lines.extend([
            "",
            "## Metric Definitions And Formulas",
            "",
            "- `co-commenter edge`: two commenters are connected when both commented on the same video; edge weight is the number of shared videos after the `min_co_videos` threshold.",
            "- `audience community`: a graph-detected commenter segment from the co-commenter graph; it is not a creator-provided label.",
            "- `video shared-audience cluster`: videos are linked when they share enough commenters, then clustered on the video graph.",
            "- `community_concentration_hhi = sum(community_share^2)`; higher values mean community sizes are more concentrated, and `effective_communities=1/HHI`.",
            "- `k-core`: the largest k for which a node belongs to a subgraph where every node has at least k in-core neighbors; it marks structural core position, not loyal-audience tier.",
            "- `betweenness_centrality`: fixed-seed sampled approximate betweenness for identifying possible bridge nodes across graph regions.",
            "- `participation_coefficient = 1 - sum((edge weight to each neighbor community / total edge weight)^2)`; higher values indicate cross-community neighbor diversity.",
            "- `conductance = external_edge_weight / min(community_volume, rest_volume)`; lower values indicate a more separated community.",
            "- `degree_assortativity`: tendency for similar-degree nodes to connect; `community_assortativity` is edge homophily by detected community label.",
            "- `video_link_opportunities`: link prediction over video pairs that do not yet have a shared-audience edge; common neighbors, Jaccard, Adamic-Adar, and resource allocation rank possible content bridges or hybrid ideas.",
            "- `theme_label`: video topic. Qwen labels are used when `qwen_video_themes.csv` exists; otherwise keyword fallback is used.",
            "- `community_share = actor-video pairs for a theme within a community / all actor-video pairs in that community`.",
            "- `overall_share = actor-video pairs for a theme across the channel / all actor-video pairs across the channel`.",
            "- `lift = community_share / overall_share`; values above 1 mean the segment over-indexes on that theme.",
            "- `negative_rate = negative comments / sentiment-scope comments in that table`; `positive_rate` is analogous. When replies are available, video/theme/hotspot sentiment includes replies.",
            "- `like_weighted_negative_rate = sum(like_count+1 for negative comments) / sum(like_count+1 for all sentiment-scope comments in that table)`; this estimates socially amplified negativity.",
            "- `commenter tier`: based on distinct videos commented on; default high>=16, mid>=6, low<6.",
            "- `return_rate`: share of commenters in one time window who comment again in the next window; `non_return_rate=1-return_rate`.",
            f"- `sentiment_source`: `{sentiment_source}`. If qwen, ternary sentiment and scores are model-generated; if keyword_proxy, they are a transparent keyword approximation. See `comment_scope` for the actual comment scope.",
            "",
            "## Core Statistical Tables",
        ])

    table_specs = [
        ("Diagnostics" if not zh else "診斷摘要", "diagnostics", ["area", "metric", "value", "diagnosis"], 12),
        ("Commenter Tiers" if not zh else "留言者活躍分層", "commenter_tiers", ["activity_tier", "n_commenters", "pct_commenters", "avg_videos", "median_videos", "total_comments"], 10),
        ("Continuity Sensitivity" if not zh else "留存敏感度", "continuity_sensitivity", ["n_windows", "n_transitions", "weighted_return_rate", "weighted_non_return_rate", "median_return_rate", "min_return_rate", "max_return_rate"], 10),
        ("Theme Summary" if not zh else "主題摘要", "theme_summary", ["primary_theme", "n_comments", "n_commenters", "n_videos"], 12),
        ("Audience Network Structure" if not zh else "留言者網路結構", "network_summary", ["n_nodes", "n_edges", "n_communities", "community_method", "modularity", "community_concentration_hhi", "effective_communities", "max_core_number", "degree_assortativity", "community_assortativity"], 1),
        ("Audience Communities" if not zh else "留言者社群", "community_summary", ["community", "n_nodes", "pct_nodes", "internal_edges", "external_edges", "conductance", "avg_core_number", "max_core_number"], 10),
        ("Community Profiles" if not zh else "留言者社群內容摘要", "community_profiles", ["community", "n_nodes", "pct_nodes", "n_comments", "n_videos_touched", "top_primary_themes"], 10),
        ("Community Content Affinity" if not zh else "社群內容偏好", "community_theme_affinity", ["community", "theme_label", "n_actor_video_pairs", "n_commenters", "n_videos", "community_share", "overall_share", "lift"], 15),
        ("Community Sentiment" if not zh else "社群情緒", "community_sentiment_summary", ["community", "n_commenters", "n_videos", "n_comments", "n_replies", "reply_share", "negative_rate", "like_weighted_negative_rate", "positive_rate", "like_weighted_positive_rate"], 10),
        ("Community Theme Sentiment" if not zh else "社群 x 主題情緒", "community_theme_sentiment", ["community", "primary_theme", "n_commenters", "n_videos", "n_comments", "n_replies", "reply_share", "negative_rate", "like_weighted_negative_rate", "positive_rate"], 15),
        ("Video Network Structure" if not zh else "影片網路結構", "video_network_summary", ["n_nodes", "n_edges", "n_video_clusters", "community_method", "modularity", "community_concentration_hhi", "effective_communities", "max_core_number", "degree_assortativity", "community_assortativity"], 1),
        ("Video Clusters" if not zh else "影片群集", "video_cluster_summary", ["video_cluster", "n_videos", "unique_commenters", "total_observed_comments", "conductance", "max_core_number", "top_theme_labels"], 10),
        ("Content Idea Opportunities" if not zh else "內容企劃機會點", "video_link_opportunities", ["opportunity_type", "opportunity_score", "source_primary_theme", "target_primary_theme", "jaccard_score", "adamic_adar_score", "resource_allocation_score", "current_shared_audience", "source_title", "target_title"], 10),
        ("Video Cluster Sentiment" if not zh else "影片群集情緒", "video_cluster_sentiment_summary", ["video_cluster", "n_videos", "n_commenters", "n_comments", "n_replies", "reply_share", "negative_rate", "like_weighted_negative_rate", "positive_rate", "like_weighted_positive_rate"], 10),
        ("Overall Sentiment" if not zh else "整體留言情緒", "sentiment_summary", ["sentiment_label", "n_comments", "n_replies", "reply_share", "pct_comments", "like_weighted_share", "avg_score_neg", "avg_score_neu", "avg_score_pos"], 5),
        ("Theme Sentiment" if not zh else "主題情緒", "sentiment_theme_summary", ["primary_theme", "n_comments", "n_replies", "reply_share", "n_negative", "negative_rate", "like_weighted_negative_rate", "n_positive", "positive_rate", "like_weighted_positive_rate"], 12),
        ("Negative Hotspots" if not zh else "負面熱點影片", "sentiment_hotspots", ["video_id", "primary_theme", "n_comments", "n_replies", "reply_share", "n_negative", "negative_rate", "like_weighted_negative_rate", "avg_score_neg", "title"], 10),
        ("Source Coverage" if not zh else "資料來源覆蓋率", "sentiment_source_summary", ["sentiment_source", "comment_scope", "n_scope_comments", "n_scope_top_level_comments", "n_scope_replies", "n_scored_comments", "coverage_rate", "parse_errors", "notes"], 5),
    ]
    table_payload = payload
    if zh:
        table_payload = dict(payload)
        table_payload["diagnostics"] = [
            _translate_diagnostic_row(row) for row in payload.get("diagnostics", [])
        ]
    for title, key, cols, limit in table_specs:
        lines.extend(["", f"### {title}", "", _markdown_table(table_payload.get(key, []), limit=limit, keys=cols)])

    if zh:
        lines.extend([
            "",
            "## 補充檔案",
            "",
            "- 完整表格在 `tables/` 目錄。此 report 只保留適合 LLM 分析的前幾列重點表。",
            "- `bridge_actors.csv`、`network_actor_metrics.csv`、`actor_communities.csv`、`video_network_metrics.csv`、`video_link_opportunities.csv`、`video_metrics.csv` 等細節表仍保留為 CSV，但不全量放入 report 以降低雜訊。",
        ])
    else:
        lines.extend([
            "",
            "## Supplemental Files",
            "",
            "- Full tables are available under `tables/`. This report includes only the most useful rows for LLM analysis.",
            "- Detailed tables such as `bridge_actors.csv`, `network_actor_metrics.csv`, `actor_communities.csv`, `video_network_metrics.csv`, `video_link_opportunities.csv`, and `video_metrics.csv` remain available as CSVs but are not fully included here to reduce noise.",
        ])
    return "\n".join(lines) + "\n"


def _fmt(value: object) -> str:
    if isinstance(value, float):
        return f"{value:.3f}"
    return str(value)


def _translate_diagnostic_row(row: dict) -> dict:
    out = dict(row)
    metric = row.get("metric")
    value = row.get("value")
    diagnosis = str(row.get("diagnosis") or "")
    if metric == "low_tier_share":
        if float(value or 0) >= 80:
            out["diagnosis"] = "留言觀眾高度偏 casual；原始留言者數更適合解讀為觸及，不宜直接當成忠誠社群規模。"
        else:
            out["diagnosis"] = "留言觀眾中有明顯的重複參與者基礎。"
    elif metric == "high_tier_commenters":
        out["diagnosis"] = f"核心重複留言者規模小但可觀測（{value} 位 actor）。"
    elif metric == "window_sensitivity_return_range":
        if diagnosis.startswith("Fixed-window retention is stable"):
            out["diagnosis"] = "固定時間窗的留存率在測試窗數下相對穩定。"
        else:
            out["diagnosis"] = "留存率會受時間窗設定影響；做趨勢判讀前應先看 rolling retention。"
    elif metric == "rolling_return_range":
        out["diagnosis"] = "Rolling retention 顯示重複留言者延續性在頻道時間線上何時增強或減弱。"
    elif metric == "audience_communities":
        out["diagnosis"] = diagnosis.replace(
            "The commenter graph separates into",
            "留言者圖分成",
        ).replace(
            "communities; largest community contains",
            "個社群；最大社群包含",
        ).replace(
            "of graph actors.",
            "的圖上 actor。",
        )
    elif metric == "community_concentration_hhi":
        out["diagnosis"] = diagnosis.replace(
            "Community-size concentration HHI is",
            "社群規模集中度 HHI 為",
        ).replace(
            "effective communities are about",
            "有效社群數約為",
        )
    elif metric == "max_k_core":
        out["diagnosis"] = diagnosis.replace(
            "The co-commenter graph has max k-core",
            "留言者共現圖的最大 k-core 為",
        ).replace(
            "interpret this as structural embeddedness, not commenter loyalty.",
            "這代表結構嵌入程度，不等同於留言者忠誠度。",
        )
    elif metric in {"top_audience_affinity", "top_video_cluster_affinity"}:
        out["diagnosis"] = diagnosis.replace(
            "over-indexes on",
            "相對高集中於",
        ).replace(
            "use this as a segment/content-positioning clue, not as causal proof.",
            "這是社群/內容定位線索，不是因果證據。",
        )
    elif metric == "video_shared_audience_clusters":
        out["diagnosis"] = diagnosis.replace(
            "Videos form",
            "影片形成",
        ).replace(
            "shared-audience clusters; largest cluster covers",
            "個 shared-audience 群集；最大群集涵蓋",
        ).replace(
            "of in-scope videos.",
            "的分析範圍影片。",
        )
    return out


def _markdown_table(
    rows: list[dict],
    limit: int = 10,
    keys: list[str] | None = None,
) -> str:
    if not rows:
        return "_No rows._"
    rows = rows[:limit]
    keys = keys or list(rows[0].keys())[:8]
    lines = ["| " + " | ".join(keys) + " |", "| " + " | ".join(["---"] * len(keys)) + " |"]
    for row in rows:
        values = [_format_cell(row.get(key)) for key in keys]
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def _format_cell(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.3f}"
    text = str(value)
    text = text.replace("|", "/").replace("\n", " ")
    return text[:140]


def _write_csv(path: Path, df: pd.DataFrame) -> None:
    if df.empty:
        path.write_text("", encoding="utf-8")
    else:
        df.to_csv(path, index=False)
