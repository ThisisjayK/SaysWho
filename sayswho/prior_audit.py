"""Has this answer been audited before? The check that makes a blind label blind.

`TODO.md` day 5, and the third fault in this workflow found by walking it rather than by the suite. Two
guards already stand between a gold set and the judge's answers, and neither of them sees this case.

`goldset.agreement` compares every blind label's timestamp against the run it is being compared with, so it
catches labelling after *that* run and says nothing about an earlier one: labels written today pass against a
run made tomorrow. Gate G4 ties a gold set to a `split_sha256`, and Phase 1 does not return the same split
twice, so a second audit of the same answer carries a different split hash and G4 reads it as a different
object rather than as the same answer judged before.

So an answer judged last week leaves a report on disk, a labeller opens a fresh split of that same answer,
labels it blind, and nothing raises. Found on 2026-08-11, when every capture on disk turned out to have been
audited already. Until this module existed the only control was a sentence in a banner asking the labeller to
remember, which is the weakest control in the project: it fails silently, and it fails in the direction that
flatters the result.

**What this checks, and what it cannot.** It reads the artefacts on disk and answers one narrow question:
does a file here carry a verdict over one of the answers about to be labelled. It cannot know what a person
has seen. A verdict read on screen and never saved is invisible to it, and so is one in another checkout or
in a terminal scrollback. So this is a floor rather than a proof, and the banner asking the labeller to
remember stays next to it.

**It never carries a verdict out.** The scan opens files full of verdicts, which is the one thing
`tools/label_goldset.py` refuses to do, and having opened them it would be self-defeating to print them. A
`PriorAudit` records the path, the answer and the name of the key that proved the file holds judge output,
never a verdict value, and `tests/test_prior_audit.py` asserts that no verdict name survives into the
rendered output.

**It errs towards refusing.** A run record covering several answers is flagged for every answer it names
rather than only for the ones its verdicts belong to, because associating a nested verdict with the nearest
answer hash is guesswork about the shape of a file. The cost of a false refusal is labelling supplementally
and reporting those labels separately, which is a real cost and a visible one. The cost of a false pass is a
kappa that means nothing while looking exactly like one that does.

**Not a gate on any rate.** This is a pre-flight check on the labelling session, which is where the failure
happens. What guards the published agreement number is still the timestamp refusal in `goldset.agreement` and
G4's split binding. A scan result recorded in a gold set's note is provenance, not a hash, and it is not
treated as one.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

#: Keys whose *presence* means a file carries judge output, whatever their value.
#:
#: This is the rule `tools/label_goldset.py` refuses an input on, and presence is the right test there: the
#: mistake it catches is passing a run record where a capture was meant, which is a mistake about which file
#: this is rather than about what is in it.
JUDGE_KEYS = ("judgements", "verdict", "void_reason", "span_verified")

#: Keys whose *truthy* value means a file carries a verdict somebody could have read.
#:
#: A different rule for a different question, and the difference is load bearing. A report written without
#: `--judge` carries `"verdict": ""` for every row, so presence proves nothing here and only a value does.
#: `judged` earns its place because the report payload sets it per source row and it is the one key that is
#: true when a verdict exists and false when the same file was written without one.
VERDICT_KEYS = JUDGE_KEYS + ("judged",)

#: Where audits land, and the reason each one is here. `reports/` is what the local server writes for every
#: audit run from the in-page button, never overwritten. `runs/` is the harness's own output plus the break
#: attempts. Both are gitignored, so both are exactly the kind of directory that accumulates unnoticed.
DEFAULT_ROOTS = ("reports", "runs")

#: Suffixes worth opening. The standalone HTML report embeds its entire payload in a script tag, so it holds
#: verdicts as surely as the JSON beside it does, and a scan that read only JSON would pass cleanly over a
#: directory full of them.
SCANNED_SUFFIXES = (".json", ".html")

#: For files that are not loadable JSON, which is what an HTML report is. Compact JSON inside a script tag,
#: so no whitespace is expected and some is tolerated anyway.
_JUDGED_TRUE = re.compile(r'"judged"\s*:\s*true')
_NONEMPTY_VERDICT = re.compile(r'"verdict"\s*:\s*"[^"]')


@dataclass(frozen=True)
class PriorAudit:
    """One file that already holds a verdict over one of the answers about to be labelled.

    `proof` is the name of the key that established it, never the verdict. This record gets printed to the
    person who is about to label blind, and putting a verdict in front of them is the failure the whole
    module exists to prevent.
    """

    path: Path
    answer_sha256: str
    proof: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": str(self.path),
            "answer_sha256": self.answer_sha256,
            "proof_key": self.proof,
            "_note": "the key that proved this file holds judge output. Never the verdict itself.",
        }


@dataclass
class Scan:
    """What the scan looked at and what it found. Absence of a look is not absence of a finding."""

    answers: list[str]
    roots_read: list[Path] = field(default_factory=list)
    roots_absent: list[Path] = field(default_factory=list)
    files_read: int = 0
    audits: list[PriorAudit] = field(default_factory=list)

    @property
    def checked(self) -> bool:
        """Whether anything was actually looked at.

        Reported separately from the result, for the same reason the ethics gate reports not-checked rather
        than pass on a directory that is not a repository, and for the same reason a missing Wayback snapshot
        makes drift unknown rather than unchanged.
        """
        return bool(self.roots_read) and bool(self.answers)

    @property
    def found(self) -> bool:
        return bool(self.audits)

    @property
    def answers_found(self) -> list[str]:
        return sorted({a.answer_sha256 for a in self.audits})

    def to_dict(self) -> dict[str, Any]:
        return {
            "checked": self.checked,
            "answers": list(self.answers),
            "roots_read": [str(p) for p in self.roots_read],
            "roots_absent": [str(p) for p in self.roots_absent],
            "files_read": self.files_read,
            "prior_audits": [a.to_dict() for a in self.audits],
        }

    def summary(self) -> str:
        """One line, for a gold set's note. Provenance that the check ran, in the file it ran for."""
        where = ", ".join(f"{p}/" for p in self.roots_read) or "nowhere"
        if not self.answers:
            return "not run: no answer to look for"
        if not self.checked:
            absent = ", ".join(f"{p}/" for p in self.roots_absent)
            return f"not checked: {absent} absent, so no artefact was read"
        if not self.audits:
            return (
                f"{self.files_read} file(s) under {where} hold no verdict over "
                f"{len(self.answers)} answer(s)"
            )
        return (
            f"{len(self.audits)} file(s) under {where} already hold a verdict over "
            f"{len(self.answers_found)} of {len(self.answers)} answer(s)"
        )

    def render(self, show: int = 5) -> str:
        """The terminal form. Says what was read, not only what was found."""
        if not self.answers:
            return "prior audit  not run: no answer to look for"
        if not self.checked:
            absent = ", ".join(f"{p}/" for p in self.roots_absent) or "nothing"
            return (
                f"prior audit  NOT CHECKED. {absent} does not exist here, so nothing was read.\n"
                "             That is not the same as no prior audit existing. Pass --audit-scan DIR."
            )

        where = ", ".join(f"{p}/" for p in self.roots_read)
        if not self.audits:
            lines = [
                f"prior audit  none. {self.files_read} file(s) under {where} carry no verdict over "
                f"{len(self.answers)} answer(s)",
                "             A floor, not a proof: it sees files, not what anybody has read.",
            ]
            if self.roots_absent:
                lines.append(
                    "             not looked at: "
                    + ", ".join(f"{p}/" for p in self.roots_absent)
                    + " (absent)"
                )
            return "\n".join(lines)

        lines = [
            f"PRIOR AUDIT  {len(self.audits)} file(s) under {where} already hold a verdict over "
            f"{len(self.answers_found)} of these {len(self.answers)} answer(s):"
        ]
        for audit in self.audits[:show]:
            lines.append(f"               {audit.path}   [answer {audit.answer_sha256[:12]}, key {audit.proof!r}]")
        if len(self.audits) > show:
            lines.append(f"               and {len(self.audits) - show} more")
        lines.append("             No verdict from those files is shown here, deliberately.")
        return "\n".join(lines)


