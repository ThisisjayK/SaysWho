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
import unicodedata
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
    "blockquote", "pre",
}

#: Cells end with a separator rather than a newline, so a row arrives as one line with its cells still
#: distinguishable. A table used to extract as one cell per line, which destroyed the association between a
#: row label and its value: "Recent mammography screening" and "80.3%" became two unrelated lines, and a
#: claim about the rate of that measure could not be found in the text even though the page stated it.
#:
#: This is also the unit the G1 skip count needs. A table arriving as one text block is one skip decision
#: covering every cell in it, which is why `FINDINGS.md` item 9 says the skip rate does not measure the
#: share of an answer that went unchecked.
_CELL_TAGS = {"td", "th"}
CELL_SEPARATOR = " | "

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
    def __init__(self, drop_tags=_DROP_TAGS, attr_names=("alt",), every_tag_is_a_block=False) -> None:
        super().__init__(convert_charrefs=True)
        self._parts: list[str] = []
        self._skip_depth = 0
        self._skip_tag: str | None = None
        self._drop_tags = drop_tags
        self._attr_names = attr_names
        #: XML has no fixed tag vocabulary, so there is no list of block tags to consult: an RSS title and
        #: its description are siblings with nothing between them and they fuse into one line.
        self._every_tag_is_a_block = every_tag_is_a_block

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
        if not self._skip_depth and tag in _CELL_TAGS:
            self._parts.append(CELL_SEPARATOR)
        if self._skip_depth:
            if tag == self._skip_tag:
                self._skip_depth -= 1
                if self._skip_depth == 0:
                    self._skip_tag = None
            return
        if tag in _BLOCK_TAGS or tag == "tr" or self._every_tag_is_a_block:
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
        # Empty cells collapse, and a row does not end on a separator.
        joined = re.sub(r"(?:\s*\|\s*){2,}", CELL_SEPARATOR, joined)
        joined = re.sub(r"\s*\|\s*$", "", joined, flags=re.M)
        joined = re.sub(r"^\s*\|\s*", "", joined, flags=re.M)
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


#: Characters that are the same character as far as a quoted span is concerned.
#:
#: Every entry here was a verdict thrown out. The span guard demands that a `SUPPORTED` verdict quote the
#: source verbatim, and it was comparing on whitespace and case alone. So a page using curly quotes and a
#: judge typing straight ones disagreed, and the verdict was voided as `JUDGE_FABRICATED_SPAN`: the one code
#: that is published as a finding about the judge. The rate was partly measuring this table's absence and
#: attributing it to Gemini. Three of five typographic variants failed before this existed.
_SPAN_FOLD = {
    # Quotation marks. Publishers use curly, models type straight, and PDF extraction produces both.
    "\u2018": "'", "\u2019": "'", "\u201a": "'", "\u201b": "'", "\u2032": "'", "\u02bc": "'",
    "\u201c": '"', "\u201d": '"', "\u201e": '"', "\u201f": '"', "\u2033": '"',
    "\u00ab": '"', "\u00bb": '"',
    # Dashes and minus signs. "21-day" against "21\u2013day" is the common case, and a number is exactly
    # where a voided verdict costs most.
    "\u2010": "-", "\u2011": "-", "\u2012": "-", "\u2013": "-", "\u2014": "-", "\u2015": "-",
    "\u2212": "-", "\u2043": "-",
    # One glyph a writer means as three dots.
    "\u2026": "...",
}

#: Characters that carry no meaning in a quoted span and are invisible on screen. A soft hyphen is inserted
#: by a typesetter at a line break, so a word broken across two lines in a PDF contains one and the same
#: word quoted by a judge does not.
_SPAN_DROP = frozenset("\u00ad\u200b\u200c\u200d\u2060\ufeff")

