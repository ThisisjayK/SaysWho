"""PDF to text, stdlib only.

A PDF is a container of objects. The text on a page lives in a content stream, usually Flate-compressed,
as arguments to the text-showing operators `Tj`, `TJ`, `'` and `"`. `zlib` is in the standard library, so
the tractable case needs no dependency: decompress the streams, walk the operators, keep the strings.

**What this does not do, stated up front because it decides how the rest of the pipeline treats the
result.** It cannot read a scanned document: there is no text layer to find, and OCR is not something to
hand-roll. It cannot reliably read a PDF whose fonts use a custom CID encoding, because there the bytes in
the stream are glyph indices in a table this parser does not follow, and the "text" recovered from one is
plausible-looking rubbish. It does not reconstruct reading order across columns, so a two-column paper
comes out interleaved at the line level while remaining correct at the sentence level.

**Symbol fonts are a known unfixed gap.** A PDF may render a bullet through a font whose glyphs sit at
ordinary letter code points, so a list item that reads "\u2022 Adults who..." on screen extracts as
"x Adults who...". This parser does not follow font encodings, so it cannot know that the "x" is a bullet.
The consequence is specific and it is recorded in `FINDINGS.md` item 14: a judge quoting a bulleted line
verbatim quotes the bullet a human sees, the extracted text has a letter there instead, and the span guard
voids a correct verdict as `JUDGE_FABRICATED_SPAN`. Two of the four voids in the first live PDF audit were
this. So a fabricated-span count over PDF sources is inflated by an unknown amount and has to be reported
separately from one over HTML until this is fixed.

**Why the failure detection matters more than the extraction.** If this returns garbled text, the judge
reads a document that does not contain the claim, returns NOT_FOUND_IN_SOURCE, and the run publishes a
citation failure that is really a parser failure. `FINDINGS.md` item 11 is that exact bug, found once
already. So every path out of here either returns text this module is willing to stand behind, or a reason
it will not, and the caller turns the second into an unauditable source rather than a verdict. There is no
middle setting and no score: a document is readable or it is not.
"""

from __future__ import annotations

import re
import zlib
from dataclasses import dataclass, field

#: Text-showing operators. `Tj` and `'` take one string, `"` takes two numbers then a string, `TJ` takes an
#: array of strings and kerning numbers.
_SHOW_ONE = re.compile(rb"\((?:[^()\\]|\\.)*\)\s*(?:Tj|'|\")", re.S)
_SHOW_ARRAY = re.compile(rb"\[(.*?)\]\s*TJ", re.S)
_HEX_SHOW = re.compile(rb"<([0-9A-Fa-f\s]*)>\s*(?:Tj|'|\")", re.S)
_STRING_IN_ARRAY = re.compile(rb"\((?:[^()\\]|\\.)*\)", re.S)

#: Operators that always start a new line: `T*` moves to the next line, `ET` ends the text object.
#:
#: `T*` gets no trailing \b: the asterisk is not a word character, so the boundary can never match after it.
#: That typo cost every line break in the document, which fused the last word of each line onto the first
#: word of the next.
_HARD_BREAKS = re.compile(rb"(?:T\*|ET\b)")

#: `tx ty Td` and `tx ty TD` move the text position, and **only a vertical move is a new line**. This is not
#: a nicety. Many PDF generators place glyphs individually, emitting `Td` between characters to kern them, so
#: treating every `Td` as a line break put a newline between every letter. Collapsed, that turned the
#: boston.gov figure "(61.1%)" into "(6 1 . 1 %)".
#:
#: The cost of that was not cosmetic. The span guard demands a verbatim quote, the judge quoted the number a
#: human reads, the spaced-out version did not contain it, and four correct verdicts were thrown out and
#: counted as `JUDGE_FABRICATED_SPAN`: the one code published as a finding about the judge. The tool was
#: about to accuse a model of inventing quotes that its own PDF reader had broken.
_MOVE = re.compile(rb"(-?[\d.]+)\s+(-?[\d.]+)\s+(?:TD|Td)\b")

