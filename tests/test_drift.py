"""Drift tests.

The load-bearing case is the last one: a page with no snapshot must come back unknown, never no-drift. That
is the same distinction the whole project rests on, applied one layer down.
"""

from __future__ import annotations

from sayswho.drift import (
    DRIFT_NO_SNAPSHOT,
    DRIFT_NONE,
    DRIFT_NOT_CHECKED,
    DRIFT_PAGE_CHANGED,
    DRIFT_PAGE_REPLACED,
    DRIFT_THRESHOLD,
    DriftChecker,
    DriftRecord,
    apply_drift,
    compare,
    span_predates_generation,
)
from sayswho.fetch import Fetcher
from sayswho.records import SOURCE_DRIFTED, SOURCE_OK, SOURCE_PAYWALLED, FetchRecord

ORIGINAL = (
    "Extending adjuvant endocrine therapy beyond five years reduced recurrence in the trial cohort, "
    "though the absolute benefit was small and concentrated in higher risk patients. "
    "No overall survival difference reached significance at the reported follow up."
)


def record(text=ORIGINAL, code=SOURCE_OK):
    return FetchRecord(
        url="https://example.org/a",
        code=code,
        fetched_at="2026-08-07T00:00:02+00:00",
        http_status=200,
        text=text,
        text_length=len(text),
    )


# ---------------------------------------------------------------- similarity


def test_identical_text_is_fully_contained():
    containment, jaccard = compare(ORIGINAL, ORIGINAL)
    assert containment == 1.0
    assert jaccard == 1.0


def test_a_page_that_only_grew_is_not_drift():
    """Containment rather than Jaccard, and this is why.

    A site that added a section since the answer was generated has not lost anything the model read. Jaccard
    would call that drift and exclude a perfectly auditable claim.
    """
    grown = ORIGINAL + " A later section was added about adverse event reporting in the extension phase."
    containment, jaccard = compare(ORIGINAL, grown)

    assert containment == 1.0, "everything the model read is still on the page"
    assert jaccard < 1.0, "Jaccard sees the growth as a difference"
    assert containment >= DRIFT_THRESHOLD


def test_a_rewritten_page_falls_below_the_threshold():
    rewritten = (
        "The trial was withdrawn following an error in the recurrence analysis. "
        "Readers should not rely on the previously reported figures for any clinical purpose."
    )
    containment, _ = compare(ORIGINAL, rewritten)
    assert containment < DRIFT_THRESHOLD


# ---------------------------------------------------------------- the checker


class _FakeFetcher:
    """Stands in for Fetcher. Records what was asked for so the id_ suffix can be asserted."""

    def __init__(self, availability_body: bytes | None, snapshot_text: str | None):
        self.availability_body = availability_body
        self.snapshot_text = snapshot_text
        self.requested: list[str] = []

        class _Cache:
            def __init__(self, outer):
                self.outer = outer

            def latest(self, url):
                if self.outer.availability_body is None:
                    return None
                return {"status": 200}, self.outer.availability_body

        self.cache = _Cache(self)

    def fetch(self, url, use_cache=True):
        self.requested.append(url)
        if "wayback/available" in url:
            status = 200 if self.availability_body is not None else 404
            return FetchRecord(url=url, code=SOURCE_OK, fetched_at="x", http_status=status, text="{}")
        text = self.snapshot_text or ""
        return FetchRecord(
            url=url,
            code=SOURCE_OK if text else SOURCE_PAYWALLED,
            fetched_at="x",
            http_status=200,
            text=text,
            text_length=len(text),
        )


AVAILABLE = (
    b'{"archived_snapshots":{"closest":{"available":true,'
    b'"url":"http://web.archive.org/web/20260101000000/https://example.org/a",'
    b'"timestamp":"20260101000000","status":"200"}}}'
)

NOT_AVAILABLE = b'{"archived_snapshots":{}}'


def test_unchanged_page_reports_no_drift():
    checker = DriftChecker(_FakeFetcher(AVAILABLE, ORIGINAL))
    drift = checker.check(record(), "2026-01-02T00:00:00+00:00")

    assert drift.status == DRIFT_NONE
    assert drift.containment == 1.0


def test_a_page_that_shed_a_reference_list_is_changed_but_still_auditable():
    """The PubMed false positive, pinned.

    The archive holds the abstract plus a Similar articles block; the live page holds the abstract alone.
    Containment falls well under the threshold, and excluding the source over that would delete a genuinely
    auditable citation from every denominator.
    """
    archived = ORIGINAL + (
        " Similar articles: Munjewar PK, Wanjari MB. Nayyar V, Mullikin KR, Lemon SC. "
        "Okwaraji G, Lobaina D, Jhumkhawala V. doi 10.1177/22799036241268841. "
        "Cited by: three further papers with their own authors and identifiers."
    )
    checker = DriftChecker(_FakeFetcher(AVAILABLE, archived))
    drift = checker.check(record(), "2026-01-02T00:00:00+00:00")

    assert drift.containment < DRIFT_THRESHOLD, "the page really did change by this measure"
    assert drift.status == DRIFT_PAGE_CHANGED
    assert drift.jaccard is not None, "both numbers are published, not just the status"

    r = record()
    apply_drift(r, drift)
    assert r.code == SOURCE_OK, "a page that lost its reference list is still the page that was cited"
    assert r.auditable


