"""What happens when the extractor, rather than the source, is the thing that failed.

Every failure in this file produces the same visible output if it is not caught: NOT_FOUND_IN_SOURCE. That
verdict carries no span, so gate G3 never sees it, and it is the verdict that accuses the product being
audited. So these are tests that the tool does not publish its own blind spots as findings about somebody
else.
"""

from __future__ import annotations

from sayswho.claims import Claim
from sayswho.extract import extract_text, extraction_looks_thin, raw_text
from sayswho.fetch import content_type_of, is_parseable
from sayswho.judge import (
    EXTRACTION_SUSPECT,
    NOT_FOUND_IN_SOURCE,
    SUPPORTED,
    extraction_dropped_evidence,
    judge_claim,
)
from sayswho.records import SOURCE_NOT_HTML, SOURCE_OK, AUDITABLE_CODES, FetchRecord

from test_judge import FakeJudge


# ---------------------------------------------------------------- content type


def test_a_pdf_is_routed_to_the_pdf_parser_not_the_html_one():
    """It is parseable now, by a different parser. What must never happen is a PDF reaching the HTML
    extractor and whatever falls out being judged."""
    from sayswho.fetch import kind_of

    assert kind_of("application/pdf", b"%PDF-1.7 ...") == "pdf"
    assert is_parseable("application/pdf", b"%PDF-1.7 ...")[0]


