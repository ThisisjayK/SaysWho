"""Extraction tests.

Extraction quality is not cosmetic. If the extractor drops the sentence that supports a claim, the judge
returns NOT_FOUND_IN_SOURCE and the pipeline records a false negative that looks exactly like a real finding.
These tests pin the behaviour the rest of the pipeline is entitled to assume.
"""

from __future__ import annotations

import pytest

from sayswho.extract import detect_wall, extract_text, normalise_for_span


def test_script_and_style_contents_never_reach_the_text():
    html = """<html><head><style>.a{color:red}</style>
    <script>var poison = "the source supports this claim";</script></head>
    <body><p>The trial reported no survival difference.</p></body></html>"""

    text = extract_text(html)

    assert "The trial reported no survival difference." in text
    assert "poison" not in text
    assert "color:red" not in text


def test_navigation_and_footers_are_dropped():
    html = """<html><body><nav>Subscribe now</nav>
    <article><p>Recurrence fell in the extended arm.</p></article>
    <footer>Subscribe now</footer></body></html>"""

    text = extract_text(html)

    assert "Recurrence fell in the extended arm." in text
    assert "Subscribe now" not in text


def test_malformed_markup_returns_text_rather_than_raising():
    """A bad page is a finding, not a crash."""
    text = extract_text("<html><body><p>Unclosed paragraph<div><span>more text</body>")
    assert "Unclosed paragraph" in text
    assert "more text" in text


def test_block_tags_become_line_breaks_so_sentences_do_not_run_together():
    text = extract_text("<p>First sentence.</p><p>Second sentence.</p>")
    assert "First sentence.Second sentence." not in text
    assert "First sentence." in text and "Second sentence." in text


def test_paywall_and_consent_walls_are_distinguished():
    assert detect_wall("Subscribe to continue reading this article.") == "paywall"
    assert detect_wall("We value your privacy. Accept all cookies to continue.") == "consent"
    assert detect_wall("An ordinary article about adjuvant therapy.") is None


def test_span_normalisation_is_stable_across_whitespace_and_case():
    """The extension and the harness must normalise identically or the §9 parity check fails."""
    a = normalise_for_span("The  extended   duration group\nreported MORE adverse events.")
    b = normalise_for_span("the extended duration group reported more adverse events.")
    assert a == b


# ---------------------------------------------------------------- span folding


@pytest.mark.parametrize(
    "name,span,page",
    [
        ("curly against straight quotes", 'found "significant variation" here', 'found “significant variation” here'),
        ("straight against curly quotes", 'found “significant variation” here', 'found "significant variation" here'),
        ("hyphen against en dash", "a 21-day reduction", "a 21–day reduction"),
        ("hyphen against em dash", "a 21-day reduction", "a 21—day reduction"),
        ("hyphen against a minus sign", "a 21-day reduction", "a 21−day reduction"),
        ("apostrophe against a right single quote", "the trial's result", "the trial’s result"),
        ("soft hyphen from a line break", "navigation reduced delay", "navi­gation reduced delay"),
        ("zero-width space", "navigation reduced delay", "navi​gation reduced delay"),
        ("an ff ligature", "the coffee finding", "the coﬀee finding"),
        ("full-width digits", "a 21 day reduction", "a ２１ day reduction"),
        ("non-breaking space", "Mass General Brigham", "Mass General Brigham"),
        ("an ellipsis glyph", "the result ... was small", "the result … was small"),
    ],
)
def test_the_span_guard_accepts_a_span_the_page_really_contains(name, span, page):
    """Every one of these voided a verdict as JUDGE_FABRICATED_SPAN, which is the code published as a finding
    about the judge. The rate was partly measuring this function and attributing it to Gemini."""
    assert normalise_for_span(span) in normalise_for_span(page), name


def test_folding_does_not_make_different_words_equal():
    """A guard that folds too much would accept a span the page does not contain, which is the failure this
    whole project exists to catch, committed by the checker."""
    assert normalise_for_span("reduced recurrence") not in normalise_for_span("increased recurrence")
    assert normalise_for_span("21 days") not in normalise_for_span("12 days")
    assert normalise_for_span("did reduce") not in normalise_for_span("did not reduce")


def test_a_precomposed_and_a_decomposed_accent_now_match():
    """This used to be the assertion that the gap existed. It was blocked on a belief that turned out to be
    wrong: that closing it meant normalising whole strings, which would desync the per-character index
    `report.py` builds. Composing would have. Decomposing does not, because it is one-to-many in the
    direction the index already tolerates.

    A publisher's CMS and a model's tokeniser disagree about this routinely, and the cost of the disagreement
    was a verdict voided as JUDGE_FABRICATED_SPAN, which is the code published as a finding about the judge.
    Written with escapes rather than literal accents on purpose: the two strings have to differ in the file
    and an editor that normalises on save would quietly make this test vacuous."""
    from sayswho.extract import normalise_for_span as n

    precomposed = "Ren\u00e9 was first"
    decomposed = "Rene\u0301 was first"
    assert precomposed != decomposed, "if these are equal the test is comparing one string with itself"
    assert n(precomposed) == n(decomposed)

    # Both directions of containment, since the guard is a substring test rather than an equality one.
    assert n("Ren\u00e9") in n("the trial by Rene\u0301 and others")
    assert n("Rene\u0301") in n("the trial by Ren\u00e9 and others")


def test_an_accent_folds_away_entirely_which_is_the_cost_of_the_fix():
    """Stated rather than hidden, because it is a real widening: the guard can no longer tell "resume" from
    "r\u00e9sum\u00e9". It was already unable to tell "Trial" from "trial", and the direction of the trade is
    the same one every row of the fold table accepts. What buys it is that a fabricated span differing from the
    page only in its accents is not a plausible fabrication, while a real span differing only in its accents is
    an ordinary Tuesday."""
    from sayswho.extract import normalise_for_span as n

    assert n("resume") == n("r\u00e9sum\u00e9")
    # And the guard still refuses a span that differs in anything else.
    assert n("resumed") != n("r\u00e9sum\u00e9")


def test_marks_that_are_not_typography_are_left_alone():
    """The line drawn instead of `category(c) == "Mn"`, which would have been shorter and wrong. A Devanagari
    virama suppresses a vowel and a Hebrew point is a vowel, so dropping either changes the word rather than
    how it was typeset. Folding them would make the guard accept a span the page does not contain, in exactly
    the languages nobody here is going to check by hand."""
    from sayswho.extract import normalise_for_span as n

    assert n("\u0915\u094d\u0937") != n("\u0915\u0937"), "the Devanagari virama survives"
    assert n("\u05e9\u05b8\u05dd") != n("\u05e9\u05dd"), "the Hebrew point survives"


def test_claim_ids_do_not_track_the_span_guard():
    """The coupling that made this fix expensive until it was separated. G4 ties a gold set to claim ids, and
    `splits.py` hashes them, so a span-guard change that moved ids would invalidate every label silently."""
    from sayswho.extract import canonical_for_id

    # Typography that the span guard now folds must leave an id alone.
    assert canonical_for_id("the trial’s 21–day result") != canonical_for_id("the trial's 21-day result")
    # Whitespace and case still do not matter, which is what the id promised all along.
    assert canonical_for_id("The  Extended\nduration") == canonical_for_id("the extended duration")


def test_the_two_normalisers_are_not_the_same_function():
    from sayswho.extract import canonical_for_id, normalise_for_span

    assert canonical_for_id is not normalise_for_span
