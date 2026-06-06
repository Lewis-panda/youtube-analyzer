# AGENTS.md

## Scope

This file applies to `ChannelCommunityAnalyzer/`.

Keep guidance concise and task-oriented. If a subdirectory needs different
rules, add a nested `AGENTS.md` there rather than expanding this file.

## Project

Channel Community Analyzer is an end-to-end Social Media Analytics tool for
YouTube channels.

Goal:

> Given a YouTube channel already present in the shared SQLite database,
> generate an interpretable commenter community health report using video
> metadata, title/description/tags, comments, sentiment-ready text, and
> commenter/video network analysis.

This project is generic. Do not bake in DoDoMen, Ian/Eric/Collab, Jeannie, or
split-specific assumptions. DoDoMen belongs only as a demo or optional appendix.

Current product direction as of 2026-06-06:

> Build a tool-oriented channel analyzer with a read-only Web dashboard demo.
> The real pipeline can take 2-3 hours and remains available through CLI /
> runner tasks, but the presentation demo should read completed run artifacts
> and must not trigger real crawling, Qwen inference, or fake progress bars.

The Web dashboard should show completed channel examples, baseline comparisons,
tables, figures, and LLM-generated owner-facing reports. It should include
standard YouTube analytics views where useful, but the project differentiation
is commenter community analysis, social/network structure, reply conflict,
semantic sentiment, external PTT event impact, and dynamic baseline percentile
context.

Read `docs/product_direction_and_repo_reorg_20260606.md` before any major repo
cleanup, dashboard work, baseline changes, or case-study changes.

Benchmark cohort scope:

> The single-channel report remains the core product, but the project should
> also support a cross-channel comparison layer. Run a benchmark cohort of
> Taiwan creator/media channels, build reference distributions for comparable
> metrics, and use cohort averages, medians, ranges, and percentiles to
> interpret whether one channel's values are high, low, or typical.

Use the benchmark cohort to contextualize metrics that are hard to evaluate in
isolation, such as core-audience share, repeat-commenter retention, community
concentration, bridge structure, sentiment rates, negative hotspots, and
reply-thread conflict. Keep this layer generic: benchmark comparisons should be
derived from completed channel runs, not from hand-coded expectations about any
specific channel.

## Start Here

For a fresh context reset, read in this order:

1. `AGENTS.md`: project rules, current state, and next todo queue.
2. `docs/product_direction_and_repo_reorg_20260606.md`: current product
   direction, Web demo constraints, repo target structure, baseline policy, and
   DoDoMen case-study boundary.
3. `docs/repo_reorg_manifest_20260606.md`: what was moved to
   `baseline_runs/`, `case_studies/`, and `legacy/`, plus compatibility symlink
   notes.
4. `docs/dashboard_data_contract.md`: generated dashboard JSON schema,
   available tabs, and read-only demo constraints.
5. `docs/data_reproducibility_contract.md`: collaboration rules for GitHub,
   Google Drive artifacts, read-only frontend behavior, and localhost-first
   deployment.
6. `docs/project_update_for_teammates_MyVersion.md`: concise project story for
   teammates and presentation framing.
7. `prompt.md`: LLM prompt for turning statistical outputs into channel-owner
   conclusion and detailed reports.
8. `scripts/benchmark_queue.py status --limit 10`: current crawler queue state.
9. `runs/*/run_summary.json` and `baseline_runs/*/run_summary.json` if present:
   active and completed Qwen/report runs.
10. `docs/runtime_benchmarks.csv`: calibrated local runtime examples.

- `README.md`: user-facing setup, run commands, output descriptions.
- `docs/data_reproducibility_contract.md`: required collaboration contract.
  The frontend is read-only, metric values must come from analyzer/builder
  outputs, large artifacts are restored from Google Drive, and cloned repos
  should run through localhost. Public IP/router-forwarding settings are
  machine-local and must not be hard-coded into frontend assets or shared data.
  Do not hand-edit downloaded or generated data artifacts to change results.
  Collaboration should change frontend presentation, statistical computation
  code, figure/report generation code, or docs. If data changes are needed,
  regenerate upstream artifacts and update the Drive manifest explicitly.
  In the normal GitHub collaboration workflow, do not run crawler or Qwen
  semantic stages; use the restored Google Drive artifacts as inputs.
- `prompt.md`: required prompt/reference when using statistical outputs,
  benchmark tables, report JSON, or CSV tables to write conclusion/detailed
  channel-owner reports. Do not generate owner-facing analysis from metric
  percentiles alone.
- `config.example.yaml`: copy/edit this for a channel run.
- `channel_analyzer/`: Python package for config, data access, analyses, and
  report generation.
- `scripts/run_pipeline.py`: main end-to-end CLI entry point.
- `scripts/run_analyzer.py`: final-report stage used by the pipeline.
- `scripts/check_run_complete.py`: verifies DB scope, Qwen CSV completion,
  parse errors, and report files.
- `legacy/qwen_offload/`, `legacy/notebooks/`, and `legacy/qwen_jobs/`:
  older Colab/teammate Qwen offload materials. Current product direction is
  local Qwen by default; offload is preserved but not core.
- `case_studies/dodomen/scripts/import_researcha_dodomen_qwen.py`: one-off
  DoDoMen migration helper that converts existing `../ResearchA/` Qwen outputs
  into the generic run format before resuming only missing rows.
- `scripts/build_benchmark_baseline.py`: aggregates completed cohort reports
  into `baseline_runs/benchmark_baseline/` membership, channel metrics, metric
  distributions, percentile ranks, and optional target-vs-baseline comparison
  via `--target-run-dir`.
