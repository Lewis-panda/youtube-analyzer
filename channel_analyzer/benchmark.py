from __future__ import annotations

from dataclasses import dataclass
import json
import math
from pathlib import Path
from urllib.parse import urlparse

import pandas as pd

from .config import load_config, output_slug


DEFAULT_METRICS = [
    "n_videos_in_scope",
    "top_level_comments",
    "top_level_commenters",
    "all_comments",
    "comments_per_video",
    "commenters_per_video",
    "comments_per_1k_views",
    "core_tier_commenter_share",
    "regular_tier_commenter_share",
    "returning_tier_commenter_share",
    "one_time_tier_commenter_share",
    "core_regular_tier_commenter_share",
    "core_regular_tier_comment_share",
    "high_tier_commenter_share",
    "mid_tier_commenter_share",
    "low_tier_commenter_share",
    "high_mid_tier_commenter_share",
    "high_mid_tier_comment_share",
    "continuity_return_rate_w4",
    "rolling_return_rate_mean",
    "rolling_return_rate_latest",
    "commenter_network_density",
    "commenter_network_modularity",
    "commenter_network_communities",
    "largest_community_share",
    "top3_community_share",
    "community_hhi",
    "top_bridge_participation_mean",
    "video_network_density",
    "video_network_modularity",
    "video_network_clusters",
    "negative_rate",
    "positive_rate",
    "like_weighted_negative_rate",
    "like_weighted_positive_rate",
    "max_video_negative_rate",
    "top5_hotspot_negative_rate_mean",
    "max_video_like_weighted_negative_rate",
    "max_community_negative_rate",
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
]


@dataclass(frozen=True)
class BenchmarkOutputs:
    output_dir: Path
    members_path: Path
    metrics_path: Path
    distributions_path: Path
    percentiles_path: Path
    readme_path: Path


def build_benchmark_baseline(
    cohort_csv: Path,
    configs_glob: str,
    runs_dir: Path,
    output_dir: Path,
    *,
    status_column: str = "正確",
    include_status: str = "O",
) -> BenchmarkOutputs:
    output_dir.mkdir(parents=True, exist_ok=True)
    cohort = load_cohort(cohort_csv, status_column=status_column, include_status=include_status)
    config_index = index_configs(configs_glob)
    members = build_membership(cohort, config_index, runs_dir)
    metrics = build_channel_metrics(members)
    distributions = build_metric_distributions(metrics)
    percentiles = build_metric_percentiles(metrics)

    members_path = output_dir / "cohort_members.csv"
    metrics_path = output_dir / "channel_metrics.csv"
    distributions_path = output_dir / "metric_distributions.csv"
    percentiles_path = output_dir / "metric_percentiles.csv"
    readme_path = output_dir / "README.md"

    members.to_csv(members_path, index=False)
    metrics.to_csv(metrics_path, index=False)
    distributions.to_csv(distributions_path, index=False)
    percentiles.to_csv(percentiles_path, index=False)
    readme_path.write_text(render_readme(members, metrics, distributions), encoding="utf-8")

    return BenchmarkOutputs(
        output_dir=output_dir,
        members_path=members_path,
        metrics_path=metrics_path,
        distributions_path=distributions_path,
        percentiles_path=percentiles_path,
        readme_path=readme_path,
    )


def load_cohort(cohort_csv: Path, *, status_column: str, include_status: str) -> pd.DataFrame:
    cohort = pd.read_csv(cohort_csv, dtype=str).fillna("")
    if status_column in cohort.columns:
        cohort = cohort[cohort[status_column].astype(str).str.strip() == include_status].copy()
    required = {"candidate_id", "channel_name", "url"}
    missing = required - set(cohort.columns)
    if missing:
        raise RuntimeError(f"Cohort CSV is missing required columns: {', '.join(sorted(missing))}")
    cohort["cohort_url_key"] = cohort["url"].map(normalize_youtube_url_key)
    return cohort.reset_index(drop=True)


def index_configs(configs_glob: str) -> pd.DataFrame:
    rows = []
    for path in sorted(Path().glob(configs_glob)):
        config = load_config(path)
        keys = set()
        if config.channel_url:
            keys.add(normalize_youtube_url_key(config.channel_url))
        if config.channel_handle:
            keys.add("handle:" + config.channel_handle.strip().lstrip("@").lower())
        if config.channel_id:
            keys.add("channel:" + config.channel_id.lower())
        rows.append(
            {
                "config_path": str(path),
                "config_run_slug": config.outputs.run_slug or "",
                "config_channel_id": config.channel_id or "",
                "config_channel_handle": config.channel_handle or "",
                "config_channel_url": config.channel_url or "",
                "config_keys": sorted(keys),
            }
        )
    return pd.DataFrame(rows)


