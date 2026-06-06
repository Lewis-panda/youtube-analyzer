from __future__ import annotations

import json
import re
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import quote

from .config import AnalyzerConfig

if TYPE_CHECKING:
    from .data import ChannelData


DEFAULT_PTT_BOARDS = [
    "Gossiping",
    "C_Chat",
    "WomenTalk",
    "YouTuber",
    "joke",
    "movie",
    "media-chaos",
    "HatePolitics",
    "Boy-Girl",
    "PublicIssue",
]

POST_LINK_RE = re.compile(r"/f/([a-zA-Z0-9_-]+)/p/(\d+)")


@dataclass
class PttPost:
    board: str
    keyword: str
    title: str
    url: str
    date: str
    author: str
    push_score: str
    body: str = ""
    pushes: int = 0
    boos: int = 0
    comment_count: int = 0
    fetched: bool = False


@dataclass
class DcardPost:
    keyword: str
    forum: str
    id: str
    url: str
    title: str = ""
    content: str = ""
    like_count: int = 0
    comment_count: int = 0
    created_at: str = ""
    fetched: bool = False


def build_external_search_keywords(config: AnalyzerConfig, data: "ChannelData") -> list[str]:
    raw = []
    raw.extend(config.external_analysis.channel_aliases)
    for value in [
        data.channel.get("title"),
        config.channel_handle,
        config.channel_url.rstrip("/").split("/")[-1] if config.channel_url else None,
    ]:
        text = str(value or "").strip()
        if text:
            raw.append(text.lstrip("@"))

    expanded: list[str] = []
    for item in raw:
        expanded.extend(split_keyword_variants(item))

    seen = set()
    out = []
    for keyword in expanded:
        normalized = normalize_keyword(keyword)
        if not normalized or normalized in seen or is_too_generic_keyword(keyword):
            continue
        seen.add(normalized)
        out.append(keyword.strip())
    return out


def split_keyword_variants(value: str) -> list[str]:
    text = re.sub(r"\s+", " ", str(value or "").strip().lstrip("@"))
    if not text:
        return []
    variants = [text]
    for part in re.split(r"[-｜|/,:：()\[\]【】]+", text):
        part = part.strip()
        if part:
            variants.append(part)
    cjk = re.sub(r"[A-Za-z0-9_@\-\s]+", "", text).strip()
    if cjk:
        variants.append(cjk)
    ascii_text = re.sub(r"[^A-Za-z0-9_@\s]+", " ", text).strip()
    if ascii_text:
        variants.append(ascii_text)
        compact = re.sub(r"\s+", "", ascii_text)
        if compact != ascii_text:
            variants.append(compact)
    return variants


def normalize_keyword(value: str) -> str:
    return re.sub(r"\s+", "", str(value or "").strip().lower())


def is_too_generic_keyword(value: str) -> bool:
    text = str(value or "").strip()
    normalized = normalize_keyword(text)
    if not normalized:
        return True
    if re.fullmatch(r"[A-Za-z0-9_]+", normalized):
        return len(normalized) < 3
    return len(normalized) < 2


def scrape_external_sources(
    output_dir: Path,
    keywords: list[str],
    *,
    sources: list[str],
    metadata: dict | None = None,
    ptt_boards: list[str] | None = None,
    ptt_max_pages: int = 30,
    dcard_scroll_passes: int = 8,
    dcard_headless: bool = False,
    allow_partial: bool = True,
) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / "external_source_manifest.json"
    manifest = read_existing_manifest(manifest_path)
    manifest.update(
        {
        "output_dir": str(output_dir),
        "metadata": metadata or {},
        "keywords": keywords,
        "sources": manifest.get("sources", {}),
        }
    )
    for source in sources:
        source = source.strip().lower()
        if source == "ptt":
            manifest["sources"]["ptt"] = run_source(
                lambda: scrape_ptt_to_dir(
                    output_dir / "ptt",
                    keywords,
                    boards=ptt_boards or DEFAULT_PTT_BOARDS,
                    max_pages=ptt_max_pages,
                ),
                allow_partial=allow_partial,
            )
        elif source == "dcard":
            manifest["sources"]["dcard"] = run_source(
                lambda: scrape_dcard_to_dir(
                    output_dir / "dcard",
                    keywords,
                    scroll_passes=dcard_scroll_passes,
                    headless=dcard_headless,
                ),
                allow_partial=allow_partial,
            )
        else:
            manifest["sources"][source] = {"status": "skipped_unknown_source", "posts": 0}
    write_json(manifest_path, manifest)
    return manifest