- `scripts/build_dashboard_index.py`: builds read-only Web demo artifacts under
  `dashboard_data/` from completed runs and baseline outputs. It must not crawl,
  run Qwen, or simulate fake progress.
- `dashboard/server.py`: dependency-light read-only dashboard server. Use
  `python3 dashboard/server.py --host 127.0.0.1 --port 8765` for local viewing
  or `--host 0.0.0.0` for LAN/router-forwarded access. Binding to `0.0.0.0`
  does not itself open public Internet access; router/firewall forwarding or a
  tunnel is still required.
- `docs/runtime_benchmarks.csv`: measured local runtime data for estimator
  calibration.
- `docs/tw_under_1_5m_Update.csv`: user-verified Taiwan benchmark cohort list.
- `docs/tw_benchmark_verified_full_channel_urls.txt`: current crawler seed file
  generated from rows marked `O` in `docs/tw_under_1_5m_Update.csv`.
- `docs/tw_under_1_5m_benchmark_candidates.csv`: older Taiwan benchmark
  candidate list; keep as input provenance, not the active seed.
- `runs/`: generated per-channel outputs.
- `dashboard_data/`: generated read-only dashboard JSON artifacts. Rebuild with
  `python3 scripts/build_dashboard_index.py` after baseline runs or reports
  change.
- `baseline_runs/`: target location for completed full runs used by dynamic
  baseline distributions and dashboard examples. Do not delete completed run
  artifacts; move/archive them only after preserving baseline readability.
- `case_studies/dodomen/`: target location for DoDoMen-only video labels and
  appendix material. Generic analyzer code must not depend on Ian/Eric/Collab
  labels.
- `legacy/`: target location for old logs, exports, qwen job zips, notebooks,
  research-only experiments, and one-off artifacts that are not part of the
  core product. Move first; delete only after explicit approval.
- `../youtube_graph_ingest/`: local shared crawler and SQLite normalization
  pipeline. Remote crawler repository:
  `https://github.com/Lewis-panda/youtube-graph.git`.
- `../SharedData/state/yt_graph.sqlite3`: shared normalized YouTube database.
- `../ResearchA/`: DoDoMen case study outputs and optional appendix material.

## Current State Snapshot

As of 2026-05-13 17:30 Asia/Taipei:

- Local Qwen environment: `micromamba run -n llm-opt ...`; local model is
  `Qwen/Qwen3-8B` via vLLM.
- Active benchmark seed: `docs/tw_benchmark_verified_full_channel_urls.txt`.
  It contains 48 verified channels from `docs/tw_under_1_5m_Update.csv`.
  Rows marked `X` are excluded: `TW023 柴米夫妻`,
  `TW038 王伯達觀點`, and `TW045 Superpie 超級派`.
- `scripts/run_benchmark_crawl_queue.sh` defaults to the full verified seed
  file, `PUBLISHED_AFTER=2023-01-01`, and non-Shorts crawling.
- The full benchmark crawler last paused because YouTube API quota was
  exhausted. Log: `logs/benchmark_crawl_full_20260513.log`.
- No benchmark crawler tmux session is currently expected to be running. If
  quota is available, resume with:

```bash
tmux new-session -d -s benchmark_crawl_full_$(date +%Y%m%d) \
  'cd /home/lewis/NTU_Course/SMA/Youtube-Network/ChannelCommunityAnalyzer && SKIP_SEED=1 RESET_STALE_RESOLVING=1 ./scripts/run_benchmark_crawl_queue.sh > logs/benchmark_crawl_full_$(date +%Y%m%d).log 2>&1'
```

Last known crawler queue state:

```text
failed: 5
graphed: 5,242
queued: 9,491
skipped: 61
next queued id: 5698
next queued video: https://www.youtube.com/watch?v=yHNDrLRUhiw
```

For the 48 verified benchmark channels, using the user's definitions:

```text
done = crawled + full Qwen/report complete
undone = crawled but not full Qwen/report complete
not crawled yet = still queued

done videos: 1,046
undone videos: 1,907
not crawled yet: 9,491
failed/skipped queue rows: 66
```

Completed full Qwen/report runs overall:

| Run | Channel | Videos | All-comment sentiment rows | Notes |
| :-- | :-- | --: | --: | :-- |
| `runs/dodomen-generic-demo/` | DoDoMen | 351 | 303,094 | demo/appendix, not cohort by default; refreshed 2026-06-03 |
| `runs/xilanceylan-full/` | 錫蘭Ceylan | 112 | 250,589 | verified benchmark cohort |
| `runs/onion-man-full/` | Onion Man | 118 | 109,733 | verified benchmark cohort |
| `runs/walkerdad-full/` | 喪屍老爸 | 473 | 88,414 | verified benchmark cohort |
| `runs/beautywu-full/` | 見習網美小吳 | 343 | 419,394 | verified benchmark cohort |
| `runs/kedaibiao-full/` | 課代表立正 | 526 | 22,118 | extra completed run |
| `runs/superpie1111-full/` | Superpie | 602 | 100,171 | extra completed run; excluded from current verified seed |

Crawled benchmark channels still needing full Qwen/report configs or runs:

```text
阿翰po影片: 43 videos
反正我很閒: 21 videos
哈哈台: 168 videos
上班不要看 NSFW: 152 videos
古娃娃WawaKu: 11 videos
阿慶師: 335 videos
欸你這週要幹嘛: 188 videos
Taiwan Bar: 111 videos
小施汽車生活頻道: 668 videos
蒼藍鴿的醫學天地: 210 videos
```

