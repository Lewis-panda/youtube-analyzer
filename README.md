# Channel Community Analyzer

End-to-end Social Media Analytics tool for YouTube comment communities.

The project answers a generic product/research question:

> Can public YouTube channel data be converted into an interpretable commenter
> community health report using only video metadata, comments, and graph
> analysis?

DoDoMen split findings are now treated as an optional demo appendix, not the
main project. This tool should work for any channel already crawled into the
shared SQLite database.

## Inputs

The analyzer reads normalized data from:

```text
../SharedData/state/yt_graph.sqlite3
```

That database is produced by the sibling crawler project:

```text
../youtube_graph_ingest/
```

Remote crawler repository:

```text
https://github.com/Lewis-panda/youtube-graph.git
```

If a channel is not in the DB yet, crawl it there first.
The crawler excludes Shorts / short-form videos under 180 seconds by default;
pass `--include-shorts` to both `seed` and `crawl-*` only when the analysis
should include Shorts. Use `--short-threshold-seconds` if a study needs a
different cutoff. It excludes currently live/upcoming videos, but completed
premieres or live archives with normal durations are treated as analyzable
videos.

## Quick Start

Copy and edit the config:

```bash
cp config.example.yaml config.local.yaml
```

Run the end-to-end pipeline:

```bash
python3 scripts/run_pipeline.py --config config.local.yaml
```

## Large Artifacts

GitHub tracks source code, configs, docs, dashboard source, compact benchmark
tables, and a small `dashboard_data/` demo snapshot. Full run outputs, raw Qwen
CSV files, local SQLite databases, legacy zips, and other large generated
artifacts are intentionally ignored.

Use Google Drive for large shared artifacts:

```bash
cp artifacts/google_drive_manifest.example.json artifacts/google_drive_manifest.json
python3 scripts/download_drive_artifacts.py
```

See `docs/google_drive_artifacts.md` for packaging, upload, and restore
instructions.

## Reproducibility Contract

This repository is designed for collaborative GitHub work. Source code,
frontend code, configs, docs, compact benchmark summaries, and the lightweight
dashboard snapshot are committed. Large generated outputs are restored from
Google Drive.

Important rules:

- Dashboard frontend code is read-only. It must not mutate `dashboard_data/`,
  `baseline_runs/`, `runs/`, the shared SQLite database, or Google Drive
  artifacts.
- Frontend code must not hand-compute replacement metric values to make a chart
  look better. If a metric is needed, add it to the Python analyzer/builder and
  regenerate the artifact from the same source files.
- Collaborators should run the dashboard on localhost after clone. Public IP
  or router-forwarding settings are machine-local deployment details and should
  not be hard-coded into the repo.
- When the underlying data changes, update the Google Drive artifact manifest
  and rebuild generated summaries explicitly.

See `docs/data_reproducibility_contract.md` for the full contract.

Estimate runtime without running stages:

```bash
python3 scripts/run_pipeline.py --config config.local.yaml --qwen all --estimate-only
```

If the channel has not been crawled yet but you already know rough scale:

```bash
python3 scripts/estimate_runtime.py --videos 600 --comments 75000 --qwen all --include-crawl
```

Runtime estimates are ranges, not guarantees. After a channel exists in the
SQLite DB, the pipeline uses exact in-scope video/comment counts and subtracts
already completed Qwen rows from existing CSVs. The formula is:

```text
remaining_units = in_scope_units - completed_output_rows
stage_seconds = remaining_units / throughput_per_min * 60 + cold_start_seconds
```

Current calibration: Qwen video themes use 20-40 videos/min; Qwen comment
sentiment uses 450-650 comments/min, calibrated from the Superpie run on this
machine where 73,117 comments with Qwen3-8B finished in roughly two hours.
Crawler estimates are intentionally broader because YouTube/API/network
throttling dominates.

The generic DoDoMen demo is complete as of 2026-05-09: 346 non-short videos,
242,919 comments, 110,790 unique commenters, 346/346 Qwen video-theme rows,
242,919/242,919 Qwen sentiment rows, 0 parse errors, and bilingual reports
under `runs/dodomen-generic-demo/`.

Measured local run timings are kept in:

```text
docs/runtime_benchmarks.csv
docs/runtime_benchmarks.md
```

Full Superpie demo after crawling the channel:

```bash
python3 scripts/run_pipeline.py --config configs/superpie1111.full.yaml --qwen existing
```

Full Qwen-assisted run:

