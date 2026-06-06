# DoDoMen Case Study

DoDoMen materials are kept here because the final presentation needs to answer
case-specific questions about the split / host-label framing.

This is not part of the default generic channel analyzer.

Contents:

- `dodomen-generic-demo/`: full DoDoMen run artifacts, accessible through the
  compatibility symlink `runs/dodomen-generic-demo`.
- `dodomen-generic-demo/custom_labels/`: video-level labels such as
  `ian`, `eric`, `collab`, and `other`.
- `external_criticism_v1/`: older DoDoMen-specific PTT/Dcard external source
  scrape used for the appendix demo.
- `scripts/`: DoDoMen-only migration or label application helpers.

Rules:

- Do not hard-code Ian/Eric/Collab logic into the generic analyzer.
- Do not use DoDoMen external posts for other channels.
- Do not show the special split case as a normal dashboard example unless the
  presentation explicitly needs it.