def build_membership(cohort: pd.DataFrame, config_index: pd.DataFrame, runs_dir: Path) -> pd.DataFrame:
    rows = []
    for item in cohort.to_dict("records"):
        match = find_config_match(item["cohort_url_key"], config_index)
        row = {
            "candidate_id": item["candidate_id"],
            "cohort_channel_name": item["channel_name"],
            "cohort_url": item["url"],
            "cohort_url_key": item["cohort_url_key"],
            "config_path": "",
            "run_dir": "",
            "channel_id": "",
            "run_channel_title": "",
            "status": "missing_config",
            "notes": "",
        }
        if match is None:
            rows.append(row)
            continue
        config_path = Path(match["config_path"])
        config = load_config(config_path)
        report_path = resolve_report_path(config, runs_dir)
        row["config_path"] = str(config_path)
        row["run_dir"] = str(report_path.parent)
        if not report_path.exists():
            row["status"] = "missing_report_json"
            rows.append(row)
            continue
        try:
            report = json.loads(report_path.read_text(encoding="utf-8"))
        except Exception as exc:
            row["status"] = "invalid_report_json"
            row["notes"] = str(exc)
            rows.append(row)
            continue
        channel = report.get("channel") or {}
        row["channel_id"] = str(channel.get("channel_id") or config.channel_id or "")
        row["run_channel_title"] = str(channel.get("title") or "")
        row["status"] = "ready"
        rows.append(row)
    return pd.DataFrame(rows)


def find_config_match(url_key: str, config_index: pd.DataFrame) -> dict | None:
    for row in config_index.to_dict("records"):
        if url_key and url_key in set(row["config_keys"]):
            return row
    return None


def resolve_report_path(config, runs_dir: Path) -> Path:
    if config.outputs.run_slug:
        slug = output_slug(config)
        return runs_dir / slug / "report.json"
    if config.channel_id:
        for report_path in runs_dir.glob("*/report.json"):
            try:
                data = json.loads(report_path.read_text(encoding="utf-8"))
            except Exception:
                continue
            channel = data.get("channel") or {}
            if str(channel.get("channel_id") or "") == config.channel_id:
                return report_path
    return runs_dir / output_slug(config) / "report.json"


