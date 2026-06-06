from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from .config import AnalyzerConfig, ExternalAnalysisConfig
from .data import ChannelData


SEMANTIC_LABEL_FILENAME = "qwen_external_post_labels.csv"


@dataclass(frozen=True)
class ExternalEventArtifacts:
    output_dir: Path
    summary_path: Path
    report_en_path: Path | None
    report_zh_path: Path | None
    status: str
    n_posts: int
    n_event_clusters: int


def run_external_event_analysis(
    config: AnalyzerConfig,
    data: ChannelData,
    sentiment_data: ChannelData,
    run_dir: Path,
    *,
    append_report: bool = True,
) -> ExternalEventArtifacts:
    external_config = config.external_analysis
    output_dir = run_dir / "external_events"
    tables_dir = run_dir / "tables"
    output_dir.mkdir(parents=True, exist_ok=True)
    tables_dir.mkdir(parents=True, exist_ok=True)

    summary = build_empty_summary("not_started", external_config)
    report_en_path = run_dir / "report_en.md"
    report_zh_path = run_dir / "report_zh.md"

    if not external_config.enabled:
        summary = build_empty_summary("disabled", external_config)
        return write_external_outputs(output_dir, summary, append_report=False)

    mismatch = external_source_channel_mismatch(external_config, data)
    if mismatch:
        summary = build_empty_summary("source_channel_mismatch", external_config)
        summary.loc[0, "notes"] = mismatch
        artifacts = write_external_outputs(output_dir, summary)
        if append_report:
            append_external_report(run_dir, summary, pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), language="en")
            append_external_report(run_dir, summary, pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), language="zh")
        return artifacts

    posts = load_external_posts(external_config)
    if posts.empty:
        status = "missing_sources_dir" if not external_config.sources_dir or not external_config.sources_dir.exists() else "no_external_posts"
        summary = build_empty_summary(status, external_config)
        artifacts = write_external_outputs(output_dir, summary, posts=posts)
        if append_report:
            append_external_report(run_dir, summary, pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), language="en")
            append_external_report(run_dir, summary, pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), language="zh")
        return artifacts

    aliases = build_aliases(config, data)
    semantic_labels = load_semantic_labels(external_config, tables_dir)
    posts = enrich_posts(posts, aliases, semantic_labels, external_config)
    daily = build_daily_external_metrics(posts)
    event_clusters = build_event_clusters(daily, posts, external_config)

    sentiment = build_sentiment_frame(sentiment_data.comments, tables_dir / "qwen_comment_sentiment.csv")
    videos = data.videos.copy()
    conflict = load_reply_thread_metrics(tables_dir)
    windows = build_event_windows(event_clusters, sentiment, videos, external_config, conflict=conflict)
    audience = build_event_audience_windows(
        event_clusters,
        data.comments.copy(),
        external_config,
        sentiment=sentiment,
    )
    diagnostics = build_external_impact_diagnostics(windows, audience)

    status = "ok"
    if event_clusters.empty:
        status = "insufficient_external_events"
    elif windows.empty and audience.empty:
        status = "no_youtube_impact_rows"

    summary = build_summary(
        status=status,
        config=external_config,
        posts=posts,
        daily=daily,
        event_clusters=event_clusters,
        sentiment=sentiment,
        audience=audience,
    )
    artifacts = write_external_outputs(
        output_dir,
        summary,
        posts=posts.drop(columns=["text"], errors="ignore"),
        daily=daily,
        event_clusters=event_clusters,
        windows=windows,
        audience=audience,
        diagnostics=diagnostics,
    )
    if append_report:
        append_external_report(run_dir, summary, windows, audience, diagnostics, language="en")
        append_external_report(run_dir, summary, windows, audience, diagnostics, language="zh")
        sync_english_alias(run_dir)
    return ExternalEventArtifacts(
        output_dir=output_dir,
        summary_path=artifacts.summary_path,
        report_en_path=report_en_path if report_en_path.exists() else None,
        report_zh_path=report_zh_path if report_zh_path.exists() else None,
        status=status,
        n_posts=len(posts),
        n_event_clusters=len(event_clusters),
    )


def build_empty_summary(status: str, config: ExternalAnalysisConfig) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "status": status,
                "sources_dir": str(config.sources_dir or ""),
                "external_sources": ",".join(config.sources),
                "n_external_posts": 0,
                "n_relevant_posts": 0,
                "n_semantic_labeled_posts": 0,
                "external_semantics_source": "",
                "n_event_clusters": 0,
                "n_sentiment_rows": 0,
                "sentiment_source": "",
                "notes": status_note(status),
            }
        ]
    )


def status_note(status: str) -> str:
    notes = {
        "disabled": "External event analysis is disabled in config.",
        "missing_sources_dir": "External source directory is missing or not configured.",
        "no_external_posts": "No parseable PTT/Dcard posts were found.",
        "source_channel_mismatch": "External source manifest belongs to a different channel.",
        "insufficient_external_events": "External posts exist, but none passed event-candidate thresholds.",
        "no_youtube_impact_rows": "Event candidates exist, but no YouTube sentiment/audience rows overlapped the windows.",
        "ok": "External event analysis completed.",
    }
    return notes.get(status, status)


def external_source_channel_mismatch(config: ExternalAnalysisConfig, data: ChannelData) -> str:
    source_dir = config.sources_dir
    if source_dir is None:
        return ""
    manifest_path = source_dir / "external_source_manifest.json"
    if not manifest_path.exists() or manifest_path.stat().st_size == 0:
        return ""
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception:
        return ""
    metadata = manifest.get("metadata") if isinstance(manifest, dict) else {}
    if not isinstance(metadata, dict):
        return ""
    source_channel_id = str(metadata.get("channel_id") or "").strip()
    expected_channel_id = str(data.channel.get("channel_id") or "").strip()
    if source_channel_id and expected_channel_id and source_channel_id != expected_channel_id:
        return (
            "External source manifest channel_id mismatch: "
            f"sources_dir={source_dir}, source_channel_id={source_channel_id}, "
            f"target_channel_id={expected_channel_id}."
        )
    return ""


def load_external_posts(config: ExternalAnalysisConfig) -> pd.DataFrame:
    source_dir = config.sources_dir
    if source_dir is None or not source_dir.exists():
        return empty_posts_frame()

    posts = []
    sources = set(config.sources)
    if "dcard" in sources:
        posts.extend(load_dcard_posts(source_dir))
    if "ptt" in sources:
        posts.extend(load_ptt_posts(source_dir))
    if not posts:
        return empty_posts_frame()
    df = pd.DataFrame(posts)
    df["date"] = pd.to_datetime(df["date"], utc=True, errors="coerce")
    df = df.dropna(subset=["date"]).copy()
    df["event_date"] = df["date"].dt.floor("D")
    df["post_uid"] = df.apply(lambda row: stable_post_uid(row), axis=1)
    return df.drop_duplicates("post_uid", keep="last").sort_values(["date", "source", "title"]).reset_index(drop=True)


def empty_posts_frame() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "post_uid",
            "source",
            "post_id",
            "date",
            "date_quality",
            "event_date",
            "title",
            "url",
            "board_or_forum",
            "keyword",
            "engagement",
            "text",
        ]
    )


