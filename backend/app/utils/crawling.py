"""Sitemap-based docs crawler.

Pipeline: locate sitemap → enumerate URLs → filter via robots.txt → fetch
each page → extract main text with BeautifulSoup → return per-page records.

Defaults: caps at 200 pages, fetches up to 5 in parallel, ignores non-HTML
URLs and pages with too little text.
"""

import asyncio
import logging
import re
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser
from xml.etree import ElementTree as ET

import httpx
from bs4 import BeautifulSoup

log = logging.getLogger(__name__)

DEFAULT_MAX_PAGES = 200
DEFAULT_CONCURRENCY = 5
DEFAULT_TIMEOUT_SECONDS = 20.0
USER_AGENT = "DocuPilotBot/0.1 (+https://github.com/)"
MIN_PAGE_CHARS = 80


@dataclass
class CrawledPage:
    url: str
    title: str
    content: str


def _origin(url: str) -> str:
    p = urlparse(url)
    return f"{p.scheme}://{p.netloc}"


async def _http_get(client: httpx.AsyncClient, url: str) -> httpx.Response | None:
    try:
        response = await client.get(url, follow_redirects=True)
        if response.status_code >= 400:
            return None
        return response
    except Exception as exc:
        log.warning("fetch failed url=%s err=%s", url, exc)
        return None


def _parse_sitemap_urls(xml_bytes: bytes) -> tuple[list[str], list[str]]:
    """Return (page_urls, nested_sitemap_urls)."""
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as exc:
        log.warning("sitemap parse error: %s", exc)
        return [], []

    ns = re.match(r"\{.*\}", root.tag)
    prefix = ns.group(0) if ns else ""

    pages: list[str] = []
    sitemaps: list[str] = []
    for elem in root.findall(f"{prefix}url/{prefix}loc"):
        if elem.text:
            pages.append(elem.text.strip())
    for elem in root.findall(f"{prefix}sitemap/{prefix}loc"):
        if elem.text:
            sitemaps.append(elem.text.strip())
    return pages, sitemaps


async def _discover_sitemap_urls(
    client: httpx.AsyncClient, base_url: str
) -> list[str]:
    """Try common sitemap locations + robots.txt; return flat list of page URLs."""
    candidates = [
        urljoin(base_url, "/sitemap.xml"),
        urljoin(base_url, "/sitemap_index.xml"),
    ]

    robots = await _http_get(client, urljoin(base_url, "/robots.txt"))
    if robots:
        for line in robots.text.splitlines():
            if line.lower().startswith("sitemap:"):
                candidates.append(line.split(":", 1)[1].strip())

    seen: set[str] = set()
    all_pages: list[str] = []
    queue = list(dict.fromkeys(candidates))

    while queue:
        sitemap_url = queue.pop(0)
        if sitemap_url in seen:
            continue
        seen.add(sitemap_url)
        response = await _http_get(client, sitemap_url)
        if not response:
            continue
        pages, nested = _parse_sitemap_urls(response.content)
        all_pages.extend(pages)
        queue.extend(s for s in nested if s not in seen)

    return list(dict.fromkeys(all_pages))


async def _load_robots(client: httpx.AsyncClient, base_url: str) -> RobotFileParser:
    rp = RobotFileParser()
    rp.set_url(urljoin(base_url, "/robots.txt"))
    response = await _http_get(client, urljoin(base_url, "/robots.txt"))
    if response:
        rp.parse(response.text.splitlines())
    else:
        rp.allow_all = True
    return rp


def _extract_main_text(html: str) -> tuple[str, str]:
    """Return (title, plain_text). Strips chrome (nav/footer/scripts)."""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "nav", "header", "footer", "aside", "form"]):
        tag.decompose()

    title_tag = soup.find("title")
    title = title_tag.get_text(strip=True) if title_tag else ""

    main = soup.find("main") or soup.find("article") or soup.find("body") or soup
    text = main.get_text(separator="\n", strip=True)
    text = re.sub(r"\n{3,}", "\n\n", text)
    if not title:
        h1 = soup.find("h1")
        if h1:
            title = h1.get_text(strip=True)
    return title or "Untitled", text


def _is_html_url(url: str) -> bool:
    bad_exts = (".pdf", ".png", ".jpg", ".jpeg", ".gif", ".svg", ".zip", ".tar", ".gz", ".css", ".js", ".xml", ".json")
    path = urlparse(url).path.lower()
    return not any(path.endswith(ext) for ext in bad_exts)


async def crawl_docs(
    base_url: str,
    max_pages: int = DEFAULT_MAX_PAGES,
    concurrency: int = DEFAULT_CONCURRENCY,
) -> list[CrawledPage]:
    headers = {"User-Agent": USER_AGENT, "Accept": "text/html"}
    timeout = httpx.Timeout(DEFAULT_TIMEOUT_SECONDS)

    async with httpx.AsyncClient(headers=headers, timeout=timeout) as client:
        sitemap_urls = await _discover_sitemap_urls(client, base_url)
        if not sitemap_urls:
            raise ValueError(
                f"No sitemap found at {base_url} (tried /sitemap.xml, /sitemap_index.xml, robots.txt)"
            )

        robots = await _load_robots(client, base_url)
        origin = _origin(base_url)

        filtered: list[str] = []
        for u in sitemap_urls:
            if not _is_html_url(u):
                continue
            if _origin(u) != origin:
                continue
            if not robots.can_fetch(USER_AGENT, u):
                continue
            filtered.append(u)
            if len(filtered) >= max_pages:
                break

        log.info(
            "crawl base=%s sitemap_urls=%d filtered=%d max_pages=%d",
            base_url, len(sitemap_urls), len(filtered), max_pages,
        )

        semaphore = asyncio.Semaphore(concurrency)

        async def fetch_one(url: str) -> CrawledPage | None:
            async with semaphore:
                response = await _http_get(client, url)
            if not response:
                return None
            content_type = response.headers.get("content-type", "")
            if "html" not in content_type.lower():
                return None
            title, text = _extract_main_text(response.text)
            if len(text) < MIN_PAGE_CHARS:
                return None
            return CrawledPage(url=url, title=title, content=text)

        results = await asyncio.gather(*(fetch_one(u) for u in filtered))
        return [page for page in results if page is not None]
