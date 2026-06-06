# Repo Reorganization Manifest

日期：2026-06-06

本次整理採用「移動與相容 symlink」，不刪除資料。

## 新增目錄

- `dashboard/`: read-only Web demo area.
- `baseline_runs/`: completed full runs and baseline artifacts.
- `case_studies/`: channel-specific appendix material.
- `case_studies/dodomen/`: DoDoMen-specific run, labels, external sources, and helpers.
- `legacy/`: archived logs, exports, offload bundles, notebooks, research material, and local ops scripts.

## 搬移內容

Completed full runs:

- `runs/*-full` -> `baseline_runs/*-full`
- Compatibility symlinks remain at `runs/*-full`.

Benchmark artifacts:

- `runs/benchmark_baseline` -> `baseline_runs/benchmark_baseline`
- `runs/baseline_completion_inventory.csv` -> `baseline_runs/baseline_completion_inventory.csv`
- Compatibility symlink remains at `runs/benchmark_baseline`.

DoDoMen case study:

- `runs/dodomen-generic-demo` -> `case_studies/dodomen/dodomen-generic-demo`
- Compatibility symlink remains at `runs/dodomen-generic-demo`.
- `scripts/apply_dodomen_delta_labels.py` -> `case_studies/dodomen/scripts/apply_dodomen_delta_labels.py`
- `scripts/import_researcha_dodomen_qwen.py` -> `case_studies/dodomen/scripts/import_researcha_dodomen_qwen.py`
- `Direction/results/external_criticism_v1` -> `case_studies/dodomen/external_criticism_v1`
- `config.example.yaml` now points to `case_studies/dodomen/external_criticism_v1`.

Legacy artifacts:

- `logs/*` -> `legacy/logs/`
- `exports/*` -> `legacy/exports/`
- `qwen_jobs/*` -> `legacy/qwen_jobs/`
- `notebooks/*` -> `legacy/notebooks/`
- `docs/qwen_colab_offload.md` -> `legacy/qwen_offload/qwen_colab_offload.md`
- `scripts/export_qwen_job.py`, `scripts/export_qwen_batches.py`,
  `scripts/import_qwen_results.py` -> `legacy/qwen_offload/scripts/`
- `scripts/run_overnight_qwen_20260513.sh`,
  `scripts/run_overnight_qwen_20260514.sh`,
  `scripts/run_completed_benchmark_qwen.sh` -> `legacy/scripts/`
- `scripts/gpu_case_fan_control.py`, `scripts/qwen-cooling-control`,
  `scripts/run_local_qwen_queue.sh`,
  `scripts/run_local_qwen_queue_with_thermal_guard.sh` -> `legacy/local_ops/`
- `Research Gap/` -> `legacy/research/Research_Gap/`
- `Direction/` -> `legacy/direction/Direction/`
- `.matplotlib/` -> `legacy/matplotlib/.matplotlib/`
- `runs/superpie1111-demo` -> `legacy/demo_runs/superpie1111-demo`
- Compatibility symlink remains at `runs/superpie1111-demo`.

## Core Scripts Remaining

- `scripts/run_pipeline.py`
- `scripts/check_run_complete.py`
- `scripts/estimate_runtime.py`
- `scripts/run_analyzer.py`
- `scripts/run_supplement.py`
- `scripts/run_external_events.py`
- `scripts/scrape_external_posts.py`
- `scripts/run_qwen_video_themes.py`
- `scripts/run_qwen_comment_sentiment.py`
- `scripts/run_qwen_external_posts.py`
- `scripts/build_benchmark_baseline.py`
- `scripts/benchmark_queue.py`
- `scripts/requeue_channel_videos.py`
- `scripts/resolve_benchmark_channel_urls.py`
- `scripts/run_benchmark_crawl_queue.sh`

## Compatibility Notes

- Existing configs still use `outputs.run_slug`, and default scripts still write
  to or read from `runs/<slug>`.
- Symlinks in `runs/` preserve that behavior during the transition.
- Future dashboard code should prefer `baseline_runs/` for completed examples
  and should treat `runs/` as active/current output.
- Generic analysis must not depend on `case_studies/dodomen/`.