def _walk_for_verdict(node: Any) -> str:
    """The name of the first key that proves this payload holds a verdict, or an empty string.

    Depth first over the whole structure, because a verdict lives three levels down in a report payload and
    two in a harness run record, and a check that knew those shapes would pass on the next one.
    """
    if isinstance(node, dict):
        for key, value in node.items():
            if str(key) in VERDICT_KEYS and value:
                return str(key)
            if hit := _walk_for_verdict(value):
                return hit
    elif isinstance(node, list):
        for value in node:
            if hit := _walk_for_verdict(value):
                return hit
    return ""


def carries_verdict(blob: bytes) -> str:
    """Which key proves this file holds judge output, or an empty string if none does.

    Parsed when the bytes are JSON and pattern matched when they are not, which is the HTML report: the same
    payload, inside a script tag, with no top level JSON to load.
    """
    try:
        payload = json.loads(blob)
    except (json.JSONDecodeError, UnicodeDecodeError, ValueError):
        text = blob.decode("utf-8", errors="ignore")
        if _JUDGED_TRUE.search(text):
            return "judged"
        if _NONEMPTY_VERDICT.search(text):
            return "verdict"
        return ""
    return _walk_for_verdict(payload)


def scan(answers: Iterable[str], roots: Iterable[Path | str] | None = None) -> Scan:
    """Look for a file that already holds a verdict over any of these answers.

    `answers` are `answer_sha256` values, which is what a stored split records and what every report and run
    record carries. Matching on the hash rather than on a path means a report renamed, moved or copied is
    still found, and a re-captured answer with the same bytes is correctly treated as the same answer.
    """
    wanted = sorted({a for a in answers if a})
    root_paths = [Path(r) for r in (DEFAULT_ROOTS if roots is None else roots)]

    result = Scan(answers=wanted)
    if not wanted:
        result.roots_absent = [p for p in root_paths if not p.is_dir()]
        result.roots_read = [p for p in root_paths if p.is_dir()]
        return result

    needles = {a: a.encode("ascii", "ignore") for a in wanted}
    for root in root_paths:
        if not root.is_dir():
            result.roots_absent.append(root)
            continue
        result.roots_read.append(root)
        for path in sorted(root.rglob("*")):
            if path.suffix.lower() not in SCANNED_SUFFIXES or not path.is_file():
                continue
            try:
                blob = path.read_bytes()
            except OSError:
                # A file we cannot read is not a file we have cleared. Counted nowhere and reported by its
                # absence from files_read, which is the honest version of skipping it.
                continue
            result.files_read += 1
            # The cheap test first, on bytes: a 64 character hex digest either appears in the file or it does
            # not, and most files fail this without ever being parsed.
            present = [a for a in wanted if needles[a] in blob]
            if not present:
                continue
            proof = carries_verdict(blob)
            if not proof:
                # The answer is named here and no verdict is. A stored split and an unjudged report both land
                # here, and neither one can anchor a labeller.
                continue
            for answer in present:
                result.audits.append(PriorAudit(path=path, answer_sha256=answer, proof=proof))

    return result
