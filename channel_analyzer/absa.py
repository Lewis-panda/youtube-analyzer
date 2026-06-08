from __future__ import annotations

from dataclasses import dataclass
import json
import os
import re
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


DEFAULT_MODEL = "Qwen/Qwen3-8B"


ASPECTS = [
    "pacing_editing",
    "commercial_sponsorship",
    "authenticity_fabrication",
    "host_persona",
    "guest_collab",
    "cultural_values_politics",
    "content_quality_information",
    "production_quality",
    "price_value_product",
    "safety_ethics",
    "other",
    "unclear",
]

ASPECT_LABELS_ZH = {
    "pacing_editing": "影片節奏/剪輯",
    "commercial_sponsorship": "業配/商業可信度",
    "authenticity_fabrication": "真實性/造假疑慮",
    "host_persona": "主持人本人",
    "guest_collab": "來賓/合作對象",
    "cultural_values_politics": "文化價值觀/政治爭議",
    "content_quality_information": "內容品質/資訊量",
    "production_quality": "製作品質",
    "price_value_product": "價格/產品價值",
    "safety_ethics": "安全/道德風險",
    "other": "其他",
    "unclear": "不明確",
}

ASPECT_KEYWORDS = {
    "pacing_editing": [
        "拖",
        "太長",
        "節奏",
        "剪輯",
        "廢話",
        "冗",
        "慢",
        "水",
        "重複",
        "pacing",
        "editing",
    ],
    "commercial_sponsorship": [
        "業配",
        "廣告",
        "贊助",
        "sponsor",
        "ad",
        "置入",
        "工商",
        "葉配",
        "商業",
        "收錢",
    ],
    "authenticity_fabrication": [
        "造假",
        "假",
        "演",
        "劇本",
        "作秀",
        "騙",
        "不真實",
        "設定",
        "fabricated",
        "fake",
        "staged",
    ],
    "host_persona": [
        "ian",
        "eric",
        "主持",
        "本人",
        "人設",
        "個性",
        "態度",
        "嘟嘟人",
        "dodo",
    ],
    "guest_collab": [
        "來賓",
        "合作",
        "collab",
        "ft",
        "嘉賓",
        "super junior",
        "sj",
        "藝人",
    ],
    "cultural_values_politics": [
        "統戰",
        "政治",
        "價值觀",
        "中國",
        "台灣",
        "文化",
        "立場",
        "辱",
        "歧視",
    ],
    "content_quality_information": [
        "內容",
        "資訊",
        "沒料",
        "無聊",
        "不好看",
        "品質",
        "題材",
        "企劃",
        "比較",
        "實測",
    ],
    "production_quality": [
        "音量",
        "收音",
        "字幕",
        "畫質",
        "鏡頭",
        "拍攝",
        "後製",
        "音質",
    ],
    "price_value_product": [
        "價格",
        "貴",
        "便宜",
        "值得",
        "cp",
        "功能",
        "產品",
        "開箱",
        "實測",
        "比較",
    ],
    "safety_ethics": [
        "危險",
        "安全",
        "道德",
        "不尊重",
        "違法",
        "倫理",
        "受傷",
        "風險",
    ],
}

ASPECT_POLARITIES = ["negative", "neutral", "positive", "mixed", "unclear"]

OUTPUT_ID_COLS = [
    "unit_id",
    "source_type",
    "source",
    "source_id",
    "video_id",
    "published_at",
    "like_count",
]


