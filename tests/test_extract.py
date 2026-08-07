"""Extraction tests.

Extraction quality is not cosmetic. If the extractor drops the sentence that supports a claim, the judge
returns NOT_FOUND_IN_SOURCE and the pipeline records a false negative that looks exactly like a real finding.
These tests pin the behaviour the rest of the pipeline is entitled to assume.
"""

from __future__ import annotations

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
