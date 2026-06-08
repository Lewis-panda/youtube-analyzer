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

from channel_analyzer.absa import (
    DEFAULT_MODEL,
    build_external_units,
    classify_units_with_vllm_to_csv,
    merge_existing_output,
    repair_existing_output,
    select_remaining,
)
from channel_analyzer.config import load_config, output_slug
from channel_analyzer.data import load_channel_data
from channel_analyzer.external_events import load_external_posts


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(description="Classify external PTT/Dcard posts with Qwen ABSA.")
    parser.add_argument("--config", required=True, help="Path to analyzer config YAML.")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--limit", type=int, default=None, help="Classify only N remaining posts.")
    parser.add_argument("--max-model-len", type=int, default=2048)
    parser.add_argument("--attention-backend", default="TRITON_ATTN")
    parser.add_argument("--gpu-memory-utilization", type=float, default=0.86)
    parser.add_argument("--sources-dir", help="Override external_analysis.sources_dir.")
    parser.add_argument(
        "--output",
        help="Optional output CSV path. Default: runs/<slug>/tables/qwen_external_absa.csv",
    )
    parser.add_argument("--repair-existing", action="store_true")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    config = load_config(Path(args.config))
    if args.sources_dir:
        config = replace(
            config,
            external_analysis=replace(config.external_analysis, sources_dir=Path(args.sources_dir).resolve()),
        )
    data = load_channel_data(config)
    slug = output_slug(config, data.channel.get("title"))
    output_path = (
        Path(args.output).resolve()
        if args.output
        else ROOT / "runs" / slug / "tables" / "qwen_external_absa.csv"
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if args.repair_existing:
        if not output_path.exists():
            raise FileNotFoundError(output_path)
        repaired = repair_existing_output(output_path)
        print(f"Repaired: {output_path}", flush=True)
        print(f"Rows: {len(repaired):,}", flush=True)
        print(f"Parse errors: {int(repaired.get('absa_parse_error', False).sum()):,}", flush=True)
        return

    posts = load_external_posts(config.external_analysis)
    units = build_external_units(posts)
    done_count = 0
    if output_path.exists() and output_path.stat().st_size > 0:
        import pandas as pd

        done_count = pd.read_csv(output_path, usecols=["unit_id"], low_memory=False)["unit_id"].nunique()
    remaining = select_remaining(units, output_path, args.limit)

    print(f"Channel: {data.channel.get('title')} ({data.channel.get('channel_id')})", flush=True)
    print(f"External posts in scope: {len(units):,}", flush=True)
    print(f"Already classified: {done_count:,}", flush=True)
    print(f"Classifying now: {len(remaining):,}", flush=True)
    if remaining.empty:
        print("Already complete; no model will be loaded.", flush=True)
        print(f"Output: {output_path}", flush=True)
        return

    new_rows = classify_units_with_vllm_to_csv(
        remaining,
        output_path=output_path,
        model_id=args.model,
        batch_size=args.batch_size,
        max_model_len=args.max_model_len,
        attention_backend=args.attention_backend,
        gpu_memory_utilization=args.gpu_memory_utilization,
    )
    merged = merge_existing_output(output_path, new_rows)
    merged.to_csv(output_path, index=False)
    print(f"Saved: {output_path}", flush=True)
    print(f"Rows: {len(merged):,}", flush=True)
    print(f"Parse errors: {int(merged.get('absa_parse_error', False).sum()):,}", flush=True)


if __name__ == "__main__":
    main()
