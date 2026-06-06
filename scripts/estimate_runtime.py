#!/usr/bin/env python3
from __future__ import annotations

from argparse import ArgumentParser
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
MPLCONFIGDIR = ROOT / ".matplotlib"
MPLCONFIGDIR.mkdir(parents=True, exist_ok=True)
os.environ["MPLCONFIGDIR"] = str(MPLCONFIGDIR)
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from channel_analyzer.config import load_config, output_slug
from channel_analyzer.data import load_channel_data
from channel_analyzer.runtime_estimator import estimate_pipeline_runtime, render_estimates


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(description="Estimate channel analyzer runtime.")
    parser.add_argument("--config", help="Optional analyzer config YAML for DB-backed counts.")
    parser.add_argument("--output", help="Optional run directory for checking completed Qwen CSVs.")
    parser.add_argument("--videos", type=int, help="Manual video count when DB data is not ready.")
    parser.add_argument("--comments", type=int, help="Manual comment count when DB data is not ready.")
    parser.add_argument(
        "--qwen",
        choices=["existing", "video", "sentiment", "all", "none"],
        default="all",
        help="Pipeline mode to estimate.",
    )
    parser.add_argument(
        "--include-crawl",
        action="store_true",
        help="Include broad crawl metadata/comment-fetch estimates.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    run_dir = Path(args.output).resolve() if args.output else None
    if args.config:
        config_path = Path(args.config).resolve()
        config = load_config(config_path)
        data = load_channel_data(config)
        if run_dir is None:
            run_dir = ROOT / "runs" / output_slug(config, data.channel.get("title"))
        n_videos = len(data.videos)
        n_comments = len(data.comments)
        print(f"Channel: {data.channel.get('title')} ({data.channel.get('channel_id')})")
        print(f"Videos in scope: {n_videos:,}")
        print(f"Comments in scope: {n_comments:,}")
        print(f"Run directory: {run_dir}")
    else:
        if args.videos is None or args.comments is None:
            raise SystemExit("Use --config, or provide both --videos and --comments.")
        n_videos = args.videos
        n_comments = args.comments
        print(f"Manual counts: {n_videos:,} videos, {n_comments:,} comments")

    print(
        render_estimates(
            estimate_pipeline_runtime(
                n_videos=n_videos,
                n_comments=n_comments,
                run_dir=run_dir,
                qwen_mode=args.qwen,
                include_crawl=args.include_crawl,
            )
        )
    )


if __name__ == "__main__":
    main()
