"""The non-HTML readers: PDF, plain text, XML and .docx, plus tables and picture-only pages.

All stdlib. The tests that matter most here are the refusals. A reader that returns garbled text produces a
NOT_FOUND_IN_SOURCE, which is the one verdict with no span and therefore no G3 check, and the one that
accuses the product. `FINDINGS.md` item 11 is that bug found once already, and every case below that ends in
a refusal exists so it cannot come back through a new door.
"""

from __future__ import annotations

import io
import zipfile

import pytest

from sayswho import pdf as pdfmod
from sayswho.extract import (
    CELL_SEPARATOR,
    extract_docx_text,
    extract_text,
    extract_xml_text,
    looks_picture_only,
)
from tests.conftest import CID_PDF, READABLE_PDF, SCANNED_PDF, build_docx


# ---------------------------------------------------------------- PDF, the readable case


def test_a_text_layer_comes_out_as_sentences():
    read = pdfmod.extract_pdf_text(READABLE_PDF)
    assert read.ok
    assert "77.0 percent of female residents" in read.text
    assert "$979 to $1,759" in read.text


def test_line_breaks_survive_so_a_quote_can_cross_one():
    """`T*` moves to the next line. Missing it fused the last word of each line onto the first of the next,
    which would fail the span guard on any quoted passage crossing a line break."""
    read = pdfmod.extract_pdf_text(READABLE_PDF)
    assert "mammogram within the prior two\nyears" in read.text
    assert "twoyears" not in read.text


def test_an_uncompressed_content_stream_is_read_too():
    """Not every generator compresses. A PDF that happens not to be Flate-encoded is not a failure."""
    from tests.conftest import build_pdf

    ops = (
        b"BT /F1 11 Tf 72 720 Td (Screening uptake rose to 80.3 percent across the state during the "
        b"period under review, and the figures were published annually by the committee.) Tj ET"
    )
    data = build_pdf([
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /Contents 4 0 R >>",
        b"<< /Length %d >>\nstream\n" % len(ops) + ops + b"\nendstream",
    ])
    read = pdfmod.extract_pdf_text(data)
    assert read.ok
    assert "80.3 percent" in read.text


def test_a_hyphen_split_across_lines_is_rejoined():
    from tests.conftest import build_pdf
    import zlib

    ops = (
        b"BT /F1 11 Tf 72 720 Td (The mammog-) Tj T* (raphy programme reported figures every year to "
        b"the coordinating committee, which published them alongside participation rates.) Tj ET"
    )
    body = zlib.compress(ops)
    data = build_pdf([
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /Contents 4 0 R >>",
        b"<< /Filter /FlateDecode /Length %d >>\nstream\n" % len(body) + body + b"\nendstream",
    ])
    read = pdfmod.extract_pdf_text(data)
    assert "mammography programme" in read.text


# ---------------------------------------------------------------- PDF, the refusals


def test_a_scan_is_refused_and_says_the_words_are_in_a_picture():
    read = pdfmod.extract_pdf_text(SCANNED_PDF)
    assert read.code == pdfmod.NO_TEXT_LAYER
    assert not read.ok
    assert read.text == "", "a refusal carries no text: nothing may reach the judge"
    assert read.has_images
    assert "picture" in read.detail


def test_a_custom_font_encoding_is_refused_rather_than_guessed_at():
    """The bytes are glyph numbers. What a naive read recovers looks like text and is not."""
    read = pdfmod.extract_pdf_text(CID_PDF)
    assert read.code == pdfmod.GARBLED
    assert read.text == ""
    assert "glyph numbers rather than letters" in read.detail
    assert read.printable_ratio < pdfmod.MIN_PRINTABLE_RATIO or read.space_ratio < pdfmod.MIN_SPACE_RATIO


def test_a_short_document_is_read_rather_than_called_a_scan():
    """A one-page notice with sixty words in it has a text layer and it read correctly. Whether that is
    enough text to audit is one rule shared by every format, applied by the fetcher, not decided here."""
    from tests.conftest import build_pdf

    ops = b"BT /F1 11 Tf 72 720 Td (Screening uptake rose to 80.3 percent this year.) Tj ET"
    read = pdfmod.extract_pdf_text(build_pdf([
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /Contents 4 0 R >>",
        b"<< /Length %d >>\nstream\n" % len(ops) + ops + b"\nendstream",
    ]))
    assert read.ok, "short is not unreadable"
    assert "80.3 percent" in read.text


def test_the_refusal_records_the_numbers_it_refused_on():
    """A heuristic that cannot be argued with is worse than one that can."""
    read = pdfmod.extract_pdf_text(CID_PDF)
    as_dict = read.to_dict()
    assert as_dict["printable_ratio"] >= 0
    assert as_dict["streams_found"] >= 1
    assert set(as_dict) >= {"code", "detail", "pages", "has_images", "space_ratio"}


