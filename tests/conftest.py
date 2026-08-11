"""A real local HTTP server for the fetch tests.

Mocking `urlopen` would test that the code calls a mock. The politeness rules in DATA_CONTRACT.md §2 are
about what actually goes over the wire, so the tests serve real HTTP and assert on what the server received.
"""

from __future__ import annotations

import io
import sys
import threading
import zipfile
import zlib
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


def build_pdf(objects: list[bytes], extra_trailer: bytes = b"") -> bytes:
    """A minimal but structurally real PDF, so the fetch tests exercise the actual parser.

    Hand-built rather than checked in as a binary: a fixture whose construction is visible can be argued
    with, and the shape here is what the parser keys on.
    """
    out = bytearray(b"%PDF-1.7\n")
    offsets = []
    for i, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += b"%d 0 obj\n" % i + body + b"\nendobj\n"
    start = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objects) + 1)
    for off in offsets:
        out += b"%010d 00000 n \n" % off
    out += b"trailer\n<< /Size %d /Root 1 0 R %s>>\nstartxref\n%d\n%%%%EOF\n" % (
        len(objects) + 1, extra_trailer, start,
    )
    return bytes(out)


def _pdf_page(content: bytes, resources: bytes = b"", extra: list[bytes] | None = None) -> bytes:
    body = zlib.compress(content)
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /Contents 4 0 R " + resources + b">>",
        b"<< /Filter /FlateDecode /Length %d >>\nstream\n" % len(body) + body + b"\nendstream",
    ]
    return build_pdf(objects + (extra or []))


#: A PDF with a real text layer, of the kind a government or journal citation actually is.
READABLE_PDF_TEXT = (
    "Boston reported that 77.0 percent of female residents had a mammogram within the prior two years. "
    "Use was lower among recent immigrants, at 61.1 percent over the same period of measurement. "
    "Navigation costs ran from $979 to $1,759 per patient enrolled in the programme that year."
)

READABLE_PDF = _pdf_page(
    b"BT /F1 11 Tf 72 720 Td "
    b"(Boston reported that 77.0 percent of female residents had a mammogram within the prior two) Tj\n"
    b"T* (years. Use was lower among recent immigrants, at 61.1 percent over the same period of) Tj\n"
    b"T* (measurement. Navigation costs ran from $979 to $1,759 per patient enrolled in the) Tj\n"
    b"T* (programme that year.) Tj\nET"
)

#: A scan: one page, one JPEG, no text layer at all. The commonest unreadable PDF in the wild.
SCANNED_PDF = _pdf_page(
    b"q 612 0 0 792 0 0 cm /I0 Do Q",
    resources=b"/Resources << /XObject << /I0 5 0 R >> >> ",
    extra=[
        b"<< /Type /XObject /Subtype /Image /Filter /DCTDecode /Width 1700 /Height 2200 /Length 9 >>\n"
        b"stream\n\xff\xd8\xff\xe0JFIF\x00\nendstream"
    ],
)

#: A PDF whose fonts use a custom encoding, so the stream holds glyph numbers rather than letters. The
#: parser must refuse this: the "text" it can recover is plausible-looking rubbish.
CID_PDF = _pdf_page(
    b"BT /F1 11 Tf 72 720 Td <" + b"".join(b"%04x" % (i % 90 + 3) for i in range(400)) + b"> Tj ET"
)


def build_docx(paragraphs: list[str], rows: list[tuple[str, str]] | None = None) -> bytes:
    """A .docx is a zip of XML. Built here for the same reason the PDFs are."""
    body = "".join(f"<w:p><w:r><w:t>{text}</w:t></w:r></w:p>" for text in paragraphs)
    if rows:
        cells = "".join(
            f"<w:tr><w:tc><w:p><w:r><w:t>{a}</w:t></w:r></w:p></w:tc>"
            f"<w:tc><w:p><w:r><w:t>{b}</w:t></w:r></w:p></w:tc></w:tr>"
            for a, b in rows
        )
        body += f"<w:tbl>{cells}</w:tbl>"
    document = (
        '<?xml version="1.0"?><w:document xmlns:w="http://schemas.openxmlformats.org/'
        f'wordprocessingml/2006/main"><w:body>{body}</w:body></w:document>'
    )
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as bundle:
        bundle.writestr("[Content_Types].xml", "<Types/>")
        bundle.writestr("word/document.xml", document)
    return buf.getvalue()


class _Handler(BaseHTTPRequestHandler):
    #: Every request the server received, as (path, user_agent).
    log: list[tuple[str, str]] = []
    #: How many times /flaky has been hit, so it can fail twice then succeed.
    flaky_hits = 0

    def log_message(self, *args):
        pass

    def _bytes(self, status: int, payload: bytes, ctype: str):
        """Send bytes as they are. The text helper encodes, which a PDF or a zip will not survive."""
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        return self.wfile.write(payload)

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
        if self.path == "/readable.pdf":
            return self._bytes(200, READABLE_PDF, "application/pdf")
        if self.path == "/scanned.pdf":
            return self._bytes(200, SCANNED_PDF, "application/pdf")
        if self.path == "/cid.pdf":
            return self._bytes(200, CID_PDF, "application/pdf")
        if self.path == "/notes.txt":
            return self._bytes(
                200,
                (
                    "Screening uptake rose to 80.3 percent in the period measured, and costs ran from "
                    "$979 to $1,759 per patient. The programme operated across eleven sites in total, "
                    "with results reported annually to the coordinating committee for review."
                ).encode(),
                "text/plain; charset=utf-8",
            )
        if self.path == "/feed.xml":
            return self._bytes(
                200,
                b"<rss><channel><item><title>Mammography rates</title><description>Uptake among women "
                b"aged 45 and over was 80.3 percent across the state, with lower figures reported among "
                b"recent immigrants and residents of assisted housing. The coordinating committee "
                b"reviewed the figures annually and published them alongside the participation rates for "
                b"each of the eleven sites taking part in the programme.</description></item>"
                b"</channel></rss>",
                "application/rss+xml",
            )
        if self.path == "/notes.docx":
            return self._bytes(
                200,
                build_docx(
                    [
                        "Screening uptake rose to 80.3 percent in the period that was measured here.",
                        "Costs ran from $979 to $1,759 per patient across the eleven participating sites.",
                    ],
                    rows=[("Recent screening", "80.3%"), ("Immigrant uptake", "61.1%")],
                ),
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        if self.path == "/chart.html":
            # A page whose content is a picture. The words may be on the screen and there is no way to
            # reach them without OCR, which is a different finding from the page being empty.
            return self._send(
                200,
                "<html><body><figure><img src='rates.png' width='900'></figure></body></html>",
            )
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
