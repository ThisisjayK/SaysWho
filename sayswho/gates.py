"""Gates. Each one has an explicit failure path and each one is tested against the bug it exists to catch.

`SCOPE.md` §3: "A claim that fails a gate exits the pipeline with a reason code and is never silently
downgraded." A gate with no failure path is decoration, so the tests in `tests/` assert that each gate fires,
not merely that it exists.
"""

from __future__ import annotations

from dataclasses import dataclass

from .goldset import COMPARABLE
from .records import AUDITABLE_CODES, NO_CITATIONS, Capture, FetchRecord


@dataclass(frozen=True)
class GateResult:
    passed: bool
    code: str = ""
    detail: str = ""


def g0_has_citations(capture: Capture) -> GateResult:
    """Gate G0. An answer with no inline citations is not scored.

    It is reported as uncitable. An uncited answer is not a zero percent answer, it is a different object,
    and giving it a zero would put a number under something that was never measured.
    """
    if not capture.citations:
        return GateResult(False, NO_CITATIONS, "answer contains no inline citations")
    missing = [c.marker for c in capture.citations if not c.url.strip()]
    if missing:
        return GateResult(False, NO_CITATIONS, f"citation markers with no URL: {missing}")
    return GateResult(True)


def g2_auditable(record: FetchRecord) -> GateResult:
    """Gate G2. Anything other than SOURCE_OK stops the claim before the judge sees it."""
    if record.code in AUDITABLE_CODES:
        return GateResult(True)
    return GateResult(False, record.code, record.detail or f"source not readable: {record.code}")


class DenominatorContract(Exception):
    """Raised when an unauditable claim reaches a published denominator.

    This is break attempt 6 in `SCOPE.md` §6 and it is core, not stretch. The test forces the violation and
    asserts this fires.
    """


def auditable_denominator(records: list[FetchRecord]) -> int:
    """Count of claims eligible for a published rate.

    The contract check lives here rather than at the reporting layer on purpose. A denominator computed
    anywhere else in the codebase would bypass it, so there is one function and everything uses it.
    """
    for record in records:
        if record.code not in AUDITABLE_CODES and record.auditable:
            raise DenominatorContract(
                f"{record.url} has code {record.code} but reports auditable=True. "
                "An unauditable claim cannot enter a denominator."
            )
    return sum(1 for record in records if record.auditable)


#: Gate G4 failure code. No gold set exists for the judge, prompt version and split this run used.
NO_CALIBRATION = "NO_CALIBRATION"


#: The smallest number of blind, comparable labels a gold set must carry before G4 calls it a calibration.
#:
#: Set to the floor of the range `SCOPE.md` §0a asks for, thirty to forty hand-labelled claims, so the gate
#: enforces the design document's own promise rather than a threshold invented in this file. Changing it is
#: a decision about what this project will publish, so it is one constant in one place and it moves by commit
#: with a reason, never by a flag on a run that wants a number.
#:
#: **This counts labels, not agreements, and the difference is not pedantic.** G4 never sees the judgements,
#: so what it can check is an upper bound on the n that kappa is eventually computed over: a blind comparable
#: label whose verdict was voided, or never produced, drops out in `goldset.agreement` afterwards. The gate
#: can refuse a set that cannot possibly calibrate. It cannot promise that one which passes does.
MIN_BLIND_COMPARABLE = 30