def read_existing_manifest(path: Path) -> dict:
    if not path.exists() or path.stat().st_size == 0:
        return {}
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return loaded if isinstance(loaded, dict) else {}


def run_source(fn, *, allow_partial: bool) -> dict:
    try:
        return fn()
    except Exception as exc:
        if not allow_partial:
            raise
        return {"status": "error", "posts": 0, "error": f"{type(exc).__name__}: {exc}"}


def scrape_ptt_to_dir(
    output_dir: Path,
    keywords: list[str],
    *,
    boards: list[str],
    max_pages: int,
) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    all_posts: dict[str, PttPost] = {}
    for board in boards:
        for keyword in keywords:
            print(f"[PTT:{board}] searching {keyword!r}", flush=True)
            for post in search_ptt_board(board, keyword, max_pages=max_pages):
                all_posts.setdefault(post.url, post)
            print(f"  running total: {len(all_posts):,}", flush=True)

    index_path = output_dir / "ptt_index.json"
    write_json(index_path, [asdict(post) for post in all_posts.values()])

    fetched_posts = []
    for idx, post in enumerate(all_posts.values(), 1):
        fetched_posts.append(fetch_ptt_article(post))
        if idx % 10 == 0:
            print(f"  PTT fetched {idx:,}/{len(all_posts):,}", flush=True)
        time.sleep(0.8)

    full_path = output_dir / "ptt_full.json"
    write_json(full_path, [asdict(post) for post in fetched_posts])
    fetched = sum(1 for post in fetched_posts if post.fetched)
    return {
        "status": "ok",
        "posts": len(fetched_posts),
        "fetched": fetched,
        "index_path": str(index_path),
        "full_path": str(full_path),
    }


def search_ptt_board(board: str, keyword: str, *, max_pages: int) -> list[PttPost]:
    try:
        from bs4 import BeautifulSoup
    except ModuleNotFoundError as exc:
        raise RuntimeError("PTT scraping requires beautifulsoup4") from exc

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
        )
    }
    cookies = {"over18": "1"}
    posts: list[PttPost] = []
    base = f"https://www.ptt.cc/bbs/{board}/search?q={quote(keyword)}"
    for page in range(1, max_pages + 1):
        url = base + f"&page={page}"
        try:
            response = ptt_get(url, headers=headers, cookies=cookies, timeout=20)
        except Exception as exc:
            print(f"  [PTT error] {board} p{page}: {exc}", flush=True)
            break
        if response.status_code == 404:
            break
        if response.status_code != 200:
            print(f"  [PTT http {response.status_code}] {board} p{page}", flush=True)
            break
        soup = BeautifulSoup(response.text, "html.parser")
        entries = soup.select("div.r-ent")
        if not entries:
            break
        for entry in entries:
            title_a = entry.select_one("div.title a")
            if not title_a:
                continue
            href = title_a.get("href", "")
            if not href:
                continue
            posts.append(
                PttPost(
                    board=board,
                    keyword=keyword,
                    title=title_a.get_text(strip=True),
                    url=f"https://www.ptt.cc{href}",
                    date=entry.select_one("div.date").get_text(strip=True) if entry.select_one("div.date") else "",
                    author=entry.select_one("div.author").get_text(strip=True) if entry.select_one("div.author") else "",
                    push_score=entry.select_one("div.nrec").get_text(strip=True) if entry.select_one("div.nrec") else "",
                )
            )
        time.sleep(0.8)
    return posts


def fetch_ptt_article(post: PttPost) -> PttPost:
    try:
        from bs4 import BeautifulSoup
    except ModuleNotFoundError as exc:
        raise RuntimeError("PTT scraping requires beautifulsoup4") from exc

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
        )
    }
    cookies = {"over18": "1"}
    try:
        response = ptt_get(post.url, headers=headers, cookies=cookies, timeout=20)
    except Exception as exc:
        print(f"  [PTT fetch error] {post.url}: {exc}", flush=True)
        return post
    if response.status_code != 200:
        return post
    soup = BeautifulSoup(response.text, "html.parser")
    main = soup.select_one("#main-content")
    if not main:
        return post
    pushes = main.select("div.push")
    post.pushes = sum(
        1
        for push in pushes
        if push.select_one("span.push-tag") and push.select_one("span.push-tag").get_text(strip=True) == "推"
    )
    post.boos = sum(
        1
        for push in pushes
        if push.select_one("span.push-tag") and push.select_one("span.push-tag").get_text(strip=True) == "噓"
    )
    post.comment_count = len(pushes)
    for push in pushes:
        push.decompose()
    text = main.get_text("\n", strip=False)
    post.body = re.sub(r"\n{3,}", "\n\n", text)[:8000]
    post.fetched = True
    return post


