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

#: A page whose markup is large but whose extracted text is tiny was probably not extracted properly:
#: a JavaScript shell, or a body this parser could not find. Above the empty threshold nothing excludes it,
#: so the run would judge every claim against boilerplate and report a page-full of NOT_FOUND_IN_SOURCE.
#:
#: Both numbers are heuristics and neither is measured. They are set to catch the shape seen live
#: (hundreds of kilobytes of markup, a few hundred characters of text) and they will be wrong in both
#: directions. This only ever raises a flag; it never changes a G2 code, because excluding a source on a
#: guess would be the same error in the other direction.
THIN_MIN_HTML_BYTES = 50_000
THIN_MAX_TEXT_RATIO = 0.002

#: Contents that are never prose in any mode.
_NEVER_TEXT = {"script", "style", "noscript", "template"}

#: Dropped from the extraction the judge reads. `svg` is deliberately absent: chart labels and figure
#: titles live in SVG text nodes, and dropping them made every claim resting on a data visualisation
#: unfindable, which reads downstream as the source not containing the claim.
_DROP_TAGS = _NEVER_TEXT | {
    "nav",
    "header",
    "footer",
    "aside",
    "form",
    "iframe",
}

#: Attributes carrying text a reader sees. `alt` is the only description of an image the page offers, so a
#: claim resting on a chart has nowhere else to be found.
_TEXT_ATTRS = ("alt", "title", "aria-label")

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
    def __init__(self, drop_tags=_DROP_TAGS, attr_names=("alt",)) -> None:
        super().__init__(convert_charrefs=True)
        self._parts: list[str] = []
        self._skip_depth = 0
        self._skip_tag: str | None = None
        self._drop_tags = drop_tags
        self._attr_names = attr_names

    def handle_starttag(self, tag, attrs):
        if self._skip_depth:
            if tag == self._skip_tag:
                self._skip_depth += 1
            return
        if tag in self._drop_tags:
            self._skip_tag = tag
            self._skip_depth = 1
            return
        for name, value in attrs:
            if name in self._attr_names and value and value.strip():
                self._parts.append(f"\n{value.strip()}\n")
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


#: Site furniture, excluded from the raw pass as well as the strict one. This is the opposite of how the
#: function was first written, and the reason it produced false positives on its first live run: every
#: mass.gov page carries a hamburger nav linking `/topics/transportation`, so a claim mentioning
#: transportation looked like text the extractor had lost. Furniture repeated site-wide is not evidence
#: that a particular page's body said anything.
_FURNITURE = {"nav", "header", "footer", "form", "iframe"}


def raw_text(html: str) -> str:
    """Content the strict pass might have dropped, for the extraction check in `judge.py`.

    Wider than `extract_text` in the only direction that matters: it keeps `aside` and attribute text, so a
    claim's numbers hiding in a sidebar or a `title` attribute are visible. It is not "everything in the
    bytes". Scripts, styles and site furniture are excluded, because a token found in a `switch` statement
    or a navigation link is not evidence that the article contained it.

    The question this answers is "did our extractor lose this", not "does this string appear anywhere".
    """
    parser = _TextExtractor(drop_tags=_NEVER_TEXT | _FURNITURE, attr_names=_TEXT_ATTRS)
    try:
        parser.feed(html)
        parser.close()
    except Exception:
        pass
    return parser.text()


def extraction_looks_thin(text_length: int, html_bytes: int) -> bool:
    """A large page that yielded almost no text.

    Flag only. The source keeps whatever G2 code it earned, because a heuristic is not grounds for
    excluding a source from every denominator. See the constants above for why neither number is measured.
    """
    if html_bytes < THIN_MIN_HTML_BYTES:
        return False
    return text_length < html_bytes * THIN_MAX_TEXT_RATIO


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
