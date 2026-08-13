"""Font encodings in PDFs: the two ways a bullet became a letter.

`FINDINGS.md` item 14 recorded this as unfixed and said why: following font encodings is beyond a stdlib
reader. That was true of the general case and not of the case in front of us, and the difference matters
because the general case is what the sentence had promised.

Two bugs, one symptom. A bulleted line reading "• Adults who lived in the US for ten or fewer years
(61.1%)" extracted as "x Adults who...", and another line's bullet was deleted outright. A judge quoting
either line verbatim was voided as `JUDGE_FABRICATED_SPAN`, which is the one code published as a finding
about the judge, so the tool was on course to accuse a model of inventing quotes its own reader had broken.

- The deleted bullet was WinAnsi 0x95, decoded as latin-1 into a control character and then stripped as
  never-content. WinAnsi is a standard encoding, so no font dictionary has to be consulted to fix it.
- The letter was a two-byte code in an embedded SymbolMT subset. That one needs the font's own reverse table,
  which is in the file, and the tests below are mostly about the conditions under which it is safe to use.

The fixtures are hand-built, like the PDFs in `conftest.py`, because a binary fixture cannot be argued with.
"""

from __future__ import annotations

import zlib

from conftest import build_pdf

from sayswho.pdf import GARBLED, OK, extract_pdf_text, parse_cmap, two_byte_cmap

#: Enough prose to clear the "is there a text layer at all" floor, so these tests are about the characters
#: rather than about the length thresholds.
FILLER = (
    "(Boston reported that 77.0 percent of female residents had a mammogram within the prior two years.) Tj\n"
    "T* (Use was lower among recent immigrants, at 61.1 percent over the same period of measurement.) Tj\n"
    "T* (Navigation costs ran from $979 to $1,759 per patient enrolled in the programme that year.) Tj\n"
)


def cmap_stream(pairs: dict[int, int]) -> bytes:
    """A ToUnicode CMap object, in the form a real one takes: bfchar entries, hex, UTF-16BE destinations."""
    entries = "".join(f"<{src:04X}> <{dst:04X}>\n" for src, dst in pairs.items())
    body = (
        "/CIDInit /ProcSet findresource begin\nbegincmap\n"
        "1 begincodespacerange\n<0000> <FFFF>\nendcodespacerange\n"
        f"{len(pairs)} beginbfchar\n{entries}endbfchar\nendcmap\nend\n"
    ).encode()
    packed = zlib.compress(body)
    return b"<< /Filter /FlateDecode /Length %d >>\nstream\n" % len(packed) + packed + b"\nendstream"


def pdf_with_fonts(content: bytes, fonts: bytes, extra: list[bytes]) -> bytes:
    """One page, one content stream, and whatever font machinery a test needs behind it."""
    packed = zlib.compress(content)
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /Contents 4 0 R /Resources << /Font << " + fonts + b" >> >> >>",
        b"<< /Filter /FlateDecode /Length %d >>\nstream\n" % len(packed) + packed + b"\nendstream",
    ]
    return build_pdf(objects + extra)


#: A two-byte font showing one glyph, whose reverse table says that glyph is a bullet. Object 5 is the font,
#: object 6 is its CMap. This is the boston.gov shape, reduced to the part that broke.
SYMBOL_PDF = pdf_with_fonts(
    b"BT /F2 11 Tf 72 720 Td " + FILLER.encode()
    + b"T* /F1 11 Tf <0078> Tj /F2 11 Tf ( Adults who lived in the US for ten or fewer years) Tj ET",
    fonts=b"/F1 5 0 R /F2 7 0 R",
    extra=[
        b"<< /Type /Font /Subtype /Type0 /BaseFont /NKIKWO+SymbolMT /Encoding /Identity-H "
        b"/DescendantFonts [8 0 R] /ToUnicode 6 0 R >>",
        cmap_stream({0x0078: 0x2022}),
        b"<< /Type /Font /Subtype /TrueType /BaseFont /IKZLEY+Calibri /Encoding /WinAnsiEncoding >>",
        b"<< /Type /Font /Subtype /CIDFontType2 /BaseFont /NKIKWO+SymbolMT >>",
    ],
)


# ---------------------------------------------------------------- the standard encoding, no font needed


