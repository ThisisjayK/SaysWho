"""PDF to text, stdlib only.

A PDF is a container of objects. The text on a page lives in a content stream, usually Flate-compressed,
as arguments to the text-showing operators `Tj`, `TJ`, `'` and `"`. `zlib` is in the standard library, so
the tractable case needs no dependency: decompress the streams, walk the operators, keep the strings.

**What this does not do, stated up front because it decides how the rest of the pipeline treats the
result.** It cannot read a scanned document: there is no text layer to find, and OCR is not something to
hand-roll. It cannot read a PDF whose fonts use a custom encoding and carry no reverse table with it, because
there the bytes in the stream are glyph indices and nothing in the file says what they stand for: the "text"
recovered from one is plausible-looking rubbish, and such a document is refused rather than read. A font that
does carry its own table is now followed through it, which is the section below. It does not reconstruct
reading order across columns, so a two-column paper comes out interleaved at the line level while remaining
correct at the sentence level.

**Symbol fonts were a known unfixed gap and are now read.** A PDF may render a bullet through a font whose
glyphs sit at ordinary letter code points, so a list item reading "\u2022 Adults who..." on screen came out as
"x Adults who...", and a judge quoting the line a human reads was voided as `JUDGE_FABRICATED_SPAN`, the one
code published as a finding about the judge. Two of the four voids in the first live PDF audit were that.

The sentence that stood here said following font encodings was beyond a stdlib reader. That was true of the
general case and false of this one, and the difference is the whole finding: the reverse table is in the
file, as an ordinary Flate stream, because a two-byte font carries a `/ToUnicode` CMap. Both halves of the
problem are fixed below, one through a standard encoding and one through the document's own table, and what
is deliberately still not done is stated where it is decided rather than here. `FINDINGS.md` item 17.

The count that rested on it is not repaired by this. The two voided spans were quoted from an extraction this
tool no longer produces, so they can only be settled by judging the fixed text, and until that run happens a
fabricated-span count over PDF sources stays reported separately from one over HTML.

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

    #: Codes in the document's two-byte table, and codes dropped because two of its fonts disagreed about
    #: them. Recorded for the same reason the ratios are: the table decides what some of this text says, so a
    #: reader has to be able to see that it was there and how much of it was refused.
    two_byte_codes: int = 0
    two_byte_conflicts: int = 0

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
            "two_byte_codes": self.two_byte_codes,
            "two_byte_conflicts": self.two_byte_conflicts,
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


#: WinAnsi, which is cp1252, differs from latin-1 in exactly one place: the range 0x80 to 0x9F, where latin-1
#: has unused control codes and cp1252 has punctuation. That range is where a bullet, a curly apostrophe, an
#: en dash and an ellipsis live, so decoding it as latin-1 produced a control character, and `_tidy` then
#: stripped it as never-content. The bullet vanished and the apostrophe with it.
#:
#: Built from the codec rather than typed, so it is Microsoft's table rather than my memory of it. The five
#: bytes cp1252 leaves undefined stay as they are, which is the same outcome as before for those.
#:
#: This is the safe half of the bullet problem: WinAnsiEncoding is a standard encoding, so no font dictionary
#: has to be consulted to know what these bytes mean. Nearly every simple font in a real PDF declares it.
_WINANSI_HIGH = {}
for _byte in range(0x80, 0xA0):
    try:
        _WINANSI_HIGH[_byte] = bytes([_byte]).decode("cp1252")
    except UnicodeDecodeError:
        pass


def _decode_string(raw: bytes) -> str:
    """A PDF literal string to text.

    PDFDocEncoding and WinAnsi are close enough to latin-1 for the characters that carry meaning here, with
    the 0x80 to 0x9F range translated afterwards: see `_WINANSI_HIGH`. A wrong guess shows up in the printable
    ratio rather than silently passing. UTF-16 text strings appear with a byte order mark; those are decoded
    properly because they are common in tagged PDFs, and they are not translated, since there the bytes were
    never single-byte codes in the first place.
    """
    if raw[:2] in (b"\xfe\xff", b"\xff\xfe"):
        try:
            return raw.decode("utf-16")
        except UnicodeDecodeError:
            pass
    return raw.decode("latin-1", errors="replace").translate(_WINANSI_HIGH)


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


# ---------------------------------------------------------------------------------------------------
# Two-byte fonts, which is the other half of the bullet problem and the harder one
#
# A Type0 font with /Encoding /Identity-H shows text as two-byte glyph indices, not characters. Decoded a
# byte at a time they come out as NUL followed by whatever the low byte happens to spell, which is how a
# bulleted line reading "\u2022 Adults who lived in the US for ten or fewer years (61.1%)" extracted as
# "x Adults who...": the bullet is glyph 0x0078 in an embedded SymbolMT subset, and 0x78 is "x".
#
# What makes this recoverable without a font model is that such a font carries a /ToUnicode CMap, which is
# the reverse table, in the file, as an ordinary Flate stream. `FINDINGS.md` item 14 recorded this as
# needing font-encoding support a stdlib reader does not have, and that was true of the general case and
# not of this one.
#
# **What is deliberately not done.** The proper route is to resolve each page's /Resources /Font dictionary
# and track the `Tf` operator, so every shown string is decoded through the font actually selected. That is
# a real object graph, and in this document it is one hidden inside compressed object streams. Instead the
# document's two-byte CMaps are unioned, a code they disagree about is dropped rather than guessed, and a
# string is decoded through the union only when every code in it resolves. Measured on the boston.gov PDF
# behind `FINDINGS.md` item 14: two two-byte fonts, nineteen codes between them, no conflicts.
#
# **Which way it errs.** Towards leaving the bytes alone. Every condition below has to hold, so the failure
# is the status quo rather than mangled text, and the ratios still guard what comes out.
# ---------------------------------------------------------------------------------------------------

#: A compressed stream larger than this is not a ToUnicode CMap. A bound on the work rather than a rule about
#: PDFs: without it, finding the CMaps would mean inflating every embedded font file in the document.
_MAX_CMAP_BYTES = 200_000

#: `<src> <dst>` inside a bfchar block, and `<lo> <hi> <dst>` inside a bfrange one.
_BFCHAR = re.compile(rb"beginbfchar(.*?)endbfchar", re.S)
_BFRANGE = re.compile(rb"beginbfrange(.*?)endbfrange", re.S)
_BF_PAIR = re.compile(rb"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>")
_BF_TRIPLE = re.compile(rb"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>")

#: An object header, so a CMap stream can be found by the object number a font refers to it by.
_OBJ_HEADER = re.compile(rb"(\d+)\s+\d+\s+obj")

#: A font that shows two-byte codes, and the object number of its reverse table.
_TWO_BYTE_FONT = re.compile(rb"/Identity-[HV]")
_TOUNICODE_REF = re.compile(rb"/ToUnicode\s+(\d+)\s+\d+\s+R")


def _utf16_be(digits: bytes) -> str:
    """A CMap destination, which is one or more UTF-16BE code units."""
    return "".join(chr(int(digits[i : i + 4], 16)) for i in range(0, len(digits) - 3, 4))


def parse_cmap(text: bytes) -> dict[int, str]:
    """Code to string, from the body of a ToUnicode CMap.

    Both forms: `beginbfchar` lists codes one at a time, `beginbfrange` gives a contiguous run and the
    character its first code maps to. A range whose destination is an array is skipped rather than guessed at,
    which costs coverage and cannot produce a wrong character.
    """
    out: dict[int, str] = {}
    for block in _BFRANGE.findall(text):
        for lo, hi, dst in _BF_TRIPLE.findall(block):
            low, high, base = int(lo, 16), int(hi, 16), int(dst, 16)
            if high < low or high - low > 0xFFFF:
                continue
            for offset in range(high - low + 1):
                out[low + offset] = chr(base + offset)
    for block in _BFCHAR.findall(text):
        for src, dst in _BF_PAIR.findall(block):
            if mapped := _utf16_be(dst):
                out[int(src, 16)] = mapped
    return out


def _numbered_objects(data: bytes) -> tuple[dict[int, bytes], dict[int, bytes]]:
    """Top-level objects by number, and the decoded body of each one that is a stream.

    Separate from `_streams`, which finds stream bodies without caring which object they belong to and is
    deliberately tolerant of files with no usable object headers at all. Here the number is the whole point:
    a font names its ToUnicode table by object number and there is no other way back to it.
    """
    bodies: dict[int, bytes] = {}
    contents: dict[int, bytes] = {}
    for match in _OBJ_HEADER.finditer(data):
        number = int(match.group(1))
        start = match.end()
        end = data.find(b"endobj", start)
        body = data[start : end if end != -1 else start + 4096]
        bodies[number] = body

        stream = re.search(rb"stream\r?\n?", body)
        if not stream:
            continue
        raw = body[stream.end() : body.find(b"endstream", stream.end())]
        if len(raw) > _MAX_CMAP_BYTES or any(f in body[: stream.start()] for f in _IMAGE_FILTERS):
            continue
        if b"/FlateDecode" in body[: stream.start()]:
            inflated = _inflate(raw)
            if inflated is not None:
                contents[number] = inflated
        else:
            contents[number] = raw
    return bodies, contents


def _objstm_objects(bodies: dict[int, bytes], contents: dict[int, bytes]) -> dict[int, bytes]:
    """Objects stored inside compressed object streams, which is where PDF 1.5 keeps its font dictionaries.

    The boston.gov document has no `/Type /Font` visible in its bytes at all: all sixteen font objects are in
    one of twenty-nine object streams. A pass that read only top-level objects would find no two-byte font
    here and conclude, wrongly and quietly, that there was nothing to fix.
    """
    out: dict[int, bytes] = {}
    for number, body in bodies.items():
        if b"/ObjStm" not in body:
            continue
        content = contents.get(number)
        count = re.search(rb"/N\s+(\d+)", body)
        first = re.search(rb"/First\s+(\d+)", body)
        if not (content and count and first):
            continue
        n, offset_zero = int(count.group(1)), int(first.group(1))
        header = content[:offset_zero].split()
        if len(header) < 2 * n:
            continue
        try:
            pairs = [(int(header[i]), int(header[i + 1])) for i in range(0, 2 * n, 2)]
        except ValueError:
            continue
        for i, (obj_number, start) in enumerate(pairs):
            end = offset_zero + (pairs[i + 1][1] if i + 1 < len(pairs) else len(content) - offset_zero)
            out[obj_number] = content[offset_zero + start : end]
    return out


def two_byte_cmap(data: bytes) -> tuple[dict[int, str], int]:
    """The document's two-byte code table, and how many codes were dropped for disagreeing.

    Only CMaps a two-byte font actually points at. That filter is what makes this safe, and it is not
    optional: the simple WinAnsi fonts in the same document carry ToUnicode tables too, keyed by single-byte
    codes, and pooling those in produced a table where code 120 meant both a bullet and the letter "x".
    """
    bodies, contents = _numbered_objects(data)
    bodies.update(_objstm_objects(bodies, contents))

    wanted: set[int] = set()
    for body in bodies.values():
        if not re.search(rb"/Type\s*/Font", body) or not _TWO_BYTE_FONT.search(body):
            continue
        if ref := _TOUNICODE_REF.search(body):
            wanted.add(int(ref.group(1)))

    table: dict[int, str] = {}
    disputed: set[int] = set()
    for number in sorted(wanted):
        content = contents.get(number)
        if not content or b"begincmap" not in content:
            continue
        for code, mapped in parse_cmap(content).items():
            if code in table and table[code] != mapped:
                disputed.add(code)
            else:
                table[code] = mapped
    for code in disputed:
        table.pop(code, None)
    return table, len(disputed)


def _decode_two_byte(raw: bytes, cmap: dict[int, str]) -> str | None:
    """The shown string read as two-byte codes, or None to leave it to the single-byte path.

    Three conditions, all of them required, because being wrong here means rewriting text that was already
    correct:

    - every two-byte code in the string resolves in the table. One unknown code and the whole string is left
      alone, since a partial decode would interleave real characters with glyph numbers;
    - the string is an even number of bytes, which two-byte codes always are;
    - and at least one byte is a control byte other than tab, newline or return. This is what separates
      two-byte text from single-byte text that happens to resolve. Two-byte codes are glyph numbers, so their
      high byte is small and the string is full of control bytes: `_tidy` already strips those as
      never-content, which is the evidence that prose does not contain them. The first version of this
      condition asked for a code above 0xFF instead, and that was worse than useless, since any two letters
      of ordinary ASCII read as one two-byte code are above 0xFF: it let "ab" be rewritten as a bullet by a
      table that happened to hold 0x6162.
    """
    if not cmap or not raw or len(raw) % 2:
        return None
    codes = [raw[i] << 8 | raw[i + 1] for i in range(0, len(raw), 2)]
    if not all(code in cmap for code in codes):
        return None
    if not any(byte < 0x20 and byte not in (0x09, 0x0A, 0x0D) for byte in raw):
        return None
    return "".join(cmap[code] for code in codes)


def _decode_shown(raw: bytes, cmap: dict[int, str]) -> str:
    """One shown string, through the two-byte table if it fits and as single-byte text otherwise."""
    mapped = _decode_two_byte(raw, cmap)
    return mapped if mapped is not None else _decode_string(raw)


def _text_from_content(content: bytes, cmap: dict[int, str] | None = None) -> str:
    """Pull the shown strings out of one decoded content stream, in stream order."""
    cmap = cmap or {}
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
                pieces.append(_decode_shown(_unescape(literal.group(0)[1:-1]), cmap))
            continue
        hexed = _HEX_SHOW.fullmatch(chunk.strip())
        if hexed:
            digits = re.sub(rb"\s", b"", hexed.group(1))
            if len(digits) % 2:
                digits += b"0"
            try:
                pieces.append(_decode_shown(bytes.fromhex(digits.decode("ascii")), cmap))
            except ValueError:
                pass
            continue
        literal = re.search(rb"\((?:[^()\\]|\\.)*\)", chunk, re.S)
        if literal:
            pieces.append(_decode_shown(_unescape(literal.group(0)[1:-1]), cmap))
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
    # Control characters, which are never content, and the reason that is safe to say: everything in this
    # range that did mean something has already been resolved. WinAnsi punctuation was translated in
    # `_decode_string`, and two-byte codes were mapped in `_decode_two_byte`, which uses the presence of these
    # very bytes as its evidence that a string held codes rather than letters. What reaches here is residue.
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

    # Built once for the whole document, before any content stream is read: the table lives in objects that
    # may appear anywhere in the file, including after the pages that use it.
    cmap, cmap_conflicts = two_byte_cmap(data)

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
        collected.append(_text_from_content(content, cmap))

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
            two_byte_codes=len(cmap), two_byte_conflicts=cmap_conflicts,
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
            two_byte_codes=len(cmap), two_byte_conflicts=cmap_conflicts,
        )

    return PdfText(
        code=OK, text=text,
        streams_found=len(streams), streams_decoded=decoded_count, pages=pages,
        has_images=has_images, printable_ratio=printable, space_ratio=space,
        two_byte_codes=len(cmap), two_byte_conflicts=cmap_conflicts,
    )
