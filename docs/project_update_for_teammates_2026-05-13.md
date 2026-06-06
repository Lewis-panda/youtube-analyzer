# Project Update for Teammates

Date: 2026-05-13

## TL;DR

I changed the project direction substantially.

The direction changed in stages: first from a DoDoMen case study to a generic
YouTube channel analyzer, and then from a single-channel analyzer to a
single-channel analyzer with a benchmark comparison layer:

> Given a YouTube channel URL or an existing channel in our shared SQLite DB,
> produce a commenter community health report, then compare the channel against
> a benchmark cohort of Taiwan creator/media channels.

The motivation is not a single jump to benchmarking. It happened in three
steps. First, the project started as a detailed DoDoMen case study. Second, I
found that a single-channel case study was too hard to generalize, so I refactored
the project into a generic channel analyzer: given any YouTube channel in the
shared DB, the system can generate a report from metadata, comments, Qwen labels,
and audience/video network analysis. Third, after the report existed, I found that
many metrics are hard to interpret without comparison. For example, a 1%
core-audience share may look low in isolation, but if similar channels average
0.5%, then 1% is actually relatively strong. That is why the current direction
adds a benchmark cohort: analyze multiple Taiwan channels, build reference
distributions, and interpret one channel's metrics using cohort averages,
medians, ranges, and percentiles.

## New Project Positioning

The project is now an end-to-end Social Media Analytics tool for YouTube
channels.

Input:

- A YouTube channel URL for crawling, or a channel already present in the shared
  SQLite database.
- Current crawl scope is videos published after `2023-01-01`.
- Shorts are excluded by default using a 180-second threshold.

Output:

- A bilingual Markdown report: English and Chinese.
- Structured JSON outputs.
- CSV tables for detailed metrics.
- Figures for community and time-series analysis.

Main report questions:

- Who are the core, returning, and one-off commenters?
- How concentrated is the audience community?
- How stable is audience retention over time?
- What video themes attract which commenter communities?
- Which videos or themes produce negative sentiment hotspots?
- What does reply-thread structure suggest about conflict or polarization?
- How does this channel compare with a benchmark cohort?

## Pipeline Overview

The system is split into two layers.

1. Crawler and database layer

The sibling project `youtube_graph_ingest` crawls YouTube metadata and comments,
normalizes them, and writes to a shared SQLite DB:

- `channels`
- `videos`
- `actors`
- `comment_threads`
- `comments`

The crawler is resumable through a URL queue. If YouTube API quota runs out, the
queue can continue the next day without restarting from scratch.

2. Analyzer and report layer

`ChannelCommunityAnalyzer` reads the shared DB and generates reports.

Key analysis components:

- video metadata summary
- commenter activity tiers
- repeat-commenter and retention metrics
- actor-video network analysis: commenter-commenter projection and video-video
  shared-audience projection
- video-theme classification using Qwen
- comment-level sentiment using Qwen
- negative hotspot detection
- reply-thread conflict/polarization diagnostics
- bilingual report generation

The system is config-driven. It should not hard-code DoDoMen-specific channel
IDs, events, or assumptions.

## Why We Pivoted

The project changed in two steps rather than jumping directly from DoDoMen to
benchmarking.

The first stage was a DoDoMen case study. The initial goal was to analyze
DoDoMen deeply: video themes, commenter communities, core audience, sentiment,
and negative hotspots. This could explain DoDoMen well, but the contribution
was too case-specific. Many design choices and interpretations would be tied to
DoDoMen, making the project hard to generalize.

The second stage was a generic channel analyzer. To make the project more
general, I changed the target from "analyze DoDoMen" to "build a channel
analysis tool." If a YouTube channel is already in the shared SQLite DB, the
same config-driven pipeline can generate a report covering audience structure,
retention, commenter communities, video shared-audience clusters, Qwen video
themes, Qwen comment sentiment, negative hotspots, and reply-thread
diagnostics. This turns DoDoMen into a demo case rather than a hard-coded
target.

The third stage is the benchmark cohort. After the analyzer worked, another
problem became clear: many single-channel metrics are difficult to evaluate
without a comparison baseline. A core-audience share of 1% may be low, typical,
or high depending on comparable channels. The new benchmark layer therefore
runs multiple Taiwan creator/media channels, builds reference distributions for
key metrics, and interprets one channel's values using cohort averages,
medians, ranges, and percentiles.

The current contribution is therefore:

- A reusable analysis pipeline for any YouTube channel in the DB.
- A config-driven channel community health report.
- A cross-channel benchmark layer for interpreting single-channel metrics.

DoDoMen is still useful, but now as a demo channel or appendix rather than the
entire project.

## Current Implementation Status

Completed:

- Generic analyzer pipeline exists.
- Reports are generated from config files rather than hard-coded channel logic.
- Qwen video-theme classification is integrated.
- Qwen comment sentiment is integrated.
- Qwen stages are resumable: if some rows already exist, reruns only classify
  missing videos/comments.
- Reply-thread supplement exists for `--depth all`.
- Runtime estimation and completion checks exist.
- Benchmark candidate URL list has been reviewed and cleaned.
- Crawler queue supports continuing after quota reset.
- Crawler now skips single-video non-quota failures instead of stopping the
  entire queue.

Not completed yet:

- Cross-channel benchmark percentile/average layer is not implemented in the
  final report yet.
- Most newly crawled benchmark channels still need Qwen analysis.
- We still need to decide the final cohort size and whether to use all 50
  channels or a smaller validated subset.

## Current Data Progress

As of 2026-05-13 00:46 Taipei time:

Crawler queue:

- `graphed`: 4,141 videos
- `queued`: 1,179 videos
- `failed`: 4 videos
- `skipped`: 61 videos
- quota is currently exhausted; the last crawl paused cleanly at
  2026-05-12 21:08 Taipei time.

