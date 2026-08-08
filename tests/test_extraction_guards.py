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


def test_a_pdf_is_not_run_through_the_html_parser():
    parseable, why = is_parseable("application/pdf", b"%PDF-1.7 ...")
    assert not parseable
    assert "pdf" in why.lower()


def test_a_pdf_mislabelled_as_html_is_still_caught():
    """The sniff runs even when the header looks fine, because a server can be wrong or lying."""
    parseable, why = is_parseable("text/html", b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    assert not parseable
    assert "regardless" in why


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


def test_raw_text_keeps_the_furniture_that_extraction_drops():
    """The comparison side of the extraction check, so it has to see more, not less."""
    html = "<nav>Skip to content</nav><aside>Funded in 2019</aside><p>Body.</p>"
    assert "Skip to content" not in extract_text(html)
    assert "Skip to content" in raw_text(html)
    assert "Funded in 2019" in raw_text(html)


def test_raw_text_still_excludes_scripts():
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


def _record(text=DOCUMENT, html=MARKUP):
    return FetchRecord(
        url="https://example.org/a", code=SOURCE_OK, fetched_at="2026-08-08T00:00:00+00:00",
        http_status=200, text=text, text_length=len(text), html=html,
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
    """Navigation is full of single capitalised words, and the raw pass keeps navigation on purpose."""
    assert extraction_dropped_evidence(
        "Boston has a screening programme.", "a screening programme", "<nav>Boston</nav>"
    ) == ()


def test_two_missing_proper_nouns_are_enough():
    assert extraction_dropped_evidence(
        "Dana Farber and Brigham both run the clinic.",
        "both run the clinic",
        "Dana Farber and Brigham",
    ) == ("Brigham", "Dana", "Farber")


def test_a_single_digit_is_not_distinctive_enough():
    assert extraction_dropped_evidence("There are 6 sites.", "there are sites", "6") == ()


def test_the_guard_does_nothing_without_stored_markup():
    """Older records carry no html. Absent evidence must not become evidence of absence."""
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
