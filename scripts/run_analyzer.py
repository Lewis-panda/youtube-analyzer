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

from channel_analyzer.analysis import run_analysis
from channel_analyzer.config import load_config
from channel_analyzer.data import load_channel_data


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(description="Generate a YouTube channel community report.")
    parser.add_argument("--config", required=True, help="Path to config YAML.")
    parser.add_argument("--output", help="Optional output run directory.")
    parser.add_argument(
        "--sentiment-include-replies",
        action="store_true",
        help=(
            "Use top-level comments for audience/network metrics but include replies "
            "in video/theme sentiment and risk tables."
        ),
    )
    parser.add_argument("--dry-run", action="store_true", help="Validate config and DB match only.")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    config = load_config(Path(args.config))
    data = load_channel_data(config)
    sentiment_data = (
        load_channel_data(config, include_replies=True)
        if args.sentiment_include_replies
        else None
    )
    print(f"Channel: {data.channel.get('title')} ({data.channel.get('channel_id')})")
    print(f"Videos in scope: {len(data.videos):,}")
    print(f"Comments in scope: {len(data.comments):,}")
    print(f"Unique commenters: {data.comments['author_actor_id'].nunique():,}")
    if sentiment_data is not None:
        n_top = int(sentiment_data.comments["is_top_level"].astype(bool).sum())
        n_replies = len(sentiment_data.comments) - n_top
        print(
            f"Sentiment comments in scope: {len(sentiment_data.comments):,} "
            f"({n_top:,} top-level, {n_replies:,} replies)"
        )
    if args.dry_run:
        print("Dry run complete.")
        return

    artifacts = run_analysis(
        config,
        data,
        sentiment_data=sentiment_data,
        output_dir=Path(args.output).resolve() if args.output else None,
    )
    print(f"Report: {artifacts.report_path}")
    print(f"English report: {artifacts.report_en_path}")
    print(f"Chinese report: {artifacts.report_zh_path}")
    print(f"Tables: {artifacts.tables_dir}")
    print(f"Figures: {artifacts.figures_dir}")


if __name__ == "__main__":
    main()
