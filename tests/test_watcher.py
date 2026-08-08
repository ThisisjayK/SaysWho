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


def capture_file(directory: Path, name: str) -> Path:
    path = directory / name
    path.write_text("{}", encoding="utf-8")
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


def test_the_ledger_records_what_the_report_found(tmp_path):
    """The notification and the log are the only signal a background run gives."""
    path = tmp_path / "audited.jsonl"
    append_ledger(path, {"capture": "c.json", "status": "ok", "counts": {"SUPPORTED": 5}})
    assert json.loads(path.read_text().strip())["counts"]["SUPPORTED"] == 5
