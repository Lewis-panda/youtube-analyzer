#!/usr/bin/env python3
"""Resolve YouTube channel URLs for benchmark cohort candidates.

This is an operator helper for crawler seeding. It queries YouTube channel
search through yt-dlp, records the top result plus alternatives, and marks
confidence so ambiguous channels can be reviewed before crawling.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import quote_plus


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "docs" / "tw_under_1_5m_benchmark_candidates.csv"
DEFAULT_OUTPUT = ROOT / "docs" / "tw_under_1_5m_benchmark_channels_resolved.csv"
DEFAULT_RAW = ROOT / "docs" / "tw_under_1_5m_benchmark_channels_search_raw.jsonl"

CHANNEL_SEARCH_FILTER = "EgIQAg%253D%253D"

OUTPUT_FIELDS = [
    "candidate_id",
    "channel_name",
    "primary_category",
    "secondary_category",
    "rough_subscriber_band",
    "channel_type",
    "priority",
    "resolved_title",
    "handle",
    "channel_id",
    "channel_url",
    "uploader_url",
    "subscriber_count",
    "verified",
    "confidence",
    "match_notes",
    "search_query",
    "search_rank",
    "alternatives_json",
    "notes",
]

QUERY_OVERRIDES = {
    "TW016": "Hello Catie",
    "TW045": "超派人生 Superpie",
    "TW051": "錫蘭 Ceylan",
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--raw-output", type=Path, default=DEFAULT_RAW)
    parser.add_argument("--limit", type=int, default=3)
    parser.add_argument("--sleep", type=float, default=1.5)
    parser.add_argument("--timeout", type=int, default=90)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    rows = read_csv(args.input)
    completed = set()
    if args.output.exists() and not args.force:
        completed = {row["candidate_id"] for row in read_csv(args.output)}

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.raw_output.parent.mkdir(parents=True, exist_ok=True)

    write_header = args.force or not args.output.exists()
    mode = "w" if args.force or not args.output.exists() else "a"
    with args.output.open(mode, newline="", encoding="utf-8") as out_fh, args.raw_output.open(
        "w" if args.force else "a", encoding="utf-8"
    ) as raw_fh:
        writer = csv.DictWriter(out_fh, fieldnames=OUTPUT_FIELDS)
        if write_header:
            writer.writeheader()

        for row in rows:
            candidate_id = row["candidate_id"]
            if candidate_id in completed:
                print(f"skip {candidate_id} {row['channel_name']}", flush=True)
                continue

            query = QUERY_OVERRIDES.get(candidate_id, row["channel_name"])
            print(f"resolve {candidate_id} {row['channel_name']} query={query}", flush=True)
            try:
                payload = run_search(query, args.limit, args.timeout)
                entries = normalize_entries(payload.get("entries") or [])
                raw_fh.write(
                    json.dumps(
                        {
                            "candidate_id": candidate_id,
                            "channel_name": row["channel_name"],
                            "search_query": query,
                            "entries": entries,
                        },
                        ensure_ascii=False,
                    )
                    + "\n"
                )
                raw_fh.flush()
                resolved = choose_entry(row["channel_name"], entries)
                output_row = build_output_row(row, query, entries, resolved)
            except Exception as exc:  # noqa: BLE001 - operator script should keep going.
                output_row = build_error_row(row, query, exc)

            writer.writerow(output_row)
            out_fh.flush()
            time.sleep(args.sleep)

    return 0


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def run_search(query: str, limit: int, timeout: int) -> dict:
    url = f"https://www.youtube.com/results?search_query={quote_plus(query)}&sp={CHANNEL_SEARCH_FILTER}"
    command = [
        "micromamba",
        "run",
        "-n",
        "llm-opt",
        "yt-dlp",
        "--flat-playlist",
        "--playlist-items",
        f"1:{limit}",
        "--dump-single-json",
        "--skip-download",
        "--no-warnings",
        url,
    ]
    result = subprocess.run(
        command,
        check=True,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return json.loads(result.stdout)


def normalize_entries(entries: list[dict]) -> list[dict]:
    normalized = []
    for index, entry in enumerate(entries, start=1):
        normalized.append(
            {
                "rank": index,
                "title": entry.get("title") or "",
                "channel": entry.get("channel") or entry.get("uploader") or "",
                "channel_id": entry.get("channel_id") or entry.get("id") or "",
                "channel_url": entry.get("channel_url") or entry.get("url") or "",
                "handle": entry.get("uploader_id") or "",
                "uploader_url": entry.get("uploader_url") or "",
                "subscriber_count": entry.get("channel_follower_count"),
                "verified": bool(entry.get("channel_is_verified")),
                "description": entry.get("description") or "",
            }
        )
    return normalized


def choose_entry(channel_name: str, entries: list[dict]) -> dict | None:
    if not entries:
        return None
    scored = [(score_match(channel_name, entry), entry) for entry in entries]
    scored.sort(key=lambda item: item[0], reverse=True)
    return scored[0][1]


def score_match(expected: str, entry: dict) -> int:
    expected_norm = normalize_text(expected)
    title_norm = normalize_text(entry.get("title") or entry.get("channel") or "")
    score = 0
    if expected_norm and expected_norm == title_norm:
        score += 100
    if expected_norm and (expected_norm in title_norm or title_norm in expected_norm):
        score += 45
    expected_tokens = set(tokenize(expected_norm))
    title_tokens = set(tokenize(title_norm))
    if expected_tokens:
        score += int(40 * len(expected_tokens & title_tokens) / len(expected_tokens))
    if entry.get("verified"):
        score += 15
    if entry.get("subscriber_count"):
        score += 5
    score -= int(entry.get("rank") or 1) - 1
    return score


def build_output_row(
    candidate: dict[str, str],
    query: str,
    entries: list[dict],
    resolved: dict | None,
) -> dict[str, object]:
    base = {field: candidate.get(field, "") for field in OUTPUT_FIELDS}
    base["search_query"] = query
    base["alternatives_json"] = json.dumps(entries, ensure_ascii=False)
    if not resolved:
        base["confidence"] = "unresolved"
        base["match_notes"] = "yt-dlp returned no channel search results"
        return base

    expected_norm = normalize_text(candidate["channel_name"])
    title_norm = normalize_text(resolved["title"])
    if expected_norm == title_norm:
        confidence = "high"
        notes = "exact normalized title match"
    elif expected_norm in title_norm or title_norm in expected_norm:
        confidence = "high" if resolved["verified"] else "medium"
        notes = "partial normalized title match"
    elif set(tokenize(expected_norm)) & set(tokenize(title_norm)):
        confidence = "medium" if resolved["verified"] else "low"
        notes = "token overlap; review before crawling"
    else:
        confidence = "low"
        notes = "top channel result does not clearly match candidate name"

    base.update(
        {
            "resolved_title": resolved["title"],
            "handle": resolved["handle"],
            "channel_id": resolved["channel_id"],
            "channel_url": resolved["channel_url"],
            "uploader_url": resolved["uploader_url"],
            "subscriber_count": resolved["subscriber_count"] or "",
            "verified": "true" if resolved["verified"] else "false",
            "confidence": confidence,
            "match_notes": notes,
            "search_rank": resolved["rank"],
        }
    )
    return base


def build_error_row(candidate: dict[str, str], query: str, exc: Exception) -> dict[str, str]:
    base = {field: candidate.get(field, "") for field in OUTPUT_FIELDS}
    base["search_query"] = query
    base["confidence"] = "error"
    base["match_notes"] = f"{type(exc).__name__}: {exc}"
    return base


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", "", value.casefold())


def tokenize(value: str) -> list[str]:
    return [token for token in re.split(r"[^0-9a-zA-Z\u4e00-\u9fff]+", value) if token]


if __name__ == "__main__":
    sys.exit(main())