```bash
micromamba run -n llm-opt python scripts/run_pipeline.py --config configs/superpie1111.full.yaml --qwen all
```

`--qwen all` runs/resumes video theme classification, comment sentiment,
repairs parseable outputs, retries parse-error rows, and regenerates the final
report. `--qwen existing` skips model inference and uses any existing Qwen CSVs.
If no Qwen CSVs exist, the analyzer still produces a complete report with
keyword-based video themes and sentiment fallback.

Report depth is explicit:

```bash
# Base Report: top-level comments only; benchmarkable audience structure.
micromamba run -n llm-opt python scripts/run_pipeline.py --config config.local.yaml --depth base --qwen existing

# Commenter Deeper Analysis chapter only: reply-thread conflict/polarization diagnostics.
micromamba run -n llm-opt python scripts/run_pipeline.py --config config.local.yaml --depth supplement --qwen sentiment

# Full community health report: base chapters plus the reply-thread chapter in one report.
micromamba run -n llm-opt python scripts/run_pipeline.py --config config.local.yaml --depth all --qwen sentiment
```

The base audience-structure chapters intentionally exclude replies from core
commenter, retention, and co-commenter network metrics. When replies are
available, video/theme/cluster sentiment and negative-hotspot tables use all
comments, because those questions are about the full discussion around a video.
The reply-thread chapter then adds thread-aware metrics such as
`thread_bipolarity`, `conflict_thread`, `pile_on_thread`, and
`parent_opposition_thread` into the same `report_en.md` / `report_zh.md` files.
It also reports conflict hotspot videos using
`conflict_score = n_conflict_threads * conflict_thread_rate_replied`, so the
ranking is not just the most negative videos.

Advanced: run only video theme classification:

```bash
micromamba run -n llm-opt python scripts/run_pipeline.py --config configs/superpie1111.full.yaml --qwen video
```

Advanced: run only comment sentiment:

```bash
micromamba run -n llm-opt python scripts/run_pipeline.py --config configs/superpie1111.full.yaml --qwen sentiment
```

The Qwen stage outputs are:

```text
runs/<channel_slug>/tables/qwen_video_themes.csv
runs/<channel_slug>/tables/qwen_comment_sentiment.csv
```

Optional PTT/Dcard external-event analysis is config-driven through
`external_analysis:`. When enabled, the pipeline appends an External Event
Analysis section to `report_en.md` / `report_zh.md` and writes detailed CSVs to:

```text
runs/<channel_slug>/external_events/
```

`external_analysis.sources_dir` must contain posts collected for the same
channel being analyzed. Do not reuse another channel's external-post scrape as a
placeholder. For a new channel, either omit `sources_dir` and let the pipeline
scrape to `runs/<channel_slug>/external_sources/`, or point it to a directory
created specifically for that channel. Pipeline-generated source directories
include `external_source_manifest.json`; if its `channel_id` does not match the
current target, external analysis refuses to run.

`external_analysis.sources` controls which scraped source files are counted.
The default is PTT-only. Use `sources: "ptt,dcard"` only when Dcard data was
collected for the same channel through a reliable browser workflow and is not a
verification page dump. The current baseline completion work should keep
external events off, or PTT-only if explicitly testing external analysis; do not
count stale or cross-channel Dcard files.

Run the target-aware external crawler plus analysis:

```bash
micromamba run -n llm-opt python scripts/run_pipeline.py \
  --config configs/superpie1111.full.yaml \
  --depth all \
  --qwen existing \
  --external-events on \
  --external-crawl on \
  --external-crawl-sources ptt \
  --external-semantics existing
```

If Qwen semantic labeling of external posts is needed, use
`--external-semantics qwen` after scraping. Dcard scraping uses Camoufox and may
need a browser-capable session such as `xvfb-run`; PTT scraping can run
headlessly.

Run with existing semantic labels or heuristic fallback:

```bash
micromamba run -n llm-opt python scripts/run_pipeline.py \
  --config config.local.yaml \
  --depth all \
  --qwen existing \
  --external-events auto \
  --external-semantics existing
```

Build the verified benchmark baseline from completed channel reports:

```bash
micromamba run -n llm-opt python scripts/build_benchmark_baseline.py \
  --cohort docs/tw_under_1_5m_Update.csv \
  --configs-glob "configs/*.full.yaml" \
  --runs-dir baseline_runs \
  --output baseline_runs/benchmark_baseline \
  --target-run-dir runs/dodomen-generic-demo
```