Update as of 2026-05-17 01:30 Asia/Taipei:

- `runs/beautywu-full/` was refreshed after importing the Colab gap-fill rows:
  344 videos, 419,485 all-comment Qwen sentiment rows, 0 parse errors, and
  complete base/supplement reports.
- Before adding new configs, all existing `configs/*.full.yaml` were Qwen
  complete; the now-legacy Qwen offload exporter dry run selected 0 existing
  configs for export.
- Added full configs for 23 crawled benchmark channels that had DB data but no
  analyzer config yet: `crowndu`, `alisasa-official`, `caizha`, `annie72127`,
  `anjouclever103`, `tolocat`, `louislee0602`, `sandymandy-official`,
  `hellocatie`, `lioumonn`, `miihuang711`, `chef-james-tw`, `dreamchefhome`,
  `goldfishbrain`, `rifat`, `blairechen`, `elephantgogo`, `liketaitai`,
  `panscitw`, `twreporterorg`, `bailingguo`, `mindiworldnews`, and
  `sscarlife`.
- Created 9 historical Colab handoff zips, now archived under `legacy/qwen_jobs/`:
  `qwen_batch_20260517_01_bailingguo.zip` (292,525 comments),
  `qwen_batch_20260517_02_sscarlife.zip` (181,184),
  `qwen_batch_20260517_03_panscitw.zip` (161,786),
  `qwen_batch_20260517_04_alisasa.zip` (83,629),
  `qwen_batch_20260517_05_food_travel.zip` (115,247),
  `qwen_batch_20260517_06_mixed_mid_a.zip` (118,115),
  `qwen_batch_20260517_07_mixed_mid_b.zip` (100,718),
  `qwen_batch_20260517_08_mixed_small_a.zip` (84,557), and
  `qwen_batch_20260517_09_mixed_small_b.zip` (39,417).
- Added `--comment-shard-count` / `--comment-shard-index` to the now-legacy
  `legacy/qwen_offload/scripts/export_qwen_job.py` for parallel Colab sharding. Also created
  recommended shard zips for the largest jobs: `bailingguo` 4 shards
  (~73k comments each), `sscarlife` 3 shards (~60k each), `panscitw` 3 shards
  (~54k each), and `alisasa` 2 shards (~42k each). Prefer these shard zips over
  the corresponding single-channel big zips on free Colab runtimes.
- Latest crawler queue status: failed 7, graphed 9,178, queued 5,553, skipped
  61; next queued video id is `B3IE8L2ZlWk`. No benchmark crawler tmux session
  was observed in `tmux ls` during this update.

Update as of 2026-06-03 22:20 Asia/Taipei:

- Existing `configs/*.full.yaml` inventory: 50/50 configs are complete under
  the current DB scope, totaling 13,569 videos and 3,168,893 all-comment Qwen
  sentiment rows. Inventory file:
  `runs/baseline_completion_inventory.csv`.
- Verified benchmark cohort comparison: 48 `O` rows from
  `docs/tw_under_1_5m_Update.csv`, 48 matched full configs, 0 missing configs.
  Extra completed configs outside the verified cohort are `kedaibiao` and
  `superpie1111`.
- Benchmark baseline outputs were generated with
  `scripts/build_benchmark_baseline.py` under `baseline_runs/benchmark_baseline/`:
  `cohort_members.csv` has 48 ready members, `channel_metrics.csv` has 48
  channel rows, and `metric_percentiles.csv` has per-channel percentile ranks.
  This initial baseline had 39 metric distributions before the 2026-06-04
  weighted reply-conflict rebuild; see the later update for the current
  43-metric baseline. DoDoMen target comparison was generated with
  `--target-run-dir runs/dodomen-generic-demo`, writing `target_metrics.csv`
  and `target_metric_percentiles.csv`; DoDoMen is not included in the
  48-channel baseline distribution.
- Dcard external posts are excluded from current project/baseline work unless
  explicitly selected. `external_analysis.sources` now controls counted sources
  and defaults to PTT-only, pipeline/scraper default crawl source is PTT-only,
  and Superpie's external config is `sources: "ptt"`. Dcard should be revisited
  later with a reliable browser workflow such as Playwright/Camoufox.

Update as of 2026-06-04 00:15 Asia/Taipei:

- Reply-conflict metrics now include structural, reply-count weighted, and
  like-weighted variants. Implementation lives in
  `channel_analyzer/supplement.py`; benchmark extraction lives in
  `channel_analyzer/benchmark.py`.
- All 48 ready benchmark cohort supplement reports were regenerated, then
  `baseline_runs/benchmark_baseline/` was rebuilt with DoDoMen as the target comparison.
  `metric_distributions.csv` now has 43 metrics, including
  `max_video_reply_count_weighted_conflict_score`,
  `max_video_like_weighted_conflict_score`,
  `max_theme_reply_count_weighted_conflict_score`, and
  `max_theme_like_weighted_conflict_score`, each with `cohort_n=48`.
- Current DoDoMen weighted conflict target values:
  max video reply-count weighted conflict score 4.99 (75.0 percentile),
  max video like-weighted conflict score 6.51 (77.1 percentile),
  max theme reply-count weighted conflict score 14.64 (75.0 percentile), and
  max theme like-weighted conflict score 17.82 (77.1 percentile).
- Owner-facing reports under `baseline_runs/benchmark_baseline/` were updated to reflect
  the rebuilt weighted conflict baseline:
  `dodomen_owner_conclusion_report_zh.md` and
  `dodomen_owner_detailed_metric_report_zh.md`.
