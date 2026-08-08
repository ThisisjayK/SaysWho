"""The watcher's bookkeeping.

The pipeline is tested elsewhere. What is tested here is the automation around it, because an automated run
fails differently: nobody is watching a terminal, so a capture that is skipped, retried forever, or audited
twice concurrently would go unnoticed until a number came out wrong.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

from watch_captures import append_ledger, pending, read_ledger  # noqa: E402


def capture_file(directory: Path, name: str, sha: str = "") -> Path:
    path = directory / name
    path.write_text(json.dumps({"answer_sha256": sha or name}), encoding="utf-8")
    return path


def test_a_new_capture_is_pending(tmp_path):
    capture_file(tmp_path, "capture-chatgpt-1.json")
    assert [p.name for p in pending(tmp_path, {})] == ["capture-chatgpt-1.json"]


def test_an_audited_capture_is_not_audited_again(tmp_path):
    """Reports land in a different directory, but the ledger is what stops the loop."""
    capture_file(tmp_path, "capture-chatgpt-1.json")
    ledger = {"capture-chatgpt-1.json": {"status": "ok"}}
    assert pending(tmp_path, ledger) == []


def test_a_failed_capture_stays_pending(tmp_path):
    """A run that died on a rate limit is retried, not written off."""
    capture_file(tmp_path, "capture-chatgpt-1.json")
    ledger = {"capture-chatgpt-1.json": {"status": "failed", "detail": "quota"}}
    assert [p.name for p in pending(tmp_path, ledger)] == ["capture-chatgpt-1.json"]


def test_captures_are_audited_oldest_first(tmp_path):
    import os

    first = capture_file(tmp_path, "capture-a.json")
    second = capture_file(tmp_path, "capture-b.json")
    os.utime(first, (1, 1))
    os.utime(second, (2, 2))
    assert [p.name for p in pending(tmp_path, {})] == ["capture-a.json", "capture-b.json"]


def test_only_capture_files_are_picked_up(tmp_path):
    """The reports directory is separate, but stray files in the watched directory must not be audited."""
    capture_file(tmp_path, "capture-chatgpt-1.json")
    capture_file(tmp_path, "split.json")
    capture_file(tmp_path, "report.json")
    assert [p.name for p in pending(tmp_path, {})] == ["capture-chatgpt-1.json"]


def test_a_missing_captures_directory_is_not_an_error(tmp_path):
    assert pending(tmp_path / "nope", {}) == []


def test_the_ledger_round_trips(tmp_path):
    path = tmp_path / "audited.jsonl"
    append_ledger(path, {"capture": "capture-a.json", "status": "ok"})
    append_ledger(path, {"capture": "capture-b.json", "status": "failed"})

    ledger = read_ledger(path)
    assert ledger["capture-a.json"]["status"] == "ok"
    assert ledger["capture-b.json"]["status"] == "failed"


def test_a_corrupt_ledger_line_costs_a_reaudit_rather_than_the_run(tmp_path):
    """Failing closed on a malformed log file would stop auditing over bookkeeping."""
    path = tmp_path / "audited.jsonl"
    path.write_text('{"capture": "a.json", "status": "ok"}\nnot json at all\n', encoding="utf-8")

    ledger = read_ledger(path)
    assert ledger["a.json"]["status"] == "ok"
    assert len(ledger) == 1


def test_a_missing_ledger_reads_as_empty(tmp_path):
    assert read_ledger(tmp_path / "nothing.jsonl") == {}


def test_the_latest_entry_for_a_capture_wins(tmp_path):
    """A retry that succeeds must clear a previous failure."""
    path = tmp_path / "audited.jsonl"
    append_ledger(path, {"capture": "capture-a.json", "status": "failed"})
    append_ledger(path, {"capture": "capture-a.json", "status": "ok"})

    assert read_ledger(path)["capture-a.json"]["status"] == "ok"


def test_a_second_run_exits_rather_than_queueing(tmp_path):
    """Two pipelines against one rate-limited free tier would back off against each other."""
    from watch_captures import main

    reports = tmp_path / "reports"
    reports.mkdir()
    (reports / ".lock").write_text("999 held", encoding="utf-8")
    capture_file(tmp_path, "capture-chatgpt-1.json")

    assert main(["--captures", str(tmp_path), "--reports", str(reports)]) == 0
    assert not (reports / "audited.jsonl").exists(), "the held lock must stop it before it audits anything"


def test_the_lock_is_released_when_there_is_nothing_to_do(tmp_path):
    from watch_captures import main

    reports = tmp_path / "reports"
    assert main(["--captures", str(tmp_path), "--reports", str(reports)]) == 0
    assert not (reports / ".lock").exists(), "a stale lock would block every future run"


# ------------------------------------------------- what the first live firing taught, one test each


def test_a_capture_that_keeps_failing_is_eventually_left_alone(tmp_path):
    """One wrong path replayed a backlog of eighteen failures on every launchd firing, twice over.

    A retry that cannot succeed is a loop, not persistence.
    """
    capture_file(tmp_path, "capture-a.json")
    ledger = {"capture-a.json": {"status": "failed", "attempts": 3}}
    assert pending(tmp_path, ledger, max_attempts=3) == []


def test_a_capture_below_the_attempt_cap_is_still_retried(tmp_path):
    """A run that died on a rate limit deserves another go."""
    capture_file(tmp_path, "capture-a.json")
    ledger = {"capture-a.json": {"status": "failed", "attempts": 1}}
    assert [p.name for p in pending(tmp_path, ledger, max_attempts=3)] == ["capture-a.json"]


def test_a_second_capture_of_an_audited_answer_is_skipped(tmp_path):
    """Twenty captures in the folder were four distinct answers.

    Capturing the same page repeatedly while fixing selectors is normal, and the audit is a function of the
    answer, so re-auditing identical text spends ten minutes of quota to learn nothing.
    """
    capture_file(tmp_path, "capture-first.json", sha="abc123")
    capture_file(tmp_path, "capture-second.json", sha="abc123")
    ledger = {"capture-first.json": {"status": "ok", "answer_sha256": "abc123"}}

    assert pending(tmp_path, ledger) == []


def test_two_unaudited_captures_of_one_answer_produce_one_audit(tmp_path):
    import os

    a = capture_file(tmp_path, "capture-a.json", sha="same")
    b = capture_file(tmp_path, "capture-b.json", sha="same")
    os.utime(a, (1, 1))
    os.utime(b, (2, 2))

    assert [p.name for p in pending(tmp_path, {})] == ["capture-a.json"]


def test_a_different_answer_is_still_audited(tmp_path):
    capture_file(tmp_path, "capture-first.json", sha="abc123")
    capture_file(tmp_path, "capture-other.json", sha="def456")
    ledger = {"capture-first.json": {"status": "ok", "answer_sha256": "abc123"}}

    assert [p.name for p in pending(tmp_path, ledger)] == ["capture-other.json"]


def test_a_capture_that_cannot_be_read_is_not_treated_as_a_duplicate(tmp_path):
    """An unreadable file has no hash, and an empty hash must not match another empty one."""
    (tmp_path / "capture-bad.json").write_text("{ not json", encoding="utf-8")
    (tmp_path / "capture-worse.json").write_text("also not json", encoding="utf-8")

    assert len(pending(tmp_path, {})) == 2


def test_a_stale_lock_is_broken_rather_than_blocking_forever(tmp_path):
    """A process killed mid-run would otherwise leave the automation dead with no sign of it."""
    import os
    import time

    from watch_captures import main

    reports = tmp_path / "reports"
    reports.mkdir()
    lock = reports / ".lock"
    lock.write_text("999 old", encoding="utf-8")
    os.utime(lock, (time.time() - 10 * 3600,) * 2)

    assert main(["--captures", str(tmp_path), "--reports", str(reports)]) == 0
    assert not lock.exists(), "the stale lock should have been broken and then released"


def test_the_ledger_never_claims_a_report_that_was_not_written(tmp_path, monkeypatch):
    """Seen live: a capture whose only source returned 403 has no auditable claims, so Phase 1 never runs
    and no report is written. The ledger recorded outcome "report" and a path to a file that did not exist.

    A log asserting an artifact it never saw is the failure this project audits other people for, in the one
    place nobody looks because it is automated.
    """
    import watch_captures

    capture = capture_file(tmp_path, "capture-a.json")
    reports = tmp_path / "reports"
    monkeypatch.setattr(watch_captures, "cli_main", None, raising=False)
    monkeypatch.setattr("sayswho.cli.main", lambda argv: 0)

    entry = watch_captures.audit(capture, reports)

    assert entry["outcome"] == "no report"
    assert "report" not in entry, "no path may be recorded when no file was written"
    assert "no source could be read" in entry["detail"]


def test_the_ledger_records_what_the_report_found(tmp_path):
    """The notification and the log are the only signal a background run gives."""
    path = tmp_path / "audited.jsonl"
    append_ledger(path, {"capture": "c.json", "status": "ok", "counts": {"SUPPORTED": 5}})
    assert json.loads(path.read_text().strip())["counts"]["SUPPORTED"] == 5