#: **A horizontal move inserts nothing.** Measured rather than assumed: swept from 0 to 8 unscaled units
#: against the boston.gov document, and every threshold in that range still produced "(6 1.1%)". Only
#: inserting nothing produced "(61.1%)".
#:
#: The risk of the other direction is words fusing where a PDF separates them by positioning alone. The same
#: sweep says that is not what this document does: the space ratio moves only from 0.131 to 0.123 when all
#: move-inserted spaces are removed, so almost every space here is a real space character inside a shown
#: string. Calibrated on one document and stated as such.
#:
#: There is also a floor under the failure mode. A PDF whose word spacing really is positional would come out
#: with almost no spaces, and `MIN_SPACE_RATIO` refuses such a document as garbled rather than passing a wall
#: of fused words to the judge. So the bad case degrades into a refusal, which costs coverage rather than
#: producing a wrong verdict.

#: Stream filters. Flate is the overwhelming majority of text streams. The image codecs are listed so an
#: image-only document can be recognised as one rather than reported as empty.
_IMAGE_FILTERS = (b"/DCTDecode", b"/JPXDecode", b"/CCITTFaxDecode", b"/JBIG2Decode")

#: PDF escape sequences inside a literal string.
_ESCAPES = {
    b"n": b"\n", b"r": b"\r", b"t": b"\t", b"b": b"\b", b"f": b"\f",
    b"(": b"(", b")": b")", b"\\": b"\\",
}

#: Below this, across the whole document, there is effectively no text layer at all: a scan that happens to
#: carry a header, or a form with nothing but field labels.
TRACE_CHARS = 20

#: Below this a document is short. Short is not the same as unreadable, and this module does not decide it:
#: a one-page notice with sixty words in it has a text layer and it read correctly. The fetcher applies the
#: one `EMPTY_THRESHOLD` rule that every format shares, so "too little text to audit" is decided in the same
#: place for a PDF as for a web page. What is decided here is only whether the words are reachable at all.
SHORT_CHARS = 200

#: Language-shaped text is nearly all printable and has spaces between words. CID glyph indices decoded as
#: bytes have neither: the bytes cluster low, spaces are rare because 0x20 is a glyph id like any other.
#: These two thresholds are the whole garbled test. Both are heuristics, neither is measured, and they are
#: deliberately set to refuse in the ambiguous case, because passing garbled text on produces a verdict
#: that accuses a source while refusing produces an unauditable claim that leaves every rate alone.
MIN_PRINTABLE_RATIO = 0.90
MIN_SPACE_RATIO = 0.05

OK = "PDF_OK"
NO_TEXT_LAYER = "PDF_NO_TEXT_LAYER"
GARBLED = "PDF_TEXT_GARBLED"
ENCRYPTED = "PDF_ENCRYPTED"


@dataclass
class PdfText:
    """The outcome of trying to read a PDF. `code` is `PDF_OK` or a reason this text is not usable."""

    code: str
    text: str = ""
    detail: str = ""
    #: Diagnostics, recorded so a refusal can be argued with rather than taken on faith.
    streams_found: int = 0
    streams_decoded: int = 0
    pages: int = 0
    has_images: bool = False
    printable_ratio: float = 0.0
    space_ratio: float = 0.0

    @property
    def ok(self) -> bool:
        return self.code == OK

    def to_dict(self) -> dict:
        return {
            "code": self.code,
            "detail": self.detail,
            "streams_found": self.streams_found,
            "streams_decoded": self.streams_decoded,
            "pages": self.pages,
            "has_images": self.has_images,
            "printable_ratio": round(self.printable_ratio, 4),
            "space_ratio": round(self.space_ratio, 4),
        }


