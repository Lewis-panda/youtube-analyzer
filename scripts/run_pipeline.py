#!/usr/bin/env python3
from __future__ import annotations

from argparse import ArgumentParser
from datetime import datetime
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
MPLCONFIGDIR = ROOT / ".matplotlib"
MPLCONFIGDIR.mkdir(parents=True, exist_ok=True)
os.environ["MPLCONFIGDIR"] = str(MPLCONFIGDIR)
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from channel_analyzer.config import load_config, output_slug
from channel_analyzer.data import load_channel_data
from channel_analyzer.run_checks import (
    build_completion_report,
    format_completion_report,
    write_run_summary,
)
from channel_analyzer.runtime_estimator import estimate_pipeline_runtime, render_estimates


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(description="Run the end-to-end channel analyzer pipeline.")
    parser.add_argument("--config", required=True, help="Path to analyzer config YAML.")
    parser.add_argument("--output", help="Optional output run directory.")
    parser.add_argument(
        "--qwen",
        choices=["existing", "video", "sentiment", "all", "none"],
        default="existing",
        help=(
            "Qwen stages to run before the final report. 'existing' and 'none' do not "
            "generate new Qwen outputs; existing CSVs are still used by the analyzer."
        ),
    )
    parser.add_argument(
        "--depth",
        choices=["base", "supplement", "all"],
        default="base",
        help=(
            "Report depth. 'base' is top-level-only community structure; "
            "'supplement' is reply-thread conflict analysis; 'all' runs both."
        ),
    )
    parser.add_argument("--video-batch-size", type=int, default=32)
    parser.add_argument("--comment-batch-size", type=int, default=64)
    parser.add_argument("--gpu-memory-utilization", type=float, default=0.88)
    parser.add_argument("--video-model-len", type=int, default=2048)
    parser.add_argument("--comment-model-len", type=int, default=1024)
    parser.add_argument("--attention-backend", default="TRITON_ATTN")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate config and show planned run directory without running stages.",
    )
    parser.add_argument(
        "--estimate-only",
        action="store_true",
        help="Show the runtime estimate and exit without running stages.",
    )
    parser.add_argument(
        "--include-crawl-estimate",
        action="store_true",
        help="Also include broad crawler-stage estimates based on in-scope counts.",
    )
    parser.add_argument(
        "--external-events",
        choices=["auto", "on", "off"],
        default="auto",
        help=(
            "Run external PTT/Dcard event analysis after report generation. "
            "'auto' runs only when external_analysis.enabled=true in config."
        ),
    )
    parser.add_argument(
        "--external-semantics",
        choices=["existing", "qwen", "none"],
        default="existing",
        help=(
            "Semantic labeling for external posts. 'existing' uses an existing "
            "tables/qwen_external_post_labels.csv if present; 'qwen' generates/resumes it."
        ),
    )
    parser.add_argument(
        "--external-crawl",
        choices=["auto", "on", "off"],
        default="auto",
        help=(
            "Scrape per-channel external PTT/Dcard posts before external analysis. "
            "'auto' runs when external analysis is enabled and no source files exist."
        ),
    )
    parser.add_argument(
        "--external-crawl-sources",
        default="ptt",
        help=(
            "Comma-separated external sources for scraping. Supported: ptt,dcard. "
            "Default is ptt; run Dcard only with an explicit browser-capable workflow."
        ),
    )
    parser.add_argument("--external-ptt-max-pages", type=int, default=30)
    parser.add_argument("--external-dcard-scroll-passes", type=int, default=8)
    parser.add_argument(
        "--external-dcard-headless",
        action="store_true",
        help="Run Dcard Camoufox scraping headless.",
    )
    parser.add_argument("--external-batch-size", type=int, default=16)
    parser.add_argument("--external-model-len", type=int, default=2048)
    return parser


