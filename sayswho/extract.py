"""HTML to text, and wall detection.

Stdlib only, on purpose for now. A real Readability port would extract better, and extraction quality is not
a cosmetic concern here: if the extractor drops the sentence that supports a claim, the judge returns
NOT_FOUND_IN_SOURCE and the pipeline records a false negative that looks exactly like a real finding.

That risk is why `extract_text` is behind a function boundary rather than inlined into the fetcher. Swapping
in trafilatura or readability-lxml is a one-line change, and it is a dependency decision that has not been
made yet.
"""

from __future__ import annotations

import re
from html.parser import HTMLParser

#: Below this many characters of extracted text, a 200 response is SOURCE_EMPTY rather than SOURCE_OK.
#: DATA_CONTRACT.md §5.
EMPTY_THRESHOLD = 200

_DROP_TAGS = {
    "script",
    "style",
    "noscript",
    "template",
    "svg",
    "nav",
    "header",
    "footer",
    "aside",
    "form",
    "iframe",
}

_BLOCK_TAGS = {
    "p", "div", "br", "li", "tr", "section", "article", "h1", "h2", "h3", "h4", "h5", "h6",
    "blockquote", "pre", "td", "th",
}

# Markers that suggest the body was withheld rather than absent. Deliberately conservative: a false
# SOURCE_PAYWALLED is a claim excluded from the denominator for the wrong reason.
_PAYWALL_MARKERS = (
    "subscribe to continue",
    "subscribe to read",
    "this article is for subscribers",
    "subscribers only",
    "already a subscriber",
    "create an account to continue reading",
    "to continue reading",
    "metered paywall",
    "paywall",
)

_CONSENT_MARKERS = (
    "accept all cookies",
    "we value your privacy",
    "manage your cookie preferences",
    "before you continue to",
    "enable javascript and cookies to continue",
    "consent to the use of cookies",
)


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._parts: list[str] = []
        self._skip_depth = 0
        self._skip_tag: str | None = None

    def handle_starttag(self, tag, attrs):
        if self._skip_depth:
            if tag == self._skip_tag:
                self._skip_depth += 1
            return
        if tag in _DROP_TAGS:
            self._skip_tag = tag
            self._skip_depth = 1
            return
        if tag in _BLOCK_TAGS:
            self._parts.append("\n")

    def handle_endtag(self, tag):
        if self._skip_depth:
            if tag == self._skip_tag:
                self._skip_depth -= 1
                if self._skip_depth == 0:
                    self._skip_tag = None
            return
        if tag in _BLOCK_TAGS:
            self._parts.append("\n")

    def handle_data(self, data):
        if self._skip_depth:
            return
        self._parts.append(data)

    def text(self) -> str:
        joined = "".join(self._parts)
        joined = re.sub(r"[ \t\r\f\v]+", " ", joined)
        joined = re.sub(r" *\n *", "\n", joined)
        joined = re.sub(r"\n{3,}", "\n\n", joined)
        return joined.strip()


def extract_text(html: str) -> str:
    """Extracted, whitespace-normalised text. Never raises on malformed markup."""
    parser = _TextExtractor()
    try:
        parser.feed(html)
        parser.close()
    except Exception:
        # Malformed markup returns whatever was parsed before the failure. An extractor that raises would
        # turn a bad page into a pipeline crash, and a bad page is a finding, not an error.
        pass
    return parser.text()


def detect_wall(text: str) -> str | None:
    """Return 'paywall', 'consent', or None.

    Heuristic, and it will be wrong in both directions. DATA_CONTRACT.md §5 commits to saying so rather than
    presenting the paywall count as exact.
    """
    lowered = text.lower()
    for marker in _PAYWALL_MARKERS:
        if marker in lowered:
            return "paywall"
    for marker in _CONSENT_MARKERS:
        if marker in lowered:
            return "consent"
    return None


def normalise_for_span(text: str) -> str:
    """Whitespace and case normalisation used by the span guard in Phase 3.

    Kept here so the fetcher, the harness and the extension all normalise identically. If they diverged, the
    extension could confirm a span the harness rejects, and the §9 parity check exists precisely to catch
    that class of disagreement.
    """
    return re.sub(r"\s+", " ", text).strip().casefold()
