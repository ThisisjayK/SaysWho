"""The ethics gate: privacy and honesty, checked rather than asserted.

`SCOPE.md` §8 and the capstone's attestation row both ask for the same thing, and they ask for it in the same
words: show the gate passing. Not a paragraph promising the contract holds, a command that fails when it does
not.

Two halves, and they fail for different reasons.

**Privacy** is about what leaves this machine. Captures carry answer text and the query behind it, stored
pages carry the sidebar of every other conversation, gold sets carry passages pasted out of cited pages, and
correspondence is correspondence. The rule is not "there is a `.gitignore` line", it is "the line works and
nothing got past it", which are different claims: a rule that exists and does not match is the failure this
half is built to catch.

**Honesty** is about what this repository says. It is the existing suite's honesty tests, run now rather than
cited: no confidence number on any surface, every path a document names exists, and the test count a document
publishes matches the suite. Running them is the point. A gate that reports on tests it did not run is the
thing the gate exists to prevent.

Every check names its failure path, because a gate without one is decoration.
"""

from __future__ import annotations

import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

#: Directories whose contents never get committed. Each carries either answer text, the query behind it, or
#: page content quoted out of a source. `DATA_CONTRACT.md` §9.
PRIVATE_DIRS = ("captures", "reports", "runs", "splits", "goldset", ".cache", "pages")

#: Individual files kept local. Correspondence stays local per `CLAUDE.md`.
PRIVATE_FILES = ("email-to-professor.md", "reply-to-professor.md")

#: Patterns for files that must never be tracked wherever they appear.
PRIVATE_GLOBS = ("sayswho-page-*.html", ".env", "*.key")

#: Committed on purpose, before `runs/` was ignored, and kept because `FINDINGS.md` item 14 cites it as the
#: evidence behind a withdrawn figure. Reviewed: it holds spans from public mammography-statistics pages
#: reached by a consumer-stratum query, and no professional-stratum content. An exception with a reason
#: beside it can be argued with. A check quietly relaxed to pass cannot.
REVIEWED_EXCEPTIONS = {
    "runs/span-reaudit.json": (
        "evidence for FINDINGS.md item 14. Public page spans from a consumer-stratum query, reviewed"
    ),
    # The day 9 run, committed 2026-08-16 so the figures quoted in STATUS.md and FINDINGS.md can be traced
    # to the record that produced them. Reviewed the same way as the entry above, and the finding is that
    # the rule this suspends does not describe this run: `runs/` protects the professional stratum's answer
    # text, and day 9 is the consumer stratum, which is synthetic. Nobody asked those ten questions.
    #
    # What it reproduces is ChatGPT's own sentences split into 71 claims, and single quoted passages from
    # cited public pages, which is exactly the list DATA_CONTRACT.md §9 publishes: verdicts, reason codes,
    # URLs and quoted spans, never a page at length. The maintainer's contact address appears in the
    # recorded User-Agent and is left alone, because editing a record of what was sent to a server would
    # make it stop being a record.
    "runs/day9/run.json": "the day 9 run record. Consumer stratum, synthetic queries, reviewed",
    "runs/day9/readout.txt": "the day 9 metric readout, the artefact two rubric rows name",
    "runs/day9/RUN_LOG.md": "the day 9 run log. Same review as run.json",
    "runs/day9/TRACE.md": "the day 9 per-number trace table, so a published figure can be checked",
}

#: Built by concatenation on purpose: written as one literal, each pattern would match this file and the
#: scanner would report itself.
KEY_PATTERNS = (
    ("Google/Gemini API key", re.compile("AI" + r"za[0-9A-Za-z_\-]{30,}")),
    ("Anthropic API key", re.compile("sk-" + r"ant-[0-9A-Za-z_\-]{30,}")),
    ("OpenAI API key", re.compile("sk-" + r"proj-[0-9A-Za-z_\-]{30,}")),
)

#: The suite's honesty tests. Run, not cited.
HONESTY_TESTS = ("tests/test_no_confidence_anywhere.py", "tests/test_documents.py")


@dataclass(frozen=True)
class Check:
    """One check, its result, and what to do when it fails."""

    name: str
    passed: bool
    detail: str = ""
    #: What a person does about it. Empty when the check passed.
    remedy: str = ""


