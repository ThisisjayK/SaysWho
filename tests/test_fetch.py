"""Fetch layer tests.

Each one asserts a rule from DATA_CONTRACT.md actually holds over real HTTP, rather than asserting that a
function exists. Section 10 of the contract claims a specific list of rules is enforced by code. This file is
the evidence for that claim, and if a test here is deleted the claim goes with it.
"""

from __future__ import annotations

import pytest

from sayswho.fetch import Fetcher, user_agent
from sayswho.records import (
    SOURCE_NO_TEXT_LAYER,
    SOURCE_UNREADABLE_ENCODING,
    SOURCE_BOT_BLOCKED,
    SOURCE_DEAD_LINK,
    SOURCE_EMPTY,
    SOURCE_NOT_HTML,
    SOURCE_OK,
    SOURCE_PAYWALLED,
    SOURCE_ROBOTS_EXCLUDED,
    SOURCE_UNREACHABLE,
    FetchRecord,
)


def fetcher(cache, **kw):
    kw.setdefault("rate_limit", 0.0)
    return Fetcher(cache, **kw)


# ---------------------------------------------------------------- G2 codes


def test_readable_page_is_source_ok(server, cache):
    record = fetcher(cache).fetch(server.url("/ok.html"))
    assert record.code == SOURCE_OK
    assert record.http_status == 200
    assert record.text_length > 200
    assert "musculoskeletal adverse events" in record.text
    assert record.auditable


def test_a_pdf_with_a_text_layer_is_read_and_auditable(server, cache):
    """PDFs used to be unauditable as a class, which in a corpus of government and journal citations threw
    away a lot of real sources. Read by `sayswho.pdf`, stdlib only."""
    record = fetcher(cache).fetch(server.url("/readable.pdf"))

    assert record.code == SOURCE_OK
    assert record.auditable
    assert record.document_kind == "pdf"
    assert record.content_type == "application/pdf"
    assert "77.0 percent" in record.text
    assert "$979 to $1,759" in record.text, "figures a claim would rest on survive extraction"
    assert record.pdf["code"] == "PDF_OK"


def test_a_scanned_pdf_says_it_is_a_scan_rather_than_being_judged(server, cache):
    """The words are on the page and there is no way to reach them without OCR. That is a finding about
    the citation, and a different one from the document being empty."""
    record = fetcher(cache).fetch(server.url("/scanned.pdf"))

    assert record.code == SOURCE_NO_TEXT_LAYER
    assert not record.auditable
    assert record.text == "", "nothing may carry into the judge"
    assert "images" in record.detail
    assert record.pdf["has_images"] is True


def test_a_pdf_this_parser_cannot_decode_blames_the_parser(server, cache):
    """A custom font encoding means the stream holds glyph numbers, and the "text" recoverable from one is
    plausible-looking rubbish. Passing it on would produce a NOT_FOUND_IN_SOURCE that accuses the source of
    something this tool did."""
    record = fetcher(cache).fetch(server.url("/cid.pdf"))

    assert record.code == SOURCE_UNREADABLE_ENCODING
    assert not record.auditable
    assert record.text == ""
    assert "glyph numbers rather than letters" in record.detail


def test_a_pdf_with_no_text_at_all_is_not_reported_as_having_no_parser(server, cache):
    """The old stub fixture: structurally a PDF, no text in it. SOURCE_NOT_HTML now means only "no parser
    for this media type", which is no longer true of PDFs."""
    record = fetcher(cache).fetch(server.url("/report.pdf"))

    assert record.code == SOURCE_NO_TEXT_LAYER
    assert record.content_type == "application/pdf"
    assert not record.auditable


def test_a_pdf_served_as_html_is_still_recognised_as_a_pdf(server, cache):
    """The magic number decides, not the header. A CDN serving a PDF as text/html is real."""
    record = fetcher(cache).fetch(server.url("/liar.html"))

    assert record.document_kind == "pdf", "the sniff wins over the header"
    assert record.code == SOURCE_NO_TEXT_LAYER
    assert not record.auditable


def test_plain_text_xml_and_docx_are_all_read(server, cache):
    """Three formats that used to be SOURCE_NOT_HTML. Each is a small stdlib function, not a dependency."""
    text = fetcher(cache).fetch(server.url("/notes.txt"))
    assert text.code == SOURCE_OK and "80.3 percent" in text.text

    feed = fetcher(cache).fetch(server.url("/feed.xml"))
    assert feed.code == SOURCE_OK and feed.document_kind == "xml"
    assert "Mammography rates" in feed.text
    assert "Uptake among women" in feed.text, "the title must not fuse into the description"

    doc = fetcher(cache).fetch(server.url("/notes.docx"))
    assert doc.code == SOURCE_OK and doc.document_kind == "docx"
    assert "80.3 percent" in doc.text
    assert "Recent screening | 80.3%" in doc.text, "a table row keeps its label with its value"


