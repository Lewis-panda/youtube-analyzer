from __future__ import annotations

from dataclasses import dataclass
import re
import sqlite3
from pathlib import Path

import pandas as pd

from .config import AnalyzerConfig


@dataclass(frozen=True)
class ChannelData:
    channel: dict
    videos: pd.DataFrame
    comments: pd.DataFrame


def connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def load_channel_data(
    config: AnalyzerConfig,
    *,
    include_replies: bool | None = None,
) -> ChannelData:
    if not config.db_path.exists():
        raise FileNotFoundError(f"SQLite database not found: {config.db_path}")
    conn = connect(config.db_path)
    try:
        channel = resolve_channel(conn, config)
        videos = load_videos(conn, channel["channel_id"], config)
        comments = load_comments(
            conn,
            channel["channel_id"],
            config,
            include_replies=include_replies,
        )
        comments = comments[comments["video_id"].isin(set(videos["video_id"]))].copy()
    finally:
        conn.close()
    return ChannelData(channel=channel, videos=videos, comments=comments)


def resolve_channel(conn: sqlite3.Connection, config: AnalyzerConfig) -> dict:
    if config.channel_id:
        row = conn.execute(
            "SELECT * FROM channels WHERE channel_id = ?",
            (config.channel_id,),
        ).fetchone()
        if row:
            return dict(row)

    candidates = []
    if config.channel_handle:
        handle = config.channel_handle.strip().lstrip("@").lower()
        candidates.append(handle)
    if config.channel_url:
        candidates.append(config.channel_url.rstrip("/").split("/")[-1].lstrip("@").lower())

    for candidate in candidates:
        row = conn.execute(
            """
            SELECT *
            FROM channels
            WHERE lower(coalesce(custom_url, '')) LIKE ?
               OR lower(coalesce(title, '')) = ?
            LIMIT 1
            """,
            (f"%{candidate}%", candidate),
        ).fetchone()
        if row:
            return dict(row)

    available = conn.execute(
        "SELECT channel_id, title, custom_url FROM channels ORDER BY title LIMIT 10"
    ).fetchall()
    sample = ", ".join(f"{r['title']} ({r['channel_id']})" for r in available)
    raise RuntimeError(
        "Channel not found in SQLite. Crawl/build it with ../youtube_graph_ingest first. "
        f"Available sample: {sample}"
    )


def load_videos(
    conn: sqlite3.Connection,
    channel_id: str,
    config: AnalyzerConfig,
) -> pd.DataFrame:
    where = ["owner_channel_id = ?"]
    params: list[object] = [channel_id]
    if config.date_start:
        where.append("published_at >= ?")
        params.append(config.date_start)
    if config.date_end:
        where.append("published_at < ?")
        params.append(config.date_end)

    df = pd.read_sql_query(
        f"""
        SELECT
          video_id,
          owner_channel_id,
          title,
          description,
          published_at,
          category_id,
          tags_json,
          duration,
          view_count,
          like_count,
          comment_count
        FROM videos
        WHERE {' AND '.join(where)}
        ORDER BY published_at
        """,
        conn,
        params=params,
    )
    if df.empty:
        raise RuntimeError("No videos matched the configured channel/date filters.")
    df["published_at"] = pd.to_datetime(df["published_at"], utc=True, errors="coerce")
    if config.exclude_shorts:
        duration_seconds = df["duration"].map(_youtube_duration_seconds)
        df = df[duration_seconds >= config.short_threshold_seconds].copy()
        if df.empty:
            raise RuntimeError(
                "No videos remain after short-form filtering. Set exclude_shorts=false "
                "or lower short_threshold_seconds in config."
            )
    return df


def load_comments(
    conn: sqlite3.Connection,
    channel_id: str,
    config: AnalyzerConfig,
    *,
    include_replies: bool | None = None,
) -> pd.DataFrame:
    where = ["v.owner_channel_id = ?"]
    params: list[object] = [channel_id]
    use_replies = config.include_replies if include_replies is None else include_replies
    if not use_replies:
        where.append("c.is_top_level = 1")
    if config.date_start:
        where.append("v.published_at >= ?")
        params.append(config.date_start)
    if config.date_end:
        where.append("v.published_at < ?")
        params.append(config.date_end)

    df = pd.read_sql_query(
        f"""
        SELECT
          c.comment_id,
          c.thread_id,
          c.video_id,
          c.author_actor_id,
          c.parent_comment_id,
          c.is_top_level,
          c.text_plain,
          c.like_count,
          c.published_at AS comment_published_at,
          v.published_at AS video_published_at,
          a.latest_display_name AS author_display_name,
          a.author_channel_url
        FROM comments c
        JOIN videos v ON c.video_id = v.video_id
        LEFT JOIN actors a ON c.author_actor_id = a.actor_id
        WHERE {' AND '.join(where)}
          AND c.author_actor_id IS NOT NULL
        """,
        conn,
        params=params,
    )
    if df.empty:
        raise RuntimeError("No comments matched the configured channel/date filters.")
    df["comment_published_at"] = pd.to_datetime(
        df["comment_published_at"], utc=True, errors="coerce"
    )
    df["video_published_at"] = pd.to_datetime(
        df["video_published_at"], utc=True, errors="coerce"
    )
    df["like_count"] = df["like_count"].fillna(0).astype(int)
    return df


def _youtube_duration_seconds(value: object) -> int:
    if not isinstance(value, str):
        return -1
    match = re.fullmatch(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", value)
    if not match:
        return -1
    hours, minutes, seconds = match.groups()
    return int(hours or 0) * 3600 + int(minutes or 0) * 60 + int(seconds or 0)
