"""A real local HTTP server for the fetch tests.

Mocking `urlopen` would test that the code calls a mock. The politeness rules in DATA_CONTRACT.md §2 are
about what actually goes over the wire, so the tests serve real HTTP and assert on what the server received.
"""

from __future__ import annotations

import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

ARTICLE = """<!doctype html>
<html><head><title>Adjuvant therapy</title>
<style>.ad{display:none}</style>
<script>window.tracking = true;</script>
</head><body>
<nav>Home About Subscribe</nav>
<article>
<h1>Adjuvant endocrine therapy duration</h1>
<p>Extending adjuvant endocrine therapy beyond five years reduced recurrence in the trial cohort,
though the absolute benefit was small and concentrated in higher risk patients.</p>
<p>The authors note that the extended duration group reported more musculoskeletal adverse events,
and that discontinuation rates rose over the second five year period.</p>
<p>No overall survival difference reached significance at the reported follow up.</p>
</article>
<footer>Copyright</footer>
</body></html>
"""

SHORT = "<!doctype html><html><body><p>Loading.</p></body></html>"

PAYWALLED = """<!doctype html><html><body>
<h1>Market size for AI assisted contract review</h1>
<p>The global market was valued at a figure that industry analysts have revised twice this year.</p>
<div class="paywall"><p>Subscribe to continue reading this article.</p></div>
</body></html>
"""

ROBOTS = "User-agent: *\nDisallow: /blocked\n"


class _Handler(BaseHTTPRequestHandler):
    #: Every request the server received, as (path, user_agent).
    log: list[tuple[str, str]] = []
    #: How many times /flaky has been hit, so it can fail twice then succeed.
    flaky_hits = 0

    def log_message(self, *args):
        pass

    def _send(self, status: int, body: str, ctype: str = "text/html; charset=utf-8"):
        payload = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self):
        type(self).log.append((self.path, self.headers.get("User-Agent", "")))

        if self.path == "/robots.txt":
            return self._send(200, ROBOTS, "text/plain; charset=utf-8")
        if self.path == "/ok.html":
            return self._send(200, ARTICLE)
        if self.path == "/short.html":
            return self._send(200, SHORT)
        if self.path == "/paywall.html":
            return self._send(200, PAYWALLED)
        if self.path == "/gzipped.html":
            import gzip

            payload = gzip.compress(ARTICLE.encode("utf-8"))
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Encoding", "gzip")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            return self.wfile.write(payload)
        if self.path == "/brotli.html":
            payload = b"\x1b\x0e\x00\xf8\x25 not really brotli, but labelled as it"
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Encoding", "br")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            return self.wfile.write(payload)
        if self.path == "/report.pdf":
            payload = b"%PDF-1.7\n1 0 obj\n<< /Type /Catalog >>\nendobj\ntrailer\n%%EOF\n"
            self.send_response(200)
            self.send_header("Content-Type", "application/pdf")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            return self.wfile.write(payload)
        if self.path == "/liar.html":
            # A PDF served as text/html. Seen in the wild from CDNs and document servers.
            payload = b"%PDF-1.4\n" + b"0" * 400
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            return self.wfile.write(payload)
        if self.path == "/forbidden.html":
            # Bot detection, as seen live on aacrjournals.org. A person clicking the link sees the page.
            return self._send(403, "<html><body>Access denied</body></html>")
        if self.path == "/ratelimited.html":
            return self._send(429, "<html><body>Too many requests</body></html>")
        if self.path == "/flaky":
            type(self).flaky_hits += 1
            if type(self).flaky_hits <= 2:
                return self._send(500, "<html><body>server error</body></html>")
            return self._send(200, ARTICLE)
        if self.path.startswith("/blocked"):
            return self._send(200, ARTICLE)
        return self._send(404, "<html><body>not found</body></html>")


@pytest.fixture
def server():
    _Handler.log = []
    _Handler.flaky_hits = 0
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    host, port = httpd.server_address

    class Server:
        base = f"http://{host}:{port}"
        handler = _Handler

        def url(self, path: str) -> str:
            return f"{self.base}{path}"

        @property
        def paths(self) -> list[str]:
            return [p for p, _ in _Handler.log]

    yield Server()
    httpd.shutdown()
    httpd.server_close()


@pytest.fixture
def cache(tmp_path):
    from sayswho.cache import FetchCache

    return FetchCache(tmp_path / "fetch-cache")
