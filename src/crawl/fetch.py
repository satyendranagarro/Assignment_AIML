"""HTTP fetch helpers for allowlisted seed URLs."""

from __future__ import annotations

import re
import time
from dataclasses import dataclass
from typing import Callable
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential

from src.crawl.robots import RobotsCache
from src.data.models import Source

# Educational excerpt cap for all-rights-reserved sources (chars of text).
DEFAULT_EXCERPT_CHARS = 12_000
# Below this, treat a "successful" fetch as thin and prefer manual fallback.
THIN_BODY_CHARS = 500


@dataclass
class FetchOutcome:
    url: str
    ok: bool
    status_code: int | None
    content_type: str | None
    body: str
    title: str
    extension: str
    error: str | None = None
    blocked_by_robots: bool = False
    used_excerpt: bool = False


def host_allowed(url: str, allowlist: tuple[str, ...] | list[str]) -> bool:
    host = urlparse(url).netloc.lower()
    if host.startswith("www."):
        bare = host[4:]
    else:
        bare = host
    allowed = {h.lower() for h in allowlist}
    return host in allowed or bare in allowed or f"www.{bare}" in allowed


def extract_title(html: str, fallback: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    og = soup.find("meta", property="og:title")
    if og and og.get("content"):
        return str(og["content"]).strip() or fallback
    if soup.title and soup.title.string:
        return soup.title.string.strip() or fallback
    h1 = soup.find("h1")
    if h1:
        return h1.get_text(" ", strip=True) or fallback
    return fallback


def html_to_excerpt(html: str, *, max_chars: int = DEFAULT_EXCERPT_CHARS) -> str:
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "noscript", "svg", "iframe", "nav", "footer"]):
        tag.decompose()
    text = soup.get_text("\n")
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.splitlines()]
    body = "\n".join(line for line in lines if line)
    body = re.sub(r"\n{3,}", "\n\n", body).strip()
    if len(body) > max_chars:
        body = body[:max_chars].rstrip() + "\n\n[Excerpt truncated for educational reuse limits.]"
    return body


def prefers_excerpt(source: Source) -> bool:
    return "all rights reserved" in (source.license or "").lower()


class SeedFetcher:
    """Fetch only allowlisted seed URLs with delay + optional robots checks."""

    def __init__(
        self,
        *,
        user_agent: str,
        delay_seconds: float = 1.5,
        respect_robots: bool = True,
        timeout: float = 30.0,
        sleep_fn: Callable[[float], None] | None = None,
        client: httpx.Client | None = None,
    ) -> None:
        self.user_agent = user_agent
        self.delay_seconds = delay_seconds
        self.respect_robots = respect_robots
        self.timeout = timeout
        self._sleep = sleep_fn or time.sleep
        self._owns_client = client is None
        self.client = client or httpx.Client(
            headers={"User-Agent": user_agent, "Accept": "text/html,application/xhtml+xml"},
            follow_redirects=True,
            timeout=timeout,
        )
        self.robots = RobotsCache(user_agent=user_agent, timeout=min(timeout, 15.0))
        self._last_request_at = 0.0

    def close(self) -> None:
        if self._owns_client:
            self.client.close()

    def __enter__(self) -> SeedFetcher:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def _throttle(self) -> None:
        if self.delay_seconds <= 0:
            return
        elapsed = time.monotonic() - self._last_request_at
        remaining = self.delay_seconds - elapsed
        if remaining > 0:
            self._sleep(remaining)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=0.5, min=0.5, max=4), reraise=True)
    def _get(self, url: str) -> httpx.Response:
        self._throttle()
        resp = self.client.get(url)
        self._last_request_at = time.monotonic()
        return resp

    def fetch_seed(self, source: Source, url: str) -> FetchOutcome:
        if not host_allowed(url, source.allowlist_hosts):
            return FetchOutcome(
                url=url,
                ok=False,
                status_code=None,
                content_type=None,
                body="",
                title=source.citation.title,
                extension=".html",
                error=f"host not allowlisted for {source.id}",
            )

        if self.respect_robots and not self.robots.allowed(url, client=self.client):
            return FetchOutcome(
                url=url,
                ok=False,
                status_code=None,
                content_type=None,
                body="",
                title=source.citation.title,
                extension=".html",
                error="blocked by robots.txt",
                blocked_by_robots=True,
            )

        try:
            resp = self._get(url)
        except Exception as exc:  # noqa: BLE001 — surface as crawl outcome
            return FetchOutcome(
                url=url,
                ok=False,
                status_code=None,
                content_type=None,
                body="",
                title=source.citation.title,
                extension=".html",
                error=str(exc),
            )

        content_type = resp.headers.get("content-type", "")
        if resp.status_code >= 400:
            return FetchOutcome(
                url=url,
                ok=False,
                status_code=resp.status_code,
                content_type=content_type,
                body="",
                title=source.citation.title,
                extension=".html",
                error=f"HTTP {resp.status_code}",
            )

        raw = resp.text
        title = extract_title(raw, source.citation.title) if "html" in content_type.lower() or raw.lstrip().startswith("<") else source.citation.title

        if prefers_excerpt(source):
            body = html_to_excerpt(raw)
            return FetchOutcome(
                url=str(resp.url),
                ok=True,
                status_code=resp.status_code,
                content_type=content_type,
                body=body,
                title=title,
                extension=".md",
                used_excerpt=True,
            )

        return FetchOutcome(
            url=str(resp.url),
            ok=True,
            status_code=resp.status_code,
            content_type=content_type,
            body=raw,
            title=title,
            extension=".html",
            used_excerpt=False,
        )