Current shared DB contains data for 17 channels:

| Channel | Videos | Top-level comments | Unique top-level commenters |
|---|---:|---:|---:|
| 欸你這週要幹嘛 | 76 | 17,079 | 10,043 |
| 喪屍老爸 | 473 | 72,735 | 26,978 |
| 見習網美小吳 | 343 | 391,623 | 163,792 |
| 阿慶師 | 335 | 19,871 | 11,388 |
| HahaTai 哈哈台 | 168 | 51,497 | 33,112 |
| 超派人生Superpie | 621 | 73,194 | 35,061 |
| 錫蘭Ceylan | 112 | 171,175 | 111,569 |
| Onion Man | 118 | 88,909 | 48,825 |
| 课代表立正 | 526 | 14,062 | 7,687 |
| 阿翰po影片 | 43 | 24,615 | 15,378 |
| The DoDo Men - 嘟嘟人 | 347 | 242,955 | 110,802 |
| 中天新聞 | 572 | 276,686 | 105,905 |
| TVBS NEWS | 200 | 62,907 | 41,029 |
| 三立新聞網SETN | 23 | 6,972 | 6,143 |
| 上班不要看 NSFW | 152 | 41,459 | 20,110 |
| 反正我很閒 | 21 | 13,060 | 8,849 |
| 古娃娃WawaKu | 11 | 588 | 550 |

## Current Qwen Analysis Progress

Depth-all Qwen complete, including video themes, all-comment sentiment, reports,
and reply supplement:

| Channel | Videos | Top-level comments | All comments for Qwen sentiment | Status |
|---|---:|---:|---:|---|
| DoDoMen | 346 | 242,919 | 299,648 | Complete |
| 錫蘭Ceylan | 112 | 171,175 | 250,589 | Complete |
| Onion Man | 118 | 88,909 | 109,733 | Complete |
| 喪屍老爸 | 473 | 72,735 | 88,414 | Complete |

Base Qwen complete, but depth-all replies still pending:

| Channel | Videos | Top-level comments | Pending replies |
|---|---:|---:|---:|
| Superpie | 602 | 73,117 | 27,054 |
| 课代表立正 | 526 | 14,062 | 8,056 |

Important caveat:

- 見習網美小吳 was Qwen-complete when its DB scope was 89 videos.
- After continuing the crawl, its current DB scope expanded to 343 videos and
  419,394 all comments, so it now needs Qwen resume for the newly added data.

## What I Need Feedback On

1. Project contribution

Is the current framing strong enough?

> Generic channel analyzer + benchmark cohort comparison layer.

Or should we narrow the final story to a smaller claim, such as "community
health diagnostics for YouTube channels"?

2. Benchmark cohort design

Should the benchmark cohort be:

- all 50 planned Taiwan creator/media channels,
- only channels under 1.5M subscribers,
- only creator channels, excluding news/media,
- or stratified by category?

3. Metrics to emphasize

The metrics I think need cross-channel comparison most are:

- core-audience share
- repeat-commenter retention
- community concentration
- bridge/community structure
- negative sentiment rate
- negative hotspot amplification
- reply-thread conflict rate

Are these the right metrics for the final report, or should we cut some?

4. Comment scope

Current design:

- top-level comments for core audience, tiers, retention, commenter network
  metrics, and video shared-audience network metrics
- all comments, including replies, for sentiment, negative hotspots, and
  reply-thread conflict

This avoids mixing reply behavior into audience-structure metrics, but still
uses replies where conflict/sentiment actually matter. Does this distinction
make sense?

5. Final deliverable

Possible final deliverables:

- single-channel report generator
- benchmark cohort dashboard/table
- final written case study using DoDoMen or 錫蘭 as an example
- methodology appendix explaining crawler, Qwen, and network metrics

We need to decide what is realistic for the final deadline.

## Next Steps

Short term:

- Continue the crawler after YouTube quota resets.
- Finish the remaining 1,179 queued videos.
- Generate configs for newly completed channels.
- Resume Qwen for 見習網美小吳 under the expanded DB scope.
- Run Qwen for additional benchmark channels once crawled.

Medium term:

- Implement the benchmark aggregation layer from completed runs under `runs/`.
- Compute cohort distributions and percentiles.
- Add benchmark interpretation into the Markdown report.
- Decide which channel to use as the main demo in the final presentation.

Risks:

- YouTube API quota is the main bottleneck.
- Full Qwen sentiment is expensive for channels with hundreds of thousands of
  comments. Concrete measured examples: Xilan Ceylan has about 1.55M
  subscribers; this run covered 112 non-Shorts videos and 250,589 all comments
  (171,175 top-level + 79,414 replies), and Qwen sentiment took 29,832 seconds,
  about 8h 17m. Onion Man has about 1.45M subscribers; this run covered 118
  videos and 109,733 all comments, and Qwen sentiment took 11,844 seconds,
  about 3h 17m. WalkerDad has about 1.50M subscribers; this run covered 473
  videos and 88,414 all comments, and Qwen sentiment took 9,141 seconds, about
  2h 32m.
- The benchmark layer needs enough completed channels to make percentile
  statements meaningful.

## Suggested Final Story

The final project can be presented as:

> A config-driven YouTube channel community analyzer that combines metadata,
> comments, Qwen-assisted theme/sentiment labeling, and audience/video network
> analysis to produce bilingual community health reports. To make metrics
> interpretable, the system adds a benchmark cohort layer: completed channel
> runs are aggregated into reference distributions, allowing a target channel's
> core-audience share, retention, concentration, sentiment, and conflict
> metrics to be interpreted relative to comparable channels.
