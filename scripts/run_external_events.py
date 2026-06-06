#!/usr/bin/env python3
from __future__ import annotations

from argparse import ArgumentParser
from dataclasses import replace
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
from channel_analyzer.external_events import run_external_event_analysis


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(description="Analyze external PTT/Dcard events against YouTube comment response.")
    parser.add_argument("--config", required=True, help="Path to analyzer config YAML.")
    parser.add_argument("--output", help="Optional run directory. Default: runs/<slug>.")
    parser.add_argument(
        "--append-report",
        action="store_true",
        default=True,
        help="Append/update an External Event Analysis section in report_en.md/report_zh.md.",
    )
    parser.add_argument(
        "--no-append-report",
        action="store_false",
        dest="append_report",
        help="Write tables only.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Validate config and external source availability only.")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Run even if external_analysis.enabled is false in config.",
    )
    parser.add_argument(
        "--sources-dir",
        help="Override external_analysis.sources_dir. Used by the pipeline for per-run scraped external sources.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    config = load_config(Path(args.config))
    if args.sources_dir:
        config = replace(
            config,
            external_analysis=replace(
                config.external_analysis,
                sources_dir=Path(args.sources_dir).expanduser().resolve(),
            ),
        )
    if args.force and not config.external_analysis.enabled:
        config = replace(config, external_analysis=replace(config.external_analysis, enabled=True))
    data = load_channel_data(config)
    sentiment_data = load_channel_data(config, include_replies=True)
    slug = output_slug(config, data.channel.get("title"))
    run_dir = Path(args.output).resolve() if args.output else ROOT / "runs" / slug
    print(f"Channel: {data.channel.get('title')} ({data.channel.get('channel_id')})")
    print(f"External enabled: {config.external_analysis.enabled}")
    print(f"External source filter: {','.join(config.external_analysis.sources)}")
    print(f"External sources directory: {config.external_analysis.sources_dir}")
    print(f"Run directory: {run_dir}")
    if args.dry_run:
        print("Dry run complete.")
        return
    artifacts = run_external_event_analysis(
        config,
        data,
        sentiment_data,
        run_dir,
        append_report=args.append_report,
    )
    print(f"External event status: {artifacts.status}")
    print(f"External posts: {artifacts.n_posts:,}")
    print(f"Event clusters: {artifacts.n_event_clusters:,}")
    print(f"Output directory: {artifacts.output_dir}")
    print(f"Summary: {artifacts.summary_path}")


if __name__ == "__main__":
    main()
