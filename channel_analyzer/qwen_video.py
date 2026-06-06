from __future__ import annotations

import json
import os
import re
from pathlib import Path

import pandas as pd

from .themes import THEME_LABELS


DEFAULT_MODEL = "Qwen/Qwen3-8B"

FORMATS = [
    "food_review",
    "business_update",
    "car_review",
    "travel_vlog",
    "city_review",
    "challenge_series",
    "guest_interview",
    "personal_story",
    "controversy_response",
    "product_review",
    "education_explainer",
    "unclear",
]

SETTINGS = [
    "taiwan",
    "usa",
    "japan",
    "korea",
    "china_hk_macau",
    "southeast_asia",
    "europe",
    "multiple",
    "online",
    "unknown",
]

AUDIENCE_INTENTS = [
    "food_discovery",
    "business_learning",
    "luxury_lifestyle",
    "local_life",
    "travel_discovery",
    "controversy_update",
    "entertainment",
    "self_improvement",
    "fan_relationship",
    "unknown",
]

SYSTEM_PROMPT = f"""You classify YouTube videos for social media network analysis.
Return one compact JSON object only. Use Traditional Chinese in reason.

Allowed theme labels:
{", ".join(THEME_LABELS)}

Allowed format values:
{", ".join(FORMATS)}

Allowed setting values:
{", ".join(SETTINGS)}

Allowed audience_intent values:
{", ".join(AUDIENCE_INTENTS)}

JSON schema:
{{
  "primary_theme": "one allowed theme",
  "secondary_themes": ["zero or more allowed themes"],
  "format": "one allowed format",
  "setting": "one allowed setting",
  "audience_intent": "one allowed audience intent",
  "entities": ["important people, brands, places, or products"],
  "confidence": 0.0,
  "reason": "short reason in Traditional Chinese"
}}

Rules:
- Use title, description, and tags together.
- Prefer the video's actual topic over creator identity.
- Use controversy_response only when the video itself mainly responds to a controversy, accusation, apology, or public dispute.
- Use business_brand when the video is about operating, investing in, expanding, or marketing a business/brand.
- Use automotive_luxury for cars, supercars, luxury ownership, watches, high-end gear, or luxury consumption.
- Use food_culture for restaurant, street food, cooking, food review, or food-business content.
- If no controlled theme clearly fits, use other.
"""


def compact_text(text: object, limit: int) -> str:
    text = re.sub(r"\s+", " ", str(text or "")).strip()
    return text[:limit]


def parse_tags(raw: object) -> str:
    if not raw:
        return ""
    try:
        tags = json.loads(str(raw))
    except Exception:
        return compact_text(raw, 320)
    if not isinstance(tags, list):
        return compact_text(raw, 320)
    return ", ".join(str(tag) for tag in tags[:32])


def build_user_prompt(row: pd.Series) -> str:
    tags = parse_tags(row.get("tags_json", ""))
    return (
        f"Video title: {row.get('title', '')}\n"
        f"Tags: {compact_text(tags, 420)}\n"
        f"Description: {compact_text(row.get('description', ''), 1200)}\n"
        "Classify this video."
    )


def parse_json_output(text: str) -> dict:
    match = re.search(r"\{.*?\}", text, flags=re.S)
    raw = match.group(0) if match else text.strip()
    parse_error = False
    try:
        parsed = json.loads(raw)
    except Exception:
        repaired = _repair_json_object(raw)
        try:
            parsed = json.loads(repaired)
        except Exception:
            parsed = {}
            parse_error = True

    primary = _clean_choice(parsed.get("primary_theme"), THEME_LABELS, "other")
    secondaries = _clean_list(parsed.get("secondary_themes"), THEME_LABELS)
    secondaries = [label for label in secondaries if label != primary and label != "other"]
    fmt = _clean_choice(parsed.get("format"), FORMATS, "unclear")
    setting = _clean_choice(parsed.get("setting"), SETTINGS, "unknown")
    intent = _clean_choice(parsed.get("audience_intent"), AUDIENCE_INTENTS, "unknown")
    entities = _clean_text_list(parsed.get("entities"), 8)
    try:
        confidence = float(parsed.get("confidence", 0.35 if parse_error else 0.7))
    except Exception:
        confidence = 0.35 if parse_error else 0.7
    confidence = min(max(confidence, 0.0), 1.0)

    labels = [primary] + secondaries
    labels = [label for label in labels if label and label != "other"]
    theme_labels = ";".join(dict.fromkeys(labels)) or "other"

    return {
        "primary_theme": primary,
        "secondary_themes": ";".join(secondaries),
        "theme_labels": theme_labels,
        "format": fmt,
        "setting": setting,
        "audience_intent": intent,
        "entities": ";".join(entities),
        "theme_confidence": confidence,
        "theme_parse_error": parse_error,
        "theme_reason": compact_text(parsed.get("reason", ""), 220),
        "theme_raw": text.strip(),
    }


