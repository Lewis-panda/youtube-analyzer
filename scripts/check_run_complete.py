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
from channel_analyzer.run_checks import build_completion_report, format_completion_report


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(description="Check whether a channel analyzer run is complete.")
    parser.add_argument("--config", required=True, help="Path to analyzer config YAML.")
    parser.add_argument("--output", help="Optional output run directory.")
    parser.add_argument(
        "--qwen",
        choices=["none", "video", "sentiment", "all"],
        default="all",
        help="Which Qwen outputs should be required for a complete run.",
    )
    parser.add_argument(
        "--depth",
        choices=["base", "supplement", "all"],
        default="base",
        help="Which report depth should be required.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    config = load_config(Path(args.config))
    data = load_channel_data(config)
    supplement_data = (
        load_channel_data(config, include_replies=True)
        if args.depth in {"supplement", "all"}
        else None
    )
    slug = output_slug(config, data.channel.get("title"))
    run_dir = Path(args.output).resolve() if args.output else ROOT / "runs" / slug
    report = build_completion_report(data, run_dir, supplement_data=supplement_data)
    print(format_completion_report(report))

    failed = []
    if not report["db_data_present"]:
        failed.append("db_data")
    if args.depth in {"base", "all"} and not report["reports"]["complete"]:
        failed.append("reports")
    if args.qwen in {"video", "all"} and not report["qwen_video_themes"]["complete"]:
        failed.append("qwen_video_themes")
    if args.qwen in {"sentiment", "all"} and not report["qwen_comment_sentiment"]["complete"]:
        failed.append("qwen_comment_sentiment")
    if args.depth in {"supplement", "all"}:
        if not report["supplement_reports"]["complete"]:
            failed.append("supplement_reports")
        if args.qwen in {"sentiment", "all"} and not report["qwen_comment_sentiment_all"]["complete"]:
            failed.append("qwen_comment_sentiment_all")

    if failed:
        raise SystemExit("Incomplete: " + ", ".join(failed))
    print("Run is complete.")


if __name__ == "__main__":
    main()
