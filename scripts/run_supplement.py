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

from channel_analyzer.config import load_config
from channel_analyzer.data import load_channel_data
from channel_analyzer.supplement import run_deeper_supplement


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(description="Generate reply-thread deeper supplement reports.")
    parser.add_argument("--config", required=True, help="Path to config YAML.")
    parser.add_argument("--output", help="Optional output run directory.")
    parser.add_argument("--dry-run", action="store_true", help="Validate config and DB match only.")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    config = load_config(Path(args.config))
    data = load_channel_data(config, include_replies=True)
    n_top = int(data.comments["is_top_level"].astype(bool).sum())
    n_replies = len(data.comments) - n_top
    print(f"Channel: {data.channel.get('title')} ({data.channel.get('channel_id')})")
    print(f"Videos in scope: {len(data.videos):,}")
    print(f"All comments in scope: {len(data.comments):,}")
    print(f"Top-level comments: {n_top:,}")
    print(f"Replies: {n_replies:,}")
    print(f"Unique commenters: {data.comments['author_actor_id'].nunique():,}")
    if args.dry_run:
        print("Dry run complete.")
        return

    artifacts = run_deeper_supplement(
        config,
        data,
        output_dir=Path(args.output).resolve() if args.output else None,
    )
    print(f"Updated English report: {artifacts.report_en_path}")
    print(f"Updated Chinese report: {artifacts.report_zh_path}")
    print(f"Supplement JSON data: {artifacts.report_json_path}")
    print(f"Tables: {artifacts.tables_dir}")


if __name__ == "__main__":
    main()