This writes cohort membership, per-channel metrics, distribution statistics, and
per-channel percentile ranks. The baseline builder reads completed reports only;
it does not run Qwen, crawl YouTube, or count optional PTT/Dcard external
events. `--target-run-dir` compares a target such as DoDoMen against the
baseline without including that target in the cohort distribution.

Build read-only dashboard data from completed runs:

```bash
python3 scripts/build_dashboard_index.py
```

This writes:

```text
dashboard_data/index.json
dashboard_data/channels/<slug>.json
```

The dashboard data builder does not crawl YouTube, run Qwen, or simulate
progress. It scans completed artifacts under `baseline_runs/`, attaches
baseline percentile metadata from `baseline_runs/benchmark_baseline/`, and
emits compact JSON packets for a Web dashboard to consume.

Serve the read-only dashboard locally:

```bash
python3 dashboard/server.py --host 127.0.0.1 --port 8765
```

Open:

```text
http://127.0.0.1:8765/
```

For LAN or router-forwarded presentation access:

```bash
python3 dashboard/server.py --host 0.0.0.0 --port 8765
```

`0.0.0.0` only exposes the server on this machine's network interfaces. Public
Internet access still requires router port forwarding and firewall allowance,
or a tunnel such as Cloudflare Tunnel. Do not commit a specific public IP into
the dashboard; collaborator clones should continue to work through localhost.
See `dashboard/README.md`.

To generate/resume Qwen semantic labels for external posts first:

```bash
micromamba run -n llm-opt python scripts/run_pipeline.py \
  --config config.local.yaml \
  --depth all \
  --qwen existing \
  --external-events auto \
  --external-semantics qwen
```

If no external posts exist, or if the posts are insufficient to form event
candidates, the stage writes a status row instead of failing the pipeline.

Qwen inference is local by default. Older Colab/teammate offload scripts,
notebooks, and handoff docs are preserved under `legacy/qwen_offload/`,
`legacy/notebooks/`, and `legacy/qwen_jobs/`, but they are no longer part of the
core product path.

DoDoMen-specific reuse: the old `../ResearchA/` case study already contains
Qwen3 outputs for most DoDoMen comments and labeled videos. To convert those
outputs into this generic run format before resuming the remaining rows:

```bash
python3 case_studies/dodomen/scripts/import_researcha_dodomen_qwen.py --config config.example.yaml
micromamba run -n llm-opt python scripts/run_pipeline.py --config config.example.yaml --qwen all
```

The importer is a migration helper, not part of the generic data contract. It
lets the generic DoDoMen demo avoid reclassifying rows that were already scored
in `ResearchA`.

Dry-run config and DB matching only:

```bash
python3 scripts/run_pipeline.py --config config.local.yaml --dry-run
```

Check whether a run is complete:

```bash
python3 scripts/check_run_complete.py --config config.local.yaml --qwen all
```

For already-crawled channels, the crawler layer is idempotent: `seed` prints
`Seeded 0 new URLs` when the queue already contains the same videos, `crawl-*`
prints `No queued URL` / `No more queued URLs` when there is nothing left to
crawl, and `build-all` prints `No more inbox bundles` when everything has been
normalized. The analyzer layer prints completion checks, skips Qwen stages that
already have complete CSVs, and writes `run_summary.json`.

## Outputs

Each run writes to:

```text
runs/<channel_slug>/
```

Output layout:

```text
report.md
report_en.md
report_zh.md
report.json
report_supplement.json        # structured data for the reply-thread chapter
run_summary.json
tables/
  channel_overview.csv
  diagnostics.csv
  video_metrics.csv
  commenter_activity.csv
  commenter_tiers.csv
  continuity_summary.csv
  continuity_sensitivity.csv
  rolling_retention.csv
  network_summary.csv
  community_summary.csv
  community_profiles.csv
  community_theme_affinity.csv
  bridge_actors.csv
  network_actor_metrics.csv
  theme_video_labels.csv
  theme_video_labels_long.csv
  theme_summary.csv
  video_network_summary.csv
  video_cluster_summary.csv
  video_clusters.csv
  video_network_metrics.csv
  video_link_opportunities.csv
  video_cluster_theme_affinity.csv
  video_cluster_sentiment_summary.csv
  theme_source_summary.csv
  qwen_video_themes.csv        # optional, if Qwen stage has been run
  sentiment_source_summary.csv
  sentiment_summary.csv
  sentiment_theme_summary.csv
  sentiment_hotspots.csv
  community_sentiment_summary.csv
  community_theme_sentiment.csv
  qwen_comment_sentiment.csv   # optional, if Qwen sentiment has been run
  reply_thread_overview.csv             # supplement
  reply_sentiment_summary.csv           # supplement
  reply_thread_metrics.csv              # supplement; no raw comment text
  reply_conflict_video_summary.csv      # supplement
  reply_conflict_theme_summary.csv      # supplement
external_sources/                      # optional per-channel PTT/Dcard scrape
  external_source_manifest.json
  ptt/
    ptt_index.json
    ptt_full.json
  dcard/
    dcard_index.json
    dcard_full.json
external_events/                       # optional, if external_analysis is enabled
  external_event_summary.csv
  external_posts.csv
  external_daily_metrics.csv
  external_event_clusters.csv
  external_event_windows.csv
  external_event_audience_windows.csv
  external_event_impact_diagnostics.csv
figures/
  channel_activity.png
  commenter_tiers.png
  community_sizes.png
  rolling_retention.png
  video_cluster_sizes.png
```

