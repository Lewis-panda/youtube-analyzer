from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd


# Calibrated from the Superpie full run on this machine:
# RTX 5060 Ti 16GB, Qwen3-8B bitsandbytes, vLLM, batch_size=64.
QWEN_SENTIMENT_COMMENTS_PER_MIN = (450, 650)
QWEN_VIDEO_THEMES_PER_MIN = (20, 40)

# Wider because crawler throughput depends on YouTube/network/API state.
CRAWL_METADATA_VIDEOS_PER_MIN = (20, 60)
CRAWL_COMMENTS_PER_MIN = (500, 1500)


@dataclass(frozen=True)
class RuntimeEstimate:
    stage: str
    units: int
    unit_name: str
    low_seconds: float
    high_seconds: float
    notes: str

    @property
    def mid_seconds(self) -> float:
        return (self.low_seconds + self.high_seconds) / 2


def estimate_pipeline_runtime(
    n_videos: int,
    n_comments: int,
    run_dir: Path | None = None,
    qwen_mode: str = "existing",
    include_crawl: bool = False,
) -> list[RuntimeEstimate]:
    done_videos, done_comments = completed_qwen_counts(run_dir) if run_dir else (0, 0)
    estimates: list[RuntimeEstimate] = []

    if include_crawl:
        estimates.extend(estimate_crawl_runtime(n_videos, n_comments))

    if qwen_mode in {"video", "all"}:
        remaining = max(n_videos - done_videos, 0)
        estimates.append(
            _throughput_estimate(
                "qwen_video_themes",
                remaining,
                "videos",
                QWEN_VIDEO_THEMES_PER_MIN,
                "Uses existing qwen_video_themes.csv rows as completed work.",
                cold_start_seconds=60 if remaining else 0,
            )
        )
    if qwen_mode in {"sentiment", "all"}:
        remaining = max(n_comments - done_comments, 0)
        estimates.append(
            _throughput_estimate(
                "qwen_comment_sentiment",
                remaining,
                "comments",
                QWEN_SENTIMENT_COMMENTS_PER_MIN,
                "Calibrated from Superpie: about 73k comments finished in roughly two hours.",
                cold_start_seconds=60 if remaining else 0,
            )
        )

    estimates.append(estimate_final_analyzer(n_videos, n_comments))
    return estimates


def estimate_crawl_runtime(n_videos: int, n_comments: int) -> list[RuntimeEstimate]:
    return [
        _throughput_estimate(
            "crawl_video_metadata",
            n_videos,
            "videos",
            CRAWL_METADATA_VIDEOS_PER_MIN,
            "Broad estimate; actual time depends on API/network throttling.",
            cold_start_seconds=30 if n_videos else 0,
        ),
        _throughput_estimate(
            "crawl_comments",
            n_comments,
            "comments",
            CRAWL_COMMENTS_PER_MIN,
            "Broad estimate; comment volume and YouTube/API throttling dominate.",
            cold_start_seconds=30 if n_comments else 0,
        ),
    ]


def estimate_final_analyzer(n_videos: int, n_comments: int) -> RuntimeEstimate:
    # CPU analysis is usually short, but graph projection can grow with the
    # active commenter/video incidence matrix. Keep this conservative.
    low = 15 + n_videos * 0.02 + n_comments * 0.0004
    high = 45 + n_videos * 0.08 + n_comments * 0.0012
    return RuntimeEstimate(
        stage="final_analyzer_report",
        units=n_comments,
        unit_name="comments",
        low_seconds=low,
        high_seconds=high,
        notes="Includes tables, graph/community analysis, report, and figures.",
    )


def completed_qwen_counts(run_dir: Path | None) -> tuple[int, int]:
    if run_dir is None:
        return 0, 0
    tables = run_dir / "tables"
    return (
        _unique_count(tables / "qwen_video_themes.csv", "video_id"),
        _unique_count(tables / "qwen_comment_sentiment.csv", "comment_id"),
    )


def render_estimates(estimates: list[RuntimeEstimate]) -> str:
    lines = ["Runtime estimate:"]
    total_low = sum(item.low_seconds for item in estimates)
    total_high = sum(item.high_seconds for item in estimates)
    for item in estimates:
        lines.append(
            "- "
            f"{item.stage}: {item.units:,} {item.unit_name}, "
            f"{format_duration_range(item.low_seconds, item.high_seconds)}. "
            f"{item.notes}"
        )
    lines.append(f"Total: {format_duration_range(total_low, total_high)}")
    return "\n".join(lines)


def format_duration_range(low_seconds: float, high_seconds: float) -> str:
    if high_seconds <= 0:
        return "0m"
    if abs(high_seconds - low_seconds) < 1:
        return _format_duration(high_seconds)
    return f"{_format_duration(low_seconds)} to {_format_duration(high_seconds)}"


def _throughput_estimate(
    stage: str,
    units: int,
    unit_name: str,
    per_min_range: tuple[int, int],
    notes: str,
    cold_start_seconds: float = 0,
) -> RuntimeEstimate:
    low_rate, high_rate = per_min_range
    if units <= 0:
        return RuntimeEstimate(stage, 0, unit_name, 0, 0, notes)
    low_seconds = units / high_rate * 60 + cold_start_seconds
    high_seconds = units / low_rate * 60 + cold_start_seconds
    return RuntimeEstimate(stage, units, unit_name, low_seconds, high_seconds, notes)


def _format_duration(seconds: float) -> str:
    seconds = max(float(seconds), 0.0)
    if seconds < 60:
        return f"{seconds:.0f}s"
    minutes = seconds / 60
    if minutes < 90:
        return f"{minutes:.0f}m"
    hours = int(minutes // 60)
    mins = int(round(minutes % 60))
    if mins == 60:
        hours += 1
        mins = 0
    return f"{hours}h {mins:02d}m"


def _unique_count(path: Path, column: str) -> int:
    if not path.exists() or path.stat().st_size <= 0:
        return 0
    try:
        return int(pd.read_csv(path, usecols=[column], low_memory=False)[column].nunique())
    except Exception:
        return 0