- DoDoMen Ian/Eric/Collab labels remain optional appendix material inherited
  from `../ResearchA/`; they must not become a dependency of the generic
  channel analyzer. The old `../ResearchA/video_label_sheet_done.csv` stops at
  343 videos through 2026-04-08, while the current shared DB has 351 non-Short
  DoDoMen videos and 351 `video_labels` rows. Delta-review files live under
  `runs/dodomen-generic-demo/custom_labels/`. On 2026-06-04 the user confirmed
  the five remaining labels and they were written to the shared DB with
  `labeler=human_delta_confirmed`: `0dYYLxnQaJM=collab`,
  `mITaFHhulzg=other`, `Q4CCBr_Q8Dc=collab`, `RUzLq2n6MOQ=collab`, and
  `VbwkmeHIkJs=eric`. The refreshed review sheet has 351 rows and
  `needs_review=0`.

Update as of 2026-06-03 15:55 Asia/Taipei:

- Current full config count: 50 files under `configs/*.full.yaml`.
- Current benchmark crawler queue is empty for the active seed/scope:
  failed 8, graphed 14,735, skipped 61, queued 0, quota_failed 0. The only
  transient failed row (`database is locked`) was reset and successfully
  crawled; it added one 百靈果News video and 92 all-scope comments. A later
  DoDoMen delta crawl seeded and graphed 5 new URLs from May 2026. The remaining
  failed rows are non-quota API failures: one `videoNotFound` and seven
  `processingFailure` rows, so do not repeatedly retry them unless the user
  explicitly wants a cleanup attempt.
- Current graph entity counts after the final crawler cleanup:
  54 channels, 14,735 videos, 1,096,894 actors, 2,865,163 threads,
  3,996,381 comments, and 19,996,640 observed edges.
- All 50 current full configs are Qwen/report complete. Final historical
  offload dry-run:
  `legacy/qwen_offload/scripts/export_qwen_batches.py --dry-run --batch-size 6 --tasks both`
  scanned 50 configs, had 0 load failures, and selected 0 configs for export.
  Every listed config had 0 remaining video rows, 0 remaining comment rows, and
  0 video/comment parse errors.
- `runs/bailingguo-full/` is now complete at 731 videos and 292,617
  all-comment Qwen sentiment rows after the final crawler delta.
- `runs/jorsindo-full/` is complete at 582 videos and 78,945 all-comment Qwen
  sentiment rows.
- `runs/dodomen-generic-demo/` was refreshed after the DoDoMen delta crawl:
  351 non-short videos, 245,544 top-level comments, 57,550 replies, 303,094
  all-comment Qwen sentiment rows, 0 parse errors, and regenerated base plus
  supplement reports. The newly graphed videos include `VbwkmeHIkJs`,
  `RUzLq2n6MOQ`, `Q4CCBr_Q8Dc`, `mITaFHhulzg`, and `0dYYLxnQaJM`.
- A DoDoMen-specific external-event appendix analysis now lives in legacy at
  `legacy/direction/Direction/scripts/analyze_dodomen_external_events.py`. It parses local
  PTT/Dcard posts now stored under `case_studies/dodomen/external_criticism_v1/`, infers
  missing Dcard no-year dates from post-id ordering, aligns them with
  comment-level Qwen sentiment plus top-level new-commenter/audience-entry
  proxies, and writes outputs under
  `runs/dodomen-generic-demo/external_event_analysis/`. Treat this as
  exploratory event-window evidence, not causal proof.
- Generic external-event analysis is now part of the end-to-end system as an
  optional config-driven stage. Core implementation:
  `channel_analyzer/external_events.py`; optional local Qwen semantic labeling:
  `channel_analyzer/qwen_external.py` and `scripts/run_qwen_external_posts.py`;
  per-channel external PTT/Dcard scraping:
  `channel_analyzer/external_scraper.py` and `scripts/scrape_external_posts.py`;
  impact/report stage: `scripts/run_external_events.py`. Pipeline flags:
  `scripts/run_pipeline.py --external-events auto|on|off
  --external-crawl auto|on|off --external-crawl-sources ptt
  --external-semantics existing|qwen|none`. The generic crawl stage writes
  target-specific raw external posts to `runs/<slug>/external_sources/`; the
  impact stage writes `runs/<slug>/external_events/` and appends a marked
  External Event Analysis block into `report_en.md`/`report_zh.md` when
  enabled. It must degrade gracefully with status rows for missing source
  directories, no posts, insufficient event candidates, or no overlapping
  YouTube impact rows.
  `external_analysis.sources` is the authoritative source filter for analysis
  and defaults to PTT-only; existing files under `sources_dir` must not be
  counted unless their source is selected there. For current baseline
  completion, keep external events off, or use PTT-only if explicitly testing
  external analysis. Do not count Dcard until a reliable per-channel browser
  crawl (for example Playwright/Camoufox) produces parseable posts rather than
  verification pages.
  `external_analysis.sources_dir` must be per-channel external-post data; do
  not reuse DoDoMen or any other channel's PTT/Dcard scrape for another
  channel, because that contaminates the per-channel analysis. Pipeline-created
  source directories include `external_source_manifest.json`; the analysis
  refuses to run if the manifest channel_id differs from the current target.
  Semantic labels, when present in `tables/qwen_external_post_labels.csv`, are
  preferred over deterministic fallback topic labels; without labels the
  heuristic path is only a screening layer and should not be treated as a final
  semantic interpretation.