def test_a_pdf_mislabelled_as_html_is_still_caught():
    """The sniff runs even when the header looks fine, because a server can be wrong or lying."""
    from sayswho.fetch import kind_of

    assert kind_of("text/html", b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n") == "pdf"


def test_a_format_with_no_parser_is_still_refused():
    """The category did not disappear, it got narrower: it means "no parser for this media type" now."""
    parseable, why = is_parseable("image/png", b"\x89PNG\r\n\x1a\n")
    assert not parseable
    assert "image/png" in why


def test_html_and_plain_text_are_parseable():
    assert is_parseable("text/html", b"<p>hello</p>")[0]
    assert is_parseable("text/plain", b"hello")[0]
    assert is_parseable("application/xhtml+xml", b"<p>hello</p>")[0]


def test_a_missing_content_type_is_treated_as_markup():
    """The conventional reading, recorded here rather than left implicit."""
    assert is_parseable("", b"<p>hello</p>")[0]


def test_content_type_parameters_are_dropped_and_case_is_normalised():
    assert content_type_of({"Content-Type": "TEXT/HTML; charset=UTF-8"}) == "text/html"
    assert content_type_of({"content-type": "application/pdf"}) == "application/pdf"
    assert content_type_of({}) == ""


def test_not_html_is_never_auditable():
    """It leaves the claim unauditable exactly like the other non-OK codes."""
    assert SOURCE_NOT_HTML not in AUDITABLE_CODES


# ---------------------------------------------------------------- what extraction now keeps


def test_image_alt_text_is_extracted():
    """A chart's alt text is the only description of it the page offers."""
    html = '<p>See the figure.</p><img src="f.png" alt="Screening rates fell to 61% in 2021">'
    assert "Screening rates fell to 61% in 2021" in extract_text(html)


def test_svg_text_is_extracted():
    """Chart labels live in SVG text nodes. Dropping the whole element dropped the numbers with it."""
    html = "<figure><svg><title>Uptake by year</title><text>78%</text></svg></figure>"
    text = extract_text(html)
    assert "Uptake by year" in text
    assert "78%" in text


def test_scripts_and_styles_are_still_never_text():
    html = "<p>real</p><script>var x = 'fake';</script><style>.a{color:red}</style>"
    text = extract_text(html)
    assert "real" in text
    assert "fake" not in text
    assert "color" not in text


def test_raw_text_sees_the_content_extraction_drops():
    """Wider than the strict pass in the one direction that matters: a sidebar is plausibly content."""
    html = "<aside>Funded in 2019</aside><p>Body.</p>"
    assert "Funded in 2019" not in extract_text(html)
    assert "Funded in 2019" in raw_text(html)


def test_raw_text_excludes_site_furniture():
    """Regression, from the guard's first live run.

    Every mass.gov page carries a hamburger nav linking /topics/transportation. With navigation in the raw
    pass, any claim mentioning transportation looked like text the extractor had lost, and two correct
    NOT_FOUND_IN_SOURCE verdicts were voided on two pages that never mention it outside the menu.
    """
    html = '<nav><a href="/topics/transportation">Transportation</a></nav><p>Body.</p>'
    assert "Transportation" not in raw_text(html)


def test_raw_text_excludes_scripts():
    """The other half of the same live failure: "Case" matched a switch statement's `case` keyword."""
    html = "<script>switch (h) { case 'www.mass.gov': break; }</script><p>Body.</p>"
    assert "case" not in raw_text(html).lower()
    assert "var x" not in raw_text("<script>var x = 1;</script><p>Body.</p>")


# ---------------------------------------------------------------- the thin-page flag


def test_a_large_page_yielding_almost_no_text_is_flagged():
    assert extraction_looks_thin(text_length=300, html_bytes=500_000)


def test_a_small_page_is_never_flagged_however_short_its_text():
    """A genuinely short page is not evidence of an extraction failure."""
    assert not extraction_looks_thin(text_length=250, html_bytes=8_000)


def test_a_normal_article_is_not_flagged():
    assert not extraction_looks_thin(text_length=6_000, html_bytes=400_000)


# ---------------------------------------------------------------- the second look


DOCUMENT = "The programme offers screening and navigation services to residents."
MARKUP = (
    "<p>The programme offers screening and navigation services to residents.</p>"
    '<img src="chart.png" alt="Uptake reached 78% in 2022">'
)


def _record(text=DOCUMENT, markup=MARKUP):
    return FetchRecord(
        url="https://example.org/a", code=SOURCE_OK, fetched_at="2026-08-08T00:00:00+00:00",
        http_status=200, text=text, text_length=len(text), raw=raw_text(markup),
    )


def test_a_number_in_the_markup_and_not_in_the_text_voids_a_not_found():
    """The claim's number survived in the page and not in what we read, so we failed, not the source."""
    judge = FakeJudge({
        "verdict": NOT_FOUND_IN_SOURCE, "span": "", "reasoning": "not addressed", "notes": "",
    })
    claim = Claim(id="PR-01#001", text="Uptake reached 78% in 2022.", markers=["[1]"],
                  urls=["https://example.org/a"])

    result = judge_claim(claim, _record(), judge)

    assert result.voided
    assert result.void_reason == EXTRACTION_SUSPECT
    assert "78%" in result.notes
    assert not result.counts_as_supported


def test_an_ordinary_not_found_is_left_alone():
    """The guard must not swallow real findings. Nothing in this claim is hiding in the markup."""
    judge = FakeJudge({
        "verdict": NOT_FOUND_IN_SOURCE, "span": "", "reasoning": "not addressed", "notes": "",
    })
    claim = Claim(id="PR-01#002", text="The programme provides transportation to appointments.",
                  markers=["[1]"], urls=["https://example.org/a"])

    result = judge_claim(claim, _record(), judge)

    assert result.verdict == NOT_FOUND_IN_SOURCE
    assert not result.voided


def test_one_capitalised_word_is_not_enough_to_fire_the_guard():
    """One word can be a coincidence. Two words missing from the same claim is a pattern."""
    assert extraction_dropped_evidence(
        "Boston has a screening programme.", "a screening programme", "Boston"
    ) == ()


def test_the_whole_mass_gov_false_positive_end_to_end():
    """Regression for the two verdicts the guard wrongly voided on its first live run.

    The claim listed services including case management and transportation assistance. Neither page said
    either, but the raw pass was seeing markup rather than an extraction, so "Case" matched a script's
    `case` keyword and "Transportation" matched a navigation link.
    """
    claim_text = (
        "The Massachusetts Breast and Cervical Cancer Program (MBCCP) provides: Breast cancer screening, "
        "Case management, Transportation assistance"
    )
    markup = (
        "<script>switch (hostname) { case 'www.mass.gov': break; }</script>"
        '<nav><a href="/topics/transportation">Transportation</a></nav>'
        "<p>The programme provides breast cancer screening at participating sites.</p>"
    )
    extracted = extract_text(markup)

    assert extraction_dropped_evidence(claim_text, extracted, raw_text(markup)) == (), (
        "the source genuinely does not mention case management or transportation assistance, so a "
        "NOT_FOUND_IN_SOURCE here is a real finding and must not be voided"
    )


def test_two_missing_proper_nouns_are_enough():
    assert extraction_dropped_evidence(
        "Dana Farber and Brigham both run the clinic.",
        "both run the clinic",
        "<p>Dana Farber and Brigham</p>",
    ) == ("Brigham", "Dana", "Farber")


def test_a_single_digit_is_not_distinctive_enough():
    assert extraction_dropped_evidence("There are 6 sites.", "there are sites", "6") == ()


def test_the_guard_does_nothing_without_a_stored_raw_pass():
    """Older records carry none. Absent evidence must not become evidence of absence."""
    assert extraction_dropped_evidence("Uptake reached 78% in 2022.", "nothing here", "") == ()


def test_the_guard_never_touches_a_supported_verdict():
    """A SUPPORTED verdict already carries a span the span guard checked. This guard is not its business."""
    judge = FakeJudge({
        "verdict": SUPPORTED, "span": "offers screening and navigation", "reasoning": "", "notes": "",
    })
    claim = Claim(id="PR-01#003", text="Uptake reached 78% in 2022.", markers=["[1]"],
                  urls=["https://example.org/a"])

    result = judge_claim(claim, _record(), judge)

    assert result.verdict == SUPPORTED
    assert not result.voided
    assert result.span_verified


# ---------------------------------------------------------------- re-reading cached bytes


def test_text_pair_reads_a_pdf_as_a_pdf_rather_than_as_markup():
    """The bug that shipped twice. `tools/reaudit_spans.py` and `tools/label_goldset.py` both need the text
    behind a cached URL, and both began by running the HTML extractor over the raw bytes. Over a PDF that
    yields `endstream endobj` and binary noise, which is neither empty nor obviously wrong, so a pasted
    passage simply never matches and records as unchecked. Two of the forty-five pairs in the first real
    labelling session were IRS PDFs."""
    from conftest import READABLE_PDF, READABLE_PDF_TEXT
    from sayswho.fetch import text_pair

    strict, permissive, kind = text_pair({"Content-Type": "application/pdf"}, READABLE_PDF)

    assert kind == "pdf"
    assert "endstream" not in strict, "this is the failure: PDF internals read as though they were text"
    assert READABLE_PDF_TEXT.split(".")[0] in " ".join(strict.split())
    assert strict == permissive, "a PDF has no furniture to strip, so the two passes are one string"


def test_text_pair_returns_nothing_for_a_format_with_no_parser():
    """An unreadable source is not a source whose spans are absent. A caller has to be able to tell those
    apart, so this returns empty rather than something that compares as a miss."""
    from sayswho.fetch import text_pair

    strict, permissive, kind = text_pair(
        {"Content-Type": "image/png"}, b"\x89PNG\r\n\x1a\n" + b"0" * 400
    )
    assert kind == "none"
    assert strict == "" and permissive == ""


def test_the_labelling_tool_can_check_a_passage_against_a_cited_pdf(tmp_path):
    """The end the fix exists for. `goldset.attribution` can only separate an extractor failure from a judge
    failure on pairs where the labeller's passage was checkable at all, and for a PDF source it never was."""
    import sys
    from pathlib import Path as _Path

    sys.path.insert(0, str(_Path(__file__).resolve().parent.parent / "tools"))

    from conftest import READABLE_PDF, READABLE_PDF_TEXT
    from sayswho.cache import FetchCache
    from sayswho.judge import span_is_present

    import label_goldset

    cache = FetchCache(tmp_path / "cache")
    url = "https://example.gov/report.pdf"
    cache.put(url, 200, {"Content-Type": "application/pdf"}, READABLE_PDF)

    pair = label_goldset.extracted_pair(cache, url)
    assert pair is not None, "the cached PDF has to be readable at all"
    text, _raw = pair
    assert span_is_present(READABLE_PDF_TEXT.split(".")[0], text)