def test_a_winansi_bullet_survives_instead_of_being_stripped():
    """The simpler of the two bugs and the one that deleted evidence rather than corrupting it. Byte 0x95 is a
    bullet in WinAnsi and an unused control code in latin-1, and `_tidy` strips control codes as
    never-content, so the bullet disappeared between the two."""
    pdf = pdf_with_fonts(
        b"BT /F1 11 Tf 72 720 Td " + FILLER.encode()
        + rb"T* (\225 Adults who were retired \(89.3%\)) Tj ET",
        fonts=b"/F1 5 0 R",
        extra=[b"<< /Type /Font /Subtype /TrueType /BaseFont /Arial /Encoding /WinAnsiEncoding >>"],
    )
    read = extract_pdf_text(pdf)
    assert read.code == OK
    assert "• Adults who were retired" in read.text


def test_the_other_winansi_punctuation_comes_through_too():
    """The same range holds the curly apostrophe, the en dash, the em dash and the ellipsis, which is to say
    it holds most of what `_SPAN_FOLD` exists to reconcile. Each one used to arrive as a control character and
    leave as nothing, so a span quoting any of them could not be confirmed."""
    pdf = pdf_with_fonts(
        b"BT /F1 11 Tf 72 720 Td " + FILLER.encode()
        + rb"T* (the trial\222s 21\226day result \205 and more) Tj ET",
        fonts=b"/F1 5 0 R",
        extra=[b"<< /Type /Font /Subtype /TrueType /BaseFont /Arial /Encoding /WinAnsiEncoding >>"],
    )
    text = extract_pdf_text(pdf).text
    assert "trial’s" in text
    assert "21–day" in text
    assert "…" in text


# ---------------------------------------------------------------- two-byte codes, through the font's own table


def test_a_symbol_font_bullet_is_read_as_a_bullet():
    """The void behind `FINDINGS.md` item 14. Glyph 0x0078 in an embedded SymbolMT subset is a bullet, and one
    byte at a time it came out as NUL followed by "x"."""
    read = extract_pdf_text(SYMBOL_PDF)
    assert read.code == OK
    assert "• Adults who lived in the US" in read.text
    assert "x Adults who lived" not in read.text
    assert read.two_byte_codes == 1


def test_the_span_guard_now_confirms_the_bulleted_line():
    """The end the whole fix exists for. A judge quoting the line a human reads used to be voided as
    `JUDGE_FABRICATED_SPAN`, and the count of those voids is published as a finding about the judge."""
    from sayswho.judge import span_is_present

    document = extract_pdf_text(SYMBOL_PDF).text
    assert span_is_present("• Adults who lived in the US for ten or fewer years", document)


def test_a_font_dictionary_inside_a_compressed_object_stream_is_still_found():
    """Not a nicety: the real document has no `/Type /Font` in its bytes at all. All sixteen of its font
    objects live inside twenty-nine compressed object streams, so a pass that read only top-level objects
    would find no two-byte font and conclude, quietly and wrongly, that there was nothing here to fix."""
    font = b"<< /Type /Font /Subtype /Type0 /Encoding /Identity-H /ToUnicode 6 0 R >>"
    payload = b"5 0 " + font
    packed = zlib.compress(payload)
    objstm = (
        b"<< /Type /ObjStm /N 1 /First 4 /Filter /FlateDecode /Length %d >>\nstream\n" % len(packed)
        + packed + b"\nendstream"
    )
    pdf = pdf_with_fonts(
        b"BT /F2 11 Tf 72 720 Td " + FILLER.encode() + b"T* /F1 11 Tf <0078> Tj ET",
        fonts=b"/F1 5 0 R /F2 7 0 R",
        extra=[
            objstm,
            cmap_stream({0x0078: 0x2022}),
            b"<< /Type /Font /Subtype /TrueType /Encoding /WinAnsiEncoding >>",
        ],
    )
    read = extract_pdf_text(pdf)
    assert read.two_byte_codes == 1, "the font was only reachable through the object stream"
    assert "•" in read.text


# ---------------------------------------------------------------- when it must not decode


def test_a_one_byte_font_table_never_enters_the_two_byte_map():
    """The filter that makes this safe, and it is not optional. The simple WinAnsi fonts in the real document
    carry ToUnicode tables too, keyed by single-byte codes, and pooling them in produced a table where code
    120 meant both a bullet and the letter "x"."""
    pdf = pdf_with_fonts(
        b"BT /F1 11 Tf 72 720 Td " + FILLER.encode() + b"ET",
        fonts=b"/F1 5 0 R",
        extra=[
            b"<< /Type /Font /Subtype /TrueType /Encoding /WinAnsiEncoding /ToUnicode 6 0 R >>",
            cmap_stream({0x0078: 0x2022}),
        ],
    )
    table, conflicts = two_byte_cmap(pdf)
    assert table == {}, "a simple font's table says nothing about two-byte codes"
    assert conflicts == 0