- DoDoMen was rerun through the generic full pipeline on 2026-06-03 with
  `micromamba run -n llm-opt python scripts/run_pipeline.py --config
  config.example.yaml --depth all --qwen existing --external-events auto
  --external-semantics existing`. The generic external stage produced 168
  parsed external posts and 18 event clusters under
  `runs/dodomen-generic-demo/external_events/`. Compared with the older
  DoDoMen-specific appendix output, impact metrics on shared event dates were
  unchanged; the main difference is event clustering/filtering
  (22 old event days to 18 generic event clusters), generic topic names,
  merging adjacent same-topic event days, dropping survey/noise days such as
  2025-05-22, and preserving same-day multi-topic discussions as
  `mixed_external_discussion` clusters.
- External-event reporting now includes
  `external_event_impact_diagnostics.csv` plus a report table combining
  negative-rate lift, like-weighted negative amplification, new-audience entry,
  new-vs-returning commenter negativity gaps, reply-conflict lift, impact
  half-life, and spillover beyond event-nearby videos. Treat these as
  event-window diagnostic associations, not causal estimates.
- Superpie external pipeline run on 2026-06-03 used the new per-channel
  crawler:
  `micromamba run -n llm-opt python scripts/scrape_external_posts.py --config
  configs/superpie1111.full.yaml --output-dir
  runs/superpie1111-full/external_sources --sources ptt --ptt-max-pages 5`
  plus a Dcard Camoufox run through the `SMA` env with explicit Superpie
  keywords. It wrote a manifest for channel `UCR_352pCZIWGrqq8Zt6ap8g`,
  fetched 115/115 PTT posts, found 252 Dcard links, but Dcard full-page fetches
  were mostly blocked by verification pages: 2 usable full posts, 249 blocked,
  1 empty. Qwen external semantic labeling completed 117/117 parsed posts with
  0 parse errors; the external analysis then produced 80 Qwen-labeled event
  clusters under `runs/superpie1111-full/external_events/`. Treat Dcard coverage
  as incomplete until a more robust Dcard collection method is used.
- Qwen JSON repair was strengthened in `channel_analyzer/qwen_comment.py` and
  `channel_analyzer/qwen_video.py` to salvage valid leading fields from common
  malformed model outputs, including a stray quote after a numeric value and a
  truncated final top-level field such as an incomplete `reason` string. This
  fixed the last persistent parse-error rows without falsifying labels.
- Local full-cooling automation now uses the root-owned helper
  `/usr/local/sbin/qwen-cooling-control` plus
  `/etc/sudoers.d/channel-community-qwen-cooling`; details are recorded in
  `/home/lewis/ComputerInfo.md`. The helper was tested to set full fans and
  restore auto without relying on a live sudo timestamp.

## Data Contract

The analyzer reads SQLite tables created by `youtube_graph_ingest`:

```text
channels
videos
actors
comment_threads
comments
```

Required columns used by the current tool:

- `channels.channel_id`, `title`, `subscriber_count`, `video_count`,
  `view_count`
- `videos.video_id`, `owner_channel_id`, `title`, `description`,
  `published_at`, `tags_json`, `view_count`, `like_count`, `comment_count`
- `comments.comment_id`, `video_id`, `author_actor_id`, `is_top_level`,
  `text_plain`, `like_count`, `published_at`

Do not require `video_labels`; custom labels are an optional future appendix.

## Runbook

From `ChannelCommunityAnalyzer/`:

```bash
python3 scripts/run_pipeline.py --config config.example.yaml
```

Estimate runtime without running stages:

```bash
python3 scripts/run_pipeline.py --config config.example.yaml --qwen all --estimate-only
python3 scripts/estimate_runtime.py --videos 600 --comments 75000 --qwen all --include-crawl
python3 scripts/check_run_complete.py --config config.example.yaml --qwen all
```

For a specific output root:

```bash
python3 scripts/run_pipeline.py --config config.example.yaml --output runs/demo
```

If the shared DB has not been populated yet, use the sibling ingestion project:

```bash
cd ../youtube_graph_ingest
python -m yt_graph.cli seed --url "https://www.youtube.com/@CHANNEL" --published-after 2023-01-01
python -m yt_graph.cli crawl-batch --limit 50
python -m yt_graph.cli build-all
```

Crawler default excludes Shorts / short-form videos under 180 seconds. Add
`--include-shorts` to both `seed` and `crawl-*` only if the user explicitly
wants Shorts included. Use `--short-threshold-seconds` if a study needs a
different cutoff. The crawler excludes currently live/upcoming videos, but
completed premieres or live archives with normal durations are analyzable.

Validated Superpie full run:

```bash
python3 scripts/run_pipeline.py --config configs/superpie1111.full.yaml --qwen existing
```

Expected scope is 602 non-short videos, 73,117 comments, and 35,045 unique
commenters. Current report outputs are `runs/superpie1111-full/report.md`
(English alias), `report_en.md`, and `report_zh.md`. Reports are concise
statistical packets for downstream LLM analysis: metric formulas first, then
core tables; long detail tables stay in CSV. They include rolling retention,
continuity sensitivity, audience-community content affinity, video
shared-audience clusters, community sentiment, community-theme sentiment, and
video-cluster sentiment.

Full Qwen-assisted pipeline:

```bash
micromamba run -n llm-opt python scripts/run_pipeline.py --config configs/superpie1111.full.yaml --qwen all
```

