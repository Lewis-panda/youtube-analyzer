# baseline_runs

Completed full channel runs used for baseline distributions and dashboard
examples.

These directories are not disposable logs. They are the case library used to
interpret whether a target channel's metrics are high, low, or typical.

Rules:

- Keep full run artifacts unless there is explicit approval to compact them.
- Baseline code may read `report.json`, `run_summary.json`, `resolved_config.json`,
  `tables/*.csv`, and `figures/*.png`.
- Use DB snapshot metadata in reports when making subscriber-count cohort
  claims.
- Do not include case-study-only runs such as DoDoMen in generic cohort
  distributions unless explicitly requested.

Current compatibility note:

- `runs/<slug>-full` symlinks point here so existing scripts that default to
  `runs/` can continue to read completed runs during the transition.