def _unescape(raw: bytes) -> bytes:
    """Resolve PDF string escapes, including three-digit octal."""
    out = bytearray()
    i = 0
    while i < len(raw):
        byte = raw[i : i + 1]
        if byte != b"\\":
            out += byte
            i += 1
            continue
        nxt = raw[i + 1 : i + 2]
        if not nxt:
            break
        if nxt in _ESCAPES:
            out += _ESCAPES[nxt]
            i += 2
            continue
        if nxt.isdigit():
            octal = raw[i + 1 : i + 4]
            digits = bytes(c for c in octal if 0x30 <= c <= 0x37)
            if digits:
                out.append(int(digits, 8) & 0xFF)
                i += 1 + len(digits)
                continue
        # A backslash before a newline is a line continuation: both disappear.
        if nxt in (b"\n", b"\r"):
            i += 2
            continue
        out += nxt
        i += 2
    return bytes(out)


def _decode_string(raw: bytes) -> str:
    """A PDF literal string to text.

    PDFBaseEncoding and WinAnsi are close enough to latin-1 for the characters that carry meaning here, and
    a wrong guess shows up in the printable ratio rather than silently passing. UTF-16 text strings appear
    with a byte order mark; those are decoded properly because they are common in tagged PDFs.
    """
    if raw[:2] in (b"\xfe\xff", b"\xff\xfe"):
        try:
            return raw.decode("utf-16")
        except UnicodeDecodeError:
            pass
    return raw.decode("latin-1", errors="replace")


def _streams(data: bytes) -> list[tuple[bytes, bytes]]:
    """Every `stream ... endstream` body, paired with the object dictionary in front of it."""
    out = []
    for match in re.finditer(rb"stream\r?\n?", data):
        start = match.end()
        end = data.find(b"endstream", start)
        if end == -1:
            continue
        header = data[max(0, match.start() - 600) : match.start()]
        out.append((header, data[start:end]))
    return out


def _inflate(body: bytes) -> bytes | None:
    """Flate-decode, tolerating the truncated and mis-lengthed streams real PDFs contain."""
    for attempt in (body, body.strip(b"\r\n")):
        try:
            return zlib.decompress(attempt)
        except zlib.error:
            pass
        try:
            # Raw deflate, and a decompressor that keeps what it got before hitting damage.
            return zlib.decompressobj().decompress(attempt)
        except zlib.error:
            continue
    return None


def _text_from_content(content: bytes) -> str:
    """Pull the shown strings out of one decoded content stream, in stream order."""
    pieces: list[str] = []
    for match in re.finditer(
        rb"|".join([_SHOW_ARRAY.pattern, _SHOW_ONE.pattern, _HEX_SHOW.pattern,
                    _MOVE.pattern, _HARD_BREAKS.pattern]),
        content,
        re.S,
    ):
        chunk = match.group(0)

        if _HARD_BREAKS.fullmatch(chunk.strip()):
            pieces.append("\n")
            continue

        move = _MOVE.fullmatch(chunk.strip())
        if move:
            # Vertical movement is a new line. Horizontal movement is kerning or a gap between words, and a
            # newline there would break a word in half.
            try:
                dy = float(move.group(2))
            except ValueError:
                continue
            if dy != 0:
                pieces.append("\n")
            continue
        if chunk.rstrip().endswith(b"TJ"):
            inner = _SHOW_ARRAY.search(chunk)
            if not inner:
                continue
            for literal in _STRING_IN_ARRAY.finditer(inner.group(1)):
                pieces.append(_decode_string(_unescape(literal.group(0)[1:-1])))
            continue
        hexed = _HEX_SHOW.fullmatch(chunk.strip())
        if hexed:
            digits = re.sub(rb"\s", b"", hexed.group(1))
            if len(digits) % 2:
                digits += b"0"
            try:
                pieces.append(_decode_string(bytes.fromhex(digits.decode("ascii"))))
            except ValueError:
                pass
            continue
        literal = re.search(rb"\((?:[^()\\]|\\.)*\)", chunk, re.S)
        if literal:
            pieces.append(_decode_string(_unescape(literal.group(0)[1:-1])))
    return "".join(pieces)