`report.md` is an English alias for `report_en.md`. The Markdown reports are
designed as compact statistical packets for downstream LLM analysis: metric
definitions and formulas appear before the tables, long detail tables stay in
CSV, and both English and Chinese versions are generated.

The pipeline prints a runtime estimate before doing work. With `--qwen all`, it
checks existing Qwen CSVs and estimates only unfinished rows, so interrupted
runs can be resumed with a realistic remaining-time estimate.
If the Qwen CSV is already complete and has 0 parse errors, the pipeline prints
an already-complete message and does not load the model for that stage.

## Current Scope

Implemented:

- config-driven channel selection
- single-command pipeline runner with resumable optional Qwen stages
- configurable short-form filtering; default excludes videos under 180 seconds
- channel overview
- actionable channel diagnostics
- video metadata table
- commenter activity and core/casual tiers
- window-based, sensitivity, and rolling commenter retention
- sparse co-commenter network projection
- audience community detection with deterministic optional Leiden/Louvain fallback
- interpretable SNA metrics: k-core, sampled betweenness bridges,
  assortativity, modularity, conductance, and community concentration
- bridge actor ranking and top structural actor metrics
- video shared-audience clustering
- video shared-audience graph structural metrics
- explainable video link prediction for creator-facing content ideas
- community-content and video-cluster content affinity/lift
- community, community-theme, and video-cluster sentiment summaries
- optional Qwen-assisted video theme classification
- optional Qwen-assisted comment sentiment classification
- CPU-only keyword-based multi-label video themes
- sentiment/risk hotspot fallback using transparent keyword rules
- Markdown and JSON report generation
- bilingual LLM-oriented statistical reports (`report_en.md`, `report_zh.md`)

Current Superpie full run:

- config: `configs/superpie1111.full.yaml`
- report: `runs/superpie1111-full/report.md` plus `report_en.md` and `report_zh.md`
- scope: 602 non-short videos, 73,117 comments, 35,045 unique commenters
- graph: 4,550 nodes, 89,903 edges, 8 automatically detected communities
- video shared-audience graph: 524 videos, 15,980 edges, 4 clusters
- Qwen video labels: 602/602 videos, 0 parse errors
- Qwen comment sentiment: 73,117/73,117 comments, 0 parse errors

Current Kedaibiao full run:

- config: `configs/kedaibiao.full.yaml`
- report: `runs/kedaibiao-full/report.md` plus `report_en.md` and `report_zh.md`
- scope: 526 non-short videos, 14,062 comments, 7,687 unique commenters
- Qwen video labels: 526/526 videos, 0 parse errors
- Qwen comment sentiment: 14,062/14,062 comments, 0 parse errors
- measured timing: crawl 7m 41s, Qwen+analyzer 31m 30s, crawl-to-report 43m 26s

Community count is not configured manually. The analyzer builds the
co-commenter graph and lets the community detection algorithm determine the
number of communities from the graph structure. Config values such as
`min_actor_videos` and `min_co_videos` only control graph construction.
`community_algorithm` can choose the detection family (`auto`, `leiden`,
`louvain`, `infomap`, or `greedy`) but not the number of communities.

Not yet implemented:

- live crawling from this project; use `../youtube_graph_ingest`
- optional event-mode placebo diagnostics
- optional custom-label appendix

## Design Principle

The generic report must not depend on DoDoMen-specific labels. Custom labels
such as Ian/Eric/Collab belong in an optional appendix after the generic report.
