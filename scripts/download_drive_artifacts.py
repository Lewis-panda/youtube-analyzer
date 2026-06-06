#!/usr/bin/env python3
from __future__ import annotations

from argparse import ArgumentParser
import json
from pathlib import Path
import re
import shutil
import sys
import tempfile
from urllib.parse import parse_qs, urlparse
from urllib.request import HTTPCookieProcessor, Request, build_opener
from zipfile import ZipFile


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "artifacts" / "google_drive_manifest.json"


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(description="Download large project artifacts from Google Drive.")
    parser.add_argument(
        "--manifest",
        type=Path,
        default=DEFAULT_MANIFEST,
        help="Artifact manifest JSON. Defaults to artifacts/google_drive_manifest.json.",
    )
    parser.add_argument(
        "--artifact",
        action="append",
        default=[],
        help="Only download named artifact. Can be repeated.",
    )
    parser.add_argument(
        "--download-dir",
        type=Path,
        default=ROOT / ".artifact_downloads",
        help="Where to cache downloaded archives.",
    )
    parser.add_argument(
        "--no-extract",
        action="store_true",
        help="Download archives but do not extract them.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-download archives even if cached files already exist.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    manifest_path = args.manifest.expanduser().resolve()
    if not manifest_path.exists():
        raise SystemExit(
            f"Manifest not found: {manifest_path}\n"
            "Copy artifacts/google_drive_manifest.example.json to "
            "artifacts/google_drive_manifest.json and fill in Drive file IDs."
        )

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, list):
        raise SystemExit("Manifest must contain an artifacts list.")

    selected = set(args.artifact)
    download_dir = args.download_dir.expanduser().resolve()
    download_dir.mkdir(parents=True, exist_ok=True)

    for artifact in artifacts:
        if not isinstance(artifact, dict):
            continue
        name = str(artifact.get("name") or "").strip()
        if selected and name not in selected:
            continue
        file_id = drive_file_id(artifact)
        if not file_id or file_id.startswith("REPLACE_"):
            status = "required" if artifact.get("required") else "optional"
            print(f"skip {name or '<unnamed>'}: missing Drive file id ({status})")
            continue

        archive_path = download_dir / f"{name or file_id}.zip"
        if args.force or not archive_path.exists():
            print(f"download {name}: {archive_path}")
            download_google_drive_file(file_id, archive_path)
        else:
            print(f"cache {name}: {archive_path}")

        if not args.no_extract:
            destination = ROOT / str(artifact.get("destination") or "")
            if not destination:
                raise SystemExit(f"Artifact {name} missing destination.")
            print(f"extract {name}: {destination}")
            destination.mkdir(parents=True, exist_ok=True)
            extract_zip(archive_path, destination)


def drive_file_id(artifact: dict[str, object]) -> str:
    explicit = str(artifact.get("drive_file_id") or "").strip()
    if explicit:
        return explicit
    url = str(artifact.get("url") or artifact.get("drive_url") or "").strip()
    if not url:
        return ""
    parsed = urlparse(url)
    query_id = parse_qs(parsed.query).get("id", [""])[0]
    if query_id:
        return query_id
    match = re.search(r"/d/([^/]+)", parsed.path)
    return match.group(1) if match else ""


def download_google_drive_file(file_id: str, output_path: Path) -> None:
    opener = build_opener(HTTPCookieProcessor())
    base = "https://drive.google.com/uc?export=download&id=" + file_id
    response = opener.open(Request(base, headers={"User-Agent": "Mozilla/5.0"}))
    token = confirm_token(response)
    if token:
        response = opener.open(
            Request(base + "&confirm=" + token, headers={"User-Agent": "Mozilla/5.0"})
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(delete=False, dir=str(output_path.parent)) as tmp:
        tmp_path = Path(tmp.name)
        shutil.copyfileobj(response, tmp)
    tmp_path.replace(output_path)


def confirm_token(response: object) -> str:
    headers = getattr(response, "headers", {})
    for key, value in getattr(headers, "items", lambda: [])():
        if key.lower().startswith("set-cookie"):
            match = re.search(r"download_warning[^=]*=([^;]+)", value)
            if match:
                return match.group(1)
    return ""


def extract_zip(archive_path: Path, destination: Path) -> None:
    with ZipFile(archive_path) as archive:
        for member in archive.infolist():
            target = (destination / member.filename).resolve()
            if not str(target).startswith(str(destination.resolve())):
                raise SystemExit(f"Refusing unsafe zip path: {member.filename}")
        archive.extractall(destination)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