def ptt_get(url: str, *, headers: dict, cookies: dict, timeout: int):
    try:
        from curl_cffi import requests as curl_requests

        return curl_requests.get(
            url,
            headers=headers,
            cookies=cookies,
            timeout=timeout,
            impersonate="chrome120",
        )
    except ModuleNotFoundError:
        import requests

        return requests.get(url, headers=headers, cookies=cookies, timeout=timeout)


def scrape_dcard_to_dir(
    output_dir: Path,
    keywords: list[str],
    *,
    scroll_passes: int,
    headless: bool,
) -> dict:
    try:
        from camoufox.sync_api import Camoufox
    except ModuleNotFoundError as exc:
        raise RuntimeError("Dcard scraping requires camoufox; run in the SMA environment with browser support") from exc

    output_dir.mkdir(parents=True, exist_ok=True)
    all_posts: dict[str, DcardPost] = {}
    with Camoufox(headless=headless, locale="zh-TW", os="linux") as browser:
        page = browser.new_page()
        page.set_viewport_size({"width": 1366, "height": 900})
        for keyword in keywords:
            print(f"[Dcard] searching {keyword!r}", flush=True)
            links = collect_dcard_search_links(page, keyword, scroll_passes=scroll_passes)
            for key, info in links.items():
                all_posts.setdefault(
                    key,
                    DcardPost(
                        keyword=keyword,
                        forum=info["forum"],
                        id=info["id"],
                        url=f"https://www.dcard.tw/f/{info['forum']}/p/{info['id']}",
                    ),
                )
            print(f"  running total: {len(all_posts):,}", flush=True)
            time.sleep(1.5)

        index_path = output_dir / "dcard_index.json"
        write_json(index_path, [asdict(post) for post in all_posts.values()])

        for idx, post in enumerate(all_posts.values(), 1):
            try:
                page.goto(post.url, timeout=30000)
                time.sleep(2.0)
                parsed = parse_dcard_post_page(page)
                post.title = parsed["title"]
                post.content = parsed["content"]
                post.fetched = bool(parsed["content"])
            except Exception as exc:
                print(f"  [Dcard fetch error] {post.url}: {exc}", flush=True)
            if idx % 5 == 0:
                print(f"  Dcard fetched {idx:,}/{len(all_posts):,}", flush=True)
            time.sleep(1.5)

    full_path = output_dir / "dcard_full.json"
    write_json(full_path, [asdict(post) for post in all_posts.values()])
    fetched = sum(1 for post in all_posts.values() if post.fetched)
    return {
        "status": "ok",
        "posts": len(all_posts),
        "fetched": fetched,
        "index_path": str(index_path),
        "full_path": str(full_path),
    }


def collect_dcard_search_links(page, keyword: str, *, scroll_passes: int) -> dict[str, dict]:
    found: dict[str, dict] = {}
    page.goto(f"https://www.dcard.tw/search/posts?query={quote(keyword)}", timeout=30000)
    time.sleep(3.0)
    for _ in range(scroll_passes):
        html = page.content()
        for match in POST_LINK_RE.finditer(html):
            forum, post_id = match.group(1), match.group(2)
            found.setdefault(f"{forum}/{post_id}", {"forum": forum, "id": post_id})
        page.mouse.wheel(0, 2000)
        time.sleep(1.0)
    return found


def parse_dcard_post_page(page) -> dict:
    out = {"title": "", "content": ""}
    title = page.title()
    if "｜Dcard" in title:
        out["title"] = title.split("｜Dcard")[0].strip()
    try:
        article = page.locator("article").first
        if article.count() > 0:
            out["content"] = article.inner_text(timeout=5000)[:8000]
    except Exception:
        pass
    if not out["content"]:
        try:
            out["content"] = page.locator("body").inner_text(timeout=5000)[:8000]
        except Exception:
            pass
    if is_dcard_verification_page(out["content"]):
        return {"title": "", "content": ""}
    return out


def is_dcard_verification_page(text: object) -> bool:
    value = str(text or "")
    return "Dcard 需要確認您的連線是安全的" in value or "需要驗證請求是真實的人類" in value


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