def main() -> None:
    started_at = datetime.now().astimezone()
    started_perf = time.perf_counter()
    stage_records: list[dict] = []
    args = build_parser().parse_args()
    config_path = Path(args.config).resolve()
    config = load_config(config_path)
    data = load_channel_data(config)
    supplement_data = (
        load_channel_data(config, include_replies=True)
        if args.depth in {"supplement", "all"}
        else None
    )
    sentiment_scope = supplement_data if supplement_data is not None else data
    slug = output_slug(config, data.channel.get("title"))
    run_dir = Path(args.output).resolve() if args.output else ROOT / "runs" / slug
    tables_dir = run_dir / "tables"
    tables_dir.mkdir(parents=True, exist_ok=True)

    print(f"Channel: {data.channel.get('title')} ({data.channel.get('channel_id')})", flush=True)
    print(f"Videos in scope: {len(data.videos):,}", flush=True)
    print(f"Comments in scope: {len(data.comments):,}", flush=True)
    print(f"Unique commenters: {data.comments['author_actor_id'].nunique():,}", flush=True)
    if supplement_data is not None:
        n_top = int(supplement_data.comments["is_top_level"].astype(bool).sum())
        n_replies = len(supplement_data.comments) - n_top
        print(
            f"Supplement comments in scope: {len(supplement_data.comments):,} "
            f"({n_top:,} top-level, {n_replies:,} replies)",
            flush=True,
        )
    print(f"Run directory: {run_dir}", flush=True)
    print(
        render_estimates(
            estimate_pipeline_runtime(
                n_videos=len(data.videos),
                n_comments=len(sentiment_scope.comments),
                run_dir=run_dir,
                qwen_mode=args.qwen,
                include_crawl=args.include_crawl_estimate,
            )
        ),
        flush=True,
    )
    completion = build_completion_report(data, run_dir, supplement_data=supplement_data)
    print(format_completion_report(completion), flush=True)
    if args.estimate_only:
        print("Estimate only complete.", flush=True)
        return
    if args.dry_run:
        print("Dry run complete.", flush=True)
        return

    if args.qwen in {"video", "all"}:
        if completion["qwen_video_themes"]["complete"]:
            print("Qwen video themes already complete; skipping model stage.", flush=True)
            stage_records.append(_skipped_stage("Qwen video themes"))
        else:
            stage_records.extend(run_qwen_video(args, config_path, tables_dir))
        completion = build_completion_report(data, run_dir, supplement_data=supplement_data)
    if args.qwen in {"sentiment", "all"}:
        sentiment_completion = build_completion_report(sentiment_scope, run_dir)
        if sentiment_completion["qwen_comment_sentiment"]["complete"]:
            print("Qwen comment sentiment already complete; skipping model stage.", flush=True)
            stage_records.append(_skipped_stage("Qwen comment sentiment"))
        else:
            stage_records.extend(
                run_qwen_sentiment(
                    args,
                    config_path,
                    tables_dir,
                    include_replies=supplement_data is not None,
                )
            )
        completion = build_completion_report(data, run_dir, supplement_data=supplement_data)

    run_external = should_run_external(args.external_events, config)
    external_sources_dir = effective_external_sources_dir(config, run_dir)
    if run_external and should_run_external_crawl(
        args.external_crawl,
        external_sources_dir,
        _source_list(args.external_crawl_sources),
    ):
        stage_records.append(run_external_crawl(args, config_path, external_sources_dir))
    if run_external and args.external_semantics == "qwen":
        stage_records.extend(run_qwen_external(args, config_path, tables_dir, external_sources_dir))

    if args.depth in {"base", "all"}:
        analyzer_cmd = [
            sys.executable,
            "scripts/run_analyzer.py",
            "--config",
            str(config_path),
        ]
        if supplement_data is not None:
            analyzer_cmd.append("--sentiment-include-replies")
        if args.output:
            analyzer_cmd.extend(["--output", str(run_dir)])
        stage_records.append(run_command("base analyzer", analyzer_cmd))
    if args.depth in {"supplement", "all"}:
        supplement_cmd = [
            sys.executable,
            "scripts/run_supplement.py",
            "--config",
            str(config_path),
        ]
        if args.output:
            supplement_cmd.extend(["--output", str(run_dir)])
        stage_records.append(run_command("commenter deeper supplement", supplement_cmd))
    if run_external:
        stage_records.append(run_external_events(args, config_path, run_dir, external_sources_dir))
    finished_at = datetime.now().astimezone()
    total_seconds = time.perf_counter() - started_perf
    completion = build_completion_report(data, run_dir, supplement_data=supplement_data)
    print(f"Pipeline complete. Report: {run_dir / 'report.md'}", flush=True)
    print(f"English report: {run_dir / 'report_en.md'}", flush=True)
    print(f"Chinese report: {run_dir / 'report_zh.md'}", flush=True)
    print(format_completion_report(completion), flush=True)
    summary_path = run_dir / "run_summary.json"
    write_run_summary(
        summary_path,
        started_at=started_at,
        finished_at=finished_at,
        total_seconds=total_seconds,
        qwen_mode=args.qwen,
        stage_records=stage_records,
        completion_report=completion,
    )
    print(f"Run summary: {summary_path}", flush=True)


