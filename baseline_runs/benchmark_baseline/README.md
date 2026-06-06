# Benchmark Baseline Outputs

這個資料夾是由 completed channel reports 聚合出的 cohort baseline。
它不重新讀 raw comments，也不納入 Dcard/PTT 外部事件；外部事件是另一個 optional analysis layer。

- Cohort members: 48
- Ready reports: 48
- Channel metric rows: 48
- Distribution metrics: 43

## Files

- `cohort_members.csv`: verified cohort row, matched config/run directory, and readiness status.
- `channel_metrics.csv`: one row per ready channel with extracted baseline metrics.
- `metric_distributions.csv`: cohort mean, median, range, and quantiles per metric.
- `metric_percentiles.csv`: percentile rank of each channel on each metric.
- `target_metrics.csv`: optional target rows, such as DoDoMen, excluded from the baseline distribution.
- `target_metric_percentiles.csv`: optional target-vs-baseline percentile comparison.

## Interpretation Notes

- Percentile is directional only. A high percentile is not automatically good; for negative rate or conflict metrics it can indicate higher risk.
- Target comparison percentiles mean percentage of baseline cohort channels with values at or below the target value. The target is not included in the baseline distribution.
- Sample size must be reported with any percentile claim. Different metrics can have different `n` if a report lacks that section.
- The baseline uses the verified `O` rows from the cohort CSV by default. Extra demo/test runs are excluded unless the script is pointed at a different cohort.
- Audience structure and network metrics come from top-level comments; sentiment and reply-conflict metrics use all comments when reply Qwen rows are available.
