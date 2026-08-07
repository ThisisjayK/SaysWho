"""Fetch layer tests.

Each one asserts a rule from DATA_CONTRACT.md actually holds over real HTTP, rather than asserting that a
function exists. Section 10 of the contract claims a specific list of rules is enforced by code. This file is
the evidence for that claim, and if a test here is deleted the claim goes with it.
"""

from __future__ import annotations

import pytest

from sayswho.fetch import Fetcher, user_agent
from sayswho.records import (
    SOURCE_EMPTY,
    SOURCE_OK,
    SOURCE_PAYWALLED,
    SOURCE_ROBOTS_EXCLUDED,
    SOURCE_UNREACHABLE,
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


def test_404_is_unreachable(server, cache):
    record = fetcher(cache).fetch(server.url("/missing.html"))
    assert record.code == SOURCE_UNREACHABLE
    assert record.http_status == 404
    assert not record.auditable


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
