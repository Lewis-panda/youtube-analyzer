from __future__ import annotations

import json
import os
import re
from pathlib import Path

import pandas as pd

from .external_events import normalize_text


DEFAULT_MODEL = "Qwen/Qwen3-8B"

RELEVANCE_TYPES = [
    "direct_channel_discussion",
    "specific_video_discussion",
    "creator_member_discussion",
    "comparison_or_recommendation",
    "indirect_mention",
    "unrelated",
    "spam_or_survey",
]

EVENT_TYPES = [
    "staff_or_host_change",
    "content_quality_criticism",
    "political_or_social_controversy",
    "apology_or_controversy",
    "content_authenticity_question",
    "collaboration_or_guest",
    "specific_video_or_series_discussion",
    "business_or_product",
    "recommendation_general",
    "other",
    "none",
]

STANCES = ["critical", "supportive", "mixed", "neutral", "unclear"]

TARGETS = [
    "channel",
    "creator",
    "staff_or_host",
    "specific_video_or_series",
    "guest",
    "external_person_or_brand",
    "other",
    "unclear",
]

SYSTEM_PROMPT = f"""You label external social posts for YouTube channel event analysis.
Return one compact JSON object only. Use Traditional Chinese in topic_label and reason.

Allowed relevance_type values:
{", ".join(RELEVANCE_TYPES)}

Allowed event_type values:
{", ".join(EVENT_TYPES)}

Allowed stance values:
{", ".join(STANCES)}

Allowed target values:
{", ".join(TARGETS)}

JSON schema:
{{
  "is_relevant": true,
  "relevance_type": "one allowed relevance_type",
  "is_noise": false,
  "is_external_event_candidate": true,
  "event_type": "one allowed event_type",
  "topic_label": "short Traditional Chinese label",
  "stance": "one allowed stance",
  "target": "one allowed target",
  "confidence": 0.0,
  "reason": "short Traditional Chinese reason"
}}

Rules:
- Relevant means the post discusses the channel, its creators/staff, a channel video/series, or a public issue directly tied to them.
- Noise includes surveys, giveaways, generic recommendation lists, or posts where the channel is only an incidental example.
- Mark is_external_event_candidate true only if the post can plausibly define or contribute to an external discussion event.
- Do not infer facts beyond the post text. If unclear, lower confidence and use unclear/other.
- Output only the JSON object.
"""


def compact_text(text: object, limit: int) -> str:
    return re.sub(r"\s+", " ", str(text or "").strip())[:limit]


def build_user_prompt(row: pd.Series, aliases: list[str]) -> str:
    alias_text = ", ".join(aliases[:12])
    return (
        f"Channel aliases: {alias_text}\n"
        f"Source: {row.get('source', '')}\n"
        f"Forum/board: {row.get('board_or_forum', '')}\n"
        f"Date: {row.get('date', '')}\n"
        f"Title: {compact_text(row.get('title', ''), 220)}\n"
        f"Post text: {compact_text(row.get('text', ''), 1800)}\n"
        "Label this external post."
    )


def parse_json_output(text: object) -> dict:
    raw_text = str(text or "").strip()
    match = re.search(r"\{.*?\}", raw_text, flags=re.S)
    raw = match.group(0) if match else raw_text
    parse_error = False
    try:
        parsed = json.loads(raw)
    except Exception:
        repaired = repair_json_object(raw)
        try:
            parsed = json.loads(repaired)
        except Exception:
            parsed = {}
            parse_error = True

    is_relevant = clean_bool(parsed.get("is_relevant"), default=False)
    is_noise = clean_bool(parsed.get("is_noise"), default=False)
    is_candidate = clean_bool(parsed.get("is_external_event_candidate"), default=False)
    relevance_type = clean_choice(parsed.get("relevance_type"), RELEVANCE_TYPES, "unrelated")
    event_type = clean_choice(parsed.get("event_type"), EVENT_TYPES, "none")
    stance = clean_choice(parsed.get("stance"), STANCES, "unclear")
    target = clean_choice(parsed.get("target"), TARGETS, "unclear")
    try:
        confidence = float(parsed.get("confidence", 0.35 if parse_error else 0.7))
    except Exception:
        confidence = 0.35 if parse_error else 0.7
    confidence = min(max(confidence, 0.0), 1.0)
    if is_noise:
        is_relevant = False
        is_candidate = False
    return {
        "is_relevant": is_relevant,
        "relevance_type": relevance_type,
        "is_noise": is_noise,
        "is_external_event_candidate": is_candidate,
        "event_type": event_type,
        "topic_label": compact_text(parsed.get("topic_label", ""), 80) or event_type,
        "stance": stance,
        "target": target,
        "semantic_confidence": confidence,
        "semantic_parse_error": parse_error,
        "semantic_reason": compact_text(parsed.get("reason", ""), 220),
        "semantic_raw": raw_text,
    }


