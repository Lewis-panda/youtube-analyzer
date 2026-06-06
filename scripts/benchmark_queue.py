#!/usr/bin/env python3
"""Small queue maintenance helpers for benchmark crawls."""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT.parent / "SharedData" / "state" / "yt_graph.sqlite3"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    sub = parser.add_subparsers(dest="command", required=True)

    sp = sub.add_parser("status", help="Print queue status and failure counts.")
    sp.add_argument("--limit", type=int, default=8)
    sp.set_defaults(func=cmd_status)

    sp = sub.add_parser("reset-quota", help="Move quotaExceeded failures back to queued.")
    sp.set_defaults(func=cmd_reset_quota)

    sp = sub.add_parser(
        "reset-stale-resolving",
        help="Move old resolving rows without bundles back to queued.",
    )
    sp.add_argument("--older-than-minutes", type=int, default=30)
    sp.set_defaults(func=cmd_reset_stale_resolving)

    args = parser.parse_args()
    args.func(args)
    return 0


def connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def cmd_status(args: argparse.Namespace) -> None:
    conn = connect(args.db)
    try:
        print("Queue status:")
        for row in conn.execute(
            """
            SELECT status, COUNT(*) AS n, MIN(id) AS min_id, MAX(id) AS max_id
            FROM url_queue
            GROUP BY status
            ORDER BY status
            """
        ):
            print(
                f"- {row['status']}: {row['n']:,}"
                f" (id {row['min_id']}..{row['max_id']})"
            )

        quota_failed = conn.execute(
            """
            SELECT COUNT(*)
            FROM url_queue
            WHERE status = 'failed' AND last_error LIKE '%quotaExceeded%'
            """
        ).fetchone()[0]
        other_failed = conn.execute(
            """
            SELECT COUNT(*)
            FROM url_queue
            WHERE status = 'failed'
              AND COALESCE(last_error, '') NOT LIKE '%quotaExceeded%'
            """
        ).fetchone()[0]
        print(f"quota_failed: {quota_failed:,}")
        print(f"other_failed: {other_failed:,}")

        print("Next queued:")
        for row in conn.execute(
            """
            SELECT id, video_id, url
            FROM url_queue
            WHERE status = 'queued'
            ORDER BY id
            LIMIT ?
            """,
            (args.limit,),
        ):
            print(f"- id={row['id']} video_id={row['video_id']} url={row['url']}")

        print("Recent graphed channels:")
        for row in conn.execute(
            """
            SELECT ch.title, ch.custom_url, COUNT(*) AS n_videos, MAX(q.updated_at) AS last_update
            FROM url_queue q
            JOIN videos v ON v.video_id = q.video_id
            LEFT JOIN channels ch ON ch.channel_id = v.owner_channel_id
            WHERE q.status = 'graphed'
            GROUP BY v.owner_channel_id
            ORDER BY last_update DESC
            LIMIT ?
            """,
            (args.limit,),
        ):
            print(
                f"- {row['title']} ({row['custom_url']}): "
                f"{row['n_videos']:,} videos, last {row['last_update']}"
            )
    finally:
        conn.close()


def cmd_reset_quota(args: argparse.Namespace) -> None:
    conn = connect(args.db)
    try:
        cur = conn.execute(
            """
            UPDATE url_queue
            SET status = 'queued',
                last_error = NULL,
                updated_at = CURRENT_TIMESTAMP
            WHERE status = 'failed'
              AND last_error LIKE '%quotaExceeded%'
            """
        )
        conn.commit()
        print(f"reset_quota_failed_to_queued: {cur.rowcount:,}")
    finally:
        conn.close()


def cmd_reset_stale_resolving(args: argparse.Namespace) -> None:
    if args.older_than_minutes < 1:
        raise SystemExit("--older-than-minutes must be >= 1")
    modifier = f"-{args.older_than_minutes} minutes"
    conn = connect(args.db)
    try:
        cur = conn.execute(
            """
            UPDATE url_queue
            SET status = 'queued',
                updated_at = CURRENT_TIMESTAMP
            WHERE status = 'resolving'
              AND bundle_id IS NULL
              AND updated_at <= datetime('now', ?)
            """,
            (modifier,),
        )
        conn.commit()
        print(f"reset_stale_resolving_to_queued: {cur.rowcount:,}")
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