def test_two_two_byte_fonts_disagreeing_about_a_code_drops_it():
    """No page resources are resolved and no `Tf` is tracked, so the tables are pooled, and pooling has to
    answer for the case where they disagree. Refusing the code leaves the bytes exactly as they were before
    any of this existed, which is the failure this whole module is allowed to have."""
    pdf = pdf_with_fonts(
        b"BT /F1 11 Tf 72 720 Td " + FILLER.encode() + b"T* <0078> Tj ET",
        fonts=b"/F1 5 0 R /F2 7 0 R",
        extra=[
            b"<< /Type /Font /Subtype /Type0 /Encoding /Identity-H /ToUnicode 6 0 R >>",
            cmap_stream({0x0078: 0x2022}),
            b"<< /Type /Font /Subtype /Type0 /Encoding /Identity-H /ToUnicode 8 0 R >>",
            cmap_stream({0x0078: 0x2020}),
        ],
    )
    table, conflicts = two_byte_cmap(pdf)
    assert 0x78 not in table
    assert conflicts == 1
    assert "•" not in extract_pdf_text(pdf).text


def test_a_string_with_an_unmapped_code_is_left_alone_entirely():
    """All or nothing per string. A partial decode would interleave real characters with glyph numbers, which
    is the plausible-looking rubbish this module refuses to produce anywhere else."""
    pdf = pdf_with_fonts(
        b"BT /F1 11 Tf 72 720 Td " + FILLER.encode() + b"T* <00780099> Tj ET",
        fonts=b"/F1 5 0 R",
        extra=[
            b"<< /Type /Font /Subtype /Type0 /Encoding /Identity-H /ToUnicode 6 0 R >>",
            cmap_stream({0x0078: 0x2022}),
        ],
    )
    assert "•" not in extract_pdf_text(pdf).text


def test_ordinary_single_byte_text_is_not_reinterpreted():
    """The condition that separates two-byte text from single-byte text that happens to resolve. Without it,
    a document with a large table could have its prose rewritten through it."""
    pdf = pdf_with_fonts(
        b"BT /F1 11 Tf 72 720 Td " + FILLER.encode() + b"T* (ab) Tj ET",
        fonts=b"/F1 5 0 R",
        extra=[
            b"<< /Type /Font /Subtype /Type0 /Encoding /Identity-H /ToUnicode 6 0 R >>",
            # 0x6162 is "ab" read as one two-byte code. Mapped, and still not applied, because the string
            # holds no control byte, so nothing about it says these were ever two-byte codes.
            cmap_stream({0x6162: 0x2022}),
        ],
    )
    text = extract_pdf_text(pdf).text
    assert text.endswith("ab")
    assert "•" not in text


def test_a_cid_document_with_no_table_is_still_refused():
    """The regression that matters most. `CID_PDF` in `conftest.py` is glyph indices with no reverse table
    anywhere, and it has to keep coming back GARBLED: passing that text to the judge produces a
    NOT_FOUND_IN_SOURCE that accuses a citation of something this parser did."""
    from conftest import CID_PDF

    read = extract_pdf_text(CID_PDF)
    assert read.code == GARBLED
    assert read.text == ""
    assert read.two_byte_codes == 0


# ---------------------------------------------------------------- the table reader itself


def test_a_bfrange_expands_and_a_bfchar_maps_one_code():
    text = (
        b"begincmap\n2 beginbfrange\n<0003> <0005> <0041>\n<0010> <0010> <0061>\nendbfrange\n"
        b"1 beginbfchar\n<0078> <2022>\nendbfchar\nendcmap"
    )
    table = parse_cmap(text)
    assert table[3] == "A" and table[4] == "B" and table[5] == "C"
    assert table[0x10] == "a"
    assert table[0x78] == "•"


def test_a_multi_unit_destination_is_kept_whole():
    """A ligature maps one code to two characters, and half a ligature is a wrong quote rather than a short
    one."""
    assert parse_cmap(b"beginbfchar\n<0001> <00660066>\nendbfchar")[1] == "ff"


def test_a_nonsense_range_is_skipped_rather_than_expanded():
    """A hostile or damaged file must not make this allocate. A reversed range yields nothing."""
    assert parse_cmap(b"beginbfrange\n<FFFF> <0000> <0041>\nendbfrange") == {}