def classify_with_vllm_to_csv(
    posts: pd.DataFrame,
    output_path: Path,
    aliases: list[str],
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
    sampling = SamplingParams(max_tokens=256, temperature=0.0)
    parsed_rows = []
    total = len(posts)
    for start in range(0, total, batch_size):
        chunk = posts.iloc[start : start + batch_size]
        messages = [
            [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": build_user_prompt(row, aliases)},
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
            [post_id_frame(chunk).reset_index(drop=True), pd.DataFrame(parsed)],
            axis=1,
        )
        chunk_out["model"] = model_id
        merged = merge_existing_output(output_path, chunk_out)
        merged.to_csv(output_path, index=False)
        print(f"  external posts classified {min(start + batch_size, total):,}/{total:,}", flush=True)

    out = pd.concat([post_id_frame(posts).reset_index(drop=True), pd.DataFrame(parsed_rows)], axis=1)
    out["model"] = model_id
    return out


def post_id_frame(posts: pd.DataFrame) -> pd.DataFrame:
    cols = [
        "post_uid",
        "source",
        "post_id",
        "date",
        "title",
        "url",
        "board_or_forum",
        "keyword",
        "engagement",
    ]
    return posts[[col for col in cols if col in posts.columns]].copy()


def merge_existing_output(path: Path, new_rows: pd.DataFrame) -> pd.DataFrame:
    if path.exists() and path.stat().st_size > 0:
        existing = pd.read_csv(path, low_memory=False)
        merged = pd.concat([existing, new_rows], ignore_index=True)
    else:
        merged = new_rows
    return merged.drop_duplicates("post_uid", keep="last")


def repair_existing_output(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, low_memory=False)
    if df.empty or "semantic_raw" not in df.columns:
        return df
    parsed = pd.DataFrame([parse_json_output(text) for text in df["semantic_raw"].fillna("")])
    for col in parsed.columns:
        df[col] = parsed[col]
    df.to_csv(path, index=False)
    return df


def select_remaining(posts: pd.DataFrame, output_path: Path, limit: int | None) -> pd.DataFrame:
    done: set[str] = set()
    if output_path.exists() and output_path.stat().st_size > 0:
        existing = pd.read_csv(output_path, usecols=["post_uid"], low_memory=False)
        done = set(existing["post_uid"].astype(str))
    remaining = posts[~posts["post_uid"].astype(str).isin(done)].copy()
    if limit is not None:
        remaining = remaining.head(limit).copy()
    return remaining


def broad_prefilter(posts: pd.DataFrame, aliases: list[str]) -> pd.DataFrame:
    if not aliases:
        return posts.copy()
    normalized_aliases = [normalize_text(alias) for alias in aliases if normalize_text(alias)]
    if not normalized_aliases:
        return posts.copy()
    text = (
        posts["title"].fillna("").astype(str)
        + "\n"
        + posts["keyword"].fillna("").astype(str)
        + "\n"
        + posts["text"].fillna("").astype(str)
    ).map(normalize_text)
    mask = text.map(lambda value: any(alias in value for alias in normalized_aliases))
    return posts[mask].copy()


def clean_choice(value: object, allowed: list[str], default: str) -> str:
    text = str(value or default).strip()
    return text if text in allowed else default


def clean_bool(value: object, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    text = str(value).strip().lower()
    if text in {"true", "1", "yes", "y"}:
        return True
    if text in {"false", "0", "no", "n"}:
        return False
    return default


def repair_json_object(raw: str) -> str:
    text = str(raw or "").strip()
    if not text:
        return text
    if not text.startswith("{"):
        start = text.find("{")
        if start >= 0:
            text = text[start:]
    if not text.startswith("{"):
        return text
    base = re.sub(r'(?<=\d)"(?=\s*[,}\]])', "", text.rstrip().rstrip(","))
    candidates = [base if base.endswith("}") else f"{base}"]
    if not candidates[0].endswith("}"):
        candidates[0] = f"{candidates[0]}}}"
    for idx in reversed(top_level_comma_positions(base)):
        candidates.append(f"{base[:idx].rstrip()}}}")
    for candidate in candidates:
        try:
            json.loads(candidate)
            return candidate
        except Exception:
            continue
    return candidates[0]


def top_level_comma_positions(text: str) -> list[int]:
    positions: list[int] = []
    depth = 0
    in_string = False
    escaped = False
    for index, char in enumerate(text):
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char in "{[":
            depth += 1
        elif char in "}]":
            depth = max(depth - 1, 0)
        elif char == "," and depth == 1:
            positions.append(index)
    return positions
