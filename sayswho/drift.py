"""Drift detection against the Wayback Machine.

The question this answers is narrow: is the page we just fetched still the page the model read? If it is not,
judging a claim against it audits a document the model never saw, and a `NOT_FOUND_IN_SOURCE` verdict would
be an artefact of the page having changed rather than a finding about the citation.

DATA_CONTRACT.md §6 fixes the method before the first run. Two things in it are judgment calls, and both are
written down here rather than tuned later:

**The threshold.** Set at 0.80 containment, below. It is not calibrated against anything, because there is no
gold set of drifted pages to calibrate it against. So the raw similarity numbers are recorded on every drift
record and published alongside the code, and a reader who thinks 0.80 is wrong can see what the number was.
A threshold nobody can inspect would be doing the work of a measurement without being one.

**Containment rather than Jaccard.** Jaccard punishes a page that grew. A site that added a new section since
the answer was generated would look drifted, even though every sentence the model read is still there.
Containment of the snapshot in the current page asks the question that actually matters: is what the model
saw still present. Both numbers are recorded.

**Page-level containment is not a gate.** It was, and it was wrong. On the first live run a PubMed abstract
came back at containment 0.62 and was excluded as `SOURCE_DRIFTED`. The 498 missing shingles were all from
the *Similar articles* and *Cited by* blocks: authors, DOIs and dates of other papers. The abstract itself,
the only part any claim would cite, was unchanged. The check measured the page's furniture, and a false
`SOURCE_DRIFTED` deletes a genuinely auditable source from every denominator. Any page with a "related
content" block behaves this way, so the failure is systematic rather than unlucky.

So the question moved. Page level now answers only "is this still the same document at all", which is a
threshold near zero rather than near one. Whether drift actually matters is decided per claim in Phase 3, by
asking whether **the span the judge quoted** is also in the archived version. Drift only matters when it
moved the sentence the claim rests on, the machinery already exists in the span guard, and it costs no model
calls.

**What this still cannot see.** It catches support that arrived *after* generation. It does not catch support
that was *removed* before we fetched: if the page once said something and no longer does, the judge returns
`NOT_FOUND_IN_SOURCE` and we cannot tell that apart from a citation that was always wrong. Detecting that
would mean judging every claim twice, against live and against archive, and doubling the run to measure it is
a trade this project has not made. It is a limitation, stated.
"""

from __future__ import annotations

import json
import urllib.parse
from dataclasses import asdict, dataclass, field
from datetime import datetime

from .extract import normalise_for_span
from .records import SOURCE_DRIFTED, SOURCE_OK, FetchRecord

#: Fixed before the first run. Not tuned afterwards. Now only the boundary between "unchanged" and
#: "changed", both of which stay auditable; it no longer gates anything.
DRIFT_THRESHOLD = 0.80

#: Below this the URL is serving a different document, not an edited one. A redirect to a homepage, a
#: paywall interstitial replacing an article, a 404 body served with a 200. That is genuinely unauditable,
#: and it is the only page-level condition that still excludes a source.
PAGE_REPLACED_THRESHOLD = 0.10

SHINGLE_SIZE = 5

AVAILABILITY_ENDPOINT = "https://archive.org/wayback/available"

DRIFT_NOT_CHECKED = "DRIFT_NOT_CHECKED"
DRIFT_NO_SNAPSHOT = "DRIFT_NO_SNAPSHOT"
DRIFT_NONE = "DRIFT_NONE"

#: The page changed but is still the same document. Recorded, not a gate: whether it matters is a per-claim
#: question answered by the span check in Phase 3.
DRIFT_PAGE_CHANGED = "DRIFT_PAGE_CHANGED"

#: The page is no longer the same document. The only drift condition that still makes a source unauditable.
DRIFT_PAGE_REPLACED = "DRIFT_PAGE_REPLACED"


@dataclass
class DriftRecord:
    url: str
    status: str
    containment: float | None = None
    jaccard: float | None = None
    snapshot_url: str = ""
    snapshot_timestamp: str = ""
    detail: str = ""

    #: The archived text, kept for the Phase 3 span check. Excluded from to_dict for the same reason
    #: FetchRecord.text is: the repo publishes verdicts and spans, not copies of pages.
    archived_text: str = field(default="", repr=False)

    @property
    def can_check_spans(self) -> bool:
        return bool(self.archived_text)

    def to_dict(self) -> dict:
        d = asdict(self)
        d.pop("archived_text", None)
        return d


def shingles(text: str, n: int = SHINGLE_SIZE) -> set[tuple[str, ...]]:
    tokens = normalise_for_span(text).split()
    if len(tokens) < n:
        return {tuple(tokens)} if tokens else set()
    return {tuple(tokens[i : i + n]) for i in range(len(tokens) - n + 1)}


def compare(snapshot_text: str, current_text: str) -> tuple[float, float]:
    """Return (containment_of_snapshot_in_current, jaccard).

    Containment is the one the threshold uses. It asks whether what the model read is still on the page,
    which is a different question from whether the page is identical.
    """
    a = shingles(snapshot_text)
    b = shingles(current_text)
    if not a and not b:
        return 1.0, 1.0
    if not a or not b:
        return 0.0, 0.0

    intersection = len(a & b)
    containment = intersection / len(a)
    jaccard = intersection / len(a | b)
    return containment, jaccard