SYSTEM_PROMPT = f"""You do aspect-based sentiment analysis for a YouTube channel analytics tool.
Return one compact JSON object only. No markdown, no explanation.

Allowed aspects:
{", ".join(ASPECTS)}

Allowed aspect_sentiment values:
{", ".join(ASPECT_POLARITIES)}

JSON schema:
{{
  "aspects": [
    {{
      "aspect": "one allowed aspect",
      "sentiment": "negative|neutral|positive|mixed|unclear",
      "severity": 0,
      "confidence": 0.0,
      "evidence": "short phrase from the text or concise paraphrase"
    }}
  ],
  "primary_aspect": "one allowed aspect",
  "summary": "short Traditional Chinese summary"
}}

Aspect definitions:
- pacing_editing: pacing, too slow/dragging, editing rhythm, repeated filler.
- commercial_sponsorship: sponsorship, ads, brand placement, commercial trust.
- authenticity_fabrication: fake/staged/scripted/manipulated/inauthentic concerns.
- host_persona: criticism or praise of the host/creator themselves.
- guest_collab: guest, collaborator, external celebrity/person/brand fit.
- cultural_values_politics: politics, nationalism, cultural values, discrimination, ideology.
- content_quality_information: content depth, usefulness, correctness, topic quality.
- production_quality: audio, subtitles, camera, visual/editing craft quality.
- price_value_product: product price, value, features, comparison, worth buying.
- safety_ethics: safety, legality, respect, moral/ethical concern.
- other: meaningful but not in the above.
- unclear: no clear aspect.

Rules:
- Use only the given text and optional context.
- A text may contain multiple aspects, but return at most 3.
- Use severity 0 for no issue/praise, 1 mild, 2 clear, 3 severe.
- Do not mark an aspect just because a keyword appears in a video title; the text must comment on it or clearly refer to it.
- If the text only tags a person, jokes unclearly, or is spam, use unclear.
- Use Traditional Chinese in summary/evidence.
- Keep each evidence under 18 Chinese characters.
- Keep summary under 24 Chinese characters.
- Output only the JSON object.
"""


@dataclass(frozen=True)
class AbsaArtifacts:
    summary_path: Path
    comment_aspect_summary_path: Path
    comment_aspect_daily_path: Path
    platform_aspect_daily_path: Path | None = None
    platform_aspect_anomalies_path: Path | None = None


def compact_text(text: object, limit: int) -> str:
    return re.sub(r"\s+", " ", str(text or "").strip())[:limit]


def build_user_prompt(row: pd.Series) -> str:
    source_type = row.get("source_type", "youtube_comment")
    return (
        f"Source type: {source_type}\n"
        f"Source/platform: {row.get('source', '')}\n"
        f"Date: {row.get('published_at', '')}\n"
        f"Video/post title: {compact_text(row.get('title', row.get('video_title', '')), 180)}\n"
        f"Known overall sentiment: {row.get('sentiment_label', '')}\n"
        f"Text: {compact_text(row.get('text_plain', row.get('text', '')), 900)}\n"
        "Classify aspect-based sentiment."
    )


def parse_json_output(text: object) -> dict[str, Any]:
    raw_text = str(text or "").strip()
    raw_text = strip_model_wrappers(raw_text)
    match = re.search(r"\{.*", raw_text, flags=re.S)
    raw = match.group(0) if match else raw_text
    parse_error = False
    repair_method = ""
    try:
        parsed = json.loads(raw)
    except Exception:
        repaired = repair_json_object(raw)
        try:
            parsed = json.loads(repaired)
            repair_method = "json_balance"
        except Exception:
            parsed = salvage_json_fields(raw)
            repair_method = "field_salvage" if parsed.get("aspects") else ""
            parse_error = True

    parsed_aspects = parsed.get("aspects")
    if not isinstance(parsed_aspects, list):
        parsed_aspects = []
    rows = []
    for item in parsed_aspects[:4]:
        if not isinstance(item, dict):
            continue
        aspect = clean_choice(item.get("aspect"), ASPECTS, "unclear")
        sentiment = clean_choice(item.get("sentiment"), ASPECT_POLARITIES, "unclear")
        severity = clean_int(item.get("severity"), default=0, min_value=0, max_value=3)
        confidence = clean_float(item.get("confidence"), default=0.35 if parse_error else 0.7)
        rows.append(
            {
                "aspect": aspect,
                "sentiment": sentiment,
                "severity": severity,
                "confidence": confidence,
                "evidence": compact_text(item.get("evidence", ""), 120),
            }
        )
    if not rows:
        rows = [
            {
                "aspect": "unclear",
                "sentiment": "unclear",
                "severity": 0,
                "confidence": 0.25,
                "evidence": "",
            }
        ]
    elif repair_method:
        parse_error = False

    primary = clean_choice(parsed.get("primary_aspect"), ASPECTS, rows[0]["aspect"])
    if primary not in {row["aspect"] for row in rows} and rows:
        primary = rows[0]["aspect"]
    return {
        "primary_aspect": primary,
        "aspect_labels": ";".join(row["aspect"] for row in rows),
        "aspect_sentiments": ";".join(f"{row['aspect']}={row['sentiment']}" for row in rows),
        "aspect_severities": ";".join(f"{row['aspect']}={row['severity']}" for row in rows),
        "aspect_confidences": ";".join(f"{row['aspect']}={row['confidence']:.2f}" for row in rows),
        "aspect_evidence": " | ".join(
            f"{row['aspect']}:{row['evidence']}" for row in rows if row.get("evidence")
        ),
        "absa_parse_error": parse_error,
        "absa_repair_method": repair_method,
        "absa_summary": compact_text(parsed.get("summary", ""), 180),
        "absa_raw": raw_text,
    }


