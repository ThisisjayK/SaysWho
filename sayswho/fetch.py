"""The fetch layer. Implements DATA_CONTRACT.md sections 2 through 7.

Everything this module does is a record or a deterministic rule. It never decides whether a source supports
a claim. It decides whether we have a source at all, which is the distinction the whole project rests on.
"""

from __future__ import annotations

import socket
import ssl
import time
import urllib.error
import urllib.request
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser

from .cache import FetchCache, now_iso
from .extract import EMPTY_THRESHOLD, detect_wall, extract_text
from .records import (
    SOURCE_EMPTY,
    SOURCE_OK,
    SOURCE_PAYWALLED,
    SOURCE_ROBOTS_EXCLUDED,
    SOURCE_UNREACHABLE,
    FetchRecord,
    sha256,
)

DEFAULT_CONTACT = "kappagantula.j@northeastern.edu"
PROJECT_URL = "https://github.com/ThisisjayK/SaysWho"

#: DATA_CONTRACT.md §2. Note that urllib does not separate connect and read timeouts, so this is the total.
#: Splitting them would need a dependency, and the contract records that rather than claiming a split.
TIMEOUT_SECONDS = 20.0
RATE_LIMIT_SECONDS = 1.0
MAX_RETRIES = 2
BACKOFF_SECONDS = (2.0, 8.0)


def user_agent(contact: str = DEFAULT_CONTACT) -> str:
    return f"SaysWho/0.1 (citation audit research; +{PROJECT_URL}; {contact})"


