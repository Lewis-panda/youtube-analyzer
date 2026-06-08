from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB_PATH = ROOT.parent / "SharedData" / "state" / "yt_graph.sqlite3"


@dataclass(frozen=True)
class AnalysisConfig:
    min_actor_videos: int = 2
    min_co_videos: int = 3
    high_activity_min_videos: int = 16
    mid_activity_min_videos: int = 6
    continuity_windows: int = 4
    continuity_window_options: str = "3,4,6,8"
    rolling_window_videos: int = 50
    rolling_horizon_videos: int = 50
    rolling_step_videos: int = 25
    top_bridge_actors: int = 50
    top_network_actors: int = 200
    betweenness_sample_size: int = 128
    community_algorithm: str = "auto"
    min_video_commenters: int = 10
    min_shared_video_commenters: int = 5
    top_video_link_opportunities: int = 100
    max_video_link_candidate_pairs: int = 200_000


@dataclass(frozen=True)
class OutputConfig:
    run_slug: str | None = None


@dataclass(frozen=True)
class ExternalAnalysisConfig:
    enabled: bool = False
    sources_dir: Path | None = None
    sources: tuple[str, ...] = ("ptt",)
    channel_aliases: tuple[str, ...] = ()
    require_alias_match: bool = False
    semantic_labels_path: Path | None = None
    min_daily_posts: int = 2
    min_external_engagement: int = 10
    merge_gap_days: int = 3
    merge_cross_topic: bool = False
    baseline_days: int = 90
    pre_days: int = 28
    post_days: int = 28
    min_event_posts: int = 1


@dataclass(frozen=True)
class AnalyzerConfig:
    project_name: str
    channel_id: str | None
    channel_url: str | None
    channel_handle: str | None
    date_start: str | None
    date_end: str | None
    include_replies: bool
    exclude_shorts: bool
    short_threshold_seconds: int
    db_path: Path
    analysis: AnalysisConfig
    outputs: OutputConfig
    external_analysis: ExternalAnalysisConfig


def load_config(path: Path) -> AnalyzerConfig:
    data = _load_mapping(path)
    analysis = data.get("analysis") or {}
    outputs = data.get("outputs") or {}
    external = data.get("external_analysis") or {}
    return AnalyzerConfig(
        project_name=str(data.get("project_name") or "Channel Community Analyzer"),
        channel_id=_optional_str(data.get("channel_id")),
        channel_url=_optional_str(data.get("channel_url")),
        channel_handle=_optional_str(data.get("channel_handle")),
        date_start=_optional_str(data.get("date_start")),
        date_end=_optional_str(data.get("date_end")),
        include_replies=bool(data.get("include_replies", False)),
        exclude_shorts=bool(data.get("exclude_shorts", True)),
        short_threshold_seconds=int(data.get("short_threshold_seconds", 180)),
        db_path=Path(data.get("db_path") or DEFAULT_DB_PATH).expanduser().resolve(),
        analysis=AnalysisConfig(
            min_actor_videos=int(analysis.get("min_actor_videos", 2)),
            min_co_videos=int(analysis.get("min_co_videos", 3)),
            high_activity_min_videos=int(analysis.get("high_activity_min_videos", 16)),
            mid_activity_min_videos=int(analysis.get("mid_activity_min_videos", 6)),
            continuity_windows=int(analysis.get("continuity_windows", 4)),
            continuity_window_options=str(
                analysis.get("continuity_window_options", "3,4,6,8")
            ),
            rolling_window_videos=int(analysis.get("rolling_window_videos", 50)),
            rolling_horizon_videos=int(analysis.get("rolling_horizon_videos", 50)),
            rolling_step_videos=int(analysis.get("rolling_step_videos", 25)),
            top_bridge_actors=int(analysis.get("top_bridge_actors", 50)),
            top_network_actors=int(analysis.get("top_network_actors", 200)),
            betweenness_sample_size=int(
                analysis.get("betweenness_sample_size", 128)
            ),
            community_algorithm=str(analysis.get("community_algorithm", "auto")),
            min_video_commenters=int(analysis.get("min_video_commenters", 10)),
            min_shared_video_commenters=int(
                analysis.get("min_shared_video_commenters", 5)
            ),
            top_video_link_opportunities=int(
                analysis.get("top_video_link_opportunities", 100)
            ),
            max_video_link_candidate_pairs=int(
                analysis.get("max_video_link_candidate_pairs", 200_000)
            ),
        ),
        outputs=OutputConfig(run_slug=_optional_str(outputs.get("run_slug"))),
        external_analysis=ExternalAnalysisConfig(
            enabled=bool(external.get("enabled", False)),
            sources_dir=_optional_path(external.get("sources_dir")),
            sources=tuple(_external_source_list(external.get("sources", "ptt"))),
            channel_aliases=tuple(_str_list(external.get("channel_aliases"))),
            require_alias_match=bool(external.get("require_alias_match", False)),
            semantic_labels_path=_optional_path(external.get("semantic_labels_path")),
            min_daily_posts=int(external.get("min_daily_posts", 2)),
            min_external_engagement=int(external.get("min_external_engagement", 10)),
            merge_gap_days=int(external.get("merge_gap_days", 3)),
            merge_cross_topic=bool(external.get("merge_cross_topic", False)),
            baseline_days=int(external.get("baseline_days", 90)),
            pre_days=int(external.get("pre_days", 28)),
            post_days=int(external.get("post_days", 28)),
            min_event_posts=int(external.get("min_event_posts", 1)),
        ),
    )


