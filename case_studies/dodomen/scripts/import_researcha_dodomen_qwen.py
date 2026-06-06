#!/usr/bin/env python3
from __future__ import annotations

from argparse import ArgumentParser
import json
import os
from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
MPLCONFIGDIR = ROOT / ".matplotlib"
MPLCONFIGDIR.mkdir(parents=True, exist_ok=True)
os.environ["MPLCONFIGDIR"] = str(MPLCONFIGDIR)
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from channel_analyzer.config import load_config, output_slug
from channel_analyzer.data import load_channel_data
from channel_analyzer.qwen_comment import DEFAULT_MODEL as DEFAULT_COMMENT_MODEL
from channel_analyzer.qwen_comment import TARGETS
from channel_analyzer.qwen_video import AUDIENCE_INTENTS, FORMATS, SETTINGS
from channel_analyzer.themes import THEME_LABELS


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(
        description=(
            "Import DoDoMen Qwen outputs from the ResearchA case-study folder "
            "into a generic ChannelCommunityAnalyzer run."
        )
    )
    parser.add_argument("--config", required=True, help="Path to analyzer config YAML.")
    parser.add_argument(
        "--researcha-dir",
        default=str(ROOT.parent / "ResearchA"),
        help="Path to the ResearchA folder containing tables/stage_* Qwen outputs.",
    )
    parser.add_argument(
        "--output",
        help="Optional run directory. Default: runs/<slug> from the config.",
    )
    parser.add_argument(
        "--prefer-existing",
        action="store_true",
        help="Keep existing generic rows when duplicate IDs are present.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    config = load_config(Path(args.config))
    data = load_channel_data(config)
    slug = output_slug(config, data.channel.get("title"))
    run_dir = Path(args.output).resolve() if args.output else ROOT / "runs" / slug
    tables_dir = run_dir / "tables"
    tables_dir.mkdir(parents=True, exist_ok=True)

    researcha = Path(args.researcha_dir).resolve()
    print(f"Channel: {data.channel.get('title')} ({data.channel.get('channel_id')})")
    print(f"Run directory: {run_dir}")
    print(f"ResearchA directory: {researcha}")

    imported_videos = import_video_themes(
        data.videos,
        researcha / "tables" / "stage_d4_llm_video_themes.csv",
        tables_dir / "qwen_video_themes.csv",
        prefer_existing=args.prefer_existing,
    )
    imported_comments = import_comment_sentiment(
        data.comments,
        researcha / "tables" / "stage_g_sentiments.csv",
        researcha / "tables" / "stage_g_sentiments_qwen3_details.csv",
        tables_dir / "qwen_comment_sentiment.csv",
        prefer_existing=args.prefer_existing,
    )

    print(
        "Imported Qwen video themes: "
        f"{imported_videos:,}/{len(data.videos):,}; "
        f"remaining {len(data.videos) - imported_videos:,}"
    )
    print(
        "Imported Qwen comment sentiment: "
        f"{imported_comments:,}/{len(data.comments):,}; "
        f"remaining {len(data.comments) - imported_comments:,}"
    )


def import_video_themes(
    videos: pd.DataFrame,
    source_path: Path,
    output_path: Path,
    *,
    prefer_existing: bool,
) -> int:
    if not source_path.exists():
        print(f"Skip video themes; missing source: {source_path}")
        return 0

    raw = pd.read_csv(source_path, low_memory=False)
    if raw.empty or "video_id" not in raw.columns:
        print(f"Skip video themes; no usable rows: {source_path}")
        return 0

    current = videos.copy()
    raw = raw.drop_duplicates("video_id", keep="last")
    raw = raw[raw["video_id"].isin(set(current["video_id"]))].copy()
    if raw.empty:
        return 0

    parsed = pd.DataFrame(
        {
            "video_id": raw["video_id"],
            "primary_theme": column_or_default(raw, "primary_theme", "other").map(clean_theme),
            "secondary_themes": raw.apply(clean_secondary_themes, axis=1),
            "format": column_or_default(raw, "format", "unclear").map(
                lambda value: clean_choice(value, FORMATS, "unclear")
            ),
            "setting": column_or_default(raw, "setting", "unknown").map(
                lambda value: clean_choice(value, SETTINGS, "unknown")
            ),
            "audience_intent": column_or_default(raw, "audience_intent", "unknown").map(
                lambda value: clean_choice(value, AUDIENCE_INTENTS, "unknown")
            ),
            "entities": column_or_default(raw, "entities", ""),
            "theme_confidence": pd.to_numeric(
                column_or_default(raw, "theme_confidence", None), errors="coerce"
            ),
            "theme_parse_error": bool_series(column_or_default(raw, "theme_parse_error", False)),
            "theme_reason": column_or_default(raw, "theme_reason", ""),
            "model": column_or_default(raw, "model", DEFAULT_COMMENT_MODEL),
        }
    )
    parsed["theme_labels"] = parsed.apply(theme_labels_from_row, axis=1)
    parsed["theme_raw"] = parsed.apply(video_raw_json, axis=1)

    out = current.merge(parsed, on="video_id", how="inner")
    out = merge_existing(output_path, out, "video_id", prefer_existing=prefer_existing)
    out.to_csv(output_path, index=False)
    return int(out["video_id"].nunique())


def import_comment_sentiment(
    comments: pd.DataFrame,
    sentiment_path: Path,
    details_path: Path,
    output_path: Path,
    *,
    prefer_existing: bool,
) -> int:
    if not sentiment_path.exists():
        print(f"Skip comment sentiment; missing source: {sentiment_path}")
        return 0

    sentiments = pd.read_csv(sentiment_path, low_memory=False)
    required = {"comment_id", "sentiment", "score_neg", "score_neu", "score_pos"}
    if sentiments.empty or not required.issubset(sentiments.columns):
        print(f"Skip comment sentiment; no usable rows: {sentiment_path}")
        return 0

    details = pd.DataFrame()
    if details_path.exists():
        detail_cols = [
            "comment_id",
            "llm_target",
            "llm_confidence",
            "llm_parse_error",
            "model",
        ]
        details = pd.read_csv(
            details_path,
            usecols=lambda col: col in detail_cols,
            low_memory=False,
        )

    meta_cols = [
        "comment_id",
        "video_id",
        "author_actor_id",
        "comment_published_at",
        "like_count",
    ]
    current = comments[meta_cols].copy()
    imported = current.merge(
        sentiments[
            ["comment_id", "sentiment", "score_neg", "score_neu", "score_pos"]
        ],
        on="comment_id",
        how="inner",
    )
    if not details.empty:
        imported = imported.merge(details, on="comment_id", how="left")
    else:
        imported["llm_target"] = "unclear"
        imported["llm_confidence"] = None
        imported["llm_parse_error"] = False
        imported["model"] = DEFAULT_COMMENT_MODEL

    imported["sentiment_label"] = imported["sentiment"].map(clean_sentiment)
    for col in ["score_neg", "score_neu", "score_pos"]:
        imported[col] = pd.to_numeric(imported[col], errors="coerce").fillna(0.0)
    imported["target"] = imported["llm_target"].map(lambda value: clean_choice(value, TARGETS, "other"))
    imported["emotion_tags"] = ""
    imported["toxicity"] = None
    imported["sentiment_confidence"] = pd.to_numeric(
        imported["llm_confidence"], errors="coerce"
    )
    imported["sentiment_parse_error"] = bool_series(imported["llm_parse_error"])
    imported["sentiment_reason"] = "imported_from_researcha_stage_g"
    imported["sentiment_raw"] = imported.apply(sentiment_raw_json, axis=1)
    imported["model"] = imported["model"].fillna(DEFAULT_COMMENT_MODEL)

    out_cols = [
        "comment_id",
        "video_id",
        "author_actor_id",
        "comment_published_at",
        "like_count",
        "sentiment_label",
        "score_neg",
        "score_neu",
        "score_pos",
        "target",
        "emotion_tags",
        "toxicity",
        "sentiment_confidence",
        "sentiment_parse_error",
        "sentiment_reason",
        "sentiment_raw",
        "model",
    ]
    out = imported[out_cols].copy()
    out = merge_existing(output_path, out, "comment_id", prefer_existing=prefer_existing)
    out.to_csv(output_path, index=False)
    return int(out["comment_id"].nunique())


def merge_existing(
    output_path: Path,
    imported: pd.DataFrame,
    id_col: str,
    *,
    prefer_existing: bool,
) -> pd.DataFrame:
    if output_path.exists() and output_path.stat().st_size > 0:
        existing = pd.read_csv(output_path, low_memory=False)
        frames = [existing, imported]
        keep = "first" if prefer_existing else "last"
        return pd.concat(frames, ignore_index=True).drop_duplicates(id_col, keep=keep)
    return imported.drop_duplicates(id_col, keep="last")


def column_or_default(frame: pd.DataFrame, column: str, default: object) -> pd.Series:
    if column in frame.columns:
        return frame[column]
    return pd.Series([default] * len(frame), index=frame.index)


def clean_theme(value: object) -> str:
    return clean_choice(value, THEME_LABELS, "other")


def clean_secondary_themes(row: pd.Series) -> str:
    value = row.get("secondary_themes", row.get("secondary_theme", ""))
    if isinstance(value, list):
        parts = value
    else:
        parts = str(value or "").replace("|", ";").replace(",", ";").split(";")
    labels = [clean_theme(part.strip()) for part in parts]
    labels = [label for label in labels if label and label != "other"]
    primary = clean_theme(row.get("primary_theme"))
    labels = [label for label in labels if label != primary]
    return ";".join(dict.fromkeys(labels))


def theme_labels_from_row(row: pd.Series) -> str:
    labels = [clean_theme(row.get("primary_theme"))]
    labels.extend(str(row.get("secondary_themes") or "").split(";"))
    labels = [clean_theme(label) for label in labels]
    labels = [label for label in labels if label and label != "other"]
    return ";".join(dict.fromkeys(labels)) or "other"


def clean_sentiment(value: object) -> str:
    text = str(value or "neutral").strip()
    if text in {"negative", "neutral", "positive"}:
        return text
    return "neutral"


def clean_choice(value: object, allowed: list[str], default: str) -> str:
    text = str(value or default).strip()
    return text if text in allowed else default


def bool_series(value: object) -> pd.Series:
    if isinstance(value, pd.Series):
        return value.fillna(False).map(to_bool)
    return pd.Series([to_bool(value)])


def to_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    text = str(value or "").strip().lower()
    return text in {"1", "true", "yes", "y"}


def video_raw_json(row: pd.Series) -> str:
    secondary = [item for item in str(row.get("secondary_themes") or "").split(";") if item]
    confidence = pd.to_numeric(row.get("theme_confidence"), errors="coerce")
    if pd.isna(confidence):
        confidence = 0.7
    payload = {
        "primary_theme": clean_theme(row.get("primary_theme")),
        "secondary_themes": secondary,
        "format": clean_choice(row.get("format"), FORMATS, "unclear"),
        "setting": clean_choice(row.get("setting"), SETTINGS, "unknown"),
        "audience_intent": clean_choice(row.get("audience_intent"), AUDIENCE_INTENTS, "unknown"),
        "entities": [
            item.strip()
            for item in str(row.get("entities") or "").split(";")
            if item.strip()
        ],
        "confidence": float(confidence),
        "reason": str(row.get("theme_reason") or "imported_from_researcha_stage_d4"),
    }
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def sentiment_raw_json(row: pd.Series) -> str:
    payload = {
        "sentiment_label": clean_sentiment(row.get("sentiment_label")),
        "score_neg": float(row.get("score_neg") or 0.0),
        "score_neu": float(row.get("score_neu") or 0.0),
        "score_pos": float(row.get("score_pos") or 0.0),
    }
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


if __name__ == "__main__":
    main()
