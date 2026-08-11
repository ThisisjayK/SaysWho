"""Existence checking tests.

No network: `resolve` takes its fetcher as an argument, so the suite does not fail when Crossref is down for
a reason that has nothing to do with this repo.

Most of these are about the boundary rather than the matching. The matching being wrong costs a lookup. The
boundary being wrong would mean this project judging a claim against a source it selected itself, which is
the exact failure it exists to catch.
"""

from __future__ import annotations

import json

import pytest

from sayswho.crossref import (
    CITATION_AMBIGUOUS,
    CITATION_LOOKUP_FAILED,
    CITATION_NOT_FOUND,
    CITATION_RESOLVED,
    ExistenceReport,
    Resolution,
    check_named,
    resolve,
)
from sayswho.records import Capture, Citation


def work(family="LeClair", year=2022, doi="10.1007/s00520-022-06879-w", title="Adjuvant therapy duration"):
    return {
        "DOI": doi,
        "title": [title],
        "author": [{"family": family, "given": "A"}],
        "issued": {"date-parts": [[year]]},
        "abstract": "SHOULD NEVER APPEAR IN A RECORD",
    }


def responder(items, calls=None):
    def fetch(url, timeout=20.0):
        if calls is not None:
            calls.append(url)
        if "/works?" in url:
            return {"message": {"items": items}}
        return {"message": items[0] if items else {}}

    return fetch


# ---------------------------------------------------------------- the three outcomes


def test_a_matching_author_and_year_resolves():
    r = resolve("LeClair et al., Supportive Care in Cancer, 2022", fetch_json=responder([work()]))
    assert r.outcome == CITATION_RESOLVED
    assert r.doi == "10.1007/s00520-022-06879-w"
    assert r.candidates == 1


def test_no_matching_author_is_not_found():
    r = resolve("LeClair et al., Supportive Care in Cancer, 2022",
                fetch_json=responder([work(family="Nakamura")]))
    assert r.outcome == CITATION_NOT_FOUND


def test_a_year_that_is_years_off_is_not_a_match():
    r = resolve("LeClair et al., Supportive Care in Cancer, 2022",
                fetch_json=responder([work(year=2015)]))
    assert r.outcome == CITATION_NOT_FOUND


def test_a_year_off_by_one_still_matches():
    """Print and online publication years differ constantly, and a citation usually names one of them."""
    r = resolve("LeClair et al., Supportive Care in Cancer, 2022",
                fetch_json=responder([work(year=2021)]))
    assert r.outcome == CITATION_RESOLVED


def test_two_matching_works_are_ambiguous_and_neither_is_named():
    """Naming one would be a choice rather than a resolution, which is the move this module refuses."""
    r = resolve(
        "LeClair et al., Supportive Care in Cancer, 2022",
        fetch_json=responder([work(doi="10.1/a"), work(doi="10.2/b", title="Another paper")]),
    )
    assert r.outcome == CITATION_AMBIGUOUS
    assert r.candidates == 2
    assert r.doi == "", "an ambiguous lookup must not name a candidate"


def test_a_doi_resolves_directly(calls=None):
    calls = []
    r = resolve("See 10.1007/s00520-022-06879-w for the trial.",
                fetch_json=responder([work()], calls))
    assert r.outcome == CITATION_RESOLVED
    assert "query.bibliographic" not in calls[0], "a DOI is unambiguous and needs no search"


def test_a_network_failure_is_not_reported_as_a_missing_paper():
    """Reporting our own outage as CITATION_NOT_FOUND would turn it into a finding about someone's citation."""

    def broken(url, timeout=20.0):
        raise OSError("connection refused")

    r = resolve("LeClair et al., 2022", fetch_json=broken)
    assert r.outcome == CITATION_LOOKUP_FAILED
    assert "connection refused" in r.detail


def test_a_citation_with_no_readable_author_reports_that_rather_than_guessing():
    r = resolve("2022", fetch_json=responder([work()]))
    assert r.outcome == CITATION_LOOKUP_FAILED
    assert "nothing to match on" in r.detail


# ---------------------------------------------------------------- the boundary


def test_a_resolution_carries_no_document_text():
    """If the text is never in the record, no later version of this can quietly start judging against it."""
    r = resolve("LeClair et al., Supportive Care in Cancer, 2022", fetch_json=responder([work()]))
    blob = json.dumps(r.to_dict())
    assert "SHOULD NEVER APPEAR" not in blob
    assert "abstract" not in blob


def test_every_record_says_it_is_existence_only():
    r = resolve("LeClair et al., 2022", fetch_json=responder([work()]))
    assert "says nothing whatever about" in r.to_dict()["note"]
    assert "enters no support-rate denominator" in r.to_dict()["note"]


def test_the_report_repeats_the_boundary_where_the_counts_are():
    report = ExistenceReport([Resolution(query="x", outcome=CITATION_RESOLVED)])
    assert "enters any support-rate denominator" in report.to_dict()["note"]
    assert "not that the citation is fabricated" in report.to_dict()["note"]
    assert "Existence only" in report.render()


def test_nothing_in_the_rates_module_knows_about_crossref():
    """The structural version of the boundary: the arithmetic cannot reach these outcomes."""
    from pathlib import Path

    source = (Path(__file__).resolve().parent.parent / "sayswho" / "rates.py").read_text()
    assert "crossref" not in source.lower()
    assert "CITATION_RESOLVED" not in source


def test_a_resolved_citation_is_not_a_pair_and_cannot_be_counted():
    """A support rate is over claim-source pairs. A resolution is not one, and there is no path that makes
    it one: `pairs_from` builds only from the split's cited URLs."""
    from sayswho.claims import Claim, ClaimSet
    from sayswho.rates import pairs_from

    claim_set = ClaimSet(
        claims=[Claim(id="c1", text="A claim with no link.", markers=[], urls=[])], skipped=[]
    )
    assert pairs_from(claim_set, [], []) == []


# ---------------------------------------------------------------- over a whole answer


def test_named_citations_in_a_capture_are_looked_up_politely():
    slept = []
    calls = []
    capture = Capture(
        query_id="PR-01", product="claude", model_id="test",
        generated_at="2026-08-11T00:00:00+00:00", captured_at="2026-08-11T00:00:01+00:00",
        answer_text=(
            "Screening reduced mortality by 78% (LeClair et al., Supportive Care in Cancer, 2022). "
            "A second finding came from Rajabiun et al., Cancer, 2025."
        ),
        citations=[Citation(marker="[1]", url="https://example.org/a")],
    )
    report = check_named(capture, fetch_json=responder([work()], calls), sleep=slept.append)

    assert len(report.resolutions) == 2
    assert slept == [1.0], "one request per second per DATA_CONTRACT.md §2, and no wait before the first"
    assert len(calls) == 2


def test_an_answer_with_no_named_citations_looks_nothing_up():
    capture = Capture(
        query_id="PR-01", product="chatgpt", model_id="test",
        generated_at="2026-08-11T00:00:00+00:00", captured_at="2026-08-11T00:00:01+00:00",
        answer_text="A claim with a real link [1].",
        citations=[Citation(marker="[1]", url="https://example.org/a")],
    )
    calls = []
    report = check_named(capture, fetch_json=responder([work()], calls))
    assert report.resolutions == []
    assert calls == []
    assert "no named citations" in report.render()


def test_the_report_passes_the_no_confidence_number_gate():
    from sayswho.gates import assert_no_confidence_number

    report = ExistenceReport([Resolution(query="x", outcome=CITATION_RESOLVED, doi="10.1/a")])
    assert_no_confidence_number(report.to_dict())
