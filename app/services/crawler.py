import asyncio
import ipaddress
import logging
import socket
from dataclasses import dataclass
from urllib.parse import urljoin, urlsplit, urlunsplit

import httpx
from bs4 import BeautifulSoup

from app.config import Settings

logger = logging.getLogger(__name__)


class CrawlError(RuntimeError):
    pass


@dataclass
class CrawledPage:
    url: str
    title: str
    text: str


PRIORITY_TERMS = ("about", "company", "contact", "product", "service", "career", "jobs", "legal", "privacy", "terms", "pricing", "customer")


async def _assert_public_host(host: str) -> None:
    if host.lower() in {"localhost", "localhost.localdomain"}:
        raise CrawlError("Local network websites are not allowed.")
    try:
        infos = await asyncio.to_thread(socket.getaddrinfo, host, None)
    except socket.gaierror as exc:
        raise CrawlError("The company website could not be resolved.") from exc
    for info in infos:
        address = ipaddress.ip_address(info[4][0])
        if not address.is_global:
            raise CrawlError("Private or local network websites are not allowed.")


def _clean_url(value: str) -> str:
    parsed = urlsplit(value)
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path or "/", "", ""))


def _extract(html: str, url: str) -> tuple[CrawledPage, list[str]]:
    soup = BeautifulSoup(html, "html.parser")
    title = soup.title.get_text(" ", strip=True) if soup.title else ""
    for element in soup.select("script, style, svg, noscript, nav, footer, iframe, form"):
        element.decompose()
    content = soup.select_one("main") or soup.select_one("article") or soup.body or soup
    lines = []
    for element in content.select("h1, h2, h3, p, li, address"):
        value = " ".join(element.get_text(" ", strip=True).split())
        if len(value) >= 20 and value not in lines:
            lines.append(value)
    links = [urljoin(url, anchor.get("href", "")) for anchor in soup.select("a[href]")]
    return CrawledPage(url=url, title=title, text="\n".join(lines)[:30000]), links


async def crawl_website(website: str, settings: Settings) -> list[CrawledPage]:
    start = _clean_url(website)
    parsed = urlsplit(start)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise CrawlError("A valid HTTP or HTTPS company website is required.")
    await _assert_public_host(parsed.hostname)
    logger.info("crawl_started", extra={"domain": parsed.hostname, "max_pages": settings.crawl_max_pages})
    root_domain = parsed.hostname.lower().removeprefix("www.")
    queue = [start]
    visited: set[str] = set()
    pages: list[CrawledPage] = []

    async with httpx.AsyncClient(
        timeout=settings.crawl_timeout_seconds,
        headers={"User-Agent": settings.crawl_user_agent},
        follow_redirects=False,
    ) as client:
        while queue and len(pages) < settings.crawl_max_pages:
            url = queue.pop(0)
            if url in visited:
                continue
            visited.add(url)
            try:
                logger.info("crawl_fetch_started", extra={"url": url})
                response = await client.get(url)
                if response.is_redirect:
                    redirected = _clean_url(urljoin(url, response.headers.get("location", "")))
                    target = urlsplit(redirected)
                    if target.hostname:
                        await _assert_public_host(target.hostname)
                    if target.hostname and target.hostname.lower().removeprefix("www.") == root_domain:
                        queue.insert(0, redirected)
                    logger.info(
                        "crawl_redirect",
                        extra={"url": url, "status_code": response.status_code, "redirect_url": redirected},
                    )
                    continue
                response.raise_for_status()
            except (httpx.HTTPError, CrawlError) as exc:
                logger.warning(
                    "crawl_fetch_failed",
                    extra={"url": url, "error_type": type(exc).__name__, "error": str(exc)},
                )
                continue
            content_type = response.headers.get("content-type", "")
            logger.info(
                "crawl_fetch_succeeded",
                extra={"url": str(response.url), "status_code": response.status_code, "content_type": content_type, "bytes": len(response.content)},
            )
            if "text/html" not in content_type:
                logger.info("crawl_page_skipped", extra={"url": str(response.url), "reason": "non_html"})
                continue
            page, discovered = _extract(response.text[:2_000_000], str(response.url))
            if page.text:
                pages.append(page)
                logger.info(
                    "crawl_page_extracted",
                    extra={"url": page.url, "characters": len(page.text), "page_number": len(pages)},
                )
            candidates = []
            for link in discovered:
                normalized = _clean_url(link)
                target = urlsplit(normalized)
                if target.scheme in {"http", "https"} and target.hostname and target.hostname.lower().removeprefix("www.") == root_domain and normalized not in visited:
                    score = sum(term in target.path.lower() for term in PRIORITY_TERMS)
                    candidates.append((score, normalized))
            for _, candidate in sorted(set(candidates), key=lambda item: (-item[0], len(item[1]))):
                if candidate not in queue:
                    queue.append(candidate)
    if not pages:
        logger.error(
            "crawl_failed_no_pages",
            extra={"domain": parsed.hostname, "attempted_urls": len(visited)},
        )
        raise CrawlError("No readable public pages were found on the company website.")
    logger.info("crawl_completed", extra={"domain": parsed.hostname, "pages": len(pages)})
    return pages


def evidence_text(pages: list[CrawledPage]) -> str:
    return "\n\n".join(f"SOURCE: {page.url}\nTITLE: {page.title}\n{page.text}" for page in pages)
