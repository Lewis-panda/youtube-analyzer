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
- `demo_target_slug`: near-term demo target. As of 2026-06-07 this is
  `dodomen-generic-demo`.
- `demo_focus`: Traditional Chinese scope/caution text for the DoDoMen-first
  presentation. It marks current percentiles as broad benchmark context, not
  matched similar-channel ranking.
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

`dashboard_summary` now includes profile-oriented segmentation fields:

- `audience_segment_profiles`: graph-detected commenter segments translated
  into channel-owner-readable profiles. Each profile includes group size,
  average comments per commenter, preferred videos/themes, over-indexed themes,
  theme/title proxy keywords, main sentiment, negative-source themes,
  representative-comment status, and business advice.
- `audience_segment_profile_contract`: source map for the intended audience
  segmentation display. It documents what each aspect means and which artifact
  supports it.
- `video_cluster_profiles`: shared-audience video clusters translated into
  explainable content groups. Each profile includes title/theme evidence,
  proxy discussion keywords, sentiment, ABSA status, metadata evidence, shared
  audience interpretation, and business read.
- `video_cluster_explanation_contract`: source map for explaining video
  clusters: title/description/tags, comment keywords, sentiment, ABSA,
  metadata, and shared audience.

Important limitations:

- Current `comment_keywords` values in these profiles are `theme/title proxy`.
  They are useful for demo framing but are not true keyword extraction from
  raw comments.
- Current Qwen comment output is ternary sentiment, not ABSA. Do not claim the
  system already knows which exact aspects viewers praise or complain about
  unless a future ABSA table is generated.
- Representative comments are intentionally absent from current cold artifacts.
  Add a raw-comment sampler before displaying quote-like examples.

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
They must not become dependencies of the generic analyzer. For the near-term
presentation demo, however, DoDoMen is included as the default `demo_target_slug`
so the page can focus on one clear case study. If a collaborator needs to
build the dashboard without the default demo case, use:

```bash
python3 scripts/build_dashboard_index.py --skip-default-demo-target
```
