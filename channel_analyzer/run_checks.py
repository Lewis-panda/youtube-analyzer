from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
from typing import Any

import pandas as pd

from .data import ChannelData


SUPPLEMENT_SECTION_MARKER = "<!-- BEGIN COMMENTER_DEEPER_ANALYSIS -->"


def build_completion_report(
    data: ChannelData,
    run_dir: Path,
    *,
    supplement_data: ChannelData | None = None,
) -> dict[str, Any]:
    tables_dir = run_dir / "tables"
    reports = {
        name: (run_dir / name).exists()
        for name in ["report.md", "report_en.md", "report_zh.md", "report.json"]
    }
    n_videos = len(data.videos)
    n_comments = len(data.comments)
    report = {
        "channel": {
            "channel_id": data.channel.get("channel_id"),
            "title": data.channel.get("title"),
        },
        "scope": {
            "videos": n_videos,
            "comments": n_comments,
            "unique_commenters": int(data.comments["author_actor_id"].nunique()),
        },
        "db_data_present": n_videos > 0 and n_comments > 0,
        "qwen_video_themes": _csv_completion(
            tables_dir / "qwen_video_themes.csv",
            id_col="video_id",
            parse_error_col="theme_parse_error",
            expected=n_videos,
        ),
        "qwen_comment_sentiment": _csv_completion(
            tables_dir / "qwen_comment_sentiment.csv",
            id_col="comment_id",
            parse_error_col="sentiment_parse_error",
            expected=n_comments,
        ),
        "reports": {
            "files": reports,
            "complete": all(reports.values()),
        },
    }
    if supplement_data is not None:
        supplement_reports = {
            "report_en.md section": _file_contains(run_dir / "report_en.md", SUPPLEMENT_SECTION_MARKER),
            "report_zh.md section": _file_contains(run_dir / "report_zh.md", SUPPLEMENT_SECTION_MARKER),
            "report_supplement.json": (run_dir / "report_supplement.json").exists(),
        }
        report["supplement_scope"] = {
            "comments": len(supplement_data.comments),
            "top_level_comments": int(
                supplement_data.comments["is_top_level"].astype(bool).sum()
            ),
            "replies": int(
                (~supplement_data.comments["is_top_level"].astype(bool)).sum()
            ),
            "unique_commenters": int(
                supplement_data.comments["author_actor_id"].nunique()
            ),
        }
        report["qwen_comment_sentiment_all"] = _csv_completion(
            tables_dir / "qwen_comment_sentiment.csv",
            id_col="comment_id",
            parse_error_col="sentiment_parse_error",
            expected=len(supplement_data.comments),
        )
        report["supplement_reports"] = {
            "files": supplement_reports,
            "complete": all(supplement_reports.values()),
        }
    return report


def format_completion_report(report: dict[str, Any]) -> str:
    scope = report["scope"]
    lines = [
        "Completion check:",
        (
            "- DB data: "
            f"{'present' if report['db_data_present'] else 'missing'} "
            f"({scope['videos']:,} videos, {scope['comments']:,} comments, "
            f"{scope['unique_commenters']:,} commenters)"
        ),
        "- Qwen video themes: " + _format_csv_completion(report["qwen_video_themes"]),
        "- Qwen comment sentiment: " + _format_csv_completion(report["qwen_comment_sentiment"]),
        "- Reports: " + _format_reports(report["reports"]),
    ]
    if "supplement_scope" in report:
        scope = report["supplement_scope"]
        lines.extend(
            [
                (
                    "- Supplement DB data: "
                    f"{scope['comments']:,} comments "
                    f"({scope['top_level_comments']:,} top-level, "
                    f"{scope['replies']:,} replies, "
                    f"{scope['unique_commenters']:,} commenters)"
                ),
                "- Qwen comment sentiment all: "
                + _format_csv_completion(report["qwen_comment_sentiment_all"]),
                "- Supplement section: " + _format_reports(report["supplement_reports"]),
            ]
        )
    return "\n".join(lines)


def write_run_summary(
    path: Path,
    *,
    started_at: datetime,
    finished_at: datetime,
    total_seconds: float,
    qwen_mode: str,
    stage_records: list[dict[str, Any]],
    completion_report: dict[str, Any],
) -> None:
    payload = {
        "started_at": started_at.isoformat(timespec="seconds"),
        "finished_at": finished_at.isoformat(timespec="seconds"),
        "total_seconds": round(total_seconds, 3),
        "qwen_mode": qwen_mode,
        "stages": stage_records,
        "completion": completion_report,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    history_path = path.with_name("run_history.jsonl")
    with history_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, default=str) + "\n")


def _csv_completion(
    path: Path,
    *,
    id_col: str,
    parse_error_col: str,
    expected: int,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "path": str(path),
        "exists": path.exists(),
        "expected": expected,
        "rows": 0,
        "unique_completed": 0,
        "remaining": expected,
        "parse_errors": None,
        "complete": False,
    }
    if not path.exists() or path.stat().st_size <= 0:
        return result

    try:
        frame = pd.read_csv(path, low_memory=False)
    except Exception as exc:
        result["read_error"] = str(exc)
        return result

    result["rows"] = int(len(frame))
    if id_col in frame.columns:
        result["unique_completed"] = int(frame[id_col].nunique())
    if parse_error_col in frame.columns:
        result["parse_errors"] = int(frame[parse_error_col].fillna(False).sum())
    remaining = max(expected - int(result["unique_completed"]), 0)
    result["remaining"] = remaining
    result["complete"] = (
        bool(result["exists"])
        and int(result["unique_completed"]) >= expected
        and (result["parse_errors"] in {0, None})
    )
    return result


def _format_csv_completion(item: dict[str, Any]) -> str:
    state = "complete" if item["complete"] else "incomplete"
    parse_errors = "n/a" if item["parse_errors"] is None else f"{item['parse_errors']:,}"
    detail = (
        f"{state} ({item['unique_completed']:,}/{item['expected']:,}, "
        f"remaining {item['remaining']:,}, parse errors {parse_errors})"
    )
    if not item["exists"]:
        return detail + " [missing CSV]"
    if item.get("read_error"):
        return detail + f" [read error: {item['read_error']}]"
    return detail


def _format_reports(reports: dict[str, Any]) -> str:
    files = reports["files"]
    state = "complete" if reports["complete"] else "incomplete"
    file_parts = [f"{name}={'ok' if exists else 'missing'}" for name, exists in files.items()]
    return f"{state} ({', '.join(file_parts)})"


def _file_contains(path: Path, needle: str) -> bool:
    if not path.exists() or path.stat().st_size <= 0:
        return False
    try:
        return needle in path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return False
