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
from channel_analyzer.external_events import (
    SEMANTIC_LABEL_FILENAME,
    build_aliases,
    load_external_posts,
)
from channel_analyzer.qwen_external import (
    DEFAULT_MODEL,
    broad_prefilter,
    classify_with_vllm_to_csv,
    merge_existing_output,
    repair_existing_output,
    select_remaining,
)


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(description="Classify external PTT/Dcard posts with Qwen semantic labels.")
    parser.add_argument("--config", required=True, help="Path to analyzer config YAML.")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--engine", choices=["vllm"], default="vllm")
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--max-model-len", type=int, default=2048)
    parser.add_argument("--attention-backend", default="TRITON_ATTN")
    parser.add_argument("--gpu-memory-utilization", type=float, default=0.88)
    parser.add_argument("--output", help="Optional CSV path. Default: runs/<slug>/tables/qwen_external_post_labels.csv")
    parser.add_argument(
        "--sources-dir",
        help="Override external_analysis.sources_dir. Used by the pipeline for per-run scraped external sources.",
    )
    parser.add_argument("--repair-existing", action="store_true")
    parser.add_argument("--retry-parse-errors", action="store_true")
    parser.add_argument(
        "--no-prefilter",
        action="store_true",
        help="Classify every parsed external post instead of alias-prefiltered posts.",
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
    data = load_channel_data(config)
    slug = output_slug(config, data.channel.get("title"))
    output_path = (
        Path(args.output).resolve()
        if args.output
        else ROOT / "runs" / slug / "tables" / SEMANTIC_LABEL_FILENAME
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if args.repair_existing:
        if not output_path.exists():
            raise FileNotFoundError(output_path)
        repaired = repair_existing_output(output_path)
        parse_errors = int(repaired.get("semantic_parse_error", False).sum()) if "semantic_parse_error" in repaired else 0
        print(f"Repaired: {output_path}")
        print(f"Rows: {len(repaired):,}")
        print(f"Parse errors: {parse_errors:,}")
        return

    posts = load_external_posts(config.external_analysis)
    aliases = build_aliases(config, data)
    if posts.empty:
        print("No external posts found; no model will be loaded.")
        print(f"Output: {output_path}")
        return
    candidates = posts if args.no_prefilter else broad_prefilter(posts, aliases)
    if args.retry_parse_errors and output_path.exists() and output_path.stat().st_size > 0:
        import pandas as pd

        existing = pd.read_csv(output_path, low_memory=False)
        if "semantic_parse_error" in existing.columns:
            before = len(existing)
            existing = existing[existing["semantic_parse_error"] != True].copy()
            existing.to_csv(output_path, index=False)
            print(f"Dropped parse-error rows: {before - len(existing):,}")
    done_count = 0
    if output_path.exists() and output_path.stat().st_size > 0:
        import pandas as pd

        done_count = pd.read_csv(output_path, usecols=["post_uid"], low_memory=False)["post_uid"].nunique()
    remaining = select_remaining(candidates, output_path, args.limit)
    print(f"Channel: {data.channel.get('title')} ({data.channel.get('channel_id')})")
    print(f"Parsed external posts: {len(posts):,}")
    print(f"Candidate posts after prefilter: {len(candidates):,}")
    print(f"Already classified: {done_count:,}")
    print(f"Classifying now: {len(remaining):,}")
    if remaining.empty:
        print("Already complete; no model will be loaded.")
        print(f"Output: {output_path}")
        return

    if args.engine != "vllm":
        raise RuntimeError(f"Unsupported engine: {args.engine}")
    new_rows = classify_with_vllm_to_csv(
        remaining,
        output_path=output_path,
        aliases=aliases,
        model_id=args.model,
        batch_size=args.batch_size,
        max_model_len=args.max_model_len,
        attention_backend=args.attention_backend,
        gpu_memory_utilization=args.gpu_memory_utilization,
    )
    merged = merge_existing_output(output_path, new_rows)
    merged.to_csv(output_path, index=False)
    parse_errors = int(merged.get("semantic_parse_error", False).sum()) if "semantic_parse_error" in merged else 0
    print(f"Saved: {output_path}")
    print(f"Rows: {len(merged):,}")
    print(f"Parse errors: {parse_errors:,}")


if __name__ == "__main__":
    main()
