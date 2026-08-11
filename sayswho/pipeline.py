"""The pipeline itself, as three generators, so nothing has to reimplement the loops to watch them run.

`sayswho/cli.py` prints each source and each verdict as it arrives, and `sayswho/harness.py` runs the same
work over a whole stratum without printing anything. Before this module existed the CLI held the only copy
of the loops, so the harness would have been a second orchestration of the same phases: two places deciding
which sources reach the judge, two places deciding what a stored split binds to, and no test that could see
them disagree.

`SCOPE.md` §9 requires the extension and the harness to agree. That contract is easier to keep when the
number of implementations of the pipeline is one, and this is that one.

Generators rather than a function returning a list, because the run is slow and watching it is how the last
four findings were noticed. A progress bar would have hidden every one of them.
"""

from __future__ import annotations

from typing import Iterator

from .drift import DRIFT_NOT_CHECKED, DriftRecord, apply_drift
from .judge import Judgement, judge_claim
from .records import Capture, FetchRecord


def fetch_sources(
    capture: Capture, fetcher, checker=None, use_cache: bool = True
) -> Iterator[tuple[FetchRecord, DriftRecord]]:
    """Fetch every cited URL once, in the order the answer cites them, with drift applied.

    One fetch per unique normalised URL. `capture.cited_urls` has already deduplicated, so a page cited
    three times with three tracking tags is one request rather than three.
    """
    for url in capture.cited_urls:
        record = fetcher.fetch(url, use_cache=use_cache)
        if checker is not None:
            drift = checker.check(record, capture.generated_at)
            apply_drift(record, drift)
        else:
            drift = DriftRecord(url=url, status=DRIFT_NOT_CHECKED, detail="drift checking was off")
        yield record, drift


def phase1(capture: Capture, client, split_path=None):
    """Return the claim set for this capture, either re-derived or loaded from a stored split.

    Loading raises rather than falling back to a fresh split. A run that looks pinned and is not is worse
    than a run that stops, and it is worse in a way nothing downstream can see.
    """
    from .claims import split_claims
    from .splits import StoredSplit

    if split_path is None:
        return split_claims(capture, client), None

    stored = StoredSplit.load(split_path)
    return stored.bind(capture), stored


def judge_claims(claim_set, records, drifts, client) -> Iterator[Judgement]:
    """Judge every claim against every auditable source it cites.

    A source that is not `SOURCE_OK` is skipped here rather than refused in `judge_claim`, so the model is
    never called at all on a page we could not read. There is a test that asserts exactly that: not that
    the verdict is discarded, but that no call was made.
    """
    by_url = {r.url: r for r in records}
    drift_by_url = {d.url: d for d in (drifts or [])}

    for claim in claim_set.claims:
        for url in claim.urls:
            record = by_url.get(url)
            if record is None or not record.auditable:
                continue
            yield judge_claim(claim, record, client, drift=drift_by_url.get(url))