#: The Combining Diacritical Marks block, U+0300 to U+036F, and nothing else.
#:
#: These are the marks that fall out of decomposing a precomposed Latin, Greek or Cyrillic letter: the acute
#: on an "e", the umlaut on an "u", the cedilla on a "c". Dropping them makes a decomposed accent and a
#: precomposed one the same character to the span guard, which is the whole point.
#:
#: The range is a deliberate line rather than `category(c) == "Mn"`, which would have been shorter and wrong.
#: Hebrew points, Arabic vowels and the Devanagari virama are all `Mn`, and none of them is typography: the
#: virama suppresses a vowel, so removing it changes the word rather than how it was typeset. A guard that
#: quietly rewrote Hindi to make a match easier would be doing the thing this project exists to catch, and it
#: would be doing it to the citations least likely to be checked by hand.
_COMBINING_TYPOGRAPHY = (0x0300, 0x036F)


def fold_for_span(ch: str) -> str:
    """One character as the span guard sees it. May return zero, one, or several characters.

    Per character rather than per string, which is not a style choice: `report.py` locates a span inside the
    answer by building a parallel index from folded positions back to raw ones, and that index is only valid
    if folding can be done character by character. A whole-string `unicodedata.normalize` would silently
    desync it and put a highlight on the wrong words.

    Accents are folded by decomposing rather than by composing, which is what makes them fixable here at all.
    Composing is a many-to-one operation and cannot be done one character at a time: nothing this function
    can see turns an "e" followed by a combining acute into a single character, because it never sees the two
    together. Decomposing is one-to-many in the other direction, which the index already handles, and it
    reaches the same place from both sides. A precomposed "\u00e9" becomes "e", and a bare combining acute
    becomes nothing at all, which is a return value this function was already allowed to produce.
    """
    if ch in _SPAN_DROP:
        return ""
    if ch in _SPAN_FOLD:
        return _SPAN_FOLD[ch]
    # NFKC per character handles ligatures, full-width forms and ordinals. It does not touch curly quotes or
    # en dashes, which is why the table above exists as well.
    folded = unicodedata.normalize("NFKC", ch).casefold()
    low, high = _COMBINING_TYPOGRAPHY
    return "".join(
        c for c in unicodedata.normalize("NFD", folded) if not low <= ord(c) <= high
    )


def normalise_for_span(text: str) -> str:
    """Text as the span guard compares it: whitespace, case and typography folded.

    Kept here so the fetcher, the harness and the drift check all normalise identically. If they diverged,
    one could confirm a span another rejects.

    **The accent gap this used to declare is closed**, and by decomposing rather than by normalising the whole
    string, so the per-character index in `report.py` still holds. See `fold_for_span`. What replaces it is
    narrower and is stated in the same place: accents inside the Combining Diacritical Marks block are folded
    away, so "resume" now matches "r\u00e9sum\u00e9", and marks outside that block are left alone because removing them
    would change the word rather than its typography.
    """
    folded = "".join(fold_for_span(ch) for ch in text)
    return re.sub(r"\s+", " ", folded).strip()


def canonical_for_id(text: str) -> str:
    """The normalisation a claim id is derived from. **Deliberately frozen.**

    This was `normalise_for_span` until the span guard needed to fold typography, and separating them is the
    whole point. A claim id is content-addressed, gate G4 ties a gold set to those ids, and `splits.py`
    hashes them. So making the span guard more tolerant would otherwise have meant relabelling the gold set,
    which is an absurd price for a table of curly quotes, and worse, it is a price that would be paid
    silently by whoever changed the span guard next.

    Whitespace and case only, so a reflowed line is the same claim. If this ever has to change, it changes
    with a relabelling, on purpose.
    """
    return re.sub(r"\s+", " ", text).strip().casefold()


# ---------------------------------------------------------------------------------------------------
# Formats other than HTML
#
# Each of these is a small function rather than a dependency, and each one either returns text or says why
# it will not. The rule from `pdf.py` applies to all of them: text this module is willing to stand behind,
# or a refusal. Never a partial read passed off as the document, because a claim judged against half a
# document produces a NOT_FOUND_IN_SOURCE that reads as a fact about the citation.
# ---------------------------------------------------------------------------------------------------