def test_a_page_whose_content_is_a_picture_says_so(server, cache):
    """Not SOURCE_EMPTY. "We could not read the picture" and "the page said nothing" are different facts,
    and only one of them is about the citation being thin."""
    record = fetcher(cache).fetch(server.url("/chart.html"))

    assert record.code == SOURCE_NO_TEXT_LAYER
    assert not record.auditable
    assert "image" in record.detail


def test_short_page_is_source_empty_not_unreachable(server, cache):
    """A 200 with nothing in it is not an error. Conflating the two would inflate the error rate."""
    record = fetcher(cache).fetch(server.url("/short.html"))
    assert record.code == SOURCE_EMPTY
    assert record.http_status == 200
    assert not record.auditable


def test_paywall_is_paywalled_not_empty(server, cache):
    """Break attempt 2 in SCOPE.md §6, at the fetch layer.

    A paywalled page is short, so the length threshold would catch it as SOURCE_EMPTY and lose the reason.
    Wall detection has to run first.
    """
    record = fetcher(cache).fetch(server.url("/paywall.html"))
    assert record.code == SOURCE_PAYWALLED
    assert "paywall wall detected" in record.detail
    assert not record.auditable


def test_404_is_a_dead_link(server, cache):
    """A 404 says the document is not there, which is a fact about the citation."""
    record = fetcher(cache).fetch(server.url("/missing.html"))
    assert record.code == SOURCE_DEAD_LINK
    assert record.http_status == 404
    assert not record.auditable


def test_403_is_bot_blocked_rather_than_a_dead_link(server, cache):
    """`FINDINGS.md` item 3: aacrjournals.org returned 403 to the single link in a whole research report.

    Folded into one code, "the citation is broken" and "the citation is unreadable to anything automated"
    become one number, and only the first is a finding about the answer being audited.
    """
    record = fetcher(cache).fetch(server.url("/forbidden.html"))
    assert record.code == SOURCE_BOT_BLOCKED
    assert record.http_status == 403
    assert not record.auditable


def test_429_is_bot_blocked_too(server, cache):
    record = fetcher(cache).fetch(server.url("/ratelimited.html"))
    assert record.code == SOURCE_BOT_BLOCKED
    assert not record.auditable


def test_an_unclassified_status_stays_unreachable(server, cache):
    """418 is neither gone nor refused, so it keeps the general code rather than being forced into one."""
    from sayswho.records import code_for_status

    assert code_for_status(418) == SOURCE_UNREACHABLE
    assert code_for_status(500) == SOURCE_UNREACHABLE


def test_all_three_are_unauditable_and_the_arithmetic_is_identical():
    """The split changes the sentence published beside the number, never the number."""
    from sayswho.gates import auditable_denominator

    records = [
        FetchRecord(url="https://a.example/1", code=SOURCE_DEAD_LINK, fetched_at="t"),
        FetchRecord(url="https://b.example/2", code=SOURCE_BOT_BLOCKED, fetched_at="t"),
        FetchRecord(url="https://c.example/3", code=SOURCE_UNREACHABLE, fetched_at="t"),
    ]
    assert auditable_denominator(records) == 0


# ---------------------------------------------------------------- politeness


def test_robots_disallow_sends_no_request(server, cache):
    """SOURCE_ROBOTS_EXCLUDED means we chose not to try, so the server must see nothing but robots.txt."""
    record = fetcher(cache).fetch(server.url("/blocked/page.html"))

    assert record.code == SOURCE_ROBOTS_EXCLUDED
    assert record.http_status is None
    assert server.paths == ["/robots.txt"]
    assert "/blocked/page.html" not in server.paths


def test_identifying_user_agent_on_every_request(server, cache):
    fetcher(cache).fetch(server.url("/ok.html"))

    agents = [ua for _, ua in server.handler.log]
    assert agents, "no requests reached the server"
    for agent in agents:
        assert agent == user_agent()
        assert "@" in agent, "the User-Agent must carry a contact address"


def test_rate_limit_waits_between_requests_to_one_host(server, cache):
    """One request per second per domain, robots.txt included."""
    slept: list[float] = []
    f = Fetcher(cache, rate_limit=1.0, sleep=slept.append)

    f.fetch(server.url("/ok.html"))

    assert len(server.paths) == 2, "expected robots.txt then the page"
    assert slept, "second request to the same host did not wait"
    assert slept[0] == pytest.approx(1.0, abs=0.05)


def test_retries_on_500_then_succeeds(server, cache):
    slept: list[float] = []
    f = Fetcher(cache, rate_limit=0.0, sleep=slept.append)

    record = f.fetch(server.url("/flaky"))

    assert record.code == SOURCE_OK
    assert record.attempts == 3, "two retries after the first attempt"
    assert slept == [2.0, 8.0], "backoff must be 2s then 8s per DATA_CONTRACT.md §2"