def load_dcard_posts(source_dir: Path) -> list[dict]:
    paths = [
        source_dir / "dcard" / "dcard_full.json",
        source_dir / "dcard_full.json",
    ]
    path = next((candidate for candidate in paths if candidate.exists()), None)
    if path is None:
        return []
    try:
        items = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []
    if not isinstance(items, list):
        return []

    explicit_dates: list[tuple[int, pd.Timestamp]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        date = parse_dcard_explicit_datetime(item.get("created_at", ""))
        if date is not None:
            explicit_dates.append((safe_int(item.get("id")), date))
    explicit_dates.sort()

    rows = []
    for item in items:
        if not isinstance(item, dict):
            continue
        post_id = safe_int(item.get("id"))
        title = str(item.get("title") or "")
        content = str(item.get("content") or item.get("body") or "")
        if not title:
            title = first_nonempty_line(content)
        text = f"{title}\n{content}".strip()
        date = parse_dcard_explicit_datetime(item.get("created_at", "")) or parse_dcard_explicit_datetime(text)
        date_quality = "explicit_dcard_created_at"
        if date is None:
            date = infer_dcard_no_year_datetime(post_id, text, explicit_dates)
            date_quality = "inferred_dcard_no_year"
        if date is None:
            continue
        rows.append(
            {
                "source": "dcard",
                "post_id": str(item.get("id") or item.get("url") or title),
                "date": date,
                "date_quality": date_quality,
                "title": title,
                "url": str(item.get("url") or ""),
                "board_or_forum": str(item.get("forum") or item.get("board") or ""),
                "keyword": str(item.get("keyword") or ""),
                "engagement": safe_int(item.get("like_count")) + safe_int(item.get("comment_count")),
                "text": text,
            }
        )
    return rows


def first_nonempty_line(text: object) -> str:
    for line in str(text or "").splitlines():
        stripped = line.strip()
        if stripped:
            return stripped[:200]
    return ""


def load_ptt_posts(source_dir: Path) -> list[dict]:
    paths = [
        source_dir / "ptt" / "ptt_full.json",
        source_dir / "ptt_full.json",
    ]
    path = next((candidate for candidate in paths if candidate.exists()), None)
    if path is None:
        return []
    try:
        items = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []
    if not isinstance(items, list):
        return []

    rows = []
    for item in items:
        if not isinstance(item, dict):
            continue
        date = parse_ptt_datetime(item.get("body", ""))
        if date is None:
            date = parse_dcard_explicit_datetime(item.get("created_at", ""))
        if date is None:
            continue
        title = str(item.get("title") or "")
        body = str(item.get("body") or item.get("content") or "")
        rows.append(
            {
                "source": "ptt",
                "post_id": str(item.get("url") or item.get("id") or title),
                "date": date,
                "date_quality": "explicit_ptt_body_time",
                "title": title,
                "url": str(item.get("url") or ""),
                "board_or_forum": str(item.get("board") or ""),
                "keyword": str(item.get("keyword") or ""),
                "engagement": safe_int(item.get("comment_count"))
                + safe_int(item.get("pushes"))
                + safe_int(item.get("boos")),
                "text": f"{title}\n{body}".strip(),
            }
        )
    return rows


def parse_dcard_explicit_datetime(created_at: object) -> pd.Timestamp | None:
    text = str(created_at or "").strip()
    match = re.search(r"(\d{2})/(\d{1,2})/(\d{1,2})\s+(\d{1,2}):(\d{2})", text)
    if not match:
        return None
    yy, month, day, hour, minute = map(int, match.groups())
    return pd.Timestamp(datetime(2000 + yy, month, day, hour, minute, tzinfo=timezone.utc))


def infer_dcard_no_year_datetime(
    post_id: int,
    text: str,
    explicit_dates: list[tuple[int, pd.Timestamp]],
) -> pd.Timestamp | None:
    match = re.search(r"(\d{1,2}) 月 (\d{1,2}) 日 (\d{1,2}):(\d{2})", text or "")
    if not match:
        return None
    month, day, hour, minute = map(int, match.groups())
    lower = max((date for known_id, date in explicit_dates if known_id < post_id), default=None)
    upper = min((date for known_id, date in explicit_dates if known_id > post_id), default=None)
    candidates = []
    for year in range(2018, 2028):
        try:
            candidate = pd.Timestamp(datetime(year, month, day, hour, minute, tzinfo=timezone.utc))
        except ValueError:
            continue
        if lower is not None and candidate < lower:
            continue
        if upper is not None and candidate > upper:
            continue
        candidates.append(candidate)
    if candidates:
        return candidates[0]
    anchors = [date for _, date in explicit_dates]
    if not anchors:
        return None
    all_candidates = [
        pd.Timestamp(datetime(year, month, day, hour, minute, tzinfo=timezone.utc))
        for year in range(2018, 2028)
    ]
    return min(all_candidates, key=lambda candidate: min(abs((candidate - anchor).total_seconds()) for anchor in anchors))


def parse_ptt_datetime(body: object) -> pd.Timestamp | None:
    match = re.search(
        r"時間\s+\w{3}\s+(\w{3})\s+(\d{1,2})\s+(\d{2}):(\d{2}):(\d{2})\s+(\d{4})",
        str(body or ""),
    )
    if not match:
        return None
    month_name, day, hour, minute, second, year = match.groups()
    try:
        dt = datetime.strptime(f"{year} {month_name} {day} {hour}:{minute}:{second}", "%Y %b %d %H:%M:%S")
    except ValueError:
        return None
    return pd.Timestamp(dt.replace(tzinfo=timezone.utc))


def stable_post_uid(row: pd.Series) -> str:
    raw = row.get("post_id") or row.get("url") or row.get("title") or ""
    return f"{row.get('source', 'external')}:{str(raw).strip()}"


def build_aliases(config: AnalyzerConfig, data: ChannelData) -> list[str]:
    aliases = list(config.external_analysis.channel_aliases)
    for value in [
        data.channel.get("title"),
        config.channel_handle,
        config.channel_url.rstrip("/").split("/")[-1] if config.channel_url else None,
    ]:
        text = str(value or "").strip()
        if text:
            aliases.append(text.lstrip("@"))
    seen = set()
    out = []
    for alias in aliases:
        normalized = normalize_text(alias)
        if normalized and normalized not in seen:
            seen.add(normalized)
            out.append(alias)
    return out


def enrich_posts(
    posts: pd.DataFrame,
    aliases: list[str],
    semantic_labels: pd.DataFrame,
    config: ExternalAnalysisConfig,
) -> pd.DataFrame:
    out = posts.copy()
    out["alias_hit"] = out.apply(lambda row: alias_hit(row, aliases), axis=1)
    out["heuristic_topic"] = out["text"].map(classify_heuristic_topic)
    out["heuristic_noise"] = out["text"].map(is_noise_post)
    out["heuristic_relevant"] = (~out["heuristic_noise"]) & (
        out["alias_hit"] | (not config.require_alias_match)
    )

    if not semantic_labels.empty:
        keep_cols = [
            col
            for col in [
                "post_uid",
                "is_relevant",
                "is_noise",
                "is_external_event_candidate",
                "event_type",
                "topic_label",
                "stance",
                "target",
                "semantic_confidence",
                "semantic_parse_error",
                "semantic_reason",
                "model",
            ]
            if col in semantic_labels.columns
        ]
        out = out.merge(semantic_labels[keep_cols], on="post_uid", how="left")
    else:
        for col in [
            "is_relevant",
            "is_noise",
            "is_external_event_candidate",
            "event_type",
            "topic_label",
            "stance",
            "target",
            "semantic_confidence",
            "semantic_parse_error",
            "semantic_reason",
            "model",
        ]:
            out[col] = np.nan

    semantic_present = out["is_relevant"].notna()
    out["semantic_used"] = semantic_present
    out["relevant"] = np.where(
        semantic_present,
        out["is_relevant"].map(to_bool),
        out["heuristic_relevant"],
    )
    out["noise"] = np.where(
        out["is_noise"].notna(),
        out["is_noise"].map(to_bool),
        out["heuristic_noise"],
    )
    out["event_topic"] = out["topic_label"].fillna("").astype(str).str.strip()
    out.loc[out["event_topic"].eq(""), "event_topic"] = out["event_type"].fillna("").astype(str).str.strip()
    out.loc[out["event_topic"].eq(""), "event_topic"] = out["heuristic_topic"]
    out["event_candidate_hint"] = out["is_external_event_candidate"].map(to_bool)
    return out


def load_semantic_labels(config: ExternalAnalysisConfig, tables_dir: Path) -> pd.DataFrame:
    path = config.semantic_labels_path or (tables_dir / SEMANTIC_LABEL_FILENAME)
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame()
    df = pd.read_csv(path, low_memory=False)
    if "post_uid" not in df.columns:
        return pd.DataFrame()
    for col in ["is_relevant", "is_noise", "is_external_event_candidate", "semantic_parse_error"]:
        if col in df.columns:
            df[col] = df[col].map(to_bool)
    return df.drop_duplicates("post_uid", keep="last")


def alias_hit(row: pd.Series, aliases: list[str]) -> bool:
    if not aliases:
        return False
    text = normalize_text(f"{row.get('title', '')}\n{row.get('keyword', '')}\n{row.get('text', '')}")
    return any(normalize_text(alias) in text for alias in aliases if normalize_text(alias))


def classify_heuristic_topic(text: object) -> str:
    lowered = normalize_text(text)
    if any(keyword in lowered for keyword in ["問卷", "填問卷", "抽1000", "學術問卷", "survey"]):
        return "survey_or_spam"
    if any(keyword in lowered for keyword in ["道歉", "炎上", "出征", "爭議", "被罵", "得罪", "apology"]):
        return "controversy_or_apology"
    if any(keyword in lowered for keyword in ["主持", "員工", "工作人員", "固定班底", "成員", "拆夥", "離開"]):
        return "staff_or_host_change"
    if any(keyword in lowered for keyword in ["統戰", "政治", "中共同路人", "西藏", "台派"]):
        return "political_or_social_controversy"
    if any(keyword in lowered for keyword in ["尬", "沒梗", "失望", "難看", "水準", "不好笑", "cringe"]):
        return "content_quality_criticism"
    if any(keyword in lowered for keyword in ["set", "造假", "真的假的", "真實", "剪輯", "腳本"]):
        return "content_authenticity_question"
    if any(keyword in lowered for keyword in ["推薦", "求推薦", "好看", "精彩"]):
        return "recommendation_or_general_mentions"
    return "general"


def is_noise_post(text: object) -> bool:
    lowered = normalize_text(text)
    return any(keyword in lowered for keyword in ["問卷", "填問卷", "抽1000", "學術問卷", "表單"])


def build_daily_external_metrics(posts: pd.DataFrame) -> pd.DataFrame:
    if posts.empty:
        return pd.DataFrame()
    eligible = posts[posts["relevant"].astype(bool) & ~posts["noise"].astype(bool)].copy()
    if eligible.empty:
        return pd.DataFrame()
    topic_mode = (
        eligible.groupby(["event_date", "event_topic"])
        .size()
        .reset_index(name="n")
        .sort_values(["event_date", "n", "event_topic"], ascending=[True, False, True])
        .drop_duplicates("event_date")
        .set_index("event_date")["event_topic"]
    )
    out = (
        eligible.groupby("event_date")
        .agg(
            external_posts=("post_uid", "count"),
            external_engagement=("engagement", "sum"),
            sources=("source", lambda s: ",".join(sorted(set(s)))),
            event_topics=("event_topic", lambda s: ";".join(sorted(set(s)))),
            top_titles=("title", lambda s: " || ".join(list(s.head(4)))),
            semantic_posts=("semantic_used", "sum"),
            candidate_hints=("event_candidate_hint", "sum"),
        )
        .reset_index()
    )
    out["dominant_topic"] = out["event_date"].map(topic_mode)
    return out


def build_event_clusters(
    daily: pd.DataFrame,
    posts: pd.DataFrame,
    config: ExternalAnalysisConfig,
) -> pd.DataFrame:
    if daily.empty:
        return pd.DataFrame()
    event_days = daily[
        (daily["external_posts"] >= config.min_daily_posts)
        | daily["sources"].str.contains(",", regex=False)
        | (daily["external_engagement"] >= config.min_external_engagement)
        | (daily["candidate_hints"] > 0)
    ].copy()
    if event_days.empty:
        return pd.DataFrame()

    event_days = event_days.sort_values(["dominant_topic", "event_date"]).reset_index(drop=True)
    clusters = []
    current = []
    current_topic = None
    last_date = None
    gap = pd.Timedelta(days=max(config.merge_gap_days, 0))
    for _, row in event_days.iterrows():
        topic = row["dominant_topic"]
        date = row["event_date"]
        should_start = current_topic != topic or last_date is None or date - last_date > gap
        if should_start and current:
            clusters.append(cluster_rows(current, posts, config))
            current = []
        current.append(row)
        current_topic = topic
        last_date = date
    if current:
        clusters.append(cluster_rows(current, posts, config))

    out = pd.DataFrame(clusters)
    if out.empty:
        return out
    out = out[
        (out["external_posts"] >= max(config.min_event_posts, config.min_daily_posts))
        | out["sources"].str.contains(",", regex=False)
        | (out["external_engagement"] >= config.min_external_engagement)
        | (out["candidate_hints"] > 0)
    ].copy()
    out = out.sort_values(["event_start", "external_posts", "external_engagement"], ascending=[True, False, False])
    out["event_cluster_id"] = [f"external_event_{idx:03d}" for idx in range(1, len(out) + 1)]
    cols = ["event_cluster_id"] + [col for col in out.columns if col != "event_cluster_id"]
    return out[cols]


def cluster_rows(rows: list[pd.Series], posts: pd.DataFrame, config: ExternalAnalysisConfig) -> dict:
    frame = pd.DataFrame(rows)
    start = frame["event_date"].min()
    end = frame["event_date"].max()
    peak = frame.sort_values(["external_posts", "external_engagement"], ascending=False).iloc[0]
    base_mask = (
        posts["relevant"].astype(bool)
        & ~posts["noise"].astype(bool)
        & (posts["event_date"] >= start)
        & (posts["event_date"] <= end)
    )
    topic_mask = base_mask & posts["event_topic"].eq(peak["dominant_topic"])
    cluster_posts = posts.loc[topic_mask].sort_values(["date", "source", "title"])
    event_topic = peak["dominant_topic"]
    topic_cluster_passes = (
        len(cluster_posts) >= max(config.min_event_posts, config.min_daily_posts)
        or "," in str(",".join(sorted(set(cluster_posts["source"]))) if not cluster_posts.empty else peak["sources"])
        or (int(cluster_posts["engagement"].sum()) if not cluster_posts.empty else int(frame["external_engagement"].sum()))
        >= config.min_external_engagement
        or (int(cluster_posts["event_candidate_hint"].sum()) if not cluster_posts.empty else int(frame["candidate_hints"].sum())) > 0
    )
    if not topic_cluster_passes and int(frame["external_posts"].sum()) >= config.min_daily_posts:
        cluster_posts = posts.loc[base_mask].sort_values(["date", "source", "title"])
        event_topic = "mixed_external_discussion"
    return {
        "event_start": start.date().isoformat(),
        "event_end": end.date().isoformat(),
        "event_date": pd.Timestamp(peak["event_date"]).date().isoformat(),
        "event_topic": event_topic,
        "sources": ",".join(sorted(set(cluster_posts["source"]))) if not cluster_posts.empty else peak["sources"],
        "external_posts": int(len(cluster_posts)) if not cluster_posts.empty else int(frame["external_posts"].sum()),
        "external_engagement": int(cluster_posts["engagement"].sum()) if not cluster_posts.empty else int(frame["external_engagement"].sum()),
        "semantic_posts": int(cluster_posts["semantic_used"].sum()) if not cluster_posts.empty else int(frame["semantic_posts"].sum()),
        "candidate_hints": int(cluster_posts["event_candidate_hint"].sum()) if not cluster_posts.empty else int(frame["candidate_hints"].sum()),
        "top_titles": " || ".join(cluster_posts["title"].head(5).tolist()) if not cluster_posts.empty else peak["top_titles"],
        "post_uids": ";".join(cluster_posts["post_uid"].head(20).tolist()) if not cluster_posts.empty else "",
        "window_pre_days": config.pre_days,
        "window_post_days": config.post_days,
        "baseline_days": config.baseline_days,
    }


def build_sentiment_frame(comments: pd.DataFrame, qwen_path: Path) -> pd.DataFrame:
    base_cols = [
        "comment_id",
        "video_id",
        "author_actor_id",
        "is_top_level",
        "comment_published_at",
        "like_count",
        "text_plain",
    ]
    c = comments[base_cols].copy()
    c["comment_published_at"] = pd.to_datetime(c["comment_published_at"], utc=True, errors="coerce")
    c = c.dropna(subset=["comment_published_at"])
    c["like_weight"] = c["like_count"].fillna(0).clip(lower=0) + 1
    if qwen_path.exists() and qwen_path.stat().st_size > 0:
        qwen = pd.read_csv(qwen_path, low_memory=False)
        if "sentiment_parse_error" in qwen.columns:
            qwen = qwen[qwen["sentiment_parse_error"].map(to_bool) == False].copy()  # noqa: E712
        keep = [col for col in ["comment_id", "sentiment_label", "score_neg", "score_pos"] if col in qwen.columns]
        if "comment_id" in keep and len(keep) >= 2:
            out = c.merge(qwen[keep].drop_duplicates("comment_id", keep="last"), on="comment_id", how="inner")
            if not out.empty:
                out["sentiment_source"] = "qwen"
                return finalize_sentiment(out)
    out = c.copy()
    lowered = out["text_plain"].fillna("").astype(str).str.lower()
    negative = lowered.str.contains("|".join(re.escape(k) for k in NEGATIVE_KEYWORDS), regex=True)
    positive = lowered.str.contains("|".join(re.escape(k) for k in POSITIVE_KEYWORDS), regex=True)
    out["sentiment_label"] = np.where(negative, "negative", np.where(positive, "positive", "neutral"))
    out["score_neg"] = np.where(negative, 0.75, 0.1)
    out["score_pos"] = np.where(positive, 0.75, 0.1)
    out["sentiment_source"] = "keyword_proxy"
    return finalize_sentiment(out)


NEGATIVE_KEYWORDS = ["失望", "難看", "爛", "討厭", "尷尬", "尬", "退訂", "不好笑", "炎上", "出征", "cringe", "bad"]
POSITIVE_KEYWORDS = ["好看", "喜歡", "支持", "精彩", "感動", "讚", "推薦", "love", "great"]


def finalize_sentiment(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["is_negative"] = out["sentiment_label"].eq("negative").astype(int)
    out["is_positive"] = out["sentiment_label"].eq("positive").astype(int)
    return out


def load_reply_thread_metrics(tables_dir: Path) -> pd.DataFrame:
    path = tables_dir / "reply_thread_metrics.csv"
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame()
    keep = [
        "thread_id",
        "video_id",
        "first_comment_at",
        "has_replies",
        "conflict_thread",
        "strict_reply_conflict_thread",
        "pile_on_thread",
        "parent_opposition_thread",
    ]
    try:
        df = pd.read_csv(path, usecols=lambda col: col in keep, low_memory=False)
    except Exception:
        return pd.DataFrame()
    if "first_comment_at" not in df.columns:
        return pd.DataFrame()
    df["first_comment_at"] = pd.to_datetime(df["first_comment_at"], utc=True, errors="coerce")
    df = df.dropna(subset=["first_comment_at"]).copy()
    for col in [
        "has_replies",
        "conflict_thread",
        "strict_reply_conflict_thread",
        "pile_on_thread",
        "parent_opposition_thread",
    ]:
        if col not in df.columns:
            df[col] = False
        df[col] = df[col].map(to_bool)
    return df


def build_event_windows(
    events: pd.DataFrame,
    sentiment: pd.DataFrame,
    videos: pd.DataFrame,
    config: ExternalAnalysisConfig,
    *,
    conflict: pd.DataFrame | None = None,
) -> pd.DataFrame:
    if events.empty or sentiment.empty:
        return pd.DataFrame()
    video_titles = videos[["video_id", "title", "published_at"]].copy()
    video_titles["published_at"] = pd.to_datetime(video_titles["published_at"], utc=True, errors="coerce")
    rows = []
    for _, event in events.iterrows():
        event_date = pd.Timestamp(event["event_start"], tz="UTC")
        baseline_start = event_date - pd.Timedelta(days=config.baseline_days + config.pre_days)
        baseline_end = event_date - pd.Timedelta(days=config.pre_days)
        pre_start = event_date - pd.Timedelta(days=config.pre_days)
        pre_end = event_date
        post_start = event_date
        post_end = event_date + pd.Timedelta(days=config.post_days)
        baseline = summarize_sentiment_window(sentiment, baseline_start, baseline_end)
        pre = summarize_sentiment_window(sentiment, pre_start, pre_end)
        post = summarize_sentiment_window(sentiment, post_start, post_end)
        z_pre, p_pre = two_prop_z(pre["negative_comments"], pre["comments"], post["negative_comments"], post["comments"])
        z_base, p_base = two_prop_z(
            baseline["negative_comments"],
            baseline["comments"],
            post["negative_comments"],
            post["comments"],
        )
        nearby = nearby_video_titles(video_titles, event_date)
        related_video_ids = nearby_video_ids(video_titles, event_date)
        affected = summarize_affected_video_spillover(
            sentiment,
            post_start,
            post_end,
            baseline["negative_rate"],
            related_video_ids,
        )
        decay = estimate_negative_impact_half_life(
            sentiment,
            post_start,
            post_end,
            baseline["negative_rate"],
        )
        baseline_conflict = summarize_conflict_window(conflict, baseline_start, baseline_end)
        pre_conflict = summarize_conflict_window(conflict, pre_start, pre_end)
        post_conflict = summarize_conflict_window(conflict, post_start, post_end)
        baseline_amp = ratio(baseline["like_weighted_negative_rate"], baseline["negative_rate"])
        post_amp = ratio(post["like_weighted_negative_rate"], post["negative_rate"])
        rows.append(
            {
                **event.to_dict(),
                "nearby_video_titles_±7d": nearby,
                "sentiment_source": sentiment["sentiment_source"].iloc[0] if "sentiment_source" in sentiment.columns and len(sentiment) else "",
                "baseline_comments": baseline["comments"],
                "baseline_negative_rate": baseline["negative_rate"],
                "baseline_like_weighted_negative_rate": baseline["like_weighted_negative_rate"],
                "pre_comments": pre["comments"],
                "pre_negative_rate": pre["negative_rate"],
                "post_comments": post["comments"],
                "post_negative_rate": post["negative_rate"],
                "comment_count_ratio_post_pre": post["comments"] / pre["comments"] if pre["comments"] else math.nan,
                "comment_volume_lift_vs_baseline": ratio(
                    post["comments"] / max(config.post_days, 1),
                    baseline["comments"] / max(config.baseline_days, 1),
                ),
                "delta_post_vs_pre_negative_rate_pp": (post["negative_rate"] - pre["negative_rate"]) * 100,
                "delta_post_vs_baseline_negative_rate_pp": (post["negative_rate"] - baseline["negative_rate"]) * 100,
                "post_vs_pre_negative_rate_p": p_pre,
                "post_vs_baseline_negative_rate_p": p_base,
                "post_vs_pre_negative_rate_z": z_pre,
                "post_vs_baseline_negative_rate_z": z_base,
                "post_like_weighted_negative_rate": post["like_weighted_negative_rate"],
                "delta_post_vs_pre_like_weighted_negative_rate_pp": (
                    post["like_weighted_negative_rate"] - pre["like_weighted_negative_rate"]
                )
                * 100,
                "delta_post_vs_baseline_like_weighted_negative_rate_pp": (
                    post["like_weighted_negative_rate"] - baseline["like_weighted_negative_rate"]
                )
                * 100,
                "baseline_negative_amplification_index": baseline_amp,
                "post_negative_amplification_index": post_amp,
                "negative_amplification_index": post_amp,
                "negative_amplification_lift_vs_baseline": ratio(post_amp, baseline_amp),
                "impact_half_life_days": decay["impact_half_life_days"],
                "impact_half_life_observed": decay["impact_half_life_observed"],
                **affected,
                "baseline_conflict_threads": baseline_conflict["conflict_threads"],
                "baseline_replied_threads": baseline_conflict["replied_threads"],
                "baseline_conflict_thread_rate_replied": baseline_conflict["conflict_thread_rate_replied"],
                "baseline_conflict_score": baseline_conflict["conflict_score"],
                "pre_conflict_threads": pre_conflict["conflict_threads"],
                "pre_replied_threads": pre_conflict["replied_threads"],
                "pre_conflict_thread_rate_replied": pre_conflict["conflict_thread_rate_replied"],
                "pre_conflict_score": pre_conflict["conflict_score"],
                "post_conflict_threads": post_conflict["conflict_threads"],
                "post_replied_threads": post_conflict["replied_threads"],
                "post_conflict_thread_rate_replied": post_conflict["conflict_thread_rate_replied"],
                "post_conflict_score": post_conflict["conflict_score"],
                "post_pile_on_threads": post_conflict["pile_on_threads"],
                "post_parent_opposition_threads": post_conflict["parent_opposition_threads"],
                "delta_post_vs_baseline_conflict_score": post_conflict["conflict_score"] - baseline_conflict["conflict_score"],
                "conflict_score_lift_vs_baseline": ratio(post_conflict["conflict_score"], baseline_conflict["conflict_score"]),
            }
        )
    return pd.DataFrame(rows)


def ratio(numerator: float, denominator: float) -> float:
    try:
        if pd.isna(numerator) or pd.isna(denominator) or denominator == 0:
            return math.nan
        return float(numerator) / float(denominator)
    except Exception:
        return math.nan


def nearby_video_ids(videos: pd.DataFrame, event_date: pd.Timestamp) -> set[str]:
    nearby = videos[
        (videos["published_at"] >= event_date - pd.Timedelta(days=7))
        & (videos["published_at"] < event_date + pd.Timedelta(days=8))
    ]
    return set(nearby["video_id"].dropna().astype(str))


def summarize_affected_video_spillover(
    sentiment: pd.DataFrame,
    start: pd.Timestamp,
    end: pd.Timestamp,
    baseline_negative_rate: float,
    related_video_ids: set[str],
) -> dict:
    empty = {
        "post_video_count": 0,
        "affected_video_count": 0,
        "affected_event_related_video_count": 0,
        "affected_non_event_video_count": 0,
        "spillover_ratio": math.nan,
    }
    if pd.isna(baseline_negative_rate):
        return empty
    sub = sentiment[(sentiment["comment_published_at"] >= start) & (sentiment["comment_published_at"] < end)]
    if sub.empty or "video_id" not in sub.columns:
        return empty
    by_video = (
        sub.groupby("video_id")
        .agg(
            comments=("comment_id", "count"),
            negative_comments=("is_negative", "sum"),
        )
        .reset_index()
    )
    by_video["negative_rate"] = by_video["negative_comments"] / by_video["comments"]
    affected = by_video[
        (by_video["comments"] >= 30)
        & (by_video["negative_rate"] >= baseline_negative_rate + 0.05)
    ].copy()
    if affected.empty:
        return {**empty, "post_video_count": int(by_video["video_id"].nunique())}
    related = affected["video_id"].astype(str).isin(related_video_ids)
    related_count = int(related.sum())
    non_related_count = int((~related).sum())
    return {
        "post_video_count": int(by_video["video_id"].nunique()),
        "affected_video_count": int(len(affected)),
        "affected_event_related_video_count": related_count,
        "affected_non_event_video_count": non_related_count,
        "spillover_ratio": ratio(non_related_count, related_count),
    }


def estimate_negative_impact_half_life(
    sentiment: pd.DataFrame,
    start: pd.Timestamp,
    end: pd.Timestamp,
    baseline_negative_rate: float,
) -> dict:
    if pd.isna(baseline_negative_rate):
        return {"impact_half_life_days": math.nan, "impact_half_life_observed": False}
    sub = sentiment[(sentiment["comment_published_at"] >= start) & (sentiment["comment_published_at"] < end)].copy()
    if sub.empty:
        return {"impact_half_life_days": math.nan, "impact_half_life_observed": False}
    sub["day"] = sub["comment_published_at"].dt.floor("D")
    daily = (
        sub.groupby("day")
        .agg(comments=("comment_id", "count"), negative_comments=("is_negative", "sum"))
        .sort_index()
    )
    daily["negative_rate"] = daily["negative_comments"] / daily["comments"]
    first_three_days = daily[daily.index < start + pd.Timedelta(days=3)]
    if first_three_days.empty:
        initial_rate = daily["negative_rate"].iloc[0]
    else:
        initial_rate = first_three_days["negative_comments"].sum() / first_three_days["comments"].sum()
    initial_lift = initial_rate - baseline_negative_rate
    if pd.isna(initial_lift) or initial_lift <= 0:
        return {"impact_half_life_days": math.nan, "impact_half_life_observed": False}
    threshold = baseline_negative_rate + initial_lift / 2
    daily["rolling_comments"] = daily["comments"].rolling(3, min_periods=1).sum()
    daily["rolling_negative_comments"] = daily["negative_comments"].rolling(3, min_periods=1).sum()
    daily["rolling_negative_rate"] = daily["rolling_negative_comments"] / daily["rolling_comments"]
    for day, row in daily.iterrows():
        if row["rolling_negative_rate"] <= threshold:
            return {
                "impact_half_life_days": int(max(0, (day - start.floor("D")).days)),
                "impact_half_life_observed": True,
            }
    return {
        "impact_half_life_days": int(math.ceil((end - start).total_seconds() / 86400)),
        "impact_half_life_observed": False,
    }


def summarize_conflict_window(conflict: pd.DataFrame | None, start: pd.Timestamp, end: pd.Timestamp) -> dict:
    empty = {
        "threads": 0,
        "replied_threads": 0,
        "conflict_threads": 0,
        "conflict_thread_rate_replied": math.nan,
        "conflict_score": math.nan,
        "pile_on_threads": 0,
        "parent_opposition_threads": 0,
    }
    if conflict is None or conflict.empty or "first_comment_at" not in conflict.columns:
        return empty
    sub = conflict[(conflict["first_comment_at"] >= start) & (conflict["first_comment_at"] < end)]
    if sub.empty:
        return {
            **empty,
            "conflict_score": 0.0,
        }
    replied = int(sub["has_replies"].sum())
    conflict_threads = int(sub["conflict_thread"].sum())
    rate = conflict_threads / replied if replied else math.nan
    return {
        "threads": int(len(sub)),
        "replied_threads": replied,
        "conflict_threads": conflict_threads,
        "conflict_thread_rate_replied": rate,
        "conflict_score": conflict_threads * rate if not pd.isna(rate) else 0.0,
        "pile_on_threads": int(sub["pile_on_thread"].sum()),
        "parent_opposition_threads": int(sub["parent_opposition_thread"].sum()),
    }


def summarize_sentiment_window(sentiment: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> dict:
    sub = sentiment[(sentiment["comment_published_at"] >= start) & (sentiment["comment_published_at"] < end)]
    n = len(sub)
    if n == 0:
        return {
            "comments": 0,
            "negative_comments": 0,
            "negative_rate": math.nan,
            "like_weighted_negative_rate": math.nan,
        }
    neg = int(sub["is_negative"].sum())
    denom = sub["like_weight"].sum()
    return {
        "comments": int(n),
        "negative_comments": neg,
        "negative_rate": neg / n,
        "like_weighted_negative_rate": float((sub["like_weight"] * sub["is_negative"]).sum() / denom) if denom else math.nan,
    }


def build_event_audience_windows(
    events: pd.DataFrame,
    comments: pd.DataFrame,
    config: ExternalAnalysisConfig,
    *,
    sentiment: pd.DataFrame | None = None,
) -> pd.DataFrame:
    if events.empty or comments.empty:
        return pd.DataFrame()
    top = comments[
        comments["is_top_level"].astype(bool)
        & comments["author_actor_id"].notna()
        & comments["comment_published_at"].notna()
    ].copy()
    if top.empty:
        return pd.DataFrame()
    top["comment_published_at"] = pd.to_datetime(top["comment_published_at"], utc=True, errors="coerce")
    top = top.dropna(subset=["comment_published_at"])
    first_seen = top.groupby("author_actor_id")["comment_published_at"].min()
    top["first_seen_at"] = top["author_actor_id"].map(first_seen)
    top_sentiment = prepare_top_level_sentiment(sentiment)
    max_seen = top["comment_published_at"].max()
    rows = []
    for _, event in events.iterrows():
        event_date = pd.Timestamp(event["event_start"], tz="UTC")
        baseline_start = event_date - pd.Timedelta(days=config.baseline_days + config.pre_days)
        baseline_end = event_date - pd.Timedelta(days=config.pre_days)
        pre_start = event_date - pd.Timedelta(days=config.pre_days)
        pre_end = event_date
        post_start = event_date
        post_end = event_date + pd.Timedelta(days=config.post_days)
        baseline = summarize_audience_window(top, baseline_start, baseline_end)
        pre = summarize_audience_window(top, pre_start, pre_end)
        post = summarize_audience_window(top, post_start, post_end)
        z_pre, p_pre = two_prop_z(pre["new_commenters"], pre["unique_commenters"], post["new_commenters"], post["unique_commenters"])
        z_base, p_base = two_prop_z(
            baseline["new_commenters"],
            baseline["unique_commenters"],
            post["new_commenters"],
            post["unique_commenters"],
        )
        follow_start = post_end
        follow_end = post_end + pd.Timedelta(days=config.post_days)
        new_authors = post["new_commenter_authors"]
        returned = top[
            (top["comment_published_at"] >= follow_start)
            & (top["comment_published_at"] < follow_end)
            & top["author_actor_id"].astype(str).isin(new_authors)
        ]["author_actor_id"].nunique()
        observed_follow_end = min(max_seen, follow_end)
        follow_days = max(0, int(math.ceil((observed_follow_end - follow_start).total_seconds() / 86400)))
        newcomer_sentiment = summarize_newcomer_sentiment_window(
            top_sentiment,
            post_start,
            post_end,
            new_authors,
        )
        rows.append(
            {
                **event.to_dict(),
                "baseline_unique_commenters": baseline["unique_commenters"],
                "baseline_new_commenters": baseline["new_commenters"],
                "baseline_new_commenter_share": baseline["new_commenter_share"],
                "pre_unique_commenters": pre["unique_commenters"],
                "pre_new_commenters": pre["new_commenters"],
                "pre_new_commenter_share": pre["new_commenter_share"],
                "post_unique_commenters": post["unique_commenters"],
                "post_new_commenters": post["new_commenters"],
                "post_new_commenter_share": post["new_commenter_share"],
                "delta_post_vs_pre_new_commenter_share_pp": (post["new_commenter_share"] - pre["new_commenter_share"]) * 100,
                "delta_post_vs_baseline_new_commenter_share_pp": (
                    post["new_commenter_share"] - baseline["new_commenter_share"]
                )
                * 100,
                "post_vs_pre_new_commenter_share_p": p_pre,
                "post_vs_baseline_new_commenter_share_p": p_base,
                "post_vs_pre_new_commenter_share_z": z_pre,
                "post_vs_baseline_new_commenter_share_z": z_base,
                "post_comments_by_new_commenters": post["comments_by_new_commenters"],
                "post_new_commenter_comment_share": post["new_commenter_comment_share"],
                "post_new_commenters_returned_next_window": int(returned),
                "post_new_commenter_next_window_return_rate": returned / post["new_commenters"] if post["new_commenters"] else math.nan,
                "followup_days_observed": follow_days,
                "followup_complete": bool(max_seen >= follow_end),
                **newcomer_sentiment,
            }
        )
    return pd.DataFrame(rows)


def prepare_top_level_sentiment(sentiment: pd.DataFrame | None) -> pd.DataFrame:
    if sentiment is None or sentiment.empty:
        return pd.DataFrame()
    required = {"author_actor_id", "comment_published_at", "is_negative", "like_weight", "is_top_level"}
    if not required.issubset(set(sentiment.columns)):
        return pd.DataFrame()
    top = sentiment[
        sentiment["is_top_level"].astype(bool)
        & sentiment["author_actor_id"].notna()
        & sentiment["comment_published_at"].notna()
    ].copy()
    if top.empty:
        return pd.DataFrame()
    top["comment_published_at"] = pd.to_datetime(top["comment_published_at"], utc=True, errors="coerce")
    return top.dropna(subset=["comment_published_at"])


def summarize_newcomer_sentiment_window(
    sentiment: pd.DataFrame,
    start: pd.Timestamp,
    end: pd.Timestamp,
    new_authors: set[str],
) -> dict:
    empty = {
        "post_new_commenter_sentiment_comments": 0,
        "post_returning_commenter_sentiment_comments": 0,
        "post_new_commenter_negative_rate": math.nan,
        "post_returning_commenter_negative_rate": math.nan,
        "new_commenter_negative_rate_gap_pp": math.nan,
        "post_new_commenter_like_weighted_negative_rate": math.nan,
        "post_returning_commenter_like_weighted_negative_rate": math.nan,
        "new_commenter_like_weighted_negative_rate_gap_pp": math.nan,
    }
    if sentiment.empty:
        return empty
    sub = sentiment[(sentiment["comment_published_at"] >= start) & (sentiment["comment_published_at"] < end)].copy()
    if sub.empty:
        return empty
    new_mask = sub["author_actor_id"].astype(str).isin(new_authors)
    new_summary = summarize_sentiment_slice(sub[new_mask])
    returning_summary = summarize_sentiment_slice(sub[~new_mask])
    return {
        "post_new_commenter_sentiment_comments": new_summary["comments"],
        "post_returning_commenter_sentiment_comments": returning_summary["comments"],
        "post_new_commenter_negative_rate": new_summary["negative_rate"],
        "post_returning_commenter_negative_rate": returning_summary["negative_rate"],
        "new_commenter_negative_rate_gap_pp": (new_summary["negative_rate"] - returning_summary["negative_rate"]) * 100,
        "post_new_commenter_like_weighted_negative_rate": new_summary["like_weighted_negative_rate"],
        "post_returning_commenter_like_weighted_negative_rate": returning_summary["like_weighted_negative_rate"],
        "new_commenter_like_weighted_negative_rate_gap_pp": (
            new_summary["like_weighted_negative_rate"] - returning_summary["like_weighted_negative_rate"]
        )
        * 100,
    }


def summarize_sentiment_slice(df: pd.DataFrame) -> dict:
    if df.empty:
        return {
            "comments": 0,
            "negative_rate": math.nan,
            "like_weighted_negative_rate": math.nan,
        }
    denom = df["like_weight"].sum()
    return {
        "comments": int(len(df)),
        "negative_rate": float(df["is_negative"].mean()),
        "like_weighted_negative_rate": float((df["like_weight"] * df["is_negative"]).sum() / denom) if denom else math.nan,
    }


def summarize_audience_window(comments: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> dict:
    sub = comments[(comments["comment_published_at"] >= start) & (comments["comment_published_at"] < end)]
    if sub.empty:
        return {
            "unique_commenters": 0,
            "new_commenters": 0,
            "new_commenter_share": math.nan,
            "comments_by_new_commenters": 0,
            "new_commenter_comment_share": math.nan,
            "new_commenter_authors": set(),
        }
    active = set(sub["author_actor_id"].dropna().astype(str))
    first_seen = sub[["author_actor_id", "first_seen_at"]].drop_duplicates("author_actor_id")
    new_authors = set(
        first_seen[
            (first_seen["first_seen_at"] >= start)
            & (first_seen["first_seen_at"] < end)
        ]["author_actor_id"].astype(str)
    )
    new_mask = sub["author_actor_id"].astype(str).isin(new_authors)
    return {
        "unique_commenters": len(active),
        "new_commenters": len(new_authors),
        "new_commenter_share": len(new_authors) / len(active) if active else math.nan,
        "comments_by_new_commenters": int(new_mask.sum()),
        "new_commenter_comment_share": float(new_mask.mean()) if len(sub) else math.nan,
        "new_commenter_authors": new_authors,
    }


def two_prop_z(k1: float, n1: float, k2: float, n2: float) -> tuple[float, float]:
    if min(n1, n2) <= 0:
        return (math.nan, math.nan)
    p1 = k1 / n1
    p2 = k2 / n2
    pooled = (k1 + k2) / (n1 + n2)
    se = math.sqrt(max(pooled * (1 - pooled) * (1 / n1 + 1 / n2), 0))
    if se == 0:
        return (math.nan, math.nan)
    z = (p2 - p1) / se
    p = math.erfc(abs(z) / math.sqrt(2))
    return (z, p)


def nearby_video_titles(videos: pd.DataFrame, event_date: pd.Timestamp) -> str:
    nearby = videos[
        (videos["published_at"] >= event_date - pd.Timedelta(days=7))
        & (videos["published_at"] < event_date + pd.Timedelta(days=8))
    ].sort_values("published_at")
    return " || ".join(nearby["title"].head(5).fillna("").astype(str).tolist())


def build_summary(
    status: str,
    config: ExternalAnalysisConfig,
    posts: pd.DataFrame,
    daily: pd.DataFrame,
    event_clusters: pd.DataFrame,
    sentiment: pd.DataFrame,
    audience: pd.DataFrame,
) -> pd.DataFrame:
    relevant = posts["relevant"].astype(bool) if "relevant" in posts.columns else pd.Series([], dtype=bool)
    return pd.DataFrame(
        [
            {
                "status": status,
                "sources_dir": str(config.sources_dir or ""),
                "external_sources": ",".join(config.sources),
                "n_external_posts": len(posts),
                "n_relevant_posts": int(relevant.sum()) if len(relevant) else 0,
                "n_semantic_labeled_posts": int(posts["semantic_used"].sum()) if "semantic_used" in posts.columns else 0,
                "external_semantics_source": (
                    "qwen_external_post_labels"
                    if "semantic_used" in posts.columns and int(posts["semantic_used"].sum()) > 0
                    else "heuristic_alias_topic"
                ),
                "n_noise_posts": int(posts["noise"].astype(bool).sum()) if "noise" in posts.columns else 0,
                "n_external_days": int(posts["event_date"].nunique()) if "event_date" in posts.columns else 0,
                "n_candidate_days": len(daily),
                "n_event_clusters": len(event_clusters),
                "n_sentiment_rows": len(sentiment),
                "sentiment_source": sentiment["sentiment_source"].iloc[0] if not sentiment.empty and "sentiment_source" in sentiment.columns else "",
                "n_audience_event_windows": len(audience),
                "baseline_days": config.baseline_days,
                "pre_days": config.pre_days,
                "post_days": config.post_days,
                "notes": status_note(status),
            }
        ]
    )


def build_external_impact_diagnostics(windows: pd.DataFrame, audience: pd.DataFrame) -> pd.DataFrame:
    if windows.empty and audience.empty:
        return pd.DataFrame()
    event_cols = [
        "event_cluster_id",
        "event_topic",
        "event_start",
        "event_end",
        "external_posts",
        "external_engagement",
        "sources",
        "top_titles",
    ]
    base_source = windows if not windows.empty else audience
    base = base_source[[col for col in event_cols if col in base_source.columns]].drop_duplicates("event_cluster_id").copy()
    window_cols = [
        "event_cluster_id",
        "post_comments",
        "baseline_negative_rate",
        "post_negative_rate",
        "delta_post_vs_baseline_negative_rate_pp",
        "post_vs_baseline_negative_rate_p",
        "post_like_weighted_negative_rate",
        "delta_post_vs_baseline_like_weighted_negative_rate_pp",
        "negative_amplification_index",
        "negative_amplification_lift_vs_baseline",
        "comment_volume_lift_vs_baseline",
        "impact_half_life_days",
        "impact_half_life_observed",
        "affected_video_count",
        "affected_event_related_video_count",
        "affected_non_event_video_count",
        "spillover_ratio",
        "post_conflict_score",
        "delta_post_vs_baseline_conflict_score",
        "conflict_score_lift_vs_baseline",
        "post_conflict_threads",
        "post_pile_on_threads",
        "post_parent_opposition_threads",
    ]
    audience_cols = [
        "event_cluster_id",
        "post_unique_commenters",
        "post_new_commenters",
        "post_new_commenter_share",
        "delta_post_vs_baseline_new_commenter_share_pp",
        "post_vs_baseline_new_commenter_share_p",
        "post_new_commenter_next_window_return_rate",
        "post_new_commenter_negative_rate",
        "post_returning_commenter_negative_rate",
        "new_commenter_negative_rate_gap_pp",
        "post_new_commenter_like_weighted_negative_rate",
        "post_returning_commenter_like_weighted_negative_rate",
        "new_commenter_like_weighted_negative_rate_gap_pp",
        "followup_complete",
    ]
    if not windows.empty:
        base = base.merge(windows[[col for col in window_cols if col in windows.columns]], on="event_cluster_id", how="left")
    if not audience.empty:
        base = base.merge(audience[[col for col in audience_cols if col in audience.columns]], on="event_cluster_id", how="left")
    for col in [
        "delta_post_vs_baseline_negative_rate_pp",
        "post_vs_baseline_negative_rate_p",
        "delta_post_vs_baseline_new_commenter_share_pp",
        "post_vs_baseline_new_commenter_share_p",
        "new_commenter_negative_rate_gap_pp",
        "conflict_score_lift_vs_baseline",
        "spillover_ratio",
    ]:
        if col not in base.columns:
            base[col] = math.nan
    base["negative_response_signal"] = (
        (base["delta_post_vs_baseline_negative_rate_pp"] >= 3)
        & (base["post_vs_baseline_negative_rate_p"] < 0.05)
    )
    base["new_audience_signal"] = (
        (base["delta_post_vs_baseline_new_commenter_share_pp"] >= 2)
        & (base["post_vs_baseline_new_commenter_share_p"] < 0.05)
    )
    base["newcomer_negative_signal"] = base["new_commenter_negative_rate_gap_pp"] >= 3
    base["conflict_lift_signal"] = base["conflict_score_lift_vs_baseline"] >= 2
    base["spillover_signal"] = base["spillover_ratio"] > 1
    signal_cols = [
        "negative_response_signal",
        "new_audience_signal",
        "newcomer_negative_signal",
        "conflict_lift_signal",
        "spillover_signal",
    ]
    base["diagnostic_signal_count"] = base[signal_cols].fillna(False).astype(bool).sum(axis=1)
    base["diagnostic_interpretation"] = base.apply(describe_diagnostic_row, axis=1)
    return base.sort_values(
        [
            "diagnostic_signal_count",
            "delta_post_vs_baseline_negative_rate_pp",
            "delta_post_vs_baseline_new_commenter_share_pp",
            "event_start",
        ],
        ascending=[False, False, False, True],
    ).reset_index(drop=True)


def describe_diagnostic_row(row: pd.Series) -> str:
    labels = []
    if to_bool(row.get("negative_response_signal")):
        labels.append("negative_response_above_baseline")
    if to_bool(row.get("new_audience_signal")):
        labels.append("new_audience_entry_above_baseline")
    if to_bool(row.get("newcomer_negative_signal")):
        labels.append("new_commenters_more_negative")
    if to_bool(row.get("conflict_lift_signal")):
        labels.append("reply_conflict_lift")
    if to_bool(row.get("spillover_signal")):
        labels.append("negative_spillover_beyond_event_nearby_videos")
    return ";".join(labels) if labels else "weak_or_baseline_like"


def write_external_outputs(
    output_dir: Path,
    summary: pd.DataFrame,
    *,
    posts: pd.DataFrame | None = None,
    daily: pd.DataFrame | None = None,
    event_clusters: pd.DataFrame | None = None,
    windows: pd.DataFrame | None = None,
    audience: pd.DataFrame | None = None,
    diagnostics: pd.DataFrame | None = None,
    append_report: bool = True,
) -> ExternalEventArtifacts:
    output_dir.mkdir(parents=True, exist_ok=True)
    summary_path = output_dir / "external_event_summary.csv"
    summary.to_csv(summary_path, index=False)
    (posts if posts is not None else empty_posts_frame()).to_csv(output_dir / "external_posts.csv", index=False)
    (daily if daily is not None else pd.DataFrame()).to_csv(output_dir / "external_daily_metrics.csv", index=False)
    (event_clusters if event_clusters is not None else pd.DataFrame()).to_csv(output_dir / "external_event_clusters.csv", index=False)
    (windows if windows is not None else pd.DataFrame()).to_csv(output_dir / "external_event_windows.csv", index=False)
    (audience if audience is not None else pd.DataFrame()).to_csv(output_dir / "external_event_audience_windows.csv", index=False)
    (diagnostics if diagnostics is not None else pd.DataFrame()).to_csv(
        output_dir / "external_event_impact_diagnostics.csv",
        index=False,
    )
    row = summary.iloc[0].to_dict() if not summary.empty else {}
    return ExternalEventArtifacts(
        output_dir=output_dir,
        summary_path=summary_path,
        report_en_path=None,
        report_zh_path=None,
        status=str(row.get("status") or ""),
        n_posts=int(row.get("n_external_posts") or 0),
        n_event_clusters=int(row.get("n_event_clusters") or 0),
    )


def append_external_report(
    run_dir: Path,
    summary: pd.DataFrame,
    windows: pd.DataFrame,
    audience: pd.DataFrame,
    diagnostics: pd.DataFrame,
    *,
    language: str,
) -> None:
    path = run_dir / ("report_zh.md" if language == "zh" else "report_en.md")
    if not path.exists():
        return
    content = strip_external_report_block(path.read_text(encoding="utf-8"))
    block = render_external_report_block(summary, windows, audience, diagnostics, language=language)
    path.write_text(content.rstrip() + "\n\n" + block + "\n", encoding="utf-8")


def strip_external_report_block(text: str) -> str:
    pattern = re.compile(
        r"\n*<!-- EXTERNAL_EVENT_ANALYSIS_START -->.*?<!-- EXTERNAL_EVENT_ANALYSIS_END -->\n*",
        flags=re.S,
    )
    return pattern.sub("\n", text).rstrip()


def render_external_report_block(
    summary: pd.DataFrame,
    windows: pd.DataFrame,
    audience: pd.DataFrame,
    diagnostics: pd.DataFrame,
    *,
    language: str,
) -> str:
    zh = language == "zh"
    row = summary.iloc[0].to_dict() if not summary.empty else {}
    status = str(row.get("status") or "unknown")
    lines = ["<!-- EXTERNAL_EVENT_ANALYSIS_START -->"]
    if zh:
        lines.extend(
            [
                "## 外部事件分析",
                "",
                "這一節把 PTT/Dcard 外部討論和 YouTube 留言反應對齊。它是事件視窗關聯分析，不是因果估計。",
                "",
                f"- 狀態：`{status}`",
                f"- 外部貼文數：{int(row.get('n_external_posts') or 0):,}",
                f"- 相關貼文數：{int(row.get('n_relevant_posts') or 0):,}",
                f"- 事件群數：{int(row.get('n_event_clusters') or 0):,}",
                f"- 外部貼文語意來源：`{row.get('external_semantics_source') or ''}`",
                f"- 情緒來源：`{row.get('sentiment_source') or ''}`",
                f"- 視窗：baseline {int(row.get('baseline_days') or 0)} 天，pre {int(row.get('pre_days') or 0)} 天，post {int(row.get('post_days') or 0)} 天。",
            ]
        )
    else:
        lines.extend(
            [
                "## External Event Analysis",
                "",
                "This section aligns PTT/Dcard external discussion with YouTube comment response. It is event-window association evidence, not a causal estimate.",
                "",
                f"- Status: `{status}`",
                f"- External posts: {int(row.get('n_external_posts') or 0):,}",
                f"- Relevant posts: {int(row.get('n_relevant_posts') or 0):,}",
                f"- Event clusters: {int(row.get('n_event_clusters') or 0):,}",
                f"- External semantic source: `{row.get('external_semantics_source') or ''}`",
                f"- Sentiment source: `{row.get('sentiment_source') or ''}`",
                f"- Windows: baseline {int(row.get('baseline_days') or 0)} days, pre {int(row.get('pre_days') or 0)} days, post {int(row.get('post_days') or 0)} days.",
            ]
        )
    if status != "ok":
        lines.extend(["", status_note(status)])
    else:
        sentiment_cols = [
            "event_cluster_id",
            "event_topic",
            "event_start",
            "event_end",
            "external_posts",
            "post_comments",
            "delta_post_vs_baseline_negative_rate_pp",
            "post_vs_baseline_negative_rate_p",
            "delta_post_vs_baseline_like_weighted_negative_rate_pp",
            "top_titles",
        ]
        audience_cols = [
            "event_cluster_id",
            "event_topic",
            "event_start",
            "event_end",
            "external_posts",
            "post_new_commenters",
            "delta_post_vs_baseline_new_commenter_share_pp",
            "post_vs_baseline_new_commenter_share_p",
            "post_new_commenter_next_window_return_rate",
            "top_titles",
        ]
        diagnostic_cols = [
            "event_cluster_id",
            "event_topic",
            "event_start",
            "external_posts",
            "delta_post_vs_baseline_negative_rate_pp",
            "negative_amplification_index",
            "delta_post_vs_baseline_new_commenter_share_pp",
            "new_commenter_negative_rate_gap_pp",
            "conflict_score_lift_vs_baseline",
            "impact_half_life_days",
            "spillover_ratio",
            "diagnostic_interpretation",
        ]
        top_sentiment = (
            windows[windows["delta_post_vs_baseline_negative_rate_pp"] > 0]
            .sort_values(
                ["delta_post_vs_baseline_negative_rate_pp", "post_comments"],
                ascending=[False, False],
            )
            .head(8)
            if not windows.empty and "delta_post_vs_baseline_negative_rate_pp" in windows.columns
            else pd.DataFrame()
        )
        top_audience = (
            audience[audience["delta_post_vs_baseline_new_commenter_share_pp"] > 0]
            .sort_values(
                ["delta_post_vs_baseline_new_commenter_share_pp", "post_new_commenters"],
                ascending=[False, False],
            )
            .head(8)
            if not audience.empty and "delta_post_vs_baseline_new_commenter_share_pp" in audience.columns
            else pd.DataFrame()
        )
        top_diagnostics = (
            diagnostics.sort_values(
                [
                    "diagnostic_signal_count",
                    "delta_post_vs_baseline_negative_rate_pp",
                    "delta_post_vs_baseline_new_commenter_share_pp",
                ],
                ascending=[False, False, False],
            )
            .head(10)
            if not diagnostics.empty and "diagnostic_signal_count" in diagnostics.columns
            else pd.DataFrame()
        )
        if zh:
            lines.extend(["", "### 負面反應高於 baseline 的事件群", ""])
        else:
            lines.extend(["", "### Event Clusters With Negative Response Above Baseline", ""])
        lines.append(markdown_table(top_sentiment, sentiment_cols))
        if zh:
            lines.extend(["", "### 新留言者高於 baseline 的事件群", ""])
        else:
            lines.extend(["", "### Event Clusters With New Commenters Above Baseline", ""])
        lines.append(markdown_table(top_audience, audience_cols))
        if zh:
            lines.extend(
                [
                    "",
                    "### 外部事件影響診斷指標",
                    "",
                    "`pp` 是 percentage points；`negative_amplification_index` 大於 1 代表 post window 中負面留言得到的 like 權重高於負面留言占比；`spillover_ratio` 只在事件附近影片也有受影響影片時才有定義。",
                    "",
                ]
            )
        else:
            lines.extend(
                [
                    "",
                    "### External Event Impact Diagnostics",
                    "",
                    "`pp` means percentage points. `negative_amplification_index` above 1 means negative comments received more like weight than their raw share in the post window. `spillover_ratio` is defined only when event-nearby videos also contain affected videos.",
                    "",
                ]
            )
        lines.append(markdown_table(top_diagnostics, diagnostic_cols))
    lines.append("<!-- EXTERNAL_EVENT_ANALYSIS_END -->")
    return "\n".join(lines)


def markdown_table(df: pd.DataFrame, cols: list[str]) -> str:
    if df.empty:
        return "No rows."
    available = [col for col in cols if col in df.columns]
    if not available:
        return "No rows."
    rows = ["| " + " | ".join(available) + " |", "| " + " | ".join(["---"] * len(available)) + " |"]
    for _, row in df[available].iterrows():
        rows.append("| " + " | ".join(format_cell(row[col]) for col in available) + " |")
    return "\n".join(rows)


def format_cell(value: object) -> str:
    if pd.isna(value):
        text = ""
    elif isinstance(value, float):
        text = f"{value:.4g}"
    else:
        text = str(value)
    return text.replace("|", "\\|").replace("\n", " ")


def sync_english_alias(run_dir: Path) -> None:
    report_en = run_dir / "report_en.md"
    report = run_dir / "report.md"
    if report_en.exists():
        report.write_text(report_en.read_text(encoding="utf-8"), encoding="utf-8")


def safe_int(value: object) -> int:
    try:
        if pd.isna(value):
            return 0
        return int(value)
    except Exception:
        return 0


def to_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    if isinstance(value, float) and math.isnan(value):
        return False
    text = str(value).strip().lower()
    return text in {"1", "true", "yes", "y", "t"}


def normalize_text(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip().lower())