#: Markup that shows a reader something this pipeline cannot read: a picture. Used to tell "this page said
#: nothing" apart from "this page said it in an image", which are different findings and only one of them is
#: about the citation being thin.
_PICTURE_TAGS = ("<img", "<svg", "<picture", "<canvas", "<figure")

#: Below this, a page with pictures in it is reported as having no readable text rather than as empty.
PICTURE_ONLY_MAX_TEXT = EMPTY_THRESHOLD


def looks_picture_only(html: str, text: str) -> bool:
    """Almost no text, and pictures where the text would be.

    A chart, a table rendered as an image, a scanned form. The words a claim rests on may be right there on
    screen and there is no way to reach them from here, which is a different statement from the page being
    empty and is worth its own outcome. `alt` text is already extracted, so this only fires when the page
    did not even offer that.
    """
    if len(text) >= PICTURE_ONLY_MAX_TEXT:
        return False
    lowered = html.lower()
    return any(tag in lowered for tag in _PICTURE_TAGS)


def extract_xml_text(data: bytes, every_tag_is_a_block: bool = True) -> str:
    """Text from XML or an RSS feed.

    The HTML parser handles it: XML has no navigation or sidebars to drop, so only scripts and styles are
    excluded, and every element's text is kept.

    `every_tag_is_a_block` is off for WordprocessingML, which marks its own paragraphs and cells. Leaving it
    on there put a newline after every `</w:t>`, which swallowed the cell separators and put every cell back
    on its own line.
    """
    parser = _TextExtractor(
        drop_tags=_NEVER_TEXT, attr_names=(), every_tag_is_a_block=every_tag_is_a_block
    )
    try:
        parser.feed(data.decode("utf-8", errors="replace"))
        parser.close()
    except Exception:
        pass
    return parser.text()


#: A .docx is a zip. This is the part with the words in it.
_DOCX_BODY = "word/document.xml"

#: Paragraph and cell ends in WordprocessingML. Without these every paragraph in the document fuses into
#: one line, which breaks sentence splitting downstream.
_DOCX_BREAKS = (
    ("</w:p>", "\n"),
    ("</w:tc>", CELL_SEPARATOR),
    ("</w:tr>", "\n"),
    ("<w:br/>", "\n"),
    ("<w:br />", "\n"),
)


def extract_docx_text(data: bytes) -> tuple[str, str]:
    """Text from a .docx. Returns (text, reason-it-failed).

    Stdlib only: a .docx is a zip of XML, so `zipfile` reaches the document part and the tags come off with
    the same parser the rest of this module uses. A .doc, the old binary format, is not this and is not
    attempted.
    """
    import io
    import zipfile

    try:
        with zipfile.ZipFile(io.BytesIO(data)) as bundle:
            if _DOCX_BODY not in bundle.namelist():
                return "", (
                    "the file is a zip but not a Word document: it has no word/document.xml. The old "
                    "binary .doc format is a different thing and is not attempted"
                )
            body = bundle.read(_DOCX_BODY).decode("utf-8", errors="replace")
    except (zipfile.BadZipFile, KeyError, OSError) as exc:
        return "", f"the .docx could not be opened as a zip: {exc}"

    # A cell holds a paragraph, and the paragraph's own break would put every cell on its own line, losing
    # the association between a row label and its value. That is the whole reason the table work exists, so
    # the paragraph end immediately inside a cell end is dropped first.
    body = body.replace("</w:p></w:tc>", "</w:tc>")
    for marker, replacement in _DOCX_BREAKS:
        body = body.replace(marker, replacement + marker)
    return extract_xml_text(body.encode("utf-8"), every_tag_is_a_block=False), ""
