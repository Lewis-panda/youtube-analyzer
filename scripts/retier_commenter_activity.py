#!/usr/bin/env python3
"""Re-tier commenter activity into coverage-based 4 tiers for completed runs.

Mirrors ``channel_analyzer.analysis.assign_commenter_tiers``: a commenter's tier
is set by catalog coverage = distinct videos commented on / total in-scope
videos (size-normalized, cross-channel comparable), with the one-time tier
(exactly one video) split out. This recomputes ``commenter_tiers.csv`` and
patches ``report.json['commenter_tiers']`` in place so the benchmark baseline and
dashboard rebuild pick up the new tiers WITHOUT re-running the full analyzer.

CPU-only, no Qwen. Reads only existing per-run artifacts (commenter_activity.csv,
video_metrics.csv, report.json).
"""
from __future__ import annotations

from argparse import ArgumentParser
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CORE_COVERAGE = 0.05
REGULAR_COVERAGE = 0.02
CORE_MIN_VIDEOS = 3
TIER_ORDER = ["core", "regular", "returning", "one_time"]


def discover_run_dirs() -> list[Path]:
    seen: dict[Path, Path] = {}
    for pattern in ("runs/*", "case_studies/*/*"):
        for path in ROOT.glob(pattern):
            tables = path / "tables"
            if (tables / "commenter_activity.csv").exists() and (path / "report.json").exists():
                seen.setdefault(path.resolve(), path)
    return sorted(seen.values(), key=lambda p: p.name)


def retier(run_dir: Path) -> dict:
    tables = run_dir / "tables"
    activity = pd.read_csv(tables / "commenter_activity.csv")
    n_videos_total = int(len(pd.read_csv(tables / "video_metrics.csv")))
    coverage = activity["n_videos"] / n_videos_total if n_videos_total > 0 else activity["n_videos"] * 0.0
    activity["activity_tier"] = np.select(
        [
            activity["n_videos"] <= 1,
            (coverage >= CORE_COVERAGE) & (activity["n_videos"] >= CORE_MIN_VIDEOS),
            coverage >= REGULAR_COVERAGE,
        ],
        ["one_time", "core", "regular"],
        default="returning",
    )
    summary = (
        activity.groupby("activity_tier")
        .agg(
            n_commenters=("author_actor_id", "count"),
            avg_videos=("n_videos", "mean"),
            median_videos=("n_videos", "median"),
            total_comments=("n_comments", "sum"),
            total_likes_received=("comment_likes_received", "sum"),
        )
        .reset_index()
    )
    total = summary["n_commenters"].sum()
    summary["pct_commenters"] = summary["n_commenters"] / total * 100 if total else 0.0
    order = pd.Categorical(summary["activity_tier"], TIER_ORDER, ordered=True)
    summary = summary.assign(_order=order).sort_values("_order").drop(columns="_order").reset_index(drop=True)

    summary.to_csv(tables / "commenter_tiers.csv", index=False)
    records = json.loads(summary.to_json(orient="records"))
    report_path = run_dir / "report.json"
    doc = json.loads(report_path.read_text(encoding="utf-8"))
    doc["commenter_tiers"] = records
    report_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "run": run_dir.name,
        "n_videos": n_videos_total,
        "tiers": {r["activity_tier"]: round(r["pct_commenters"], 1) for r in records},
    }


def main() -> None:
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("run_dirs", nargs="*", help="Run dirs to re-tier (default: auto-discover).")
    args = parser.parse_args()
    run_dirs = [Path(p).resolve() for p in args.run_dirs] if args.run_dirs else discover_run_dirs()
    print(f"Re-tiering {len(run_dirs)} run(s) | core>={CORE_COVERAGE:.0%} regular>={REGULAR_COVERAGE:.0%} coverage")
    for run_dir in run_dirs:
        try:
            result = retier(run_dir)
            tiers = result["tiers"]
            print(
                f"  {result['run']:<32} N={result['n_videos']:>4}  "
                + " ".join(f"{k}={tiers.get(k, 0.0)}%" for k in TIER_ORDER)
            )
        except Exception as exc:  # noqa: BLE001
            print(f"  {run_dir.name:<32} ERROR: {exc}")


if __name__ == "__main__":
    main()
