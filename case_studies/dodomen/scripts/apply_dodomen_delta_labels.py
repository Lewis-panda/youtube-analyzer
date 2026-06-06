#!/usr/bin/env python3
"""Apply user-confirmed DoDoMen Ian/Eric/Collab delta labels."""

from __future__ import annotations

import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT.parent / "SharedData" / "state" / "yt_graph.sqlite3"

UPDATES = [
    ("0dYYLxnQaJM", "collab"),
    ("mITaFHhulzg", "other"),
    ("Q4CCBr_Q8Dc", "collab"),
    ("RUzLq2n6MOQ", "collab"),
    ("VbwkmeHIkJs", "eric"),
]


def main() -> None:
    con = sqlite3.connect(DB_PATH)
    con.execute("PRAGMA busy_timeout=30000")
    con.executemany(
        """
        INSERT INTO video_labels (video_id, label, labeler, labeled_at, notes)
        VALUES (
            ?,
            ?,
            'human_delta_confirmed',
            datetime('now'),
            '2026-06 delta label confirmed by user in Codex chat.'
        )
        ON CONFLICT(video_id) DO UPDATE SET
          label = excluded.label,
          labeler = excluded.labeler,
          labeled_at = excluded.labeled_at,
          notes = excluded.notes
        """,
        UPDATES,
    )
    con.commit()
    rows = con.execute(
        """
        SELECT video_id, label, labeler, labeled_at, notes
        FROM video_labels
        WHERE video_id IN (?, ?, ?, ?, ?)
        ORDER BY video_id
        """,
        [video_id for video_id, _ in UPDATES],
    ).fetchall()
    for row in rows:
        print("\t".join(str(value) for value in row))
    con.close()


if __name__ == "__main__":
    main()