def g4_calibration_exists(goldset, judge_class: str, judge_model: str,
                          judge_prompt_version: str, claim_prompt_version: str,
                          split_sha256: str,
                          min_blind_comparable: int = MIN_BLIND_COMPARABLE) -> GateResult:
    """Gate G4. Aggregate rates are refused unless a gold set was labelled for this exact configuration.

    Per-claim verdicts still emit. `SCOPE.md` §3: an uncalibrated judge can produce useful individual
    audits; it cannot produce a trustworthy percentage.

    The tuple includes `split_sha256` because Phase 1 does not return the same split twice, so "the gold set
    for this judge and prompt version" did not identify a fixed set of claims. `FINDINGS.md` item 8.

    Membership rather than equality: a gold set covers every answer it was labelled against, and the run in
    front of it judges one of them at a time. Equality made a set spanning two answers, which is what
    reaching thirty to forty pairs requires, calibrate neither of them.

    Every mismatch is reported separately rather than as one "no calibration" answer, because the reasons
    need different actions: relabel, revert the prompt, re-pin the split, swap the judge back, or label more.

    **The label check was added on day 8, and the hole it closes was open the whole time.** Until then this
    function verified that a gold set existed for the configuration and looked at no label in it. It had no
    minimum count and did not ask whether a single label was blind, so a set of forty supplemental labels
    spanning every split in a run would have opened the gate and printed a stratum rate calibrated by
    whatever blind labels happened to be underneath, which on day 8 was two. Supplemental labels are excluded
    from kappa by construction in `goldset.agreement`, so a set made only of them calibrates nothing while
    satisfying every check this gate used to make. `FINDINGS.md` item 22.

    The gate is named for what it should verify, and now does: that a calibration exists, not that a file
    does.
    """
    if goldset is None:
        return GateResult(
            False, NO_CALIBRATION,
            "no gold set has been labelled for this judge and prompt version, so no aggregate rate may be "
            "printed. Per-claim verdicts still emit.",
        )

    mismatches = []
    if goldset.judge_class != judge_class or goldset.judge_model != judge_model:
        mismatches.append(
            f"gold set was labelled against {goldset.judge_class} {goldset.judge_model}, this run used "
            f"{judge_class} {judge_model}"
        )
    if goldset.judge_prompt_version != judge_prompt_version:
        mismatches.append(
            f"gold set was labelled under judge prompt {goldset.judge_prompt_version}, this run used "
            f"{judge_prompt_version}"
        )
    if goldset.claim_prompt_version != claim_prompt_version:
        mismatches.append(
            f"gold set was labelled under claim prompt {goldset.claim_prompt_version}, this run used "
            f"{claim_prompt_version}"
        )
    if not goldset.split_sha256s:
        mismatches.append(
            "gold set records no split at all, so there is nothing to say it was labelled against these "
            "claims. A set that binds to nothing would otherwise calibrate everything"
        )
    elif split_sha256 not in goldset.split_sha256s:
        labelled = ", ".join(s[:16] for s in goldset.split_sha256s)
        mismatches.append(
            f"gold set was labelled against split(s) {labelled}, this run judged split {split_sha256[:16]}. "
            "A gold set is valid for the splits it was labelled against and no others"
        )

    blind_comparable = [l for l in goldset.blind if l.label in COMPARABLE]
    if not goldset.blind:
        mismatches.append(
            f"gold set holds {len(goldset.labels)} label(s) and not one of them is blind. Supplemental "
            "labels are excluded from kappa by construction, so this set calibrates nothing however many "
            "of them there are"
        )
    elif len(blind_comparable) < min_blind_comparable:
        mismatches.append(
            f"gold set holds {len(blind_comparable)} blind label(s) that can be compared with a verdict and "
            f"{min_blind_comparable} is the floor. {len(goldset.supplemental)} supplemental label(s) are "
            "not counted here, because kappa excludes them"
        )

    if mismatches:
        return GateResult(False, NO_CALIBRATION, "; ".join(mismatches))
    return GateResult(True)


def assert_no_confidence_number(payload) -> None:
    """`SCOPE.md` §1b: no numeric confidence anywhere, enforced by a test rather than by intention.

    Walks any nested structure and rejects a key that looks like a confidence score. It is a blunt check on
    purpose. The failure it prevents is a plausible number appearing next to a claim nobody could verify.
    """
    banned = ("confidence", "certainty", "probability", "trust_score", "score")

    def walk(node, path="$"):
        if isinstance(node, dict):
            for key, value in node.items():
                lowered = str(key).lower()
                for bad in banned:
                    if bad in lowered:
                        raise AssertionError(f"confidence-like field {path}.{key} is not allowed")
                walk(value, f"{path}.{key}")
        elif isinstance(node, (list, tuple)):
            for i, value in enumerate(node):
                walk(value, f"{path}[{i}]")

    walk(payload)
