# DoDoMen Ian/Eric Delta Labels

This folder tracks DoDoMen-specific Ian/Eric/Collab labels outside the generic
ChannelCommunityAnalyzer pipeline.

The generic project must not depend on these labels. They are only for the
optional DoDoMen appendix inherited from `../ResearchA/`.

## Current Status

- Old ResearchA CSV: `../ResearchA/video_label_sheet_done.csv`
  - 343 rows
  - Last labeled video: 2026-04-08
- Current shared DB non-Short DoDoMen scope:
  - 351 long videos
  - 351 labeled in `video_labels`
  - 5 delta labels confirmed by the user on 2026-06-04 and written to the
    shared DB as `labeler=human_delta_confirmed`.
- Three videos absent from the old CSV are already labeled in the shared DB:
  - `dFgrvH2lXHY`: `ian`
  - `dDMMc4695wY`: `collab`
  - `PZ0sLJjt_kY`: `eric`

## Candidate Labels

`ian_eric_delta_labels_20260604.csv` contains:

- 3 existing DB labels that should be copied into any refreshed ResearchA CSV.
- 5 delta labels confirmed by the user in chat on 2026-06-04.

`video_label_sheet_refreshed_review_20260604.csv` is the 351-video review sheet
for the current non-Short DoDoMen scope. It merges the shared DB's existing
`video_labels` rows with the delta labels above:

- `current_db_label`: existing DB label, already usable.
- `review_label`: existing DB label when present, otherwise candidate label.
- `needs_review`: currently `false` for all rows after the confirmed labels
  were imported.

`apply_confirmed_delta_labels.sql` is a convenience patch for the shared DB.
The user has confirmed the five labels and the DB has already been updated.

## Likely Missing Labels

| video_id | Candidate | Confidence | Caveat |
| :-- | :-- | :-- | :-- |
| `0dYYLxnQaJM` | `collab` | medium-high | Jeannie/team presence may matter; verify Ian and Eric are both primary. |
| `mITaFHhulzg` | `other` | user-confirmed | Team/employee-led under the strict rule. |
| `Q4CCBr_Q8Dc` | `collab` | high | Could be `other` only if pure MV is treated as non-host content. |
| `RUzLq2n6MOQ` | `collab` | high | Behind-the-scenes appears Ian+Eric joint. |
| `VbwkmeHIkJs` | `eric` | high | Comment evidence strongly identifies it as Eric solo travel. |
