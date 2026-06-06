#!/usr/bin/env python3
from __future__ import annotations

from argparse import ArgumentParser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import csv
import json
import mimetypes
from pathlib import Path
import re
from urllib.parse import parse_qs, unquote, urlparse


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_DIR = ROOT / "dashboard_data"
STATIC_DIR = Path(__file__).resolve().parent / "static"
SAFE_NAME = re.compile(r"^[A-Za-z0-9_.-]+$")
BLOCKED_TABLES = {
    "qwen_comment_sentiment",
    "commenter_activity",
    "actor_communities",
    "reply_thread_metrics",
}


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(description="Serve the read-only Channel Community dashboard demo.")
    parser.add_argument("--host", default="127.0.0.1", help="Bind host. Use 0.0.0.0 for LAN/external access.")
    parser.add_argument("--port", type=int, default=8765, help="Bind port.")
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR, help="Generated dashboard_data directory.")
    return parser


class DashboardServer(ThreadingHTTPServer):
    def __init__(self, server_address: tuple[str, int], handler, data_dir: Path):
        super().__init__(server_address, handler)
        self.data_dir = data_dir.resolve()


class Handler(BaseHTTPRequestHandler):
    server: DashboardServer

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = unquote(parsed.path)
        query = parse_qs(parsed.query)
        try:
            if path in {"/", "/index.html"}:
                self.send_file(STATIC_DIR / "index.html", "text/html; charset=utf-8")
            elif path.startswith("/static/"):
                self.send_static(path.removeprefix("/static/"))
            elif path == "/api/index":
                self.send_json(read_json(self.server.data_dir / "index.json"))
            elif path.startswith("/api/channels/"):
                self.send_json(read_channel(self.server.data_dir, path.split("/")[-1]))
            elif path.startswith("/api/table/"):
                _, _, _, slug, table = path.split("/", 4)
                limit = int(first_query_value(query, "limit", "120"))
                self.send_json(read_table(self.server.data_dir, slug, table, limit))
            elif path.startswith("/api/report/"):
                slug = path.split("/")[-1]
                lang = first_query_value(query, "lang", "zh")
                self.send_json(read_report(self.server.data_dir, slug, lang))
            elif path.startswith("/api/figure/"):
                _, _, _, slug, figure = path.split("/", 4)
                self.send_figure(self.server.data_dir, slug, figure)
            else:
                self.send_error(HTTPStatus.NOT_FOUND, "Not found")
        except HttpError as exc:
            self.send_error(exc.status, exc.message)
        except Exception as exc:
            self.send_error(HTTPStatus.INTERNAL_SERVER_ERROR, str(exc))

    def log_message(self, fmt: str, *args) -> None:
        print(f"{self.address_string()} - {fmt % args}")

    def send_json(self, data: object, status: int = HTTPStatus.OK) -> None:
        body = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_static(self, name: str) -> None:
        if "/" in name or "\\" in name or not name:
            raise HttpError(HTTPStatus.BAD_REQUEST, "Invalid static file")
        path = STATIC_DIR / name
        ctype = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        if path.suffix == ".js":
            ctype = "text/javascript; charset=utf-8"
        elif path.suffix == ".css":
            ctype = "text/css; charset=utf-8"
        self.send_file(path, ctype)

    def send_file(self, path: Path, content_type: str) -> None:
        if not path.exists() or not path.is_file():
            raise HttpError(HTTPStatus.NOT_FOUND, "File not found")
        body = path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_figure(self, data_dir: Path, slug: str, figure: str) -> None:
        channel = read_channel(data_dir, slug)
        item = find_named_artifact(channel, "figures", figure)
        path = resolve_project_path(item["path"])
        self.send_file(path, "image/png")


class HttpError(Exception):
    def __init__(self, status: HTTPStatus, message: str):
        super().__init__(message)
        self.status = status
        self.message = message


def read_json(path: Path) -> object:
    if not path.exists():
        raise HttpError(HTTPStatus.NOT_FOUND, f"Missing JSON: {path.name}")
    return json.loads(path.read_text(encoding="utf-8"))


def read_channel(data_dir: Path, slug: str) -> dict:
    validate_name(slug, "slug")
    path = data_dir / "channels" / f"{slug}.json"
    data = read_json(path)
    if not isinstance(data, dict):
        raise HttpError(HTTPStatus.INTERNAL_SERVER_ERROR, "Invalid channel JSON")
    return data


def read_table(data_dir: Path, slug: str, table: str, limit: int) -> dict:
    validate_name(slug, "slug")
    validate_name(table, "table")
    if table in BLOCKED_TABLES:
        raise HttpError(HTTPStatus.FORBIDDEN, f"Table is not exposed in the demo: {table}")
    limit = max(1, min(limit, 500))
    channel = read_channel(data_dir, slug)
    item = find_named_artifact(channel, "tables", table)
    path = resolve_project_path(item["path"])
    rows: list[dict[str, str]] = []
    total_seen = 0
    with path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        columns = reader.fieldnames or []
        for row in reader:
            total_seen += 1
            if len(rows) < limit:
                rows.append(row)
    return {
        "slug": slug,
        "table": table,
        "path": item["path"],
        "columns": columns,
        "rows": rows,
        "limit": limit,
        "returned_rows": len(rows),
        "total_rows": total_seen,
        "truncated": total_seen > len(rows),
    }


def read_report(data_dir: Path, slug: str, lang: str) -> dict:
    validate_name(slug, "slug")
    channel = read_channel(data_dir, slug)
    reports = channel.get("reports") or {}
    key = "report_zh_md" if lang == "zh" else "report_en_md" if lang == "en" else "report_md"
    report_path = reports.get(key) or reports.get("report_md")
    if not report_path:
        raise HttpError(HTTPStatus.NOT_FOUND, "Report unavailable")
    path = resolve_project_path(str(report_path))
    if not path.exists():
        raise HttpError(HTTPStatus.NOT_FOUND, "Report file missing")
    return {
        "slug": slug,
        "lang": lang,
        "path": display_path(path),
        "text": path.read_text(encoding="utf-8", errors="replace"),
    }


def find_named_artifact(channel: dict, group: str, name: str) -> dict:
    validate_name(name, group)
    artifacts = (channel.get("artifacts") or {}).get(group) or []
    for item in artifacts:
        if item.get("name") == name:
            return item
    raise HttpError(HTTPStatus.NOT_FOUND, f"Artifact not found: {name}")


def resolve_project_path(raw: str) -> Path:
    path = (ROOT / raw).resolve()
    try:
        path.relative_to(ROOT)
    except ValueError as exc:
        raise HttpError(HTTPStatus.FORBIDDEN, "Path outside project root") from exc
    if not path.exists():
        raise HttpError(HTTPStatus.NOT_FOUND, f"Path does not exist: {raw}")
    return path


def validate_name(value: str, label: str) -> None:
    if not SAFE_NAME.match(value):
        raise HttpError(HTTPStatus.BAD_REQUEST, f"Invalid {label}: {value}")


def first_query_value(query: dict[str, list[str]], key: str, default: str) -> str:
    values = query.get(key) or []
    return values[0] if values else default


def display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def main() -> None:
    args = build_parser().parse_args()
    data_dir = args.data_dir.expanduser().resolve()
    if not (data_dir / "index.json").exists():
        raise SystemExit(f"Missing dashboard index: {data_dir / 'index.json'}")
    server = DashboardServer((args.host, args.port), Handler, data_dir)
    print(f"Serving dashboard on http://{args.host}:{args.port}")
    print("Mode: read-only; no crawler, no Qwen, no fake progress.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