def classify_units_with_vllm_to_csv(
    units: pd.DataFrame,
    output_path: Path,
    model_id: str,
    batch_size: int,
    max_model_len: int,
    attention_backend: str | None,
    gpu_memory_utilization: float,
) -> pd.DataFrame:
    if attention_backend:
        os.environ["VLLM_ATTENTION_BACKEND"] = attention_backend

    from vllm import LLM, SamplingParams

    llm = LLM(
        model=model_id,
        trust_remote_code=True,
        dtype="half",
        quantization="bitsandbytes",
        load_format="bitsandbytes",
        max_model_len=max_model_len,
        gpu_memory_utilization=gpu_memory_utilization,
        enforce_eager=True,
        attention_config={"backend": attention_backend} if attention_backend else None,
    )
    sampling = SamplingParams(max_tokens=384, temperature=0.0)
    parsed_rows: list[dict[str, Any]] = []
    total = len(units)
    for start in range(0, total, batch_size):
        chunk = units.iloc[start : start + batch_size]
        messages = [
            [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": build_user_prompt(row)},
            ]
            for _, row in chunk.iterrows()
        ]
        outputs = llm.chat(
            messages,
            sampling_params=sampling,
            use_tqdm=False,
            chat_template_kwargs={"enable_thinking": False},
        )
        parsed = [parse_json_output(out.outputs[0].text) for out in outputs]
        parsed_rows.extend(parsed)
        chunk_out = pd.concat(
            [output_id_frame(chunk).reset_index(drop=True), pd.DataFrame(parsed)],
            axis=1,
        )
        chunk_out["model"] = model_id
        merged = merge_existing_output(output_path, chunk_out)
        merged.to_csv(output_path, index=False)
        print(f"  ABSA classified {min(start + batch_size, total):,}/{total:,}", flush=True)

    out = pd.concat([output_id_frame(units).reset_index(drop=True), pd.DataFrame(parsed_rows)], axis=1)
    out["model"] = model_id
    return out


def output_id_frame(units: pd.DataFrame) -> pd.DataFrame:
    out = units.copy()
    for col in OUTPUT_ID_COLS:
        if col not in out.columns:
            out[col] = None
    return out[OUTPUT_ID_COLS]


def merge_existing_output(path: Path, new_rows: pd.DataFrame) -> pd.DataFrame:
    if path.exists() and path.stat().st_size > 0:
        existing = pd.read_csv(path, low_memory=False)
        merged = pd.concat([existing, new_rows], ignore_index=True)
    else:
        merged = new_rows
    return merged.drop_duplicates("unit_id", keep="last")


def completed_output_unit_ids(output_path: Path) -> set[str]:
    if not output_path.exists() or output_path.stat().st_size <= 0:
        return set()
    existing = pd.read_csv(output_path, low_memory=False)
    if existing.empty or "unit_id" not in existing.columns:
        return set()
    complete = pd.Series(True, index=existing.index)
    if "absa_parse_error" in existing.columns:
        complete &= ~existing["absa_parse_error"].astype(str).str.lower().eq("true")
    if "absa_raw" in existing.columns:
        complete &= existing["absa_raw"].notna()
        complete &= existing["absa_raw"].astype(str).str.strip().ne("")
    return set(existing.loc[complete, "unit_id"].astype(str))


def select_remaining(units: pd.DataFrame, output_path: Path, limit: int | None) -> pd.DataFrame:
    done = completed_output_unit_ids(output_path)
    remaining = units[~units["unit_id"].astype(str).isin(done)].copy()
    if limit is not None:
        remaining = remaining.head(limit).copy()
    return remaining


def repair_existing_output(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, low_memory=False)
    if df.empty or "absa_raw" not in df.columns:
        return df
    parsed = pd.DataFrame([parse_json_output(text) for text in df["absa_raw"].fillna("")])
    for col in parsed.columns:
        df[col] = parsed[col]
    df.to_csv(path, index=False)
    return df