def test_no_retry_on_4xx(server, cache):
    """A 404 is an answer, not a failure to get one. Retrying it wastes the site's bandwidth."""
    slept: list[float] = []
    f = Fetcher(cache, rate_limit=0.0, sleep=slept.append)

    record = f.fetch(server.url("/missing.html"))

    assert record.attempts == 1
    assert slept == []
    assert server.paths.count("/missing.html") == 1


# ---------------------------------------------------------------- cache


def test_second_fetch_reads_cache_and_does_not_re_request(server, cache):
    """DATA_CONTRACT.md §7: a rerun audits the same bytes."""
    f = fetcher(cache)
    first = f.fetch(server.url("/ok.html"))
    hits_after_first = server.paths.count("/ok.html")

    second = f.fetch(server.url("/ok.html"))

    assert hits_after_first == 1
    assert server.paths.count("/ok.html") == 1, "the cached fetch went back to the network"
    assert second.content_sha256 == first.content_sha256
    assert second.detail == "from cache"


def test_cache_is_append_only(server, cache):
    """A refetch is a second record, never a replacement for the first."""
    f = fetcher(cache)
    url = server.url("/ok.html")

    f.fetch(url)
    f.fetch(url, use_cache=False)

    assert cache.count(url) == 2


def test_body_is_written_to_cache_before_it_is_classified(server, cache):
    """The record has to exist on disk even for a page that fails its gate."""
    url = server.url("/short.html")
    record = fetcher(cache).fetch(url)

    assert record.code == SOURCE_EMPTY
    assert cache.count(url) == 1
    meta, body = cache.latest(url)
    assert meta["content_sha256"] == record.content_sha256
    assert body


# ---------------------------------------------------------------- content encoding


def test_gzipped_body_is_decoded_before_extraction(server, cache):
    """Regression test for a bug that would have faked an entire finding.

    Wayback's id_ endpoint replays the original crawled bytes with their original Content-Encoding, so
    archived pages arrive gzipped even though we never send Accept-Encoding. Undecoded, the extractor turns
    compressed bytes into thousands of characters of binary noise. That passes the length threshold as
    SOURCE_OK, then shares zero shingles with the live page, so every archived comparison reports drift and
    every source becomes unauditable. A clean, consistent, entirely artefactual result.
    """
    record = fetcher(cache).fetch(server.url("/gzipped.html"))

    assert record.code == SOURCE_OK
    assert "musculoskeletal adverse events" in record.text
    assert "\x00" not in record.text


def test_an_encoding_we_cannot_decode_is_refused_rather_than_passed_through(server, cache):
    """Brotli needs a dependency. Letting the raw bytes through would look like a readable article."""
    record = fetcher(cache).fetch(server.url("/brotli.html"))

    assert record.code == SOURCE_EMPTY
    assert "unsupported content-encoding: br" in record.detail
    assert record.text_length == 0


def test_a_malformed_response_becomes_an_outcome_rather_than_ending_the_run(cache, monkeypatch):
    """Found on the first real stratum pass, and it is the transient kind that looks like nothing.

    One server returned a chunked body whose size line `http.client` could not parse, which surfaces as
    `ValueError: invalid literal for int() with base 16: b\'\'` from inside urlopen. That is not a URLError,
    so it escaped the handler, ended the whole capture and cost that query its run record. The rerun
    succeeded.

    A stratum run fetches every cited URL of every answer, so betting on none of them misbehaving is not a
    bet worth taking. One bad response should cost one source, recorded, and not the run."""
    f = fetcher(cache)

    def explode(url):
        raise ValueError("invalid literal for int() with base 16: b''")

    monkeypatch.setattr(f, "_raw_request", lambda url: explode(url))
    monkeypatch.setattr(f, "allowed", lambda url: True)

    record = f.fetch("https://example.org/chunked-badly")

    assert record.code == SOURCE_UNREACHABLE
    assert "ValueError" in record.detail, "the exception type has to survive into the record"
    assert "base 16" in record.detail
    assert record.attempts >= 1


def test_a_malformed_response_is_retried_like_any_other_failure(cache, monkeypatch):
    """It goes down the same path a timeout does, which means the retry policy in DATA_CONTRACT.md section 2
    applies to it rather than a second policy existing for surprises."""
    f = fetcher(cache, max_retries=2)
    monkeypatch.setattr(f, "allowed", lambda url: True)

    calls = []

    def explode(url):
        calls.append(url)
        raise ValueError("invalid literal for int() with base 16: b''")

    monkeypatch.setattr(f, "_raw_request", explode)
    record = f.fetch("https://example.org/chunked-badly")

    assert len(calls) == 3, "one attempt plus two retries, the same as a timeout"
    assert record.attempts == 3