class Fetcher:
    """Politeness, retries, caching and G2 assignment.

    Injectable `sleep` and `clock` so the rate limiter can be tested without the test suite taking a minute.
    The defaults are the real ones.
    """

    def __init__(
        self,
        cache: FetchCache,
        contact: str = DEFAULT_CONTACT,
        rate_limit: float = RATE_LIMIT_SECONDS,
        timeout: float = TIMEOUT_SECONDS,
        max_retries: int = MAX_RETRIES,
        backoff: tuple[float, ...] = BACKOFF_SECONDS,
        sleep=time.sleep,
        clock=time.monotonic,
    ) -> None:
        self.cache = cache
        self.contact = contact
        self.rate_limit = rate_limit
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff = backoff
        self._sleep = sleep
        self._clock = clock
        self._last_request: dict[str, float] = {}
        self._robots: dict[str, RobotFileParser | None] = {}
        #: Every URL this fetcher actually sent a request for. Tests assert on it, and so does the run log.
        self.requested: list[str] = []

    # ------------------------------------------------------------------ politeness

    def _host(self, url: str) -> str:
        return urlsplit(url).netloc.lower()

    def _wait_turn(self, host: str) -> None:
        """One request per second per domain. Applies to robots.txt too."""
        last = self._last_request.get(host)
        if last is not None:
            elapsed = self._clock() - last
            if elapsed < self.rate_limit:
                self._sleep(self.rate_limit - elapsed)
        self._last_request[host] = self._clock()

    def _robots_for(self, url: str) -> RobotFileParser | None:
        """Fetch and cache robots.txt for the host. None means no usable robots.txt.

        A missing or unreadable robots.txt is treated as permission, which is the conventional reading. It is
        recorded here rather than left implicit, because "we could not read robots.txt so we fetched anyway"
        is a decision, not an absence of one.
        """
        host = self._host(url)
        if host in self._robots:
            return self._robots[host]

        parts = urlsplit(url)
        robots_url = f"{parts.scheme}://{parts.netloc}/robots.txt"
        parser: RobotFileParser | None = None
        try:
            status, _, body = self._raw_request(robots_url)
            if status == 200:
                parser = RobotFileParser()
                parser.parse(body.decode("utf-8", errors="replace").splitlines())
        except Exception:
            parser = None

        self._robots[host] = parser
        return parser

    def allowed(self, url: str) -> bool:
        parser = self._robots_for(url)
        if parser is None:
            return True
        return parser.can_fetch(user_agent(self.contact), url)

    # ------------------------------------------------------------------ transport

    def _raw_request(self, url: str) -> tuple[int, dict, bytes]:
        """One HTTP request, rate limited, with the identifying User-Agent. No retries, no robots check."""
        self._wait_turn(self._host(url))
        self.requested.append(url)

        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": user_agent(self.contact),
                "Accept": "text/html,application/xhtml+xml,application/pdf;q=0.9,*/*;q=0.5",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return response.status, dict(response.headers), response.read()
        except urllib.error.HTTPError as exc:
            # An HTTP error is still a response. Read it so the status and body are recorded.
            body = b""
            try:
                body = exc.read()
            except Exception:
                pass
            return exc.code, dict(exc.headers or {}), body

    # ------------------------------------------------------------------ the fetch

    def fetch(self, url: str, use_cache: bool = True) -> FetchRecord:
        """Fetch one cited URL and assign its G2 code."""
        if use_cache:
            cached = self.cache.latest(url)
            if cached is not None:
                meta, body = cached
                return self._classify(url, meta["status"], body, meta["fetched_at"], attempts=0, cached=True)

        if not self.allowed(url):
            return FetchRecord(
                url=url,
                code=SOURCE_ROBOTS_EXCLUDED,
                fetched_at=now_iso(),
                attempts=0,
                detail="robots.txt disallows this path, so no request was made",
            )

        attempts = 0
        last_detail = ""
        while True:
            attempts += 1
            try:
                status, headers, body = self._raw_request(url)
            except (urllib.error.URLError, socket.timeout, ssl.SSLError, TimeoutError) as exc:
                status, headers, body = None, {}, b""
                last_detail = f"{type(exc).__name__}: {exc}"
            else:
                last_detail = ""

            retryable = status is None or status >= 500
            if retryable and attempts <= self.max_retries:
                # DATA_CONTRACT.md §2: retries on timeout and 5xx only. A 4xx is an answer, not a failure
                # to get one, so it never reaches here.
                self._sleep(self.backoff[min(attempts - 1, len(self.backoff) - 1)])
                continue
            break

        if status is None:
            return FetchRecord(
                url=url,
                code=SOURCE_UNREACHABLE,
                fetched_at=now_iso(),
                attempts=attempts,
                detail=last_detail,
            )

        meta = self.cache.put(url, status, headers, body)
        return self._classify(url, status, body, meta["fetched_at"], attempts=attempts, cached=False)

    def _classify(
        self, url: str, status: int, body: bytes, fetched_at: str, attempts: int, cached: bool
    ) -> FetchRecord:
        """Assign the G2 code. Deterministic, and the only place a code is chosen."""
        base = dict(
            url=url,
            fetched_at=fetched_at,
            http_status=status,
            content_sha256=sha256(body),
            attempts=attempts,
            detail="from cache" if cached else "",
        )

        if status != 200:
            return FetchRecord(code=SOURCE_UNREACHABLE, text_length=0, **base)

        text = extract_text(body.decode("utf-8", errors="replace"))

        # Wall detection runs before the length threshold. A paywalled page usually is short, and reporting
        # it as SOURCE_EMPTY would lose the reason it was empty.
        wall = detect_wall(text)
        if wall is not None:
            return FetchRecord(
                code=SOURCE_PAYWALLED,
                text_length=len(text),
                text=text,
                **{**base, "detail": f"{wall} wall detected"},
            )

        if len(text) < EMPTY_THRESHOLD:
            return FetchRecord(
                code=SOURCE_EMPTY,
                text_length=len(text),
                text=text,
                **{**base, "detail": f"{len(text)} chars extracted, threshold {EMPTY_THRESHOLD}"},
            )

        return FetchRecord(code=SOURCE_OK, text_length=len(text), text=text, **base)
