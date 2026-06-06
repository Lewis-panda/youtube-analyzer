#!/usr/bin/env python3
"""Requeue existing channel videos for a refresh crawl."""

from __future__ import annotations

import argparse
import re
import sqlite3
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT.parent / "SharedData" / "state" / "yt_graph.sqlite3"
ISO_DURATION_RE = re.compile(
    r"^P"
    r"(?:(?P<days>\d+)D)?"
    r"(?:T"
    r"(?:(?P<hours>\d+)H)?"
    r"(?:(?P<minutes>\d+)M)?"
    r"(?:(?P<seconds>\d+)S)?"
    r")?$"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--config", type=Path, help="Analyzer YAML config with channel_id.")
    parser.add_argument("--channel-id", help="YouTube channel_id. Overrides --config.")
    parser.add_argument("--published-after", help="Only requeue videos on/after this ISO datetime/date.")
    parser.add_argument("--exclude-shorts", action="store_true", default=True)
    parser.add_argument("--include-shorts", action="store_true")
    parser.add_argument("--short-threshold-seconds", type=int, default=180)
    parser.add_argument("--apply", action="store_true", help="Actually update url_queue.")
    return parser.parse_args()


def load_channel_id(args: argparse.Namespace) -> str:
    if args.channel_id:
        return args.channel_id
    if not args.config:
        raise SystemExit("Provide --channel-id or --config.")
    data = yaml.safe_load(args.config.read_text(encoding="utf-8")) or {}
    channel_id = data.get("channel_id")
    if not channel_id:
        raise SystemExit(f"Config has no channel_id: {args.config}")
    return str(channel_id)


def duration_seconds(value: str | None) -> int | None:
    if not value:
        return None
    match = ISO_DURATION_RE.match(value)
    if not match:
        return None
    parts = {key: int(val) if val else 0 for key, val in match.groupdict().items()}
    return (
        parts["days"] * 86400
        + parts["hours"] * 3600
        + parts["minutes"] * 60
        + parts["seconds"]
    )


def main() -> int:
    args = parse_args()
    channel_id = load_channel_id(args)
    exclude_shorts = args.exclude_shorts and not args.include_shorts

    conn = sqlite3.connect(args.db)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout=30000")
    try:
        where = ["v.owner_channel_id = ?"]
        params: list[object] = [channel_id]
        if args.published_after:
            where.append("datetime(v.published_at) >= datetime(?)")
            params.append(args.published_after)
        rows = conn.execute(
            f"""
            SELECT
              v.video_id,
              v.title,
              v.published_at,
              v.duration,
              q.id AS queue_id,
              q.status AS queue_status,
              q.bundle_id
            FROM videos v
            LEFT JOIN url_queue q ON q.video_id = v.video_id
            WHERE {' AND '.join(where)}
            ORDER BY datetime(v.published_at)
            """,
            params,
        ).fetchall()
        videos = []
        skipped_shorts = 0
        for row in rows:
            seconds = duration_seconds(row["duration"])
            if exclude_shorts and seconds is not None and seconds < args.short_threshold_seconds:
                skipped_shorts += 1
                continue
            videos.append(row)

        print(f"channel_id: {channel_id}")
        print(f"videos_selected: {len(videos):,}")
        print(f"shorts_skipped: {skipped_shorts:,}")
        print(f"apply: {args.apply}")
        status_counts: dict[str, int] = {}
        for row in videos:
            status = row["queue_status"] or "missing_queue_row"
            status_counts[status] = status_counts.get(status, 0) + 1
        for status, count in sorted(status_counts.items()):
            print(f"- {status}: {count:,}")

        if not args.apply:
            print("dry_run: no DB changes")
            return 0

        inserted = 0
        updated = 0
        for row in videos:
            url = f"https://www.youtube.com/watch?v={row['video_id']}"
            if row["queue_id"] is None:
                conn.execute(
                    """
                    INSERT INTO url_queue (url, video_id, status, last_error, updated_at)
                    VALUES (?, ?, 'queued', NULL, CURRENT_TIMESTAMP)
                    """,
                    (url, row["video_id"]),
                )
                inserted += 1
            else:
                conn.execute(
                    """
                    UPDATE url_queue
                    SET status = 'queued',
                        last_error = NULL,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (row["queue_id"],),
                )
                updated += 1
        conn.commit()
        print(f"inserted_queue_rows: {inserted:,}")
        print(f"updated_queue_rows: {updated:,}")
        print("status: queued for refresh crawl")
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