`--qwen all` runs/resumes video theme classification, comment sentiment,
repair, parse-error retry, and final report generation. Use `--qwen video` or
`--qwen sentiment` to run only one model-assisted stage. Use `--qwen existing`
to skip model inference and regenerate the report from existing CSVs.
The pipeline prints runtime estimates before execution and only estimates
unfinished Qwen rows based on existing output CSVs.
It also prints a completion check before/after execution, skips a Qwen stage if
its CSV is already complete with 0 parse errors, and writes
`runs/<slug>/run_summary.json`.

Report depth:

```bash
micromamba run -n llm-opt python scripts/run_pipeline.py --config config.example.yaml --depth base --qwen existing
micromamba run -n llm-opt python scripts/run_pipeline.py --config config.example.yaml --depth supplement --qwen sentiment
micromamba run -n llm-opt python scripts/run_pipeline.py --config config.example.yaml --depth all --qwen sentiment
```

`base` uses top-level comments only for benchmarkable audience structure,
retention, and co-commenter networks. When `--depth all` is used, the base
analyzer must still include replies in video/theme/cluster sentiment and
negative-hotspot tables by passing `--sentiment-include-replies` to
`scripts/run_analyzer.py`. `supplement` then adds thread conflict/polarization
diagnostics. Do not mix replies into base commenter tiers or network metrics,
but do include replies for per-video sentiment/risk questions.

Runtime estimate method:

```text
remaining_units = in_scope_units - completed_output_rows
stage_seconds = remaining_units / throughput_per_min * 60 + cold_start_seconds
```

Current heuristics: Qwen video themes 20-40 videos/min, Qwen comment sentiment
450-650 comments/min, crawl metadata 20-60 videos/min, crawl comments
500-1500 comments/min. Final CPU report uses
`15 + 0.02*videos + 0.0004*comments` to
`45 + 0.08*videos + 0.0012*comments` seconds. Treat these as calibrated ranges,
not guarantees.
Latest measured local benchmark is `docs/runtime_benchmarks.csv`; Kedaibiao
full run was 526 non-short videos, 14,062 comments, 7,687 commenters, crawl
7m41s, Qwen+analyzer 31m30s, and crawl-to-report 43m26s.

Verified Superpie Qwen video state on 2026-05-13: 602 video rows, 0 parse errors.
Primary themes are mostly `automotive_luxury`, `food_culture`,
`controversy_response`, `personal_team_life`, and `travel_exploration`.

Verified Superpie Qwen sentiment state on 2026-05-13: 100,171 all-comment rows
(73,117 top-level comments + 27,054 replies), 0 parse errors. Output is
comment-level ternary sentiment with
`sentiment_label`, `score_neg`, `score_neu`, and `score_pos`; it does not export
raw comment text.

Verified completed Qwen runs on 2026-05-13:

- `configs/kedaibiao.full.yaml`: 526 videos, 22,118 all-comment sentiment rows,
  0 parse errors, reports under `runs/kedaibiao-full/`.
- `configs/superpie1111.full.yaml`: 602 videos, 100,171 all-comment sentiment
  rows, 0 parse errors, reports under `runs/superpie1111-full/`.
- `configs/beautywu.full.yaml`: 343 videos, 419,394 all-comment sentiment rows,
  0 parse errors, reports under `runs/beautywu-full/`.

Verified DoDoMen generic state on 2026-06-03:

```bash
micromamba run -n llm-opt python scripts/check_run_complete.py --config config.example.yaml --depth all --qwen sentiment
```

Expected scope is 351 non-short videos, 245,544 comments, and 111,537 unique
top-level commenters for the base report. The depth-all run is complete:
351/351 Qwen video-theme rows, 303,094/303,094 all-comment Qwen sentiment rows
(245,544 top-level comments + 57,550 replies), 0 parse errors, and unified
Markdown reports under `runs/dodomen-generic-demo/`. Most historical top-level
Qwen rows were imported from `../ResearchA/` with
`case_studies/dodomen/scripts/import_researcha_dodomen_qwen.py`; the 2026-05-10 run classified the
previously missing reply rows for the commenter deeper analysis chapter, and
the 2026-06-03 delta run classified the 5 newly crawled videos plus their 3,446
new all-scope comments.
Do not split the generated Markdown report into separate base/supplement files:
`report_en.md` and `report_zh.md` should contain both the base chapters and the
reply-thread chapter. Supplement structured data stays in `report_supplement.json`
and reply-thread CSVs such as `tables/reply_thread_metrics.csv`,
`tables/reply_conflict_video_summary.csv`, and
`tables/reply_conflict_theme_summary.csv`.

## Next Todo Lists

Update this section as work is completed so a future context reset can resume
without reconstructing state from chat history.

Crawler and data collection:

- [ ] After quota reset, resume the full benchmark crawler from queued rows with
  `SKIP_SEED=1 RESET_STALE_RESOLVING=1 ./scripts/run_benchmark_crawl_queue.sh`.
- [ ] Keep `docs/tw_benchmark_verified_full_channel_urls.txt` as the default
  seed unless the user edits `docs/tw_under_1_5m_Update.csv` again.
- [ ] When the crawler pauses or finishes, run
  `python3 scripts/benchmark_queue.py status --limit 10` and update the
  snapshot above.
- [ ] If the user changes the analysis window, e.g. from `2023-01-01` to
  `2020-01-01`, use the crawler's resumable seed/crawl/build flow to append
  missing videos and reuse existing DB/Qwen outputs where scopes overlap.

Full Qwen/report completion:

