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

from channel_analyzer.external_scraper import (
    DEFAULT_PTT_BOARDS,
    build_external_search_keywords,
    scrape_external_sources,
)


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(description="Scrape per-channel external PTT/Dcard posts for event analysis.")
    parser.add_argument("--config", help="Path to analyzer config YAML.")
    parser.add_argument(
        "--keywords",
        help="Comma-separated search keywords. If set, --config is only used for metadata and DB is not loaded.",
    )
    parser.add_argument("--channel-id", default="", help="Metadata channel_id for manifest when --keywords is used.")
    parser.add_argument("--channel-title", default="", help="Metadata channel title for manifest when --keywords is used.")
    parser.add_argument("--channel-handle", default="", help="Metadata channel handle for manifest when --keywords is used.")
    parser.add_argument("--run-slug", default="", help="Metadata run slug for manifest when --keywords is used.")
    parser.add_argument(
        "--output-dir",
        help="External source directory. Default: external_analysis.sources_dir or runs/<slug>/external_sources.",
    )
    parser.add_argument(
        "--sources",
        default="ptt",
        help=(
            "Comma-separated sources to scrape. Supported: ptt,dcard. "
            "Default is ptt; run Dcard only when a browser-capable workflow is intended."
        ),
    )
    parser.add_argument(
        "--ptt-boards",
        default=",".join(DEFAULT_PTT_BOARDS),
        help="Comma-separated PTT boards.",
    )
    parser.add_argument("--ptt-max-pages", type=int, default=30)
    parser.add_argument("--dcard-scroll-passes", type=int, default=8)
    parser.add_argument(
        "--dcard-headless",
        action="store_true",
        help="Run Camoufox headless. If blocked, retry with xvfb-run and non-headless mode.",
    )
    parser.add_argument(
        "--no-allow-partial",
        action="store_false",
        dest="allow_partial",
        help="Fail the whole scrape if one source fails.",
    )
    parser.add_argument("--dry-run", action="store_true")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if not args.config and not args.keywords:
        raise RuntimeError("Provide --config or --keywords.")

    config = None
    data = None
    slug = args.run_slug.strip() or "channel_run"
    if args.keywords:
        keywords = [keyword.strip() for keyword in args.keywords.split(",") if keyword.strip()]
        channel_title = args.channel_title.strip()
        channel_id = args.channel_id.strip()
        channel_handle = args.channel_handle.strip()
        if args.config:
            config_path = Path(args.config).resolve()
        else:
            config_path = None
    else:
        from channel_analyzer.config import load_config, output_slug
        from channel_analyzer.data import load_channel_data

        config = load_config(Path(args.config))
        data = load_channel_data(config)
        slug = output_slug(config, data.channel.get("title"))
        keywords = build_external_search_keywords(config, data)
        channel_title = str(data.channel.get("title") or "")
        channel_id = str(data.channel.get("channel_id") or "")
        channel_handle = str(config.channel_handle or "")
        config_path = Path(args.config).resolve()

    if args.output_dir:
        output_dir = Path(args.output_dir).expanduser().resolve()
    elif config is not None:
        output_dir = config.external_analysis.sources_dir or ROOT / "runs" / slug / "external_sources"
    else:
        output_dir = ROOT / "runs" / slug / "external_sources"
    sources = [source.strip().lower() for source in args.sources.split(",") if source.strip()]
    boards = [board.strip() for board in args.ptt_boards.split(",") if board.strip()]

    print(f"Channel: {channel_title or '(metadata only)'} ({channel_id})", flush=True)
    print(f"Output directory: {output_dir}", flush=True)
    print(f"Sources: {', '.join(sources)}", flush=True)
    print(f"Search keywords: {', '.join(keywords) if keywords else '(none)'}", flush=True)
    if not keywords:
        raise RuntimeError("No external search keywords could be derived. Set external_analysis.channel_aliases.")
    if args.dry_run:
        print("Dry run complete.", flush=True)
        return

    manifest = scrape_external_sources(
        output_dir,
        keywords,
        sources=sources,
        metadata={
            "channel_id": channel_id,
            "channel_title": channel_title,
            "channel_handle": channel_handle,
            "run_slug": slug,
            "config_path": str(config_path or ""),
        },
        ptt_boards=boards,
        ptt_max_pages=args.ptt_max_pages,
        dcard_scroll_passes=args.dcard_scroll_passes,
        dcard_headless=args.dcard_headless,
        allow_partial=args.allow_partial,
    )
    print(f"Manifest: {output_dir / 'external_source_manifest.json'}", flush=True)
    for source, info in manifest["sources"].items():
        print(f"{source}: {info}", flush=True)


if __name__ == "__main__":
    main()
