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

from channel_analyzer.absa import run_absa_aggregation
from channel_analyzer.config import load_config, output_slug
from channel_analyzer.data import load_channel_data


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(description="Aggregate comment/external ABSA outputs.")
    parser.add_argument("--config", required=True, help="Path to analyzer config YAML.")
    parser.add_argument("--run-dir", help="Optional run directory. Default: runs/<slug>.")
    parser.add_argument("--comment-absa", help="Optional qwen_comment_absa.csv path.")
    parser.add_argument("--external-absa", help="Optional qwen_external_absa.csv path.")
    parser.add_argument("--output-dir", help="Optional output directory. Default: <run-dir>/absa.")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    config = load_config(Path(args.config))
    data = load_channel_data(config)
    slug = output_slug(config, data.channel.get("title"))
    run_dir = Path(args.run_dir).resolve() if args.run_dir else ROOT / "runs" / slug
    tables_dir = run_dir / "tables"
    comment_absa = Path(args.comment_absa).resolve() if args.comment_absa else tables_dir / "qwen_comment_absa.csv"
    external_absa = Path(args.external_absa).resolve() if args.external_absa else tables_dir / "qwen_external_absa.csv"
    output_dir = Path(args.output_dir).resolve() if args.output_dir else run_dir / "absa"
    artifacts = run_absa_aggregation(
        run_dir,
        comment_absa_path=comment_absa,
        external_absa_path=external_absa if external_absa.exists() else None,
        output_dir=output_dir,
    )
    print(f"ABSA summary: {artifacts.comment_aspect_summary_path}", flush=True)
    print(f"ABSA daily: {artifacts.comment_aspect_daily_path}", flush=True)
    if artifacts.platform_aspect_daily_path:
        print(f"Platform daily: {artifacts.platform_aspect_daily_path}", flush=True)
    if artifacts.platform_aspect_anomalies_path:
        print(f"Platform anomalies: {artifacts.platform_aspect_anomalies_path}", flush=True)


if __name__ == "__main__":
    main()