def aspect_keyword_pattern() -> re.Pattern:
    words = []
    for items in ASPECT_KEYWORDS.values():
        words.extend(items)
    escaped = [re.escape(item) for item in sorted(set(words), key=len, reverse=True)]
    return re.compile("|".join(escaped), flags=re.I)


def keyword_hit_aspects(text: object) -> list[str]:
    value = str(text or "")
    hits = []
    for aspect, words in ASPECT_KEYWORDS.items():
        if any(re.search(re.escape(word), value, flags=re.I) for word in words):
            hits.append(aspect)
    return hits


def build_comment_units(
    comments: pd.DataFrame,
    videos: pd.DataFrame,
    sentiment_path: Path | None,
    scope: str,
) -> pd.DataFrame:
    units = comments.copy()
    titles = videos[["video_id", "title"]].rename(columns={"title": "video_title"})
    units = units.merge(titles, on="video_id", how="left")
    units["unit_id"] = units["comment_id"].astype(str)
    units["source_type"] = "youtube_comment"
    units["source"] = "youtube"
    units["source_id"] = units["comment_id"]
    units["published_at"] = units["comment_published_at"]
    if sentiment_path and sentiment_path.exists() and sentiment_path.stat().st_size > 0:
        sentiment = pd.read_csv(
            sentiment_path,
            usecols=lambda col: col
            in {
                "comment_id",
                "sentiment_label",
                "score_neg",
                "score_pos",
                "sentiment_parse_error",
            },
            low_memory=False,
        )
        if "sentiment_parse_error" in sentiment.columns:
            sentiment = sentiment[sentiment["sentiment_parse_error"].astype(str).str.lower() != "true"]
        units = units.merge(sentiment.drop_duplicates("comment_id", keep="last"), on="comment_id", how="left")
    else:
        units["sentiment_label"] = ""
    units["aspect_keyword_hits"] = units["text_plain"].fillna("").map(lambda text: ";".join(keyword_hit_aspects(text)))
    has_keyword = units["aspect_keyword_hits"].astype(str).str.len() > 0
    is_negative = units["sentiment_label"].astype(str).eq("negative")
    is_positive = units["sentiment_label"].astype(str).eq("positive")
    if scope == "negative":
        units = units[is_negative].copy()
    elif scope == "positive":
        units = units[is_positive].copy()
    elif scope == "keyword":
        units = units[has_keyword].copy()
    elif scope == "negative_or_keyword":
        units = units[is_negative | has_keyword].copy()
    elif scope == "all":
        units = units.copy()
    else:
        raise ValueError(f"Unsupported ABSA comment scope: {scope}")
    return units.sort_values(["published_at", "unit_id"]).reset_index(drop=True)


def build_external_units(posts: pd.DataFrame) -> pd.DataFrame:
    if posts.empty:
        return pd.DataFrame()
    out = posts.copy()
    if "post_uid" not in out.columns:
        out["post_uid"] = out.apply(
            lambda row: f"{row.get('source', 'external')}:{row.get('post_id', row.name)}",
            axis=1,
        )
    text_cols = [col for col in ["title", "text", "body", "content"] if col in out.columns]
    if not text_cols:
        out["text"] = out.get("title", "")
    else:
        out["text"] = out[text_cols].fillna("").agg("\n".join, axis=1)
    out["unit_id"] = out["post_uid"].astype(str)
    out["source_type"] = "external_post"
    out["source"] = out.get("source", "external")
    out["source_id"] = out.get("post_id", out["unit_id"])
    out["video_id"] = None
    out["published_at"] = out.get("date", out.get("event_date", ""))
    out["like_count"] = out.get("engagement", 0)
    out["sentiment_label"] = out.get("stance", "")
    return out.sort_values(["published_at", "unit_id"]).reset_index(drop=True)


