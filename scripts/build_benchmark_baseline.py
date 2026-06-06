#!/usr/bin/env python3
from __future__ import annotations

from argparse import ArgumentParser
from pathlib import Path
import os
import sys

ROOT = Path(__file__).resolve().parents[1]
MPLCONFIGDIR = ROOT / "legacy" / "matplotlib" / ".matplotlib"
MPLCONFIGDIR.mkdir(parents=True, exist_ok=True)
os.environ["MPLCONFIGDIR"] = str(MPLCONFIGDIR)
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd

from channel_analyzer.benchmark import build_benchmark_baseline, build_target_comparison


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(description="Build cohort baseline distributions from completed channel reports.")
    parser.add_argument(
        "--cohort",
        default="docs/tw_under_1_5m_Update.csv",
        help="CSV with candidate_id, channel_name, url, and a status column.",
    )
    parser.add_argument(
        "--configs-glob",
        default="configs/*.full.yaml",
        help="Glob of analyzer configs to match against cohort URLs.",
    )
    parser.add_argument(
        "--runs-dir",
        default="baseline_runs",
        help="Directory containing completed per-channel run directories.",
    )
    parser.add_argument(
        "--output",
        default="baseline_runs/benchmark_baseline",
        help="Output directory for baseline CSVs.",
    )
    parser.add_argument(
        "--status-column",
        default="正確",
        help="Cohort CSV column used to filter verified rows.",
    )
    parser.add_argument(
        "--include-status",
        default="O",
        help="Status value to include from the cohort CSV.",
    )
    parser.add_argument(
        "--target-run-dir",
        action="append",
        default=[],
        help=(
            "Optional completed run directory to compare against the baseline "
            "without including it in the cohort distribution. Can be repeated."
        ),
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    outputs = build_benchmark_baseline(
        Path(args.cohort),
        args.configs_glob,
        Path(args.runs_dir),
        Path(args.output),
        status_column=args.status_column,
        include_status=args.include_status,
    )
    print(f"Benchmark output: {outputs.output_dir}")
    print(f"Members: {outputs.members_path}")
    print(f"Channel metrics: {outputs.metrics_path}")
    print(f"Distributions: {outputs.distributions_path}")
    print(f"Percentiles: {outputs.percentiles_path}")
    print(f"README: {outputs.readme_path}")

    if args.target_run_dir:
        baseline_metrics = pd.read_csv(outputs.metrics_path)
        target_dirs = [Path(item) for item in args.target_run_dir]
        target_metrics, target_percentiles = build_target_comparison(
            target_dirs,
            baseline_metrics,
        )
        target_metrics_path = outputs.output_dir / "target_metrics.csv"
        target_percentiles_path = outputs.output_dir / "target_metric_percentiles.csv"
        target_metrics.to_csv(target_metrics_path, index=False)
        target_percentiles.to_csv(target_percentiles_path, index=False)
        print(f"Target metrics: {target_metrics_path}")
        print(f"Target percentiles: {target_percentiles_path}")


if __name__ == "__main__":
    main()
