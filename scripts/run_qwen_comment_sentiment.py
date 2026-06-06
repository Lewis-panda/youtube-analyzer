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
from channel_analyzer.qwen_comment import (
    DEFAULT_MODEL,
    classify_with_vllm_to_csv,
    merge_existing_output,
    repair_existing_output,
    select_remaining,
)


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(description="Classify channel comments with Qwen sentiment.")
    parser.add_argument("--config", required=True, help="Path to analyzer config YAML.")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--engine", choices=["vllm"], default="vllm")
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--limit", type=int, default=None, help="Classify only N remaining comments.")
    parser.add_argument("--max-model-len", type=int, default=1024)
    parser.add_argument("--attention-backend", default="TRITON_ATTN")
    parser.add_argument("--gpu-memory-utilization", type=float, default=0.88)
    parser.add_argument(
        "--include-replies",
        action="store_true",
        help="Classify all comments, including replies, instead of the config's base scope.",
    )
    parser.add_argument(
        "--output",
        help="Optional CSV path. Default: runs/<slug>/tables/qwen_comment_sentiment.csv",
    )
    parser.add_argument(
        "--repair-existing",
        action="store_true",
        help="Re-parse sentiment_raw in the existing output CSV and exit.",
    )
    parser.add_argument(
        "--retry-parse-errors",
        action="store_true",
        help="Drop existing parse-error rows before selecting remaining comments.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    config = load_config(Path(args.config))
    data = load_channel_data(
        config,
        include_replies=True if args.include_replies else None,
    )
    slug = output_slug(config, data.channel.get("title"))
    output_path = (
        Path(args.output).resolve()
        if args.output
        else ROOT / "runs" / slug / "tables" / "qwen_comment_sentiment.csv"
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if args.repair_existing:
        if not output_path.exists():
            raise FileNotFoundError(output_path)
        repaired = repair_existing_output(output_path)
        parse_errors = int(repaired.get("sentiment_parse_error", False).sum())
        print(f"Repaired: {output_path}", flush=True)
        print(f"Rows: {len(repaired):,}", flush=True)
        print(f"Parse errors: {parse_errors:,}", flush=True)
        return

    comments = data.comments.copy()
    video_titles = data.videos[["video_id", "title"]].rename(columns={"title": "video_title"})
    comments = comments.merge(video_titles, on="video_id", how="left")
    comments = comments.sort_values(["comment_published_at", "comment_id"]).reset_index(drop=True)

    if args.retry_parse_errors and output_path.exists() and output_path.stat().st_size > 0:
        import pandas as pd

        existing = pd.read_csv(output_path, low_memory=False)
        if "sentiment_parse_error" in existing.columns:
            before = len(existing)
            existing = existing[existing["sentiment_parse_error"] != True].copy()
            existing.to_csv(output_path, index=False)
            print(f"Dropped parse-error rows: {before - len(existing):,}", flush=True)

    done_count = 0
    if output_path.exists() and output_path.stat().st_size > 0:
        import pandas as pd

        done_count = pd.read_csv(
            output_path, usecols=["comment_id"], low_memory=False
        )["comment_id"].nunique()
    remaining = select_remaining(comments, output_path, args.limit)
    print(f"Channel: {data.channel.get('title')} ({data.channel.get('channel_id')})", flush=True)
    print(f"Comments in scope: {len(comments):,}", flush=True)
    print(f"Already classified: {done_count:,}", flush=True)
    print(f"Classifying now: {len(remaining):,}", flush=True)
    if remaining.empty:
        print("Already complete; no model will be loaded.", flush=True)
        print(f"No remaining comments. Output: {output_path}", flush=True)
        return

    if args.engine == "vllm":
        new_rows = classify_with_vllm_to_csv(
            remaining,
            output_path=output_path,
            model_id=args.model,
            batch_size=args.batch_size,
            max_model_len=args.max_model_len,
            attention_backend=args.attention_backend,
            gpu_memory_utilization=args.gpu_memory_utilization,
        )
    else:
        raise RuntimeError(f"Unsupported engine: {args.engine}")

    merged = merge_existing_output(output_path, new_rows)
    merged.to_csv(output_path, index=False)
    parse_errors = int(merged.get("sentiment_parse_error", False).sum())
    print(f"Saved: {output_path}", flush=True)
    print(f"Rows: {len(merged):,}", flush=True)
    print(f"Parse errors: {parse_errors:,}", flush=True)


if __name__ == "__main__":
    main()