@dataclass
class EthicsReport:
    privacy: list[Check]
    honesty: list[Check]
    #: True when a check could not run rather than failed. Reported separately: "we did not check" is not
    #: "we checked and it was fine", which is the distinction this whole project is organised around.
    skipped: list[str]

    @property
    def passed(self) -> bool:
        return all(c.passed for c in self.privacy + self.honesty)

    def to_dict(self) -> dict:
        return {
            "passed": self.passed,
            "privacy": [vars(c) for c in self.privacy],
            "honesty": [vars(c) for c in self.honesty],
            "skipped": list(self.skipped),
        }

    def render(self) -> str:
        lines = ["ETHICS GATE", ""]
        for title, checks in (("PRIVACY", self.privacy), ("HONESTY", self.honesty)):
            lines.append(title)
            for c in checks:
                lines.append(f"  {'PASS' if c.passed else 'FAIL'}  {c.name}")
                if c.detail:
                    lines.append(f"        {c.detail}")
                if not c.passed and c.remedy:
                    lines.append(f"        do: {c.remedy}")
            lines.append("")
        for note in self.skipped:
            lines.append(f"  not checked: {note}")
        if self.skipped:
            lines.append("")
        lines.append("GATE PASSED" if self.passed else "GATE FAILED. The run does not happen.")
        return "\n".join(lines)


def _git(repo: Path, *args: str) -> tuple[int, str]:
    try:
        proc = subprocess.run(
            ["git", *args], cwd=repo, capture_output=True, text=True, timeout=30,
        )
    except (OSError, subprocess.SubprocessError) as exc:  # pragma: no cover - environment dependent
        return 1, str(exc)
    return proc.returncode, proc.stdout


def _is_git_repo(repo: Path) -> bool:
    code, _ = _git(repo, "rev-parse", "--git-dir")
    return code == 0


def _private(path: str) -> bool:
    """Does this path live somewhere that never gets committed."""
    p = Path(path)
    if path in PRIVATE_FILES:
        return True
    if p.parts and p.parts[0] in PRIVATE_DIRS:
        return True
    return any(p.match(glob) for glob in PRIVATE_GLOBS)


def privacy_checks(repo: Path) -> tuple[list[Check], list[str]]:
    """What must not leave this machine, checked against git rather than against the .gitignore text."""
    checks: list[Check] = []
    skipped: list[str] = []

    if not _is_git_repo(repo):
        skipped.append("not a git repository, so nothing could be checked about what is staged or tracked")
        return checks, skipped

    # 1. Anything staged that the ignore rules cover got there by a deliberate `git add -f`.
    _, staged_out = _git(repo, "diff", "--cached", "--name-only")
    staged = [p for p in staged_out.splitlines() if p.strip()]
    offenders = [p for p in staged if _private(p) and p not in REVIEWED_EXCEPTIONS]
    checks.append(Check(
        "no private file staged for commit",
        not offenders,
        f"{len(staged)} file(s) staged" + (f"; private: {', '.join(offenders)}" if offenders else ""),
        "git restore --staged " + " ".join(offenders) if offenders else "",
    ))

    # 2. Anything already tracked from a private path. Ignoring a directory does not untrack what is in it,
    #    which is the failure mode that makes rule 3 insufficient on its own.
    _, tracked_out = _git(repo, "ls-files")
    tracked = [p for p in tracked_out.splitlines() if p.strip()]
    leaked = [p for p in tracked if _private(p) and p not in REVIEWED_EXCEPTIONS]
    reviewed = [p for p in tracked if p in REVIEWED_EXCEPTIONS]
    detail = f"{len(tracked)} tracked file(s)"
    if reviewed:
        detail += f"; {len(reviewed)} reviewed exception(s): {', '.join(reviewed)}"
    if leaked:
        detail += f"; unreviewed: {', '.join(leaked)}"
    checks.append(Check(
        "no private file tracked",
        not leaked,
        detail,
        "git rm --cached " + " ".join(leaked) if leaked else "",
    ))

    # 3. The rules work. A .gitignore line that exists and does not match is worth nothing, and this project
    #    has already shipped one rule that was written and one that was merely intended.
    not_ignored = []
    for name in PRIVATE_DIRS:
        code, _ = _git(repo, "check-ignore", "-q", f"{name}/probe.json")
        if code != 0:
            not_ignored.append(f"{name}/")
    for name in PRIVATE_FILES:
        code, _ = _git(repo, "check-ignore", "-q", name)
        if code != 0:
            not_ignored.append(name)
    checks.append(Check(
        "every private path is actually ignored",
        not not_ignored,
        f"{len(PRIVATE_DIRS) + len(PRIVATE_FILES)} rule(s) checked against git"
        + (f"; not ignored: {', '.join(not_ignored)}" if not_ignored else ""),
        f"add {', '.join(not_ignored)} to .gitignore with the reason" if not_ignored else "",
    ))

    # 4. Key-shaped strings in anything tracked. DATA_CONTRACT.md §8: the key is read from the environment
    #    and is never written to disk.
    hits = []
    for rel in tracked:
        f = repo / rel
        try:
            text = f.read_text(encoding="utf-8", errors="ignore")
        except (OSError, UnicodeDecodeError):
            continue
        for label, pattern in KEY_PATTERNS:
            if pattern.search(text):
                hits.append(f"{rel} ({label})")
    checks.append(Check(
        "no API key in any tracked file",
        not hits,
        f"{len(tracked)} tracked file(s) scanned for {len(KEY_PATTERNS)} key shapes"
        + (f"; found: {', '.join(hits)}" if hits else ""),
        "rotate the key immediately, then remove it from the file and from history" if hits else "",
    ))

    return checks, skipped