def output_slug(config: AnalyzerConfig, channel_title: str | None = None) -> str:
    if config.outputs.run_slug:
        return slugify(config.outputs.run_slug)
    if channel_title:
        return slugify(channel_title)
    if config.channel_handle:
        return slugify(config.channel_handle)
    if config.channel_id:
        return slugify(config.channel_id)
    return "channel_run"


def slugify(value: str) -> str:
    raw = value.strip().lower().lstrip("@")
    raw = re.sub(r"[^a-z0-9]+", "-", raw)
    raw = raw.strip("-")
    return raw or "channel"


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() in {"none", "null"}:
        return None
    return text


def _optional_path(value: Any) -> Path | None:
    text = _optional_str(value)
    if text is None:
        return None
    path = Path(text).expanduser()
    if not path.is_absolute():
        path = ROOT / path
    return path.resolve()


def _str_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return [str(item).strip() for item in value if str(item).strip()]
    text = str(value).strip()
    if not text:
        return []
    return [item.strip() for item in re.split(r"[;,]", text) if item.strip()]


def _external_source_list(value: Any) -> list[str]:
    sources = [item.lower() for item in _str_list(value)]
    allowed = {"ptt", "dcard"}
    invalid = sorted(set(sources) - allowed)
    if invalid:
        raise RuntimeError(
            "Unsupported external_analysis.sources value(s): "
            + ", ".join(invalid)
            + ". Supported values: ptt, dcard."
        )
    return [source for source in sources if source in allowed]


def _load_mapping(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    try:
        import yaml  # type: ignore

        loaded = yaml.safe_load(text)
        if not isinstance(loaded, dict):
            raise RuntimeError(f"Config must be a mapping: {path}")
        return loaded
    except ModuleNotFoundError:
        return _parse_minimal_yaml(text)


def _parse_minimal_yaml(text: str) -> dict[str, Any]:
    """Small YAML subset parser for this project's example config.

    Supports top-level scalar keys and one-level nested mappings with two-space
    indentation. Use PyYAML for anything more complex.
    """
    root: dict[str, Any] = {}
    current: dict[str, Any] | None = None
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].rstrip()
        if not line:
            continue
        if not raw.startswith(" "):
            key, value = _split_key_value(line)
            if value == "":
                current = {}
                root[key] = current
            else:
                current = None
                root[key] = _parse_scalar(value)
            continue
        if current is None:
            raise RuntimeError(f"Unsupported config indentation: {raw}")
        key, value = _split_key_value(line.strip())
        current[key] = _parse_scalar(value)
    return root


def _split_key_value(line: str) -> tuple[str, str]:
    if ":" not in line:
        raise RuntimeError(f"Invalid config line: {line}")
    key, value = line.split(":", 1)
    return key.strip(), value.strip()


def _parse_scalar(value: str) -> Any:
    if value.lower() in {"null", "none"}:
        return None
    if value.lower() == "true":
        return True
    if value.lower() == "false":
        return False
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    try:
        return int(value)
    except ValueError:
        return value