def build_channel_metrics(members: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for member in members.to_dict("records"):
        if member["status"] != "ready":
            continue
        report_path = Path(member["run_dir"]) / "report.json"
        report = json.loads(report_path.read_text(encoding="utf-8"))
        row = {
            "candidate_id": member["candidate_id"],
            "cohort_channel_name": member["cohort_channel_name"],
            "channel_id": member["channel_id"],
            "run_channel_title": member["run_channel_title"],
            "run_dir": member["run_dir"],
        }
        row.update(extract_metrics(report))
        rows.append(row)
    return pd.DataFrame(rows)


def extract_metrics(report: dict) -> dict:
    overview = first(report.get("channel_overview"))
    sentiment_source = first(report.get("sentiment_source_summary"))
    network = first(report.get("network_summary"))
    video_network = first(report.get("video_network_summary"))
    tiers = report.get("commenter_tiers") or []
    continuity = choose_continuity(report.get("continuity_sensitivity") or [])
    rolling = report.get("rolling_retention") or []
    communities = report.get("community_summary") or []
    bridges = report.get("bridge_actors") or []
    sentiment = report.get("sentiment_summary") or []
    hotspots = report.get("sentiment_hotspots") or []
    community_sentiment = report.get("community_sentiment_summary") or []
    deeper = report.get("commenter_deeper_analysis") or {}
    reply_overview = first(deeper.get("reply_thread_overview"))
    reply_sentiment = deeper.get("reply_sentiment_summary") or []
    conflict_videos = deeper.get("reply_conflict_video_summary") or []
    conflict_themes = deeper.get("reply_conflict_theme_summary") or []

    n_videos = to_float(overview.get("n_videos_in_scope"))
    top_comments = to_float(overview.get("n_comments_in_scope"))
    top_commenters = to_float(overview.get("n_commenters_in_scope"))
    total_views = to_float(overview.get("total_views_in_scope"))
    all_comments = to_float(sentiment_source.get("n_scope_comments"))

    def tier_share(name: str) -> float:
        return nan_to_zero(tier_value(tiers, name, "pct_commenters")) / 100

    core_share = tier_share("core")
    regular_share = tier_share("regular")
    returning_share = tier_share("returning")
    one_time_share = tier_share("one_time")
    if core_share + regular_share + returning_share + one_time_share == 0:
        # Legacy 3-tier report (high/mid/low) not yet re-tiered: map across.
        core_share = tier_share("high")
        regular_share = tier_share("mid")
        returning_share = tier_share("low")
        one_time_share = 0.0
    engaged_share = core_share + regular_share
    total_tier_comments = sum(to_float(item.get("total_comments")) for item in tiers)
    engaged_comments = sum(
        to_float(item.get("total_comments"))
        for item in tiers
        if str(item.get("activity_tier")) in {"core", "regular", "high", "mid"}
    )

    community_shares = sorted(
        [to_float(item.get("pct_nodes")) / 100 for item in communities],
        reverse=True,
    )
    hotspot_negative_rates = sorted(
        [to_float(item.get("negative_rate")) for item in hotspots],
        reverse=True,
    )

    return {
        "n_videos_in_scope": n_videos,
        "top_level_comments": top_comments,
        "top_level_commenters": top_commenters,
        "all_comments": all_comments,
        "comments_per_video": divide(top_comments, n_videos),
        "commenters_per_video": divide(top_commenters, n_videos),
        "comments_per_1k_views": divide(top_comments * 1000, total_views),
        "core_tier_commenter_share": core_share,
        "regular_tier_commenter_share": regular_share,
        "returning_tier_commenter_share": returning_share,
        "one_time_tier_commenter_share": one_time_share,
        "core_regular_tier_commenter_share": engaged_share,
        "core_regular_tier_comment_share": divide(engaged_comments, total_tier_comments),
        "high_tier_commenter_share": core_share,
        "mid_tier_commenter_share": regular_share,
        "low_tier_commenter_share": returning_share + one_time_share,
        "high_mid_tier_commenter_share": engaged_share,
        "high_mid_tier_comment_share": divide(engaged_comments, total_tier_comments),
        "continuity_return_rate_w4": to_float(continuity.get("weighted_return_rate")),
        "rolling_return_rate_mean": mean([to_float(item.get("return_rate")) for item in rolling]),
        "rolling_return_rate_latest": to_float(rolling[-1].get("return_rate")) if rolling else math.nan,
        "commenter_network_density": to_float(network.get("density")),
        "commenter_network_modularity": to_float(network.get("modularity")),
        "commenter_network_communities": to_float(network.get("n_communities")),
        "largest_community_share": community_shares[0] if community_shares else math.nan,
        "top3_community_share": sum(community_shares[:3]) if community_shares else math.nan,
        "community_hhi": sum(value * value for value in community_shares) if community_shares else math.nan,
        "top_bridge_participation_mean": mean(
            [to_float(item.get("participation_coefficient")) for item in bridges]
        ),
        "video_network_density": to_float(video_network.get("density")),
        "video_network_modularity": to_float(video_network.get("modularity")),
        "video_network_clusters": to_float(video_network.get("n_video_clusters")),
        "negative_rate": sentiment_label_value(sentiment, "negative", "pct_comments"),
        "positive_rate": sentiment_label_value(sentiment, "positive", "pct_comments"),
        "like_weighted_negative_rate": sentiment_label_value(sentiment, "negative", "like_weighted_share"),
        "like_weighted_positive_rate": sentiment_label_value(sentiment, "positive", "like_weighted_share"),
        "max_video_negative_rate": max_or_nan(hotspot_negative_rates),
        "top5_hotspot_negative_rate_mean": mean(hotspot_negative_rates[:5]),
        "max_video_like_weighted_negative_rate": max_or_nan(
            [to_float(item.get("like_weighted_negative_rate")) for item in hotspots]
        ),
        "max_community_negative_rate": max_or_nan(
            [to_float(item.get("negative_rate")) for item in community_sentiment]
        ),
        "reply_share_all_comments": to_float(reply_overview.get("reply_share_all_comments")),
        "pct_threads_with_replies": to_float(reply_overview.get("pct_threads_with_replies")),
        "reply_negative_rate": reply_label_value(reply_sentiment, "reply", "negative_rate"),
        "max_video_conflict_score": max_or_nan(
            [to_float(item.get("conflict_score")) for item in conflict_videos]
        ),
        "max_video_reply_count_weighted_conflict_score": max_or_nan(
            [
                to_float(item.get("reply_count_weighted_conflict_score"))
                for item in conflict_videos
            ]
        ),
        "max_video_like_weighted_conflict_score": max_or_nan(
            [to_float(item.get("like_weighted_conflict_score")) for item in conflict_videos]
        ),
        "max_video_conflict_thread_rate_replied": max_or_nan(
            [to_float(item.get("conflict_thread_rate_replied")) for item in conflict_videos]
        ),
        "max_theme_conflict_score": max_or_nan(
            [to_float(item.get("conflict_score")) for item in conflict_themes]
        ),
        "max_theme_reply_count_weighted_conflict_score": max_or_nan(
            [
                to_float(item.get("reply_count_weighted_conflict_score"))
                for item in conflict_themes
            ]
        ),
        "max_theme_like_weighted_conflict_score": max_or_nan(
            [to_float(item.get("like_weighted_conflict_score")) for item in conflict_themes]
        ),
    }


def build_metric_distributions(metrics: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for metric in DEFAULT_METRICS:
        if metric not in metrics.columns:
            continue
        values = pd.to_numeric(metrics[metric], errors="coerce").dropna()
        if values.empty:
            continue
        rows.append(
            {
                "metric": metric,
                "n": int(values.count()),
                "mean": values.mean(),
                "median": values.median(),
                "std": values.std(ddof=0),
                "min": values.min(),
                "p10": values.quantile(0.10),
                "p25": values.quantile(0.25),
                "p75": values.quantile(0.75),
                "p90": values.quantile(0.90),
                "max": values.max(),
            }
        )
    return pd.DataFrame(rows)


def build_metric_percentiles(metrics: pd.DataFrame) -> pd.DataFrame:
    id_cols = ["candidate_id", "cohort_channel_name", "channel_id", "run_channel_title", "run_dir"]
    rows = []
    for metric in DEFAULT_METRICS:
        if metric not in metrics.columns:
            continue
        values = pd.to_numeric(metrics[metric], errors="coerce")
        if values.dropna().empty:
            continue
        pct = values.rank(method="average", pct=True) * 100
        for idx, value in values.items():
            if pd.isna(value):
                continue
            row = {col: metrics.loc[idx, col] for col in id_cols}
            row.update(
                {
                    "metric": metric,
                    "value": value,
                    "percentile": pct.loc[idx],
                    "n_cohort": int(values.notna().sum()),
                }
            )
            rows.append(row)
    return pd.DataFrame(rows)


def build_target_comparison(
    target_run_dirs: list[Path],
    baseline_metrics: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    targets = build_target_metrics(target_run_dirs)
    rows = []
    for target in targets.to_dict("records"):
        for metric in DEFAULT_METRICS:
            if metric not in target or metric not in baseline_metrics.columns:
                continue
            value = to_float(target.get(metric))
            if math.isnan(value):
                continue
            cohort_values = pd.to_numeric(baseline_metrics[metric], errors="coerce").dropna()
            if cohort_values.empty:
                continue
            median = float(cohort_values.median())
            rows.append(
                {
                    "target_label": target["target_label"],
                    "channel_id": target["channel_id"],
                    "run_channel_title": target["run_channel_title"],
                    "run_dir": target["run_dir"],
                    "metric": metric,
                    "value": value,
                    "cohort_n": int(cohort_values.count()),
                    "cohort_mean": float(cohort_values.mean()),
                    "cohort_median": median,
                    "cohort_min": float(cohort_values.min()),
                    "cohort_max": float(cohort_values.max()),
                    "percentile_at_or_below": float((cohort_values <= value).mean() * 100),
                    "delta_vs_median": value - median,
                    "ratio_vs_median": divide(value, median),
                }
            )
    return targets, pd.DataFrame(rows)


def build_target_metrics(target_run_dirs: list[Path]) -> pd.DataFrame:
    rows = []
    for run_dir in target_run_dirs:
        report_path = run_dir / "report.json"
        if not report_path.exists():
            raise FileNotFoundError(f"Target report not found: {report_path}")
        report = json.loads(report_path.read_text(encoding="utf-8"))
        channel = report.get("channel") or {}
        title = str(channel.get("title") or run_dir.name)
        row = {
            "target_label": title,
            "channel_id": str(channel.get("channel_id") or ""),
            "run_channel_title": title,
            "run_dir": str(run_dir),
        }
        row.update(extract_metrics(report))
        rows.append(row)
    return pd.DataFrame(rows)


def render_readme(members: pd.DataFrame, metrics: pd.DataFrame, distributions: pd.DataFrame) -> str:
    ready = int((members["status"] == "ready").sum()) if "status" in members.columns else 0
    total = len(members)
    lines = [
        "# Benchmark Baseline Outputs",
        "",
        "這個資料夾是由 completed channel reports 聚合出的 cohort baseline。",
        "它不重新讀 raw comments，也不納入 Dcard/PTT 外部事件；外部事件是另一個 optional analysis layer。",
        "",
        f"- Cohort members: {total}",
        f"- Ready reports: {ready}",
        f"- Channel metric rows: {len(metrics)}",
        f"- Distribution metrics: {len(distributions)}",
        "",
        "## Files",
        "",
        "- `cohort_members.csv`: verified cohort row, matched config/run directory, and readiness status.",
        "- `channel_metrics.csv`: one row per ready channel with extracted baseline metrics.",
        "- `metric_distributions.csv`: cohort mean, median, range, and quantiles per metric.",
        "- `metric_percentiles.csv`: percentile rank of each channel on each metric.",
        "- `target_metrics.csv`: optional target rows, such as DoDoMen, excluded from the baseline distribution.",
        "- `target_metric_percentiles.csv`: optional target-vs-baseline percentile comparison.",
        "",
        "## Interpretation Notes",
        "",
        "- Percentile is directional only. A high percentile is not automatically good; for negative rate or conflict metrics it can indicate higher risk.",
        "- Target comparison percentiles mean percentage of baseline cohort channels with values at or below the target value. The target is not included in the baseline distribution.",
        "- Sample size must be reported with any percentile claim. Different metrics can have different `n` if a report lacks that section.",
        "- The baseline uses the verified `O` rows from the cohort CSV by default. Extra demo/test runs are excluded unless the script is pointed at a different cohort.",
        "- Audience structure and network metrics come from top-level comments; sentiment and reply-conflict metrics use all comments when reply Qwen rows are available.",
        "",
    ]
    return "\n".join(lines)


def normalize_youtube_url_key(url: object) -> str:
    text = str(url or "").strip()
    if not text:
        return ""
    parsed = urlparse(text if "://" in text else "https://" + text)
    path = parsed.path.rstrip("/")
    if "/channel/" in path:
        return "channel:" + path.split("/channel/", 1)[1].split("/", 1)[0].lower()
    if "/@" in path:
        return "handle:" + path.split("/@", 1)[1].split("/", 1)[0].lower()
    if path.startswith("/@"):
        return "handle:" + path[2:].split("/", 1)[0].lower()
    last = path.split("/")[-1].lower()
    return "last:" + last if last else ""


def first(value: object) -> dict:
    if isinstance(value, list) and value:
        item = value[0]
        return item if isinstance(item, dict) else {}
    return {}


def choose_continuity(rows: list[dict]) -> dict:
    if not rows:
        return {}
    for row in rows:
        n_windows = to_float(row.get("n_windows"))
        if not math.isnan(n_windows) and int(n_windows) == 4:
            return row
    return rows[0]


def tier_value(rows: list[dict], tier: str, field: str) -> float:
    for row in rows:
        if str(row.get("activity_tier")) == tier:
            return to_float(row.get(field))
    return math.nan


def sentiment_label_value(rows: list[dict], label: str, field: str) -> float:
    for row in rows:
        if str(row.get("sentiment_label")) == label:
            return to_float(row.get(field))
    return math.nan


def reply_label_value(rows: list[dict], label: str, field: str) -> float:
    for row in rows:
        if str(row.get("is_top_level_label")) == label:
            return to_float(row.get(field))
    return math.nan


def to_float(value: object) -> float:
    try:
        if value is None or value == "":
            return math.nan
        return float(value)
    except (TypeError, ValueError):
        return math.nan


def nan_to_zero(value: float) -> float:
    return 0.0 if math.isnan(value) else value


def divide(num: float, den: float) -> float:
    if den == 0 or math.isnan(den):
        return math.nan
    return num / den


def mean(values: list[float]) -> float:
    clean = [value for value in values if not math.isnan(value)]
    if not clean:
        return math.nan
    return sum(clean) / len(clean)


def max_or_nan(values: list[float]) -> float:
    clean = [value for value in values if not math.isnan(value)]
    return max(clean) if clean else math.nan
