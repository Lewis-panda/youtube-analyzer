# Dashboard Data Contract

The dashboard demo is read-only. It consumes generated artifacts and must not
trigger crawler, Qwen inference, or fake progress bars.

Frontend code must treat `dashboard_data/` as immutable input. It may filter,
sort, visualize, and annotate values, but must not overwrite metric values or
hard-code machine-specific public URLs. Collaborator clones should default to
localhost; public-IP deployment belongs to local ops, not the data contract.

Build data:

```bash
python3 scripts/build_dashboard_index.py
```

Outputs:

```text
dashboard_data/index.json
dashboard_data/channels/<slug>.json
```

## `index.json`

Top-level fields:

- `schema_version`: integer schema version.
- `generated_at`: UTC generation timestamp.
- `product_mode`: currently `read_only_demo`.
- `baseline`: summary of baseline cohort files and metric count.
- `examples`: list of completed channel examples for the landing page.
- `errors`: non-fatal run directories skipped by the builder.

Each example includes:

- `slug`
- `title`
- `channel_id`
- `subscriber_count`
- `n_videos_in_scope`
- `n_comments_in_scope`
- `n_commenters_in_scope`
- `date_min`
- `date_max`
- `json_path`
- `run_dir`
- `negative_rate`
- `positive_rate`
- `baseline_metrics`
- `available_tabs`

## Channel JSON

Each `channels/<slug>.json` includes:

- `channel`: channel metadata and analysis scope.
- `overview`: first row from `channel_overview`.
- `run_summary`: summarized run timing and stage status.
- `config`: display-safe config summary.
- `reports`: paths to Markdown/JSON reports.
- `artifacts.tables`: paths to generated CSV tables.
- `artifacts.figures`: paths to generated figures.
- `tabs`: availability map for dashboard tabs.
- `dashboard_summary`: compact values for cards and top lists.
- `baseline`: percentile metrics and cohort distributions for this channel.

## Dashboard Tabs

Current tab IDs:

- `overview`
- `videos`
- `themes`
- `community`
- `video_network`
- `reply_conflict`
- `baseline`
- `external_events`
- `cold_report`
- `owner_report`

Tabs may be unavailable for a channel if the required artifacts are missing.

## Case Studies

DoDoMen split labels and appendix material live under `case_studies/dodomen/`.
They are excluded from `dashboard_data/index.json` by default. If a special
case-study page is needed, use `--include-run` explicitly:

```bash
python3 scripts/build_dashboard_index.py \
  --include-run case_studies/dodomen/dodomen-generic-demo
```