- [x] Create missing `configs/*.full.yaml` files for crawled benchmark channels
  that do not yet have configs as of 2026-05-17. Repeat this when the crawler
  adds more channels.
- [x] Run
  `micromamba run -n llm-opt python scripts/run_pipeline.py --config <config> --depth all --qwen all`
  for crawled-but-undone benchmark channels. As of 2026-06-03, the 48 verified
  `O` cohort rows all match full configs and those configs are Qwen/report
  complete under the current DB scope.
- [x] Colab/teammate Qwen offload materials were archived to
  `legacy/qwen_offload/`, `legacy/notebooks/`, and `legacy/qwen_jobs/`.
  Current product direction is local Qwen by default; do not use offload as the
  core path unless the user explicitly re-enables it.
- [x] Prioritize small/medium completed-crawl channels first to increase cohort
  sample size quickly: 古娃娃, 反正我很閒, 阿翰, Taiwan Bar, 上班不要看, 哈哈台,
  欸你這週要幹嘛, 蒼藍鴿, 阿慶師, 小施汽車生活頻道.
- [ ] Append measured rows to `docs/runtime_benchmarks.csv` when reliable
  crawl/Qwen/report timings are known.

Benchmark cohort layer:

- [x] Add a config-driven benchmark builder that reads completed `runs/*`
  outputs, filters to the chosen cohort membership, and writes cohort metric
  distributions. Current entry point:
  `micromamba run -n llm-opt python scripts/build_benchmark_baseline.py`.
- [x] Output cohort membership and sample size before any percentile claims.
- [x] Compute averages, medians, ranges, and percentiles for core-audience
  share, repeat-commenter retention, community concentration, bridge structure,
  sentiment rates, negative hotspots, and reply-thread conflict.
- [x] Add target-vs-baseline comparison that keeps demo/target channels such as
  DoDoMen outside the baseline distribution while reporting their metric
  percentile against the cohort.
- [ ] Integrate benchmark context into `report_en.md` and `report_zh.md` without
  making benchmark comparison mandatory for single-channel reports.

Network-method extensions:

- [x] First add interpretable social network analysis metrics: Leiden/Infomap
  communities, k-core, betweenness/bridges, assortativity, modularity, and
  community concentration. Current implementation lives in
  `channel_analyzer/network_analysis.py`; Leiden and Infomap are optional
  runtime paths with Louvain/NetworkX fallbacks.
- [x] Add interpretable video link prediction for creator-facing content ideas
  before graph embeddings. Start with the video shared-audience graph and output
  candidate pairs/themes that are structurally near but not already strongly
  connected, using explainable scores such as common neighbors, Jaccard,
  Adamic-Adar, and resource allocation. Current output:
  `tables/video_link_opportunities.csv`.
- [ ] Centrality extensions should be chosen by creator-facing analysis value,
  not by implementation ease. Current node metrics include raw `degree`,
  `weighted_degree`, `core_number`, sampled normalized `betweenness_centrality`,
  participation, and bridge scores; they do not yet include normalized degree,
  PageRank, eigenvector, Katz, closeness, or harmonic centrality. If extending,
  prioritize `degree_centrality`, `weighted_degree_share`, and weighted
  PageRank for both commenter and video node metrics because they answer
  benchmarkable core-position and anchor-video questions. Consider harmonic
  centrality for disconnected graphs, especially video shared-audience graphs.
  Keep eigenvector and Katz out of the main report unless they add a distinct
  validated insight beyond PageRank/k-core/weighted degree; they are better as
  appendix or robustness checks. Do not pass relationship-strength `weight`
  directly as a path distance for closeness/betweenness; if a weighted path
  metric is needed, derive a distance such as `1 / weight` explicitly.
- [ ] Then add optional embedding methods such as node2vec or GraphSAGE for
  commenter/video similarity and cross-channel positioning.
- [ ] Treat GAT/HGT/other GNNs as an experimental layer only after defining a
  prediction task, such as next-video return, negative-hotspot risk, repeat
  commenter retention, shared-audience similarity, or reply-conflict risk.
- [ ] Do not present GNN attention weights as causal explanations. Keep the main
  report grounded in interpretable metrics; put experimental SOTA methods in an
  appendix or future-work section until validated.

Network dependency notes:

- Required graph stack lives in `requirements.txt`: `scipy`, `networkx`, and
  `python-louvain` for the current sparse projections and Louvain community
  detection path.
- Do not add heavy optional graph dependencies just for roadmap items. Add them
  to `requirements.txt` only when the pipeline actually imports them in
  production code or an explicit optional script.
- Candidate optional SNA dependencies: `igraph` + `leidenalg` for Leiden, and
  `infomap` for Infomap. Keep deterministic seeds and record the chosen method
  in output summaries.
- Candidate embedding/GNN dependencies, such as node2vec, PyTorch Geometric, or
  DGL, are future optional/experimental dependencies and must stay behind
  explicit tasks and outputs.

Qwen offload dependency notes:

- Local export/import uses the existing analyzer environment plus pandas; do
  not add Colab-only inference dependencies to `requirements.txt`.
- The bundled Colab runner expects `pandas` and `vllm` in the remote notebook.
  Default Colab handoff uses `Qwen/Qwen3-8B-AWQ` with `--quantization awq` to
  stay closer to local Qwen3-8B quality while avoiding bitsandbytes/CUDA runtime
  mismatches. If AWQ fails on a Colab runtime, fall back to
  `Qwen/Qwen3-4B --quantization none`. It is self-contained and does not
  require copying the shared SQLite DB. The one-click notebook runs inference in
  a `!python` subprocess, then uploads the result zip to Google Drive from a
  separate notebook cell and prints share/download URLs. Do not rely on
  `google.colab.auth.authenticate_user()` inside a `!python` subprocess.
