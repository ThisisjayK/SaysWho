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
saw still present. Both numbers are recorded; only containment decides the code.
"""

from __future__ import annotations

import json
import urllib.parse
from dataclasses import asdict, dataclass
from datetime import datetime

from .extract import normalise_for_span
from .records import SOURCE_DRIFTED, SOURCE_OK, FetchRecord

#: Fixed before the first run. Not tuned afterwards.
DRIFT_THRESHOLD = 0.80
SHINGLE_SIZE = 5

AVAILABILITY_ENDPOINT = "https://archive.org/wayback/available"

DRIFT_NOT_CHECKED = "DRIFT_NOT_CHECKED"
DRIFT_NO_SNAPSHOT = "DRIFT_NO_SNAPSHOT"
DRIFT_NONE = "DRIFT_NONE"
DRIFT_DETECTED = "DRIFT_DETECTED"


@dataclass
class DriftRecord:
    url: str
    status: str
    containment: float | None = None
    jaccard: float | None = None
    snapshot_url: str = ""
    snapshot_timestamp: str = ""
    detail: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


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
        drifted = containment < DRIFT_THRESHOLD

        return DriftRecord(
            url=record.url,
            status=DRIFT_DETECTED if drifted else DRIFT_NONE,
            containment=round(containment, 4),
            jaccard=round(jaccard, 4),
            snapshot_url=raw_url,
            snapshot_timestamp=snapshot_ts,
            detail=(
                f"containment {containment:.4f} below threshold {DRIFT_THRESHOLD}"
                if drifted
                else f"containment {containment:.4f} at or above threshold {DRIFT_THRESHOLD}"
            ),
        )


def apply_drift(record: FetchRecord, drift: DriftRecord) -> FetchRecord:
    """Upgrade a fetch record to SOURCE_DRIFTED when drift was detected.

    A drifted page is UNAUDITABLE, same as an unreachable one. We hold the current page but not the one the
    model read, and auditing against the wrong document would produce a verdict about a text nobody cited.
    """
    if drift.status != DRIFT_DETECTED:
        return record
    record.code = SOURCE_DRIFTED
    record.detail = drift.detail
    return record
