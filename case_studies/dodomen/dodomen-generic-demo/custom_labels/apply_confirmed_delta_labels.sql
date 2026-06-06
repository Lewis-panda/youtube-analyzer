-- Optional DoDoMen appendix label patch.
-- Apply only after a human confirms the five candidate labels in:
-- runs/dodomen-generic-demo/custom_labels/ian_eric_delta_labels_20260604.csv
--
-- These rows intentionally use labeler='human_delta_confirmed'. Do not run this
-- if the labels were only inferred from metadata/comments.

INSERT INTO video_labels (video_id, label, labeler, labeled_at, notes)
VALUES
  ('0dYYLxnQaJM', 'collab', 'human_delta_confirmed', datetime('now'), '2026-06 delta label confirmed from manual review.'),
  ('mITaFHhulzg', 'other', 'human_delta_confirmed', datetime('now'), '2026-06 delta label confirmed from manual review.'),
  ('Q4CCBr_Q8Dc', 'collab', 'human_delta_confirmed', datetime('now'), '2026-06 delta label confirmed from manual review.'),
  ('RUzLq2n6MOQ', 'collab', 'human_delta_confirmed', datetime('now'), '2026-06 delta label confirmed from manual review.'),
  ('VbwkmeHIkJs', 'eric', 'human_delta_confirmed', datetime('now'), '2026-06 delta label confirmed from manual review.')
ON CONFLICT(video_id) DO UPDATE SET
  label = excluded.label,
  labeler = excluded.labeler,
  labeled_at = excluded.labeled_at,
  notes = excluded.notes;
