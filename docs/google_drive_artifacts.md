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

## Recommended Bundles

For collaborators who need to rebuild baselines or inspect completed runs:

```bash
zip -r baseline_runs_full.zip baseline_runs \
  -x 'baseline_runs/benchmark_baseline/*'
```

For optional DoDoMen appendix work:

```bash
zip -r dodomen_case_study_outputs.zip \
  case_studies/dodomen/dodomen-generic-demo
```

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