def run_absa_aggregation(
    run_dir: Path,
    comment_absa_path: Path,
    output_dir: Path | None = None,
    external_absa_path: Path | None = None,
) -> AbsaArtifacts:
    output_dir = output_dir or run_dir / "absa"
    output_dir.mkdir(parents=True, exist_ok=True)
    tables_dir = run_dir / "tables"

    comments = pd.read_csv(comment_absa_path, low_memory=False) if comment_absa_path.exists() else pd.DataFrame()
    sentiment_path = tables_dir / "qwen_comment_sentiment.csv"
    full_channel_negative_rate = np.nan
    full_channel_positive_rate = np.nan
    full_channel_comment_units = np.nan
    if sentiment_path.exists() and sentiment_path.stat().st_size > 0:
        sentiment = pd.read_csv(
            sentiment_path,
            usecols=lambda col: col in {"comment_id", "sentiment_label", "score_neg", "score_pos", "like_count"},
            low_memory=False,
        )
        sentiment = sentiment.drop_duplicates("comment_id", keep="last")
        full_channel_comment_units = int(sentiment["comment_id"].nunique())
        full_channel_negative_rate = float(sentiment["sentiment_label"].astype(str).eq("negative").mean())
        full_channel_positive_rate = float(sentiment["sentiment_label"].astype(str).eq("positive").mean())
    if not comments.empty and sentiment_path.exists() and sentiment_path.stat().st_size > 0:
        comments = comments.merge(
            sentiment.rename(columns={"comment_id": "unit_id"}),
            on="unit_id",
            how="left",
            suffixes=("", "_overall"),
        )
    aspect_rows = explode_absa_rows(comments)
    summary = summarize_comment_aspects(
        aspect_rows,
        comments,
        full_channel_negative_rate=full_channel_negative_rate,
        full_channel_positive_rate=full_channel_positive_rate,
        full_channel_comment_units=full_channel_comment_units,
    )
    daily = summarize_aspect_daily(aspect_rows, platform_col=None)
    external_daily = pd.DataFrame()
    anomalies = pd.DataFrame()

    if external_absa_path and external_absa_path.exists() and external_absa_path.stat().st_size > 0:
        external = pd.read_csv(external_absa_path, low_memory=False)
        external_rows = explode_absa_rows(external)
        yt_rows = aspect_rows.copy()
        yt_rows["platform"] = "youtube"
        external_rows["platform"] = external_rows.get("source", "external")
        all_platform_rows = pd.concat([yt_rows, external_rows], ignore_index=True)
        external_daily = summarize_aspect_daily(all_platform_rows, platform_col="platform")
        anomalies = detect_platform_aspect_anomalies(external_daily)

    summary_path = output_dir / "comment_aspect_summary.csv"
    daily_path = output_dir / "comment_aspect_daily.csv"
    platform_daily_path = output_dir / "platform_aspect_daily.csv"
    anomalies_path = output_dir / "platform_aspect_anomalies.csv"
    meta_path = output_dir / "absa_summary.json"

    summary.to_csv(summary_path, index=False)
    daily.to_csv(daily_path, index=False)
    external_daily.to_csv(platform_daily_path, index=False)
    anomalies.to_csv(anomalies_path, index=False)
    meta = {
        "comment_absa_path": str(comment_absa_path),
        "external_absa_path": str(external_absa_path) if external_absa_path else None,
        "n_scored_comment_units": int(comments["unit_id"].nunique()) if not comments.empty else 0,
        "n_comment_aspect_rows": int(len(aspect_rows)),
        "full_channel_comment_units": clean_json(full_channel_comment_units),
        "full_channel_negative_rate": clean_json(full_channel_negative_rate),
        "full_channel_positive_rate": clean_json(full_channel_positive_rate),
        "n_external_platform_days": int(len(external_daily)),
        "n_platform_anomalies": int(len(anomalies)),
        "aspects": ASPECT_LABELS_ZH,
        "scope_note_zh": (
            "目前 ABSA 可用於 candidate-scope diagnostics；若不是 all scope，"
            "mention rate 不可解讀為全留言區比例。"
        ),
    }
    meta_path.write_text(json.dumps(clean_json(meta), ensure_ascii=False, indent=2), encoding="utf-8")
    return AbsaArtifacts(
        summary_path=summary_path,
        comment_aspect_summary_path=summary_path,
        comment_aspect_daily_path=daily_path,
        platform_aspect_daily_path=platform_daily_path,
        platform_aspect_anomalies_path=anomalies_path,
    )