- Qwen job bundles may include raw public YouTube comment text for inference.
  Do not include author display names or author channel URLs in exported
  offload inputs.

External-source dependency notes:

- PTT external scraping is part of the regular environment and needs
  `requests` plus `beautifulsoup4` from `requirements.txt`. If `curl_cffi` is
  installed, the scraper uses it for Chrome impersonation; otherwise it falls
  back to `requests`.
- Dcard external scraping is optional and browser-dependent. It imports
  `camoufox` only when `--external-crawl-sources` includes `dcard`; on SSH or
  headless machines it may need `xvfb-run` or a browser-capable session.
- Pipeline-created external source folders must keep
  `external_source_manifest.json`; the external analysis checks the manifest
  channel_id before using the raw posts.

Presentation and documentation:

- [ ] Keep `docs/project_update_for_teammates_MyVersion.md` as the concise
  teammate-facing update. Avoid replacing it with a verbose rewrite.
- [ ] Final story should describe the three-stage pivot: DoDoMen case study to
  generic channel analyzer to benchmark cohort comparison layer.
- [ ] Keep DoDoMen as a demo/appendix example, not the core product framing.

## Implementation Rules

- Keep analysis config-driven; no hard-coded channel IDs or event dates.
- Write outputs only under the configured `runs/<slug>/` directory.
- Prefer SQLite queries plus pandas for tabular work.
- Use sparse matrices for commenter-commenter and video-video projections when
  possible.
- Keep LLM/theme/sentiment stages optional; the tool must still run without GPU.
- Keep `scripts/run_pipeline.py` as the main public entry point. Stage-specific
  scripts are implementation/resume tools, not the recommended user flow.
- Keep runtime estimates in `channel_analyzer/runtime_estimator.py`; they are
  calibrated heuristics, not guarantees. Crawler estimates should stay broad.
- Keep completion checks in `channel_analyzer/run_checks.py` and
  `scripts/check_run_complete.py`.
- Add measured runtime rows to `docs/runtime_benchmarks.csv` when a new channel
  is run end to end and the timings are known.
- Keep benchmark cohort work data-driven. Cross-channel baselines should be
  computed from completed run outputs under `runs/`, and should report sample
  size and cohort membership before using averages or percentiles in a report.
- Do not treat the Taiwan benchmark candidate list as an analytical result.
  It is crawler/input metadata; only completed channel reports should enter
  reference distributions.
- Keep Markdown reports bilingual and LLM-oriented. `report.md` should remain
  an English alias; `report_en.md` and `report_zh.md` are the explicit outputs.
  The generated Markdown report should be one file per language with multiple
  chapters. Do not create base-only or supplement-only Markdown reports.
  Reply-thread analysis appends into the main reports; `report_supplement.json`
  is structured data only.
- When asking an LLM or subagent to turn statistics into a channel-owner
  conclusion report or detailed report, read `prompt.md` first and require the
  analysis to cover semantic themes, audience communities, video
  shared-audience clusters, link opportunities, sentiment, reply conflict, and
  benchmark context. Do not rely only on `target_metric_percentiles.csv`.
- Sentiment scope is not the same as audience-structure scope. Audience
  communities, tiers, and retention use top-level comments; video/theme/cluster
  sentiment and negative hotspots should use all comments when replies are
  available. The report should expose this with `comment_scope`,
  `n_scope_top_level_comments`, and `n_scope_replies`.
- Negative hotspots and conflict hotspots are different. Negative hotspots sort
  by negative sentiment amplification; conflict hotspots come from reply-thread
  structure and should use `conflict_score = n_conflict_threads *
  conflict_thread_rate_replied` plus `n_pile_on_threads` and
  `n_parent_opposition_threads`.
- Do not describe Qwen video labels as sentiment. Video themes and comment
  sentiment are separate optional stages.
- Use deterministic seeds for community detection and sampling.
- Do not hard-code or preselect the number of communities. Community detection
  should infer the count from the graph; config should only tune graph
  construction thresholds.
- Keep audience network and video network concepts separate:
  commenter-commenter edges represent shared video participation; video-video
  edges represent shared audience. Both are derived from the commenter-video
  bipartite graph.
- Add advanced graph methods only behind explicit tasks and outputs. Start with
  interpretable SNA metrics; treat graph embeddings or graph neural networks as
  optional extensions, not required report dependencies.
- Treat comments as public platform data but avoid exporting large raw comment
  text dumps unless the user explicitly needs them.

## Verification

After code changes:

```bash
python3 -m py_compile channel_analyzer/*.py scripts/run_analyzer.py scripts/run_pipeline.py scripts/run_supplement.py scripts/estimate_runtime.py scripts/run_qwen_video_themes.py scripts/run_qwen_comment_sentiment.py scripts/check_run_complete.py case_studies/dodomen/scripts/import_researcha_dodomen_qwen.py
micromamba run -n llm-opt python scripts/run_pipeline.py --config config.example.yaml --depth all --qwen sentiment --dry-run
```

If there is usable data for the configured channel, also run the analyzer and
check that `report.md`, `report_en.md`, `report_zh.md`, `report.json`,
`report_supplement.json`, `run_summary.json`, `tables/`, and `figures/` are
created. For `--depth supplement/all`, verify that `report_en.md` and
`report_zh.md` contain the `COMMENTER_DEEPER_ANALYSIS` section marker.