def classify_with_vllm(
    videos: pd.DataFrame,
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
    sampling = SamplingParams(max_tokens=320, temperature=0.0)
    return _classify_with_chat_llm(videos, model_id, batch_size, llm, sampling)


def classify_with_vllm_to_csv(
    videos: pd.DataFrame,
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
    sampling = SamplingParams(max_tokens=320, temperature=0.0)
    return _classify_with_chat_llm(
        videos,
        model_id,
        batch_size,
        llm,
        sampling,
        output_path=output_path,
    )


def _classify_with_chat_llm(
    videos: pd.DataFrame,
    model_id: str,
    batch_size: int,
    llm,
    sampling,
    output_path: Path | None = None,
) -> pd.DataFrame:
    parsed_rows: list[dict] = []
    total = len(videos)
    for start in range(0, total, batch_size):
        chunk = videos.iloc[start : start + batch_size]
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
        if output_path is not None:
            chunk_out = pd.concat(
                [chunk.reset_index(drop=True), pd.DataFrame(parsed)],
                axis=1,
            )
            chunk_out["model"] = model_id
            merged = merge_existing_output(output_path, chunk_out)
            merged.to_csv(output_path, index=False)
        print(f"  classified {min(start + batch_size, total):,}/{total:,}", flush=True)

    out = pd.concat([videos.reset_index(drop=True), pd.DataFrame(parsed_rows)], axis=1)
    out["model"] = model_id
    return out


def merge_existing_output(path: Path, new_rows: pd.DataFrame) -> pd.DataFrame:
    if path.exists() and path.stat().st_size > 0:
        existing = pd.read_csv(path, low_memory=False)
        merged = pd.concat([existing, new_rows], ignore_index=True)
    else:
        merged = new_rows
    return merged.drop_duplicates("video_id", keep="last")


def repair_existing_output(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, low_memory=False)
    if df.empty or "theme_raw" not in df.columns:
        return df
    parsed = pd.DataFrame([parse_json_output(text) for text in df["theme_raw"].fillna("")])
    update_cols = [
        "primary_theme",
        "secondary_themes",
        "theme_labels",
        "format",
        "setting",
        "audience_intent",
        "entities",
        "theme_confidence",
        "theme_parse_error",
        "theme_reason",
        "theme_raw",
    ]
    for col in update_cols:
        if col in parsed.columns:
            df[col] = parsed[col]
    df.to_csv(path, index=False)
    return df


def select_remaining(videos: pd.DataFrame, output_path: Path, limit: int | None) -> pd.DataFrame:
    done: set[str] = set()
    if output_path.exists() and output_path.stat().st_size > 0:
        done = set(pd.read_csv(output_path, usecols=["video_id"], low_memory=False)["video_id"])
    remaining = videos[~videos["video_id"].isin(done)].copy()
    if limit is not None:
        remaining = remaining.head(limit).copy()
    return remaining


def _clean_choice(value: object, allowed: list[str], default: str) -> str:
    text = str(value or default).strip()
    return text if text in allowed else default


def _clean_list(value: object, allowed: list[str]) -> list[str]:
    if isinstance(value, list):
        raw = value
    else:
        raw = re.split(r"[;,|]", str(value or ""))
    labels = [_clean_choice(item, allowed, "") for item in raw]
    return [label for label in dict.fromkeys(labels) if label]


def _clean_text_list(value: object, limit: int) -> list[str]:
    if isinstance(value, list):
        raw = value
    else:
        raw = re.split(r"[;,|]", str(value or ""))
    out = [compact_text(item, 48) for item in raw]
    return [item for item in out if item][:limit]


def _repair_json_object(raw: str) -> str:
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

    for idx in reversed(_top_level_comma_positions(base)):
        candidates.append(f"{base[:idx].rstrip()}}}")

    for candidate in candidates:
        try:
            json.loads(candidate)
            return candidate
        except Exception:
            continue
    return candidates[0]


def _top_level_comma_positions(text: str) -> list[int]:
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
