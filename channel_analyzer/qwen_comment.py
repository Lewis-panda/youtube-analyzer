from __future__ import annotations

import json
import os
import re
from pathlib import Path

import pandas as pd


DEFAULT_MODEL = "Qwen/Qwen3-8B"

SENTIMENT_LABELS = ["negative", "neutral", "positive"]
TARGETS = [
    "creator",
    "guest",
    "video",
    "product",
    "brand",
    "audience",
    "platform",
    "other",
    "unclear",
]
EMOTION_TAGS = [
    "praise",
    "support",
    "criticism",
    "disappointment",
    "anger",
    "question",
    "suggestion",
    "joke",
    "sarcasm",
    "spam",
    "off_topic",
]

OUTPUT_ID_COLS = [
    "comment_id",
    "video_id",
    "author_actor_id",
    "comment_published_at",
    "like_count",
]

SYSTEM_PROMPT = f"""You classify YouTube comment sentiment for social media analytics.
Return one compact JSON object only. No explanation, no markdown.

Allowed sentiment_label values:
{", ".join(SENTIMENT_LABELS)}

JSON schema:
{{
  "sentiment_label": "negative|neutral|positive",
  "score_neg": 0.0,
  "score_neu": 0.0,
  "score_pos": 0.0
}}

Rules:
- Use only the comment text and optional video title context.
- positive means praise, support, excitement, approval, or friendly humor.
- negative means criticism, disappointment, anger, hostility, boycott/退訂 intent, or clear disapproval.
- neutral means factual comments, questions, ambiguous jokes, spam, tags, or unclear/off-topic text.
- If the comment is mixed, choose the dominant tone and lower confidence.
- Do not treat profanity as negative if it is clearly joking or praising.
- Scores should be probabilities and should sum to roughly 1.
- Output only the JSON object with the four schema fields.
"""


def compact_text(text: object, limit: int) -> str:
    text = re.sub(r"\s+", " ", str(text or "")).strip()
    return text[:limit]


def build_user_prompt(row: pd.Series) -> str:
    return (
        f"Video title: {compact_text(row.get('video_title', ''), 80)}\n"
        f"Comment: {compact_text(row.get('text_plain', ''), 280)}\n"
        "Classify this comment."
    )


def parse_json_output(text: str) -> dict:
    match = re.search(r"\{.*?\}", str(text or ""), flags=re.S)
    raw = match.group(0) if match else str(text or "").strip()
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

    scores = {
        "negative": _clean_score(parsed.get("score_neg", parsed.get("neg"))),
        "neutral": _clean_score(parsed.get("score_neu", parsed.get("neu"))),
        "positive": _clean_score(parsed.get("score_pos", parsed.get("pos"))),
    }
    label = _clean_choice(parsed.get("sentiment_label", parsed.get("label")), SENTIMENT_LABELS, "")
    if not label:
        label = max(scores, key=scores.get) if sum(scores.values()) > 0 else "neutral"
    scores = _normalize_scores(scores, label, parse_error)

    target = _clean_choice(parsed.get("target"), TARGETS, "unclear")
    tags = _clean_list(parsed.get("emotion_tags"), EMOTION_TAGS)
    toxicity = _clean_score(parsed.get("toxicity"))
    try:
        confidence = float(parsed.get("confidence", 0.35 if parse_error else 0.7))
    except Exception:
        confidence = 0.35 if parse_error else 0.7
    confidence = min(max(confidence, 0.0), 1.0)

    return {
        "sentiment_label": label,
        "score_neg": scores["negative"],
        "score_neu": scores["neutral"],
        "score_pos": scores["positive"],
        "target": target,
        "emotion_tags": ";".join(tags),
        "toxicity": toxicity,
        "sentiment_confidence": confidence,
        "sentiment_parse_error": parse_error,
        "sentiment_reason": compact_text(parsed.get("reason", ""), 180),
        "sentiment_raw": str(text or "").strip(),
    }


def classify_with_vllm_to_csv(
    comments: pd.DataFrame,
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
    sampling = SamplingParams(max_tokens=96, temperature=0.0)
    return _classify_with_chat_llm(
        comments,
        model_id,
        batch_size,
        llm,
        sampling,
        output_path=output_path,
    )


def _classify_with_chat_llm(
    comments: pd.DataFrame,
    model_id: str,
    batch_size: int,
    llm,
    sampling,
    output_path: Path,
) -> pd.DataFrame:
    parsed_rows: list[dict] = []
    total = len(comments)
    for start in range(0, total, batch_size):
        chunk = comments.iloc[start : start + batch_size]
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
            [
                _output_id_frame(chunk).reset_index(drop=True),
                pd.DataFrame(parsed),
            ],
            axis=1,
        )
        chunk_out["model"] = model_id
        merged = merge_existing_output(output_path, chunk_out)
        merged.to_csv(output_path, index=False)
        print(f"  classified {min(start + batch_size, total):,}/{total:,}", flush=True)

    out = pd.concat(
        [_output_id_frame(comments).reset_index(drop=True), pd.DataFrame(parsed_rows)],
        axis=1,
    )
    out["model"] = model_id
    return out


def merge_existing_output(path: Path, new_rows: pd.DataFrame) -> pd.DataFrame:
    if path.exists() and path.stat().st_size > 0:
        existing = pd.read_csv(path, low_memory=False)
        merged = pd.concat([existing, new_rows], ignore_index=True)
    else:
        merged = new_rows
    return merged.drop_duplicates("comment_id", keep="last")


def repair_existing_output(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, low_memory=False)
    if df.empty or "sentiment_raw" not in df.columns:
        return df
    parsed = pd.DataFrame([parse_json_output(text) for text in df["sentiment_raw"].fillna("")])
    update_cols = [
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
    ]
    for col in update_cols:
        if col in parsed.columns:
            df[col] = parsed[col]
    df.to_csv(path, index=False)
    return df


def select_remaining(
    comments: pd.DataFrame,
    output_path: Path,
    limit: int | None,
) -> pd.DataFrame:
    done: set[str] = set()
    if output_path.exists() and output_path.stat().st_size > 0:
        done = set(
            pd.read_csv(output_path, usecols=["comment_id"], low_memory=False)["comment_id"]
        )
    remaining = comments[~comments["comment_id"].isin(done)].copy()
    if limit is not None:
        remaining = remaining.head(limit).copy()
    return remaining


def _output_id_frame(comments: pd.DataFrame) -> pd.DataFrame:
    out = comments.copy()
    for col in OUTPUT_ID_COLS:
        if col not in out.columns:
            out[col] = None
    return out[OUTPUT_ID_COLS]


def _clean_score(value: object) -> float:
    try:
        score = float(value)
    except Exception:
        return 0.0
    if pd.isna(score):
        return 0.0
    return min(max(score, 0.0), 1.0)


def _normalize_scores(scores: dict[str, float], label: str, parse_error: bool) -> dict[str, float]:
    total = sum(scores.values())
    if total <= 0:
        if parse_error:
            return {"negative": 0.25, "neutral": 0.50, "positive": 0.25}
        base = {"negative": 0.10, "neutral": 0.10, "positive": 0.10}
        base[label] = 0.80
        return base
    return {key: value / total for key, value in scores.items()}


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