def _wayback_timestamp(iso: str) -> str:
    """ISO 8601 to the YYYYMMDDhhmmss form the Wayback APIs use."""
    cleaned = iso.replace("Z", "+00:00")
    return datetime.fromisoformat(cleaned).strftime("%Y%m%d%H%M%S")


class DriftChecker:
    def __init__(self, fetcher, availability_endpoint: str = AVAILABILITY_ENDPOINT) -> None:
        self.fetcher = fetcher
        self.availability_endpoint = availability_endpoint

    def nearest_snapshot(self, url: str, generated_at: str) -> tuple[str, str] | None:
        """Closest archived snapshot to the answer's generation time, or None."""
        query = urllib.parse.urlencode({"url": url, "timestamp": _wayback_timestamp(generated_at)})
        record = self.fetcher.fetch(f"{self.availability_endpoint}?{query}")

        if record.http_status != 200:
            return None

        cached = self.fetcher.cache.latest(f"{self.availability_endpoint}?{query}")
        if cached is None:
            return None

        try:
            payload = json.loads(cached[1].decode("utf-8", errors="replace"))
            closest = payload["archived_snapshots"]["closest"]
            if not closest.get("available"):
                return None
            return closest["url"], closest.get("timestamp", "")
        except (ValueError, KeyError, TypeError):
            return None

    def check(self, record: FetchRecord, generated_at: str) -> DriftRecord:
        if record.code != SOURCE_OK:
            return DriftRecord(
                url=record.url,
                status=DRIFT_NOT_CHECKED,
                detail=f"source was {record.code}, so there is nothing to compare",
            )

        snapshot = self.nearest_snapshot(record.url, generated_at)
        if snapshot is None:
            # Reported as unknown, never as no-drift. An absent snapshot is not evidence the page is
            # unchanged, and treating it as such would quietly convert missing data into a clean result.
            return DriftRecord(
                url=record.url,
                status=DRIFT_NO_SNAPSHOT,
                detail="no archived snapshot near the generation timestamp, so drift is unknown",
            )

        snapshot_url, snapshot_ts = snapshot
        # The id_ suffix asks Wayback for the original bytes without its own injected toolbar. Without it,
        # every comparison would find drift that the archive itself introduced.
        raw_url = snapshot_url.replace(f"/{snapshot_ts}/", f"/{snapshot_ts}id_/", 1)
        archived = self.fetcher.fetch(raw_url)

        if not archived.text:
            return DriftRecord(
                url=record.url,
                status=DRIFT_NO_SNAPSHOT,
                snapshot_url=raw_url,
                snapshot_timestamp=snapshot_ts,
                detail=f"snapshot fetch returned {archived.code}, so drift is unknown",
            )

        containment, jaccard = compare(archived.text, record.text)

        if containment < PAGE_REPLACED_THRESHOLD:
            status = DRIFT_PAGE_REPLACED
            detail = (
                f"containment {containment:.4f} below {PAGE_REPLACED_THRESHOLD}: this URL is serving a "
                "different document from the one that was archived"
            )
        elif containment < DRIFT_THRESHOLD:
            status = DRIFT_PAGE_CHANGED
            detail = (
                f"containment {containment:.4f}: the page changed but is still the same document. Whether "
                "that matters is decided per claim, by checking the judge's span against the archive"
            )
        else:
            status = DRIFT_NONE
            detail = f"containment {containment:.4f} at or above threshold {DRIFT_THRESHOLD}"

        return DriftRecord(
            url=record.url,
            status=status,
            containment=round(containment, 4),
            jaccard=round(jaccard, 4),
            snapshot_url=raw_url,
            snapshot_timestamp=snapshot_ts,
            detail=detail,
            archived_text=archived.text,
        )


def apply_drift(record: FetchRecord, drift: DriftRecord) -> FetchRecord:
    """Mark a source unauditable only when the URL now serves a *different document*.

    A page that merely changed stays auditable. Excluding it would delete a real source over a reference list
    that churned, which is what the old whole-page gate did. An edited page is still the page that was cited;
    a replaced one is not.
    """
    if drift.status != DRIFT_PAGE_REPLACED:
        return record
    record.code = SOURCE_DRIFTED
    record.detail = drift.detail
    return record


def span_predates_generation(span: str, drift: DriftRecord) -> bool | None:
    """Was the judge's span already on the page when the answer was written?

    `None` when there is nothing to compare against, which is most of the time: five of six sources on the
    first live run had no archived snapshot at all. Unknown is reported as unknown, never as yes.
    """
    if not drift.can_check_spans or not span.strip():
        return None
    # The same comparison G3 uses, rather than a second copy of it. These two are the only places a span is
    # checked against a document, and when G3 learned to tolerate a footnote marker this one would otherwise
    # have kept voiding the same span as SPAN_ADDED_AFTER_GENERATION: one bug, two codes, and the second one
    # blames the page for changing rather than the judge for quoting.
    from .judge import span_is_present

    return span_is_present(span, drift.archived_text)