def explode_absa_rows(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    rows = []
    for row in df.itertuples(index=False):
        base = row._asdict()
        sentiments = parse_key_value_list(base.get("aspect_sentiments"))
        severities = parse_key_value_list(base.get("aspect_severities"))
        confidences = parse_key_value_list(base.get("aspect_confidences"))
        labels = [item.strip() for item in str(base.get("aspect_labels") or "").split(";") if item.strip()]
        if not labels:
            labels = ["unclear"]
        for aspect in labels:
            rows.append(
                {
                    "unit_id": base.get("unit_id"),
                    "source_type": base.get("source_type"),
                    "source": base.get("source"),
                    "video_id": base.get("video_id"),
                    "published_at": base.get("published_at"),
                    "like_count": as_number(base.get("like_count")) or 0,
                    "aspect": aspect,
                    "aspect_label_zh": ASPECT_LABELS_ZH.get(aspect, aspect),
                    "aspect_sentiment": sentiments.get(aspect, "unclear"),
                    "severity": as_number(severities.get(aspect)) or 0,
                    "confidence": as_number(confidences.get(aspect)) or 0,
                    "overall_sentiment_label": base.get("sentiment_label"),
                    "primary_aspect": base.get("primary_aspect"),
                }
            )
    return pd.DataFrame(rows)


def summarize_comment_aspects(
    aspect_rows: pd.DataFrame,
    units: pd.DataFrame,
    full_channel_negative_rate: float | None = None,
    full_channel_positive_rate: float | None = None,
    full_channel_comment_units: int | float | None = None,
) -> pd.DataFrame:
    if aspect_rows.empty:
        return pd.DataFrame()
    scoped_units = max(int(units["unit_id"].nunique()), 1)
    scored_channel_negative_rate = 0.0
    scored_channel_positive_rate = 0.0
    if "sentiment_label" in units.columns:
        scored_channel_negative_rate = float(units["sentiment_label"].astype(str).eq("negative").mean())
        scored_channel_positive_rate = float(units["sentiment_label"].astype(str).eq("positive").mean())
    full_units = as_number(full_channel_comment_units)
    full_neg_rate = as_number(full_channel_negative_rate)
    full_pos_rate = as_number(full_channel_positive_rate)
    if not full_units or full_units <= 0:
        full_units = np.nan
    if full_neg_rate is None:
        full_neg_rate = np.nan
    if full_pos_rate is None:
        full_pos_rate = np.nan
    negative_rows = aspect_rows[aspect_rows["aspect_sentiment"].isin(["negative", "mixed"])].copy()
    positive_rows = aspect_rows[aspect_rows["aspect_sentiment"].isin(["positive", "mixed"])].copy()
    total_negative_aspect_units = max(int(negative_rows["unit_id"].nunique()), 1)
    total_positive_aspect_units = max(int(positive_rows["unit_id"].nunique()), 1)
    rows = []
    for aspect, group in aspect_rows.groupby("aspect"):
        if aspect == "unclear":
            continue
        units_n = int(group["unit_id"].nunique())
        neg_units = int(group[group["aspect_sentiment"].isin(["negative", "mixed"])]["unit_id"].nunique())
        pos_units = int(group[group["aspect_sentiment"].isin(["positive", "mixed"])]["unit_id"].nunique())
        mention_rate = units_n / scoped_units
        aspect_negative_rate = neg_units / units_n if units_n else 0.0
        aspect_positive_rate = pos_units / units_n if units_n else 0.0
        negative_prevalence_per_full_comment = neg_units / full_units if full_units and not pd.isna(full_units) else np.nan
        positive_prevalence_per_full_comment = pos_units / full_units if full_units and not pd.isna(full_units) else np.nan
        avg_severity = float(group["severity"].mean()) if len(group) else 0.0
        like_total = (group["like_count"].fillna(0).astype(float) + 1).sum()
        like_neg = (
            group[group["aspect_sentiment"].isin(["negative", "mixed"])]["like_count"].fillna(0).astype(float)
            + 1
        ).sum()
        like_pos = (
            group[group["aspect_sentiment"].isin(["positive", "mixed"])]["like_count"].fillna(0).astype(float)
            + 1
        ).sum()
        rows.append(
            {
                "aspect": aspect,
                "aspect_label_zh": ASPECT_LABELS_ZH.get(aspect, aspect),
                "n_scored_mentions": units_n,
                "mention_rate_scored_scope": mention_rate,
                "n_negative_or_mixed": neg_units,
                "aspect_negative_rate": aspect_negative_rate,
                "aspect_negative_lift_vs_scored_channel_negative_rate": (
                    aspect_negative_rate / scored_channel_negative_rate if scored_channel_negative_rate else np.nan
                ),
                "negative_aspect_prevalence_per_full_comment": negative_prevalence_per_full_comment,
                "negative_aspect_prevalence_lift_vs_full_channel_negative_rate": (
                    negative_prevalence_per_full_comment / full_neg_rate
                    if full_neg_rate and not pd.isna(full_neg_rate)
                    else np.nan
                ),
                "negative_aspect_share": neg_units / total_negative_aspect_units,
                "like_weighted_aspect_negative_rate": float(like_neg / like_total) if like_total else 0.0,
                "n_positive_or_mixed": pos_units,
                "aspect_positive_rate": aspect_positive_rate,
                "aspect_positive_lift_vs_scored_channel_positive_rate": (
                    aspect_positive_rate / scored_channel_positive_rate if scored_channel_positive_rate else np.nan
                ),
                "positive_aspect_prevalence_per_full_comment": positive_prevalence_per_full_comment,
                "positive_aspect_prevalence_lift_vs_full_channel_positive_rate": (
                    positive_prevalence_per_full_comment / full_pos_rate
                    if full_pos_rate and not pd.isna(full_pos_rate)
                    else np.nan
                ),
                "positive_aspect_share": pos_units / total_positive_aspect_units,
                "like_weighted_aspect_positive_rate": float(like_pos / like_total) if like_total else 0.0,
                "avg_severity": avg_severity,
                "scored_channel_negative_rate": scored_channel_negative_rate,
                "scored_channel_positive_rate": scored_channel_positive_rate,
                "full_channel_negative_rate": full_neg_rate,
                "full_channel_positive_rate": full_pos_rate,
                "full_channel_comment_units": full_units,
                "scope_note": (
                    "mention_rate_scored_scope uses the ABSA-scored subset. "
                    "positive/negative_aspect_prevalence_lift metrics use the full "
                    "qwen_comment_sentiment denominator when available."
                ),
            }
        )
    out = pd.DataFrame(rows)
    if scored_channel_positive_rate > scored_channel_negative_rate:
        return out.sort_values(
            ["positive_aspect_prevalence_lift_vs_full_channel_positive_rate", "n_positive_or_mixed"],
            ascending=False,
        )
    return out.sort_values(
        ["negative_aspect_prevalence_lift_vs_full_channel_negative_rate", "n_negative_or_mixed"],
        ascending=False,
    )


def summarize_aspect_daily(aspect_rows: pd.DataFrame, platform_col: str | None) -> pd.DataFrame:
    if aspect_rows.empty:
        return pd.DataFrame()
    frame = aspect_rows.copy()
    frame["date"] = pd.to_datetime(frame["published_at"], errors="coerce", utc=True).dt.date.astype(str)
    frame = frame[frame["date"].notna() & frame["aspect"].ne("unclear")]
    frame["is_negative_aspect"] = frame["aspect_sentiment"].isin(["negative", "mixed"]).astype(int)
    frame["is_positive_aspect"] = frame["aspect_sentiment"].isin(["positive", "mixed"]).astype(int)
    group_cols = ["date", "aspect"]
    if platform_col:
        group_cols.insert(1, platform_col)
    return (
        frame.groupby(group_cols)
        .agg(
            n_units=("unit_id", "nunique"),
            n_negative_aspect_units=("is_negative_aspect", "sum"),
            n_positive_aspect_units=("is_positive_aspect", "sum"),
            avg_severity=("severity", "mean"),
            total_like_weight=("like_count", lambda s: float((s.fillna(0).astype(float) + 1).sum())),
        )
        .reset_index()
        .sort_values(group_cols)
    )


def detect_platform_aspect_anomalies(daily: pd.DataFrame) -> pd.DataFrame:
    if daily.empty or "platform" not in daily.columns:
        return pd.DataFrame()
    rows = []
    frame = daily.copy()
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce", utc=True)
    frame = frame.dropna(subset=["date"])
    for (platform, aspect), group in frame.groupby(["platform", "aspect"]):
        values = group["n_negative_aspect_units"].astype(float)
        mean = float(values.mean())
        std = float(values.std(ddof=0))
        threshold = max(mean + 2 * std, 3.0)
        hits = group[group["n_negative_aspect_units"] >= threshold].copy()
        for _, row in hits.iterrows():
            rows.append(
                {
                    "platform": platform,
                    "aspect": aspect,
                    "aspect_label_zh": ASPECT_LABELS_ZH.get(aspect, aspect),
                    "date": row["date"].date().isoformat(),
                    "n_negative_aspect_units": int(row["n_negative_aspect_units"]),
                    "baseline_mean_daily": mean,
                    "baseline_std_daily": std,
                    "z_score": (float(row["n_negative_aspect_units"]) - mean) / std if std else np.nan,
                    "threshold": threshold,
                }
            )
    out = pd.DataFrame(rows)
    if out.empty:
        return out
    return out.sort_values(["date", "platform", "n_negative_aspect_units"], ascending=[True, True, False])


def parse_key_value_list(value: Any) -> dict[str, str]:
    out = {}
    for item in str(value or "").split(";"):
        if "=" not in item:
            continue
        key, val = item.split("=", 1)
        out[key.strip()] = val.strip()
    return out


def clean_choice(value: Any, choices: list[str], default: str) -> str:
    text = str(value or "").strip()
    return text if text in choices else default


def clean_float(value: Any, default: float) -> float:
    try:
        out = float(value)
    except Exception:
        out = default
    if pd.isna(out):
        out = default
    return min(max(out, 0.0), 1.0)


def clean_int(value: Any, default: int, min_value: int, max_value: int) -> int:
    try:
        out = int(float(value))
    except Exception:
        out = default
    return max(min_value, min(max_value, out))


def as_number(value: Any) -> float | None:
    try:
        out = float(value)
    except Exception:
        return None
    if pd.isna(out):
        return None
    return out


def repair_json_object(text: str) -> str:
    raw = str(text or "").strip()
    raw = strip_model_wrappers(raw)
    raw = raw.replace("\n", " ")
    if raw and not raw.startswith("{"):
        raw = "{" + raw
    raw = re.sub(r",\s*$", "", raw)
    raw = re.sub(r",\s*([}\]])", r"\1", raw)
    open_square = raw.count("[") - raw.count("]")
    open_curly = raw.count("{") - raw.count("}")
    if open_square > 0:
        raw += "]" * open_square
    if open_curly > 0:
        raw += "}" * open_curly
    raw = re.sub(r",\s*([}\]])", r"\1", raw)
    raw = re.sub(r",\s*$", "", raw)
    if raw and not raw.endswith("}"):
        raw = raw + "}"
    return raw


def strip_model_wrappers(text: str) -> str:
    raw = str(text or "").strip()
    raw = re.sub(r"^```(?:json)?", "", raw.strip(), flags=re.I).strip()
    raw = re.sub(r"```$", "", raw.strip()).strip()
    raw = re.sub(r"<think>.*?</think>", "", raw, flags=re.S | re.I).strip()
    return raw


def salvage_json_fields(text: str) -> dict[str, Any]:
    raw = str(text or "")
    aspects: list[dict[str, Any]] = []
    item_pattern = re.compile(
        r'"aspect"\s*:\s*"(?P<aspect>[^"]+)"'
        r'.{0,240}?"sentiment"\s*:\s*"(?P<sentiment>[^"]+)"'
        r'.{0,160}?"severity"\s*:\s*(?P<severity>[0-3])'
        r'.{0,160}?"confidence"\s*:\s*(?P<confidence>[0-9.]+)'
        r'(?:.{0,220}?"evidence"\s*:\s*"(?P<evidence>[^"]*)")?',
        flags=re.S,
    )
    for match in item_pattern.finditer(raw):
        aspects.append(
            {
                "aspect": match.group("aspect"),
                "sentiment": match.group("sentiment"),
                "severity": match.group("severity"),
                "confidence": match.group("confidence"),
                "evidence": match.group("evidence") or "",
            }
        )
        if len(aspects) >= 4:
            break
    primary_match = re.search(r'"primary_aspect"\s*:\s*"([^"]+)"', raw)
    summary_match = re.search(r'"summary"\s*:\s*"([^"]*)"', raw)
    return {
        "aspects": aspects,
        "primary_aspect": primary_match.group(1) if primary_match else (aspects[0]["aspect"] if aspects else "unclear"),
        "summary": summary_match.group(1) if summary_match else "",
    }


def clean_json(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: clean_json(v) for k, v in value.items()}
    if isinstance(value, list):
        return [clean_json(v) for v in value]
    if isinstance(value, float) and (np.isnan(value) or np.isinf(value)):
        return None
    if isinstance(value, np.generic):
        return value.item()
    return value
