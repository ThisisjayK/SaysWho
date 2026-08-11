"""Re-extraction from stored page HTML.

The selector engine is a deliberate subset. These tests pin the forms the adapters actually use, and the
last group checks that unsupported syntax raises rather than quietly matching nothing, since a selector that
silently matches nothing produces an empty citation list that looks exactly like an uncited answer.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from sayswho.reextract import citations_in, parse, reextract, select

CLAUDE_PAGE = """
<html><body>
  <div class="dframe-sidebar-body"><a href="https://claude.ai/chat/other">Another conversation</a></div>
  <main>
    <div class="font-claude-response"><div class="standard-markdown">
      <p>Your report is ready. It maps the major hospital systems.</p>
    </div></div>
    <div class="bg-surface-3 flex h-full">
      <div class="standard-markdown">
        <p>Extending therapy reduced recurrence
          <a href="https://aacrjournals.org/cebp/article/A039" class="group/tag">aacrjournals</a>
        </p>
        <p>Another claim <a href="https://pubmed.ncbi.nlm.nih.gov/34767089/">PubMed</a></p>
      </div>
    </div>
  </main>
  <footer><a href="https://support.anthropic.com/en/articles/8525154">Claude is AI and can make mistakes</a></footer>
</body></html>
"""

CHATGPT_PAGE = """
<html><body>
  <div data-message-author-role="user"><p>My question</p></div>
  <div data-message-author-role="assistant">
    <p>An answer <a href="https://www.bmc.org/nav?utm_source=chatgpt.com">Boston Medical Center
    +1</a></p>
    <p>More <a href="https://www.mass.gov/mbccp?utm_source=chatgpt.com">Massachusetts Government</a></p>
  </div>
</body></html>
"""


# ---------------------------------------------------------------- selectors


def test_class_selector():
    root = parse(CLAUDE_PAGE)
    assert len(select(root, ".font-claude-response")) == 1


def test_descendant_selector_crosses_intermediate_elements():
    root = parse(CLAUDE_PAGE)
    found = select(root, ".bg-surface-3 .standard-markdown")
    assert len(found) == 1
    assert "aacrjournals" in found[0].text_content()


def test_attribute_equals_selector():
    root = parse(CHATGPT_PAGE)
    assert len(select(root, '[data-message-author-role="assistant"]')) == 1


def test_attribute_prefix_selector():
    root = parse(CLAUDE_PAGE)
    anchors = select(root, 'a[href^="http"]')
    assert len(anchors) == 4


def test_unsupported_selector_syntax_raises_rather_than_matching_nothing():
    """A selector that silently matches nothing gives an empty citation list.

    That is indistinguishable from an answer with no citations, which is a verdict the pipeline would then
    report as though it were a finding.
    """
    with pytest.raises(ValueError):
        select(parse(CLAUDE_PAGE), "div > p")


# ---------------------------------------------------------------- citations


def test_page_furniture_is_excluded():
    root = parse(CLAUDE_PAGE)
    body = select(root, "body")[0]
    urls = [c["url"] for c in citations_in(body)]

    assert not any("support.anthropic.com" in u for u in urls)
    assert not any("claude.ai" in u for u in urls)


def test_expander_suffix_is_stripped_from_the_marker():
    root = parse(CHATGPT_PAGE)
    container = select(root, '[data-message-author-role="assistant"]')[0]
    markers = [c["marker"] for c in citations_in(container)]

    assert "Boston Medical Center" in markers
    assert not any("+1" in m for m in markers)


# ---------------------------------------------------------------- whole pass


def test_reextract_picks_the_container_with_the_citations():
    """Two containers match on Claude. Only the report has anything to audit."""
    result = reextract(CLAUDE_PAGE, "claude")

    assert result is not None
    assert result.selector == ".bg-surface-3 .standard-markdown"
    assert len(result.citations) == 2
    assert result.candidates_considered >= 2


def test_reextract_normalises_urls_for_deduplication():
    result = reextract(CHATGPT_PAGE, "chatgpt")
    assert result is not None
    assert all("utm_source" not in u for u in result.urls)
    assert result.citations[0]["url"].endswith("utm_source=chatgpt.com"), (
        "the citation keeps the URL exactly as the answer gave it"
    )


def test_reextract_returns_none_when_no_container_matches():
    assert reextract("<html><body><p>nothing here</p></body></html>", "chatgpt") is None


# ---------------------------------------------------------------- Perplexity: citations that are not links


PERPLEXITY = (Path(__file__).resolve().parent.parent / "fixtures" / "perplexity-answer.html").read_text()


def test_perplexity_citations_are_found_even_though_the_page_has_no_links():
    """Probed against a live answer on 2026-08-11: every citation is a span carrying the URL in
    `data-pplx-citation-url`, and the document contains no `<a href>` at all.

    The old anchors-only rule did not find "roughly a third" of them. It found none, and produced a clean
    capture reporting zero citations, which G0 then treats as an uncited answer.
    """
    from sayswho.reextract import reextract

    result = reextract(PERPLEXITY, "perplexity")
    assert result is not None
    assert result.selector == ".prose"
    assert len(result.citations) == 2, "three chips, two distinct sources"
    assert {c["marker"] for c in result.citations} == {"boston", "americashealthrankings"}
    assert all(c["url"].startswith("https://") for c in result.citations)


def test_the_nested_chip_is_not_counted_twice():
    """Perplexity wraps its chip in a second element of the same class. Only the outer one carries the
    attribute, and counting both would double every citation on the page."""
    from sayswho.reextract import reextract

    body = re.sub(r"<!--.*?-->", "", PERPLEXITY, flags=re.S)
    assert body.count("data-pplx-citation-url") == 3, "three chips carry a URL"
    assert body.count('class="citation inline"') == 6, "and each is wrapped in one more of the same class"
    assert len(reextract(PERPLEXITY, "perplexity").citations) == 2, "two distinct sources, counted once each"


def test_a_perplexity_pdf_citation_survives_extraction():
    """The first live Perplexity answer cited a boston.gov PDF, which is `SOURCE_NOT_HTML` downstream and
    a code that has never fired on real data. It has to reach the fetch layer to fire at all."""
    from sayswho.reextract import reextract

    urls = [c["url"] for c in reextract(PERPLEXITY, "perplexity").citations]
    assert any(u.endswith(".pdf") for u in urls)


def test_product_chrome_is_still_excluded():
    """The settings link in the page's own navigation is furniture, not a citation."""
    from sayswho.reextract import reextract

    urls = [c["url"] for c in reextract(PERPLEXITY, "perplexity").citations]
    assert not any("perplexity.ai" in u for u in urls)


def test_an_ordinary_anchor_page_is_unaffected():
    """The rule is additive. Anchors are still citations, and are still preferred."""
    from sayswho.reextract import reextract

    html = """<html><body><div class="prose">
      <p>A claim <a href="https://example.org/a">example</a>.</p>
    </div></body></html>"""
    result = reextract(html, "perplexity")
    assert [c["url"] for c in result.citations] == ["https://example.org/a"]