def run_qwen_video(args, config_path: Path, tables_dir: Path) -> list[dict]:
    output = tables_dir / "qwen_video_themes.csv"
    base = [
        sys.executable,
        "scripts/run_qwen_video_themes.py",
        "--config",
        str(config_path),
        "--output",
        str(output),
    ]
    return [
        run_command(
            "Qwen video themes",
            base
            + [
                "--batch-size",
                str(args.video_batch_size),
                "--max-model-len",
                str(args.video_model_len),
                "--attention-backend",
                args.attention_backend,
                "--gpu-memory-utilization",
                str(args.gpu_memory_utilization),
            ],
        ),
        run_command("repair Qwen video themes", base + ["--repair-existing"]),
        run_command(
            "retry Qwen video parse errors",
            base
            + [
                "--retry-parse-errors",
                "--batch-size",
                "1",
                "--max-model-len",
                str(args.video_model_len),
                "--attention-backend",
                args.attention_backend,
                "--gpu-memory-utilization",
                str(args.gpu_memory_utilization),
            ],
        ),
    ]


def run_qwen_sentiment(
    args,
    config_path: Path,
    tables_dir: Path,
    *,
    include_replies: bool,
) -> list[dict]:
    output = tables_dir / "qwen_comment_sentiment.csv"
    base = [
        sys.executable,
        "scripts/run_qwen_comment_sentiment.py",
        "--config",
        str(config_path),
        "--output",
        str(output),
    ]
    if include_replies:
        base.append("--include-replies")
    return [
        run_command(
            "Qwen comment sentiment",
            base
            + [
                "--batch-size",
                str(args.comment_batch_size),
                "--max-model-len",
                str(args.comment_model_len),
                "--attention-backend",
                args.attention_backend,
                "--gpu-memory-utilization",
                str(args.gpu_memory_utilization),
            ],
        ),
        run_command("repair Qwen comment sentiment", base + ["--repair-existing"]),
        run_command(
            "retry Qwen sentiment parse errors",
            base
            + [
                "--retry-parse-errors",
                "--batch-size",
                "16",
                "--max-model-len",
                str(args.comment_model_len),
                "--attention-backend",
                args.attention_backend,
                "--gpu-memory-utilization",
                str(args.gpu_memory_utilization),
            ],
        ),
    ]


def should_run_external(mode: str, config) -> bool:
    if mode == "off":
        return False
    if mode == "on":
        return True
    return bool(config.external_analysis.enabled)


def effective_external_sources_dir(config, run_dir: Path) -> Path:
    return config.external_analysis.sources_dir or run_dir / "external_sources"


