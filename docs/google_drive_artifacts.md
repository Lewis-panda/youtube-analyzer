# Google Drive Artifacts

Large generated artifacts are intentionally not committed to GitHub.

The repository tracks code, configs, docs, dashboard source, a small
`dashboard_data/` demo snapshot, and compact benchmark summary tables. Full run
directories, raw Qwen CSVs, reply-thread tables, legacy zips, and local SQLite
databases should live outside Git and can be shared through Google Drive.

The point is reproducibility: collaborators should compute from the same
restored artifact files. Frontend changes should not alter the underlying
statistics; metric changes belong in analyzer/builder code plus an explicit
artifact refresh.

For ordinary GitHub collaboration, these artifacts are sufficient. Collaborators
do not need to run Qwen or any semantic analysis stage unless the team is
intentionally creating a new artifact release.

Minimal dependency rule: downloading artifacts uses Python standard library
only. Rebuilding `dashboard_data/` currently needs `pandas`, available through
`requirements-dashboard.txt`. Do not install full analyzer, crawler, browser,
or Qwen dependencies just to restore artifacts.

The committed shared manifest is:

```text
artifacts/google_drive_manifest.public.json
```

The current public artifact files are:

- `baseline_runs_full`: `https://drive.google.com/file/d/15MDTKPfBofg_BNpyJ0RlAL6__HwunCZJ/view?usp=sharing`
- `dodomen_case_study_outputs`: `https://drive.google.com/file/d/1gTPF_jqE441W7CuGsDmYZ1OdtDUfIhQN/view?usp=sharing`

By default, `scripts/download_drive_artifacts.py` uses this public manifest and
verifies SHA-256 checksums before extraction. Use
`artifacts/google_drive_manifest.json` only as a private local override.

## Recommended Bundles

For collaborators who need to rebuild baselines or inspect completed runs:

```bash
(cd baseline_runs && zip -r ../artifacts/drive_uploads/baseline_runs_full_clean_20260606.zip . \
  -x '*/__pycache__/*' '*/.matplotlib/*' '.matplotlib/*')
```

For optional DoDoMen appendix work:

```bash
(cd case_studies/dodomen && zip -r ../../artifacts/drive_uploads/dodomen_case_study_outputs_clean_20260606.zip . \
  -x '*/__pycache__/*' '*/.matplotlib/*' '.matplotlib/*')
```

When building the Drive zips used by `scripts/download_drive_artifacts.py`,
create the archive from inside the destination directory. For example,
`baseline_runs_full` should contain the contents of `baseline_runs/`, not a
nested top-level `baseline_runs/` directory. `dodomen_case_study_outputs`
should contain the contents of `case_studies/dodomen/`, including
`dodomen-generic-demo/` and `external_criticism_v1/`.

Upload each zip to Google Drive, set the file permission to anyone-with-link
reader, and copy the file ID from the URL.

## Manifest

Copy the example manifest:

```bash
cp artifacts/google_drive_manifest.example.json artifacts/google_drive_manifest.json
```

Fill in each `drive_file_id`.

The manifest file is ignored by Git so private file IDs can stay local. If a
course team wants a public shared manifest, commit a separate sanitized manifest
only after confirming the Drive files are meant to be public.

## Restore After Clone

Collaborators can run:

```bash
python3 scripts/download_drive_artifacts.py
```

Or download one bundle:

```bash
python3 scripts/download_drive_artifacts.py --artifact baseline_runs_full
```

Downloaded zips are cached under `.artifact_downloads/` and extracted into the
manifest destination paths.

## Notes

- Do not commit raw SQLite DBs, Qwen job zips, or full comment-level outputs.
- `dashboard_data/` is a lightweight demo snapshot and can be regenerated with
  `python3 scripts/build_dashboard_index.py` after artifacts are restored.
- If Google Drive blocks scripted downloads for very large files, download the
  zip manually through a browser and place it in `.artifact_downloads/`.