def _ratios(text: str) -> tuple[float, float]:
    """Printable ratio and space ratio, the two numbers the garbled test rests on."""
    if not text:
        return 0.0, 0.0
    printable = sum(1 for c in text if c.isprintable() or c in "\n\t")
    spaces = sum(1 for c in text if c.isspace())
    return printable / len(text), spaces / len(text)


def _tidy(text: str) -> str:
    text = text.replace("\r", "\n")
    # Control characters, which are never content. A symbol font maps its glyphs to low code points, so a
    # bulleted list in this document arrives as NUL followed by a letter. Stripping the NUL is unambiguous
    # cleanup. The letter left behind is not: see the note on symbol fonts below.
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
    # Hyphenated line breaks, which are how a PDF stores a word split across two lines.
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_pdf_text(data: bytes) -> PdfText:
    """Text from a PDF, or a reason there is none to be had.

    The reasons are the point. A caller must be able to tell "this document is a photograph of a page" from
    "this parser could not cope", because the first is a finding about the citation and the second is a
    limitation of this tool, and reporting either as a claim not being supported would be a lie.
    """
    pages = len(re.findall(rb"/Type\s*/Page\b", data))
    streams = _streams(data)
    has_images = any(f in data for f in _IMAGE_FILTERS) or b"/Image" in data

    # Encryption first: everything downstream would look like damage.
    if re.search(rb"/Encrypt\b", data):
        return PdfText(
            code=ENCRYPTED,
            detail="the PDF is encrypted, so its content streams cannot be read",
            streams_found=len(streams), pages=pages, has_images=has_images,
        )

    decoded_count = 0
    collected: list[str] = []
    for header, body in streams:
        content = body
        if b"/FlateDecode" in header:
            inflated = _inflate(body)
            if inflated is None:
                continue
            content = inflated
        elif any(f in header for f in _IMAGE_FILTERS):
            continue
        elif b"/Filter" in header:
            # Some other filter: LZW, RunLength, an encryption crypt filter. Not attempted rather than
            # attempted badly.
            continue
        decoded_count += 1
        collected.append(_text_from_content(content))

    text = _tidy("".join(collected))
    printable, space = _ratios(text)

    # Nothing reachable, or so little that the pages must be pictures. The second condition is what makes
    # this a scan rather than a short document: a page of images with a running header on it.
    if len(text) < TRACE_CHARS or (has_images and len(text) < SHORT_CHARS):
        detail = (
            "no text layer: the pages are images, so the words are in a picture this tool cannot read"
            if has_images
            else "no text layer: the document carries no extractable text"
        )
        return PdfText(
            code=NO_TEXT_LAYER, text="", detail=detail,
            streams_found=len(streams), streams_decoded=decoded_count, pages=pages,
            has_images=has_images, printable_ratio=printable, space_ratio=space,
        )

    if printable < MIN_PRINTABLE_RATIO or space < MIN_SPACE_RATIO:
        return PdfText(
            code=GARBLED, text="",
            detail=(
                f"the text layer decoded to something that is not language "
                f"(printable {printable:.2f}, spaces {space:.2f}). The fonts most likely use a custom "
                f"encoding this parser does not follow, so the characters are glyph numbers rather than "
                f"letters. Refused rather than judged."
            ),
            streams_found=len(streams), streams_decoded=decoded_count, pages=pages,
            has_images=has_images, printable_ratio=printable, space_ratio=space,
        )

    return PdfText(
        code=OK, text=text,
        streams_found=len(streams), streams_decoded=decoded_count, pages=pages,
        has_images=has_images, printable_ratio=printable, space_ratio=space,
    )