def has_external_source_files(source_dir: Path, sources: list[str]) -> bool:
    candidates = []
    if "ptt" in sources:
        candidates.extend(
            [
                source_dir / "ptt" / "ptt_full.json",
                source_dir / "ptt_full.json",
            ]
        )
    if "dcard" in sources:
        candidates.extend(
            [
                source_dir / "dcard" / "dcard_full.json",
                source_dir / "dcard_full.json",
            ]
        )
    return any(path.exists() and path.stat().st_size > 2 for path in candidates)


def should_run_external_crawl(mode: str, source_dir: Path, sources: list[str]) -> bool:
    if mode == "off":
        return False
    if mode == "on":
        return True
    return not has_external_source_files(source_dir, sources)


def _source_list(value: str) -> list[str]:
    return [item.strip().lower() for item in value.split(",") if item.strip()]


def run_external_crawl(args, config_path: Path, sources_dir: Path) -> dict:
    command = [
        sys.executable,
        "scripts/scrape_external_posts.py",
        "--config",
        str(config_path),
        "--output-dir",
        str(sources_dir),
        "--sources",
        args.external_crawl_sources,
        "--ptt-max-pages",
        str(args.external_ptt_max_pages),
        "--dcard-scroll-passes",
        str(args.external_dcard_scroll_passes),
    ]
    if args.external_dcard_headless:
        command.append("--dcard-headless")
    return run_command("external post scrape", command)


def run_qwen_external(args, config_path: Path, tables_dir: Path, sources_dir: Path) -> list[dict]:
    output = tables_dir / "qwen_external_post_labels.csv"
    base = [
        sys.executable,
        "scripts/run_qwen_external_posts.py",
        "--config",
        str(config_path),
        "--output",
        str(output),
        "--sources-dir",
        str(sources_dir),
    ]
    return [
        run_command(
            "Qwen external post semantics",
            base
            + [
                "--batch-size",
                str(args.external_batch_size),
                "--max-model-len",
                str(args.external_model_len),
                "--attention-backend",
                args.attention_backend,
                "--gpu-memory-utilization",
                str(args.gpu_memory_utilization),
            ],
        ),
        run_command("repair Qwen external post semantics", base + ["--repair-existing"]),
        run_command(
            "retry Qwen external semantic parse errors",
            base
            + [
                "--retry-parse-errors",
                "--batch-size",
                "4",
                "--max-model-len",
                str(args.external_model_len),
                "--attention-backend",
                args.attention_backend,
                "--gpu-memory-utilization",
                str(args.gpu_memory_utilization),
            ],
        ),
    ]


def run_external_events(args, config_path: Path, run_dir: Path, sources_dir: Path) -> dict:
    command = [
        sys.executable,
        "scripts/run_external_events.py",
        "--config",
        str(config_path),
        "--output",
        str(run_dir),
        "--sources-dir",
        str(sources_dir),
    ]
    if args.external_events == "on":
        command.append("--force")
    return run_command("external event analysis", command)


def run_command(label: str, command: list[str]) -> dict:
    print("", flush=True)
    print(f"== {label} ==", flush=True)
    print("$ " + " ".join(command), flush=True)
    started_at = datetime.now().astimezone()
    start = time.perf_counter()
    subprocess.run(command, cwd=ROOT, check=True)
    elapsed = time.perf_counter() - start
    print(f"{label} complete in {elapsed:.1f}s", flush=True)
    return {
        "stage": label,
        "status": "completed",
        "started_at": started_at.isoformat(timespec="seconds"),
        "finished_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "elapsed_seconds": round(elapsed, 3),
    }


def _skipped_stage(label: str) -> dict:
    now = datetime.now().astimezone().isoformat(timespec="seconds")
    return {
        "stage": label,
        "status": "skipped_complete",
        "started_at": now,
        "finished_at": now,
        "elapsed_seconds": 0.0,
    }


if __name__ == "__main__":
    main()
