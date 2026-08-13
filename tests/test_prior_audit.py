"""Tests for the prior-audit scan.

The failure this closes is the quietest one in the gold set workflow: an answer that was audited last week,
labelled today as blind, producing a kappa that looks exactly like a real one. So these tests are mostly
about the two ways the scan could be wrong in that direction, and one way it must not be wrong in the other.

- It has to find a verdict wherever it is written: a report's JSON, the same report's HTML, a harness run
  record, a subdirectory.
- It must not flag a file that names the answer and holds no verdict, because a stored split does exactly
  that and refusing those would make blind labelling impossible rather than merely honest.
- It must never carry a verdict out of the files it opens. It is the one thing here that reads them, and it
  reads them on behalf of a person who must not see them.
"""

from __future__ import annotations

import json

from sayswho.judge import CONTRADICTED, NOT_FOUND_IN_SOURCE, PARTIALLY_SUPPORTED, SUPPORTED
from sayswho.prior_audit import VERDICT_KEYS, carries_verdict, scan

ANSWER = "3f" * 32
OTHER = "ab" * 32


def report(path, answer=ANSWER, verdict=SUPPORTED, judged=True):
    """A report payload shaped like the one `sayswho/report.py` writes, cut down to what the scan reads."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({
        "generated_by": "SaysWho",
        "meta": {"product": "chatgpt", "answer_sha256": answer, "split_sha256": "c" * 64},
        "claims": [{
            "id": "claim-1",
            "state": "SUPPORTED" if verdict else "COULD_NOT_VERIFY",
            "sources": [{"url": "https://example.org/1", "verdict": verdict, "span": "on the page",
                         "voided": False, "void_reason": "", "judged": judged}],
        }],
        "judged": judged,
    }))
    return path


# ---------------------------------------------------------------- finding one


def test_a_judged_report_over_the_same_answer_is_found(tmp_path):
    report(tmp_path / "reports" / "r.json")
    result = scan([ANSWER], roots=[tmp_path / "reports"])
    assert result.found
    assert result.audits[0].answer_sha256 == ANSWER
    assert result.audits[0].path.name == "r.json"


def test_a_report_over_a_different_answer_is_not_found(tmp_path):
    """The scan matches on the answer hash, so an afternoon of unrelated audits does not block labelling."""
    report(tmp_path / "reports" / "r.json", answer=OTHER)
    result = scan([ANSWER], roots=[tmp_path / "reports"])
    assert not result.found
    assert result.files_read == 1, "the file still has to have been read for that to mean anything"


def test_an_unjudged_report_names_the_answer_and_does_not_count(tmp_path):
    """A report written without --judge carries `"verdict": ""` on every row. Presence of the key proves
    nothing here: there is no verdict in it for a labeller to be anchored by."""
    report(tmp_path / "reports" / "r.json", verdict="", judged=False)
    assert not scan([ANSWER], roots=[tmp_path / "reports"]).found


def test_a_stored_split_names_the_answer_and_does_not_count(tmp_path):
    """The file the labeller is about to label against names the same answer. Flagging it would refuse every
    session, which is the failure mode that gets a guard deleted rather than fixed."""
    (tmp_path / "runs").mkdir()
    (tmp_path / "runs" / "s.json").write_text(json.dumps({
        "answer_sha256": ANSWER, "split_sha256": "d" * 64,
        "claims": [{"id": "c1", "text": "A claim.", "markers": ["[1]"], "urls": ["https://example.org/1"]}],
    }))
    assert not scan([ANSWER], roots=[tmp_path / "runs"]).found


def test_a_harness_run_record_is_found_through_its_nested_judgements(tmp_path):
    """Two shapes hold verdicts and neither is the report: the harness nests judgements under each run item,
    and the break-attempt runner writes its own. A scan that knew one shape would pass on the other."""
    (tmp_path / "runs").mkdir()
    (tmp_path / "runs" / "record.json").write_text(json.dumps({
        "runs": [{"answer_sha256": ANSWER, "judgements": [
            {"claim_id": "c1", "url": "https://example.org/1", "verdict": NOT_FOUND_IN_SOURCE},
        ]}],
    }))
    result = scan([ANSWER], roots=[tmp_path / "runs"])
    assert result.found
    assert result.audits[0].proof in VERDICT_KEYS


def test_the_html_report_counts_too(tmp_path):
    """`report.py` embeds the whole payload in a script tag, so the HTML holds the verdicts as surely as the
    JSON does. A scan that opened only JSON would pass cleanly over a directory full of them."""
    (tmp_path / "reports").mkdir()
    payload = {"meta": {"answer_sha256": ANSWER},
               "claims": [{"sources": [{"verdict": CONTRADICTED, "judged": True}]}]}
    (tmp_path / "reports" / "r.html").write_text(
        "<!doctype html><html><body><script>window.saysWhoRender(el, "
        + json.dumps(payload, separators=(",", ":"))
        + ");</script></body></html>"
    )
    assert scan([ANSWER], roots=[tmp_path / "reports"]).found


def test_subdirectories_are_searched(tmp_path):
    """`runs/break/results.json` and `runs/day7/record.json` are both one level down, and the day-7 run is
    the one whose verdicts would matter most."""
    report(tmp_path / "runs" / "day7" / "record.json")
    assert scan([ANSWER], roots=[tmp_path / "runs"]).found


def test_several_answers_are_checked_at_once(tmp_path):
    """A real gold set spans two or three answers, so the scan takes the set and reports which of them it
    found rather than answering yes or no about the batch."""
    report(tmp_path / "reports" / "a.json", answer=ANSWER)
    result = scan([ANSWER, OTHER], roots=[tmp_path / "reports"])
    assert result.answers_found == [ANSWER]
    assert len(result.answers) == 2


# ---------------------------------------------------------------- not checked is not clean


def test_a_missing_directory_reports_not_checked_rather_than_clean(tmp_path):
    """The same distinction as a missing Wayback snapshot making drift unknown rather than unchanged. A scan
    that looked nowhere has found nothing, and those are different sentences."""
    result = scan([ANSWER], roots=[tmp_path / "nope"])
    assert not result.checked
    assert not result.found
    assert "NOT CHECKED" in result.render()
    assert "not checked" in result.summary()


def test_an_absent_root_beside_a_present_one_is_named(tmp_path):
    """Half a scan reports which half it was."""
    (tmp_path / "reports").mkdir()
    result = scan([ANSWER], roots=[tmp_path / "reports", tmp_path / "runs"])
    assert result.checked, "one readable root is a real check"
    assert result.roots_absent == [tmp_path / "runs"]
    assert "runs" in result.render()


def test_no_answer_to_look_for_is_not_a_pass(tmp_path):
    result = scan([], roots=[tmp_path])
    assert not result.checked
    assert "no answer" in result.render()


# ---------------------------------------------------------------- it never shows a verdict


def test_the_scan_never_carries_a_verdict_out_of_the_files_it_opens(tmp_path):
    """The point of the whole module. It opens files full of verdicts on behalf of somebody who must not see
    one, so neither its rendered output nor its record may contain a verdict name."""
    for n, verdict in enumerate((SUPPORTED, PARTIALLY_SUPPORTED, NOT_FOUND_IN_SOURCE, CONTRADICTED)):
        report(tmp_path / "reports" / f"r{n}.json", verdict=verdict)

    result = scan([ANSWER], roots=[tmp_path / "reports"])
    assert len(result.audits) == 4

    surfaces = [result.render(), result.summary(), json.dumps(result.to_dict())]
    for surface in surfaces:
        for verdict in (SUPPORTED, PARTIALLY_SUPPORTED, NOT_FOUND_IN_SOURCE, CONTRADICTED):
            assert verdict not in surface, f"a verdict reached the labeller through {surface[:40]!r}"
    # The key name is reported, because "which field proved it" is what makes the refusal arguable.
    assert "verdict" in surfaces[0] or "judged" in surfaces[0]


def test_the_render_shows_a_bounded_number_of_files(tmp_path):
    """119 audits on disk is a real number in this repo. A refusal that prints all of them buries its own
    instructions."""
    for n in range(20):
        report(tmp_path / "reports" / f"r{n}.json")
    printed = scan([ANSWER], roots=[tmp_path / "reports"]).render(show=5)
    assert printed.count("r") > 0
    assert "and 15 more" in printed


# ---------------------------------------------------------------- the verdict test itself


def test_carries_verdict_reads_a_truthy_value_not_a_present_key():
    assert carries_verdict(json.dumps({"verdict": ""}).encode()) == ""
    assert carries_verdict(json.dumps({"judgements": []}).encode()) == ""
    assert carries_verdict(json.dumps({"judged": False}).encode()) == ""
    assert carries_verdict(json.dumps({"verdict": SUPPORTED}).encode()) == "verdict"
    assert carries_verdict(json.dumps({"judged": True}).encode()) == "judged"
    assert carries_verdict(json.dumps({"a": [{"b": {"void_reason": "X"}}]}).encode()) == "void_reason"


def test_carries_verdict_on_bytes_that_are_not_json():
    assert carries_verdict(b"<html>nothing here</html>") == ""
    assert carries_verdict(b'<script>{"judged":true}</script>') == "judged"
    assert carries_verdict(b'<script>{"verdict":""}</script>') == ""
