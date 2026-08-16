"""The re-audit tool has to read both shapes that carry verdicts, and say so when it reads neither.

Day 9 it was pointed at a stratum run record holding two voided spans and printed "No voided spans found in
these reports. Nothing to re-audit." It reads `claims[].sources[]`, which is the per-answer report shape, and
a run record nests `runs[].judgements[]` while using `claims` for a dict of counts. So the loop found nothing
and said so in the same words it would have used for a genuinely clean run.

That is the failure worth testing: not a wrong answer but a reassuring one. The fabricated-span figure is
published as a finding about the judge, and §8 requires this check before it may be described as one, so a
check that silently passes over the evidence is the same class of fault as the extraction bugs in item 11.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

from reaudit_spans import Summary, recheck, voided_rows

FABRICATED = "JUDGE_FABRICATED_SPAN"


def run_record(**judgement) -> dict:
    """A stratum run record, the shape `tools/run_stratum.py` writes."""
    return {
        "generated_by": "tools/run_stratum.py",
        # A run record uses `claims` for counts rather than for a list. Reading it as a list is how the
        # original loop found nothing, so the fixture keeps the dict.
        "runs": [{"query_id": "CO-24", "claims": {"claim_count": 1}, "judgements": [judgement]}],
    }


def report(**row) -> dict:
    """A per-answer report, the shape the CLI and the local server write."""
    return {
        "generated_by": "sayswho.cli",
        "claims": [{"id": row.pop("claim_id", "CO-24#abc"), "sources": [row]}],
    }


def test_a_stratum_run_record_yields_its_voided_judgements():
    """The bug. Two voids in a run record read as zero, and the tool called that nothing to re-audit."""
    payload = run_record(
        claim_id="CO-24#2391984c", url="https://example.test/a", span="not on the page",
        verdict="SUPPORTED", voided=True, void_reason=FABRICATED,
    )
    rows, shape = voided_rows(payload)

    assert shape == "stratum run record"
    assert [claim_id for claim_id, _ in rows] == ["CO-24#2391984c"]


def test_a_per_answer_report_still_yields_its_voided_sources():
    """The shape that always worked. Fixing the first must not cost the second."""
    payload = report(
        claim_id="CO-24#abc", url="https://example.test/a", span="not on the page",
        verdict="SUPPORTED", voided=True, void_reason=FABRICATED,
    )
    rows, shape = voided_rows(payload)

    assert shape == "per-answer report"
    assert [claim_id for claim_id, _ in rows] == ["CO-24#abc"]


def test_a_verdict_that_stands_is_not_collected():
    """Only voided rows are re-audited. A standing verdict has nothing to overturn."""
    payload = run_record(
        claim_id="CO-24#fine", url="https://example.test/a", span="on the page",
        verdict="SUPPORTED", voided=False, void_reason="",
    )
    rows, _shape = voided_rows(payload)

    assert rows == []


def test_an_unrecognised_shape_is_named_rather_than_reported_as_clean(tmp_path):
    """The half of the fix that matters most. A file this tool cannot read must not print the same
    reassuring nothing as a file with no voids in it."""
    path = tmp_path / "mystery.json"
    path.write_text(json.dumps({"generated_by": "something else", "claims": {"claim_count": 3}}))

    summary = recheck([path], tmp_path / "cache")
    rendered = summary.render()

    assert summary.unreadable == ["mystery.json"]
    assert "NOT" in rendered and "does not read" in rendered
    assert "Nothing to re-audit" not in rendered


def test_a_genuinely_clean_report_still_says_nothing_to_re_audit(tmp_path):
    """The other side of it. Distinguishing the two states is the point, so the clean state has to keep
    reading as clean rather than every empty result now looking like a parse failure."""
    path = tmp_path / "clean.json"
    path.write_text(json.dumps(report(
        claim_id="CO-01#ok", url="https://example.test/a", span="on the page",
        verdict="SUPPORTED", voided=False, void_reason="",
    )))

    summary = recheck([path], tmp_path / "cache")
    rendered = summary.render()

    assert summary.unreadable == []
    assert "Nothing to re-audit" in rendered


def test_a_void_the_fold_cannot_change_is_not_counted_as_re_checked(tmp_path):
    """`SPAN_ADDED_AFTER_GENERATION` is a fact about when the text appeared, not about string comparison.
    The day 9 run has one, and counting it among the re-checked spans would inflate the denominator of a
    figure about the judge."""
    path = tmp_path / "drifted.json"
    path.write_text(json.dumps(run_record(
        claim_id="CO-21#1fe4892a", url="https://example.test/a", span="added later",
        verdict="SUPPORTED", voided=True, void_reason="SPAN_ADDED_AFTER_GENERATION",
    )))

    summary = recheck([path], tmp_path / "cache")

    assert len(summary.outcomes) == 1
    assert summary.of("not a string-comparison void")
    assert not summary.of("still fabricated")
    assert not summary.of("was really on the page")


def test_summary_starts_empty():
    """`unreadable` is a list field on a dataclass, so a shared default would leak between runs."""
    assert Summary().unreadable == []
    assert Summary().outcomes == []
