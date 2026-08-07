"""Drift tests.

The load-bearing case is the last one: a page with no snapshot must come back unknown, never no-drift. That
is the same distinction the whole project rests on, applied one layer down.
"""

from __future__ import annotations

from sayswho.drift import (
    DRIFT_DETECTED,
    DRIFT_NO_SNAPSHOT,
    DRIFT_NONE,
    DRIFT_NOT_CHECKED,
    DRIFT_THRESHOLD,
    DriftChecker,
    DriftRecord,
    apply_drift,
    compare,
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


def test_changed_page_reports_drift_and_records_the_number():
    checker = DriftChecker(_FakeFetcher(AVAILABLE, "An entirely different article about something else."))
    drift = checker.check(record(), "2026-01-02T00:00:00+00:00")

    assert drift.status == DRIFT_DETECTED
    assert drift.containment is not None and drift.containment < DRIFT_THRESHOLD
    assert drift.jaccard is not None, "both numbers are published, not just the verdict"


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


def test_detected_drift_makes_the_source_unauditable():
    r = record()
    assert r.auditable

    apply_drift(r, DriftRecord(url=r.url, status=DRIFT_DETECTED, containment=0.2, detail="containment 0.2"))

    assert r.code == SOURCE_DRIFTED
    assert not r.auditable, "a page we cannot match to what the model read cannot enter a denominator"


def test_unknown_drift_leaves_the_source_alone():
    r = record()
    apply_drift(r, DriftRecord(url=r.url, status=DRIFT_NO_SNAPSHOT))
    assert r.code == SOURCE_OK


def test_drift_checker_accepts_the_real_fetcher_type(cache):
    """Cheap guard that the fake above has not drifted from the real interface."""
    checker = DriftChecker(Fetcher(cache, rate_limit=0.0))
    assert checker.fetcher.cache is cache