def test_a_url_now_serving_a_different_document_is_unauditable():
    """The one page-level condition that still excludes. A redirect to a homepage is not an edit."""
    checker = DriftChecker(_FakeFetcher(AVAILABLE, "Sign in to continue. Create an account. Our newsletter."))
    drift = checker.check(record(), "2026-01-02T00:00:00+00:00")

    assert drift.status == DRIFT_PAGE_REPLACED
    r = record()
    apply_drift(r, drift)
    assert r.code == SOURCE_DRIFTED and not r.auditable


def test_snapshot_is_fetched_with_the_id_suffix():
    """Without id_, Wayback returns its own toolbar wrapped around the page.

    Every comparison would then find drift the archive introduced rather than drift the publisher did.
    """
    fetcher = _FakeFetcher(AVAILABLE, ORIGINAL)
    DriftChecker(fetcher).check(record(), "2026-01-02T00:00:00+00:00")

    snapshot_requests = [u for u in fetcher.requested if "web.archive.org" in u]
    assert snapshot_requests
    assert all("id_/" in u for u in snapshot_requests)


def test_no_snapshot_is_unknown_and_never_no_drift():
    """The load-bearing case.

    An absent snapshot is not evidence the page is unchanged. Reporting it as DRIFT_NONE would convert
    missing data into a clean result, which is the exact move this project exists to refuse.
    """
    checker = DriftChecker(_FakeFetcher(NOT_AVAILABLE, ORIGINAL))
    drift = checker.check(record(), "2026-01-02T00:00:00+00:00")

    assert drift.status == DRIFT_NO_SNAPSHOT
    assert drift.status != DRIFT_NONE
    assert drift.containment is None, "no number is reported when nothing was compared"
    assert "unknown" in drift.detail


def test_an_unreadable_source_is_not_drift_checked():
    checker = DriftChecker(_FakeFetcher(AVAILABLE, ORIGINAL))
    drift = checker.check(record(code=SOURCE_PAYWALLED), "2026-01-02T00:00:00+00:00")

    assert drift.status == DRIFT_NOT_CHECKED


# ---------------------------------------------------------------- applying it


def test_a_replaced_page_makes_the_source_unauditable():
    r = record()
    assert r.auditable

    apply_drift(r, DriftRecord(url=r.url, status=DRIFT_PAGE_REPLACED, containment=0.02, detail="replaced"))

    assert r.code == SOURCE_DRIFTED
    assert not r.auditable, "a URL serving a different document cannot enter a denominator"


def test_a_merely_changed_page_does_not(): 
    r = record()
    apply_drift(r, DriftRecord(url=r.url, status=DRIFT_PAGE_CHANGED, containment=0.62, detail="changed"))
    assert r.code == SOURCE_OK, "this is the regression the PubMed false positive produced"


# ---------------------------------------------------------------- drift, asked per claim


ARCHIVED = "Recurrence fell in the extended arm. No survival difference was seen."
LIVE = ARCHIVED + " A 2026 correction adds that overall survival improved by 12%."


def drift_with_archive(text=ARCHIVED):
    return DriftRecord(url="https://example.org/a", status=DRIFT_PAGE_CHANGED, archived_text=text)


def test_a_span_that_was_already_on_the_archived_page_predates_the_answer():
    assert span_predates_generation("Recurrence fell in the extended arm", drift_with_archive()) is True


def test_a_span_added_after_generation_is_detected():
    """The case that actually matters: the verdict rests on text the model could not have read."""
    assert span_predates_generation("overall survival improved by 12%", drift_with_archive()) is False


def test_no_snapshot_means_unknown_rather_than_yes():
    """Five of six sources on the first live run had no snapshot. Unknown has to stay unknown."""
    no_archive = DriftRecord(url="u", status=DRIFT_NO_SNAPSHOT)
    assert span_predates_generation("anything at all", no_archive) is None


def test_unknown_drift_leaves_the_source_alone():
    r = record()
    apply_drift(r, DriftRecord(url=r.url, status=DRIFT_NO_SNAPSHOT))
    assert r.code == SOURCE_OK


def test_drift_checker_accepts_the_real_fetcher_type(cache):
    """Cheap guard that the fake above has not drifted from the real interface."""
    checker = DriftChecker(Fetcher(cache, rate_limit=0.0))
    assert checker.fetcher.cache is cache