def honesty_checks(repo: Path, run_suite: bool = True) -> tuple[list[Check], list[str]]:
    """Whether what this repository says about itself is true, by running the tests that check it."""
    checks: list[Check] = []
    skipped: list[str] = []

    if not run_suite:
        skipped.append("the honesty tests were not run, so this half of the gate says nothing")
        return checks, skipped

    # Probe once, before running anything. `sys.executable` is the interpreter that launched this gate, and
    # if it has no pytest then every run below returns 1 with an empty stdout, which renders as "no output"
    # under a remedy telling somebody to go and find the document that is lying. There is no such document.
    # It is the wrong interpreter, and saying so is the difference between a two-second fix and an afternoon.
    # Every document naming this gate says to launch it with `.venv/bin/python` for exactly this reason.
    probe = subprocess.run([sys.executable, "-c", "import pytest"], capture_output=True, text=True)
    if probe.returncode != 0:
        checks.append(Check(
            "pytest is importable by this interpreter", False,
            f"{sys.executable} cannot import pytest, so neither honesty test ran",
            "launch the gate with the interpreter holding the dependencies: "
            "`.venv/bin/python tools/ethics_gate.py`",
        ))
        return checks, skipped

    for path in HONESTY_TESTS:
        if not (repo / path).exists():
            checks.append(Check(
                f"{path} present", False, "the file naming this check does not exist",
                "restore the test, or this half of the gate is decoration",
            ))
            continue
        # sys.executable, not "python3". The interpreter running this gate is the one with pytest and the
        # dependencies installed; the bare name resolves to whatever is first on PATH, which reported both
        # honesty checks as failures the first time this ran.
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", path, "-q", "--no-header", "-p", "no:cacheprovider"],
            cwd=repo, capture_output=True, text=True,
        )
        tail = [l for l in proc.stdout.strip().splitlines() if l.strip()]
        summary = tail[-1] if tail else "no output"
        checks.append(Check(
            f"{path}", proc.returncode == 0, summary,
            "read the failure; a document is claiming something untrue about this code" if proc.returncode else "",
        ))

    return checks, skipped


def run(repo: Path | str = ".", run_suite: bool = True) -> EthicsReport:
    repo = Path(repo).resolve()
    privacy, p_skipped = privacy_checks(repo)
    honesty, h_skipped = honesty_checks(repo, run_suite=run_suite)
    return EthicsReport(privacy=privacy, honesty=honesty, skipped=p_skipped + h_skipped)
