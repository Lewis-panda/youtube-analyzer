# Runtime Benchmarks

This file summarizes measured local runs for calibrating rough pipeline
estimates. The machine, YouTube/API throttling, GPU availability, and prompt
shape can change these numbers, so treat them as empirical references rather
than guarantees.

Raw benchmark rows are in `docs/runtime_benchmarks.csv`.

## Current Rows

| run_id | channel | videos | comments | commenters | crawl | Qwen video | Qwen sentiment | Qwen pipeline | active max | crawl-to-report wall |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| kedaibiao-full | 课代表立正 | 526 | 14,062 | 7,687 | 7m 41s | 5m 54s | 25m 32s | 31m 30s | 39m 41s | 43m 26s |
| dodomen-generic-import-gap-fill | The DoDo Men - 嘟嘟人 | 346 | 242,919 | 110,790 | n/a | 48s | 8m 56s | 10m 14s | n/a | n/a |
| dodomen-depth-all-reply-supplement | The DoDo Men - 嘟嘟人 | 346 | 299,648 | 122,338 | n/a | reused | 2h 5m 23s | n/a | n/a | n/a |

Notes:

- `kedaibiao-full` excluded videos shorter than 180 seconds.
- Seed inserted 526 URLs and filtered 59 videos; seed duration was not captured.
- Build finished before the first 30-second status check, so the CSV records
  `build_seconds_max=30`.
- `active max` is `crawl_seconds + build_seconds_max + qwen_pipeline_seconds`.
- `crawl-to-report wall` is `report_end - crawl_start`; it includes waiting and
  orchestration gaps between stages.
- Qwen outputs completed with 0 video-theme parse errors and 0 comment-sentiment
  parse errors.
- `dodomen-generic-import-gap-fill` is not a full crawl/Qwen benchmark. It
  completed the generic DoDoMen run after importing the existing ResearchA
  Qwen outputs: 335 video-theme rows and 239,051 comment-sentiment rows were
  reused, and only the remaining 11 videos plus 3,868 comments were classified.
- `dodomen-depth-all-reply-supplement` is also incremental. It reuses existing
  top-level Qwen outputs and measures only the 56,729 newly classified replies
  needed for the reply-thread supplement. The listed comment/commenter counts
  are all-comment scope, not base-report top-level scope. After optimizing the
  supplement aggregation, a clean rerun with Qwen skipped took 56.5 seconds:
  base report 39.8 seconds and supplement 9.7 seconds.