def test_text_pair_agrees_with_the_fetcher_on_the_same_bytes(server, cache):
    """What keeps a helper from turning into a second implementation. `fetch.text_pair` is the read-only half
    of `Fetcher._classify`, and the classifier is what assigns outcome codes, so the two can only be trusted to
    agree if something runs the same bytes through both and checks.

    Per document kind, because the kinds are where they would diverge: the PDF path, the markup path, and the
    permissive pass that only markup has. The routing was duplicated in two tools before this, and both copies
    had the same bug."""
    from sayswho.fetch import text_pair

    f = fetcher(cache)
    # One per parser: the PDF path, markup, a feed and a .docx. Each is a place the two could diverge, and
    # the permissive pass is only different from the strict one for markup.
    for path in ("/readable.pdf", "/ok.html", "/feed.xml", "/notes.docx"):
        record = f.fetch(server.url(path))
        entry = cache.latest(server.url(path))
        assert entry is not None, path
        meta, body = entry
        strict, permissive, _kind = text_pair(meta.get("headers", {}), body)

        assert strict == record.text, f"{path}: strict pass disagrees with the fetcher"
        assert permissive == record.raw, f"{path}: permissive pass disagrees with the fetcher"


# ---------------------------------------------------------------- a refusal wearing a status code


def test_a_404_that_is_really_a_bot_block_is_recorded_as_blocked(cache, monkeypatch):
    """The one unauditable code that accuses a citation rather than this pipeline, applied to a page that is
    not dead. The FDA's Akamai edge answered a cited URL with 404 and a `location` header pointing at
    `/apology_objects/abuse-detection-apology.html`. A person opened the same URL and read the article in
    full. `SOURCE_DEAD_LINK` would have published "the product cited a page that does not exist".

    The evidence was in the response headers the whole time, which is why this is a bug about reading rather
    than about the web. `FINDINGS.md` item 21."""
    f = fetcher(cache)
    monkeypatch.setattr(f, "allowed", lambda url: True)
    body = (
        b'<!DOCTYPE html><html><head><title>FDA Apology</title></head><body><script>'
        b'window.location.href = "/apology_objects/excessive-requests-apology.html";</script></body></html>'
    )
    monkeypatch.setattr(f, "_raw_request", lambda url: (
        404, {"content-type": "text/html", "location": "/apology_objects/abuse-detection-apology.html"}, body,
    ))

    record = f.fetch("https://example.gov/scripts/record.cfm?id=1")

    assert record.code == SOURCE_BOT_BLOCKED, "a 404 that says it is an abuse page is not a dead link"
    assert record.http_status == 404, "the status is still recorded truthfully"
    assert "abuse-detection" in record.detail
    assert not record.auditable, "the arithmetic is unchanged: it is unauditable either way"


def test_an_ordinary_404_is_still_a_dead_link(cache, monkeypatch):
    """The other half. A 404 is normally an answer about the document, and this must not turn every one of
    them into a story about robots."""
    f = fetcher(cache)
    monkeypatch.setattr(f, "allowed", lambda url: True)
    monkeypatch.setattr(f, "_raw_request", lambda url: (
        404, {"content-type": "text/html"}, b"<html><body><h1>Not Found</h1></body></html>",
    ))

    assert f.fetch("https://example.org/gone").code == SOURCE_DEAD_LINK


def test_a_long_page_about_bot_detection_is_not_reported_as_one(cache, monkeypatch):
    """The precision guard. A block page is small; an article discussing abuse detection is not, and the
    words appear in both. Without a size bound this would misread a real document about the subject."""
    f = fetcher(cache)
    monkeypatch.setattr(f, "allowed", lambda url: True)
    article = (
        b"<html><body><article><p>This paper studies abuse detection and unusual traffic on the web. </p>"
        + b"<p>" + b"Discussion of the topic continues at length. " * 400 + b"</p></article></body></html>"
    )
    monkeypatch.setattr(f, "_raw_request", lambda url: (404, {"content-type": "text/html"}, article))

    assert len(article) > 8_000, "the fixture has to be past the size bound or it proves nothing"
    assert f.fetch("https://example.org/paper").code == SOURCE_DEAD_LINK


def test_a_403_block_page_stays_blocked_and_says_why(cache, monkeypatch):
    """A 403 already mapped to blocked, so this asserts the detail improves rather than the code changing."""
    f = fetcher(cache)
    monkeypatch.setattr(f, "allowed", lambda url: True)
    monkeypatch.setattr(f, "_raw_request", lambda url: (
        403, {"content-type": "text/html"}, b"<html><body>Checking your browser before accessing.</body></html>",
    ))

    record = f.fetch("https://example.org/blocked")
    assert record.code == SOURCE_BOT_BLOCKED
    assert "checking your browser" in record.detail

