"""robots.txt checks for allowlisted crawl hosts."""

from __future__ import annotations

from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import httpx


class RobotsCache:
    """Cache RobotFileParser instances per origin.

    If robots.txt is missing or forbidden (404/403), allow fetches — matching
    urllib's usual "no robots.txt ⇒ OK" behaviour. Network errors also fail open
    so a flaky robots endpoint does not block an otherwise allowlisted seed crawl.
    """

    def __init__(self, *, user_agent: str, timeout: float = 15.0) -> None:
        self.user_agent = user_agent
        self.timeout = timeout
        self._parsers: dict[str, RobotFileParser] = {}
        self._open_origins: set[str] = set()

    def _origin(self, url: str) -> str:
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}"

    def allowed(self, url: str, *, client: httpx.Client | None = None) -> bool:
        origin = self._origin(url)
        if origin in self._open_origins:
            return True
        parser = self._parsers.get(origin)
        if parser is None:
            robots_url = f"{origin}/robots.txt"
            parser = RobotFileParser()
            parser.set_url(robots_url)
            try:
                if client is not None:
                    resp = client.get(robots_url, timeout=self.timeout)
                    if resp.status_code in {401, 403, 404}:
                        self._open_origins.add(origin)
                        return True
                    if resp.status_code >= 400:
                        self._open_origins.add(origin)
                        return True
                    parser.parse(resp.text.splitlines())
                else:
                    parser.read()
            except Exception:
                self._open_origins.add(origin)
                return True
            self._parsers[origin] = parser
        return bool(parser.can_fetch(self.user_agent, url))