def test_an_encrypted_pdf_is_its_own_reason():
    from tests.conftest import build_pdf
    import zlib

    body = zlib.compress(b"BT (hello) Tj ET")
    data = build_pdf(
        [
            b"<< /Type /Catalog /Pages 2 0 R >>",
            b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
            b"<< /Type /Page /Parent 2 0 R /Contents 4 0 R >>",
            b"<< /Filter /FlateDecode /Length %d >>\nstream\n" % len(body) + body + b"\nendstream",
        ],
        extra_trailer=b"/Encrypt 9 0 R ",
    )
    read = pdfmod.extract_pdf_text(data)
    assert read.code == pdfmod.ENCRYPTED
    assert read.text == ""


def test_rubbish_that_is_not_a_pdf_does_not_raise():
    """A bad document is a finding, not a crash."""
    for junk in (b"", b"%PDF-", b"%PDF-1.7\nnot really\n", b"\x00\x01\x02" * 500):
        read = pdfmod.extract_pdf_text(junk)
        assert not read.ok
        assert read.text == ""


# ---------------------------------------------------------------- tables


def test_a_table_row_keeps_its_label_with_its_value():
    """One cell per line destroyed the association: "Recent mammography screening" and "80.3%" became two
    unrelated lines, so a claim about that measure's rate could not be found in a page that stated it."""
    text = extract_text(
        "<table><tr><th>Measure</th><th>Rate</th></tr>"
        "<tr><td>Recent mammography screening</td><td>80.3%</td></tr>"
        "<tr><td>Uptake among recent immigrants</td><td>61.1%</td></tr></table>"
    )
    assert f"Recent mammography screening{CELL_SEPARATOR}80.3%" in text
    assert f"Uptake among recent immigrants{CELL_SEPARATOR}61.1%" in text


def test_a_row_does_not_end_on_a_separator():
    text = extract_text("<table><tr><td>a</td><td>b</td></tr></table>")
    assert text == "a | b"


def test_empty_cells_do_not_stack_separators():
    text = extract_text("<table><tr><td>a</td><td></td><td></td><td>b</td></tr></table>")
    assert text == "a | b"


# ---------------------------------------------------------------- the other formats


def test_an_rss_title_does_not_fuse_into_its_description():
    """XML has no fixed tag vocabulary, so there is no block-tag list to consult and siblings ran together."""
    text = extract_xml_text(
        b"<rss><item><title>Mammography rates</title><description>Uptake was 80.3 percent.</description>"
        b"</item></rss>"
    )
    assert "Mammography rates\nUptake was 80.3 percent." in text


def test_a_docx_keeps_paragraphs_and_table_rows():
    data = build_docx(
        ["Screening uptake rose to 80.3 percent.", "Costs ran from $979 to $1,759 per patient."],
        rows=[("Recent screening", "80.3%")],
    )
    text, why_not = extract_docx_text(data)
    assert why_not == ""
    assert "Screening uptake rose to 80.3 percent." in text
    assert "Costs ran from $979 to $1,759 per patient." in text
    assert f"Recent screening{CELL_SEPARATOR}80.3%" in text


def test_a_zip_that_is_not_a_word_document_says_so():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as bundle:
        bundle.writestr("something/else.xml", "<x/>")
    text, why_not = extract_docx_text(buf.getvalue())
    assert text == ""
    assert "not a Word document" in why_not
    assert ".doc" in why_not, "the old binary format is named, since that is the likely confusion"


def test_something_that_is_not_a_zip_at_all_does_not_raise():
    text, why_not = extract_docx_text(b"this is not a zip")
    assert text == ""
    assert "could not be opened as a zip" in why_not


# ---------------------------------------------------------------- pictures


@pytest.mark.parametrize(
    "markup",
    [
        "<figure><img src='chart.png'></figure>",
        "<svg><rect/></svg>",
        "<picture><source srcset='a.webp'></picture>",
        "<canvas id='plot'></canvas>",
    ],
)
def test_a_page_that_is_only_a_picture_is_recognised(markup):
    assert looks_picture_only(markup, "")


def test_a_page_with_real_text_is_not_called_a_picture():
    """Pictures alongside prose are the normal case and must not trip this."""
    assert not looks_picture_only("<p>" + "x " * 200 + "</p><img src='chart.png'>", "x " * 200)


def test_alt_text_still_counts_as_text():
    """A chart with a described alt attribute is readable, and that description is where a claim resting on
    the chart has to be found."""
    text = extract_text(
        "<img alt='" + ("Screening uptake rose to 80.3 percent in the period measured. " * 5) + "'>"
    )
    assert "80.3 percent" in text
    assert not looks_picture_only("<img alt='...'>", text)
