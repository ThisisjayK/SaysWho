"""The ethics gate, tested by breaking it.

`SCOPE.md` §3: a gate with no failure path is decoration. So each check here is forced to fail against a
throwaway repository built for the purpose, rather than asserted to exist. The privacy half is the part worth
testing hardest, because its failure is irreversible: a key or a transcript that reaches a public remote
cannot be recalled by fixing the check afterwards.

The honesty half shells out to pytest, so these tests pass `run_suite=False` and the report says out loud
that it did not check rather than reporting a pass it did not earn.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sayswho.ethics import (  # noqa: E402
    PRIVATE_DIRS,
    PRIVATE_FILES,
    REVIEWED_EXCEPTIONS,
    honesty_checks,
    privacy_checks,
    run,
)

REPO = Path(__file__).resolve().parent.parent


def git(repo: Path, *args: str):
    return subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True)


@pytest.fixture
def clean_repo(tmp_path):
    """A repository with the same ignore rules as this one and nothing private in it."""
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "-q")
    git(repo, "config", "user.email", "t@example.org")
    git(repo, "config", "user.name", "t")

    rules = "\n".join([f"{d}/" for d in PRIVATE_DIRS] + list(PRIVATE_FILES) + ["*.key", ".env"])
    (repo / ".gitignore").write_text(rules + "\n")
    (repo / "README.md").write_text("# fine\n")
    git(repo, "add", ".gitignore", "README.md")
    git(repo, "commit", "-qm", "init")
    return repo


def by_name(checks, fragment):
    return next(c for c in checks if fragment in c.name)


# ---------------------------------------------------------------- the gate passes when it should


def test_a_clean_repo_passes_every_privacy_check(clean_repo):
    checks, skipped = privacy_checks(clean_repo)
    assert not skipped
    assert all(c.passed for c in checks), [c for c in checks if not c.passed]


def test_this_repository_passes_the_privacy_half(clean_repo):
    """The one that matters. Run against the real repo, which is about to be pushed to a public remote."""
    checks, skipped = privacy_checks(REPO)
    assert not skipped
    failed = [f"{c.name}: {c.detail}" for c in checks if not c.passed]
    assert not failed, failed


# ---------------------------------------------------------------- and fails when it should


def test_a_force_added_capture_is_caught(clean_repo):
    """The realistic leak: `git add -f` on something the ignore rules cover, because it was needed once."""
    (clean_repo / "captures").mkdir()
    (clean_repo / "captures" / "capture-chatgpt-1.json").write_text('{"answer": "private"}')
    git(clean_repo, "add", "-f", "captures/capture-chatgpt-1.json")

    check = by_name(privacy_checks(clean_repo)[0], "staged")
    assert not check.passed
    assert "capture-chatgpt-1.json" in check.detail
    assert "git restore --staged" in check.remedy


def test_correspondence_staged_for_commit_is_caught(clean_repo):
    (clean_repo / "email-to-professor.md").write_text("Dear Professor")
    git(clean_repo, "add", "-f", "email-to-professor.md")

    assert not by_name(privacy_checks(clean_repo)[0], "staged").passed


def test_a_private_file_already_tracked_is_caught(clean_repo):
    """Ignoring a directory does not untrack what is already in it, so the staged check alone has a hole."""
    (clean_repo / "goldset").mkdir()
    (clean_repo / "goldset" / "day5.gold.json").write_text('{"labels": []}')
    git(clean_repo, "add", "-f", "goldset/day5.gold.json")
    git(clean_repo, "commit", "-qm", "oops")

    check = by_name(privacy_checks(clean_repo)[0], "tracked")
    assert not check.passed
    assert "goldset/day5.gold.json" in check.detail
    assert "git rm --cached" in check.remedy


def test_a_reviewed_exception_does_not_fail_the_gate(clean_repo):
    """One file is committed on purpose. An exception with a reason beside it can be argued with; a check
    quietly relaxed to pass cannot."""
    name = next(iter(REVIEWED_EXCEPTIONS))
    path = clean_repo / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("[]")
    git(clean_repo, "add", "-f", name)
    git(clean_repo, "commit", "-qm", "reviewed")

    check = by_name(privacy_checks(clean_repo)[0], "tracked")
    assert check.passed
    assert name in check.detail, "a reviewed exception is named in the output, not silently skipped"


def test_an_ignore_rule_that_does_not_match_is_caught(clean_repo):
    """The failure this check exists for: a rule that was written and does not work. Nothing is leaked yet,
    which is exactly when it is cheap to fix."""
    (clean_repo / ".gitignore").write_text("captures\n")  # no trailing slash, and the rest gone
    git(clean_repo, "add", ".gitignore")
    git(clean_repo, "commit", "-qm", "weaken")

    check = by_name(privacy_checks(clean_repo)[0], "actually ignored")
    assert not check.passed
    assert "goldset/" in check.detail and "runs/" in check.detail
    assert ".gitignore" in check.remedy


def test_a_key_in_a_tracked_file_is_caught(clean_repo):
    """DATA_CONTRACT.md §8: the key is read from the environment and never written to disk."""
    leaked = "AI" + "za" + "S" * 34
    (clean_repo / "config.py").write_text(f'GEMINI_API_KEY = "{leaked}"\n')
    git(clean_repo, "add", "config.py")
    git(clean_repo, "commit", "-qm", "leak")

    check = by_name(privacy_checks(clean_repo)[0], "API key")
    assert not check.passed
    assert "config.py" in check.detail
    assert "rotate the key" in check.remedy


def test_the_scanner_does_not_report_its_own_patterns(clean_repo):
    """The patterns are built by concatenation so the literals never appear in the source. Written as one
    string each, the scanner finds itself and the gate can never pass."""
    source = (REPO / "sayswho" / "ethics.py").read_text()
    for _, pattern in __import__("sayswho.ethics", fromlist=["KEY_PATTERNS"]).KEY_PATTERNS:
        assert not pattern.search(source), "the key scanner matches its own source"


# ---------------------------------------------------------------- what it does when it cannot check


def test_a_directory_that_is_not_a_repository_reports_not_checked(tmp_path):
    """"We did not check" is not "we checked and it was fine", and the report keeps them apart."""
    checks, skipped = privacy_checks(tmp_path)
    assert checks == []
    assert skipped and "not a git repository" in skipped[0]


def test_skipping_the_suite_is_reported_rather_than_passed():
    checks, skipped = honesty_checks(REPO, run_suite=False)
    assert checks == []
    assert skipped and "says nothing" in skipped[0]


def test_a_report_with_no_honesty_checks_still_renders_its_refusal(tmp_path):
    report = run(tmp_path, run_suite=False)
    text = report.render()
    assert "not checked" in text
    assert "ETHICS GATE" in text


# ---------------------------------------------------------------- the failing gate says the run stops


def test_a_failing_gate_says_the_run_does_not_happen(clean_repo):
    (clean_repo / "captures").mkdir()
    (clean_repo / "captures" / "c.json").write_text("{}")
    git(clean_repo, "add", "-f", "captures/c.json")

    report = run(clean_repo, run_suite=False)
    assert not report.passed
    assert "GATE FAILED. The run does not happen." in report.render()


def test_the_cli_exits_non_zero_when_the_gate_fails(clean_repo, capsys):
    sys.path.insert(0, str(REPO / "tools"))
    import ethics_gate

    (clean_repo / ".env").write_text("GEMINI_API_KEY=x")
    git(clean_repo, "add", "-f", ".env")

    assert ethics_gate.main(["--repo", str(clean_repo), "--no-suite"]) == 1
    assert "FAIL" in capsys.readouterr().out


def test_the_cli_exits_zero_on_this_repository(capsys):
    sys.path.insert(0, str(REPO / "tools"))
    import ethics_gate

    assert ethics_gate.main(["--repo", str(REPO), "--no-suite"]) == 0
    assert "GATE PASSED" in capsys.readouterr().out


def test_an_interpreter_without_pytest_says_so_rather_than_blaming_a_document(monkeypatch):
    """The failure this prevents is a wrong diagnosis, not a missed one.

    Every document naming this gate used to say `python3 tools/ethics_gate.py`, and on a machine where that
    resolves to an interpreter without pytest, both honesty runs returned 1 with an empty stdout. The gate
    rendered that as `no output` under the remedy "a document is claiming something untrue about this code",
    which is a sentence that sends somebody hunting a prose bug that does not exist. The gate should still
    fail, because honesty really was not checked, and it should name the interpreter.
    """
    def no_pytest(cmd, *args, **kwargs):
        if cmd[1:] == ["-c", "import pytest"]:
            return subprocess.CompletedProcess(cmd, 1, "", "No module named pytest")
        raise AssertionError("the gate ran an honesty test after the probe said pytest was missing")

    monkeypatch.setattr("sayswho.ethics.subprocess.run", no_pytest)
    checks, _skipped = honesty_checks(REPO)

    assert len(checks) == 1, "one accurate check, not two misleading ones"
    assert not checks[0].passed, "honesty was not checked, so it must not report a pass"
    assert "pytest" in checks[0].name
    assert ".venv/bin/python" in checks[0].remedy, "the remedy has to name the interpreter that works"
