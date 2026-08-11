#!/usr/bin/env python3
"""Measure how much of an answer's named-but-unlinked citations the patterns actually find.

    python3 tools/measure_named_recall.py --capture captures/PR-01.json --marked marked/PR-01.txt
    python3 tools/measure_named_recall.py --capture captures/PR-01.json --template marked/PR-01.txt

`TODO.md`: "the current count is a floor and the writeup has to keep saying so until that is measured".
This is the measurement. It cannot be done without a person reading an answer and writing down every source
it names, so the marking is human work and this is the one command that follows it.

**The marked file.** One named source per line, copied from the answer exactly as it appears there. Blank
lines and lines starting with `#` are ignored, so `--template` can hand back a starting point with what the
patterns already found in it, and the reader's job becomes adding the ones that are missing rather than
transcribing from scratch.

That convenience has a cost and it is worth stating: a reader given the tool's answers first will anchor on
them. If the recall figure matters, mark the answer from a blank file. `--template` exists for the case
where the alternative is not marking it at all.

**What the numbers mean.** Recall is what the writeup needs, since the published claim is "this count is a
floor". Precision is reported too, because a pattern that matched prose would inflate a published number,
which is the failure this module was designed to avoid rather than the one it was designed to measure.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sayswho.named_citations import find_named_citations  # noqa: E402
from sayswho.rates import wilson_interval  # noqa: E402
from sayswho.records import Capture  # noqa: E402


def normalise(line: str) -> str:
    return " ".join(line.split()).strip().casefold().rstrip(".,;")


def read_marked(path: Path) -> list[str]:
    lines = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        lines.append(raw)
    return lines


#: The parts of a citation that identify it: surnames, journal words, years, identifiers. Case is kept out
#: of it, and short words are dropped, because "et al" and "in" identify nothing.
_SIGNATURE = re.compile(r"\b(?:[A-Za-z][A-Za-z'’\-]{3,}|(?:19|20)\d{2}|\d{6,}|10\.\d{4,9}/\S+)\b")
_IGNORE = frozenset({"et", "al", "the", "and", "study", "paper", "trial", "report", "review", "analysis"})


def signature(text: str) -> frozenset[str]:
    return frozenset(
        t.casefold() for t in _SIGNATURE.findall(text) if t.casefold() not in _IGNORE
    )


def overlaps(a: str, b: str) -> bool:
    """Whether two written forms are the same citation.

    Deliberately loose, and not by substring. A person writes "LeClair et al. 2022" where the pattern
    matched "LeClair et al., Supportive Care in Cancer, 2022": neither contains the other, and calling them
    two different citations would measure typing conventions rather than recall.

    So one is the same citation as the other when its identifying tokens are a subset of the other's. That
    matches a short hand-written form against a long matched one in either direction, and does not match two
    different papers, whose surnames and years differ.
    """
    x, y = signature(a), signature(b)
    if not x or not y:
        return bool(normalise(a)) and normalise(a) == normalise(b)
    return x <= y or y <= x


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--capture", type=Path, required=True)
    parser.add_argument("--marked", type=Path, help="a file of hand-marked named citations, one per line")
    parser.add_argument("--template", type=Path, help="write a starting file and exit, marking nothing")
    args = parser.parse_args(argv)

    capture = Capture.from_json(args.capture)
    found = find_named_citations(capture.answer_text)

    if args.template:
        args.template.parent.mkdir(parents=True, exist_ok=True)
        args.template.write_text(
            "# Every source this answer names without linking, one per line, copied as it appears.\n"
            "# Lines below were found by the patterns. Add what they missed; delete what is not a citation.\n"
            "#\n"
            "# Reading these first will anchor you. If the recall figure matters, start from a blank file.\n"
            "#\n"
            f"# capture: {args.capture}\n"
            f"# answer_sha256: {capture.answer_sha256}\n\n"
            + "\n".join(c.text for c in found)
            + "\n",
            encoding="utf-8",
        )
        print(f"wrote {args.template} with {len(found)} pattern match(es) in it. Nothing was measured.")
        return 0

    if not args.marked:
        parser.error("pass --marked with a hand-marked file, or --template to start one")

    marked = read_marked(args.marked)
    if not marked:
        print("the marked file has no entries. Nothing to measure against.", file=sys.stderr)
        return 2

    hits = [m for m in marked if any(overlaps(m, c.text) for c in found)]
    misses = [m for m in marked if m not in hits]
    spurious = [c for c in found if not any(overlaps(m, c.text) for m in marked)]

    recall = len(hits) / len(marked)
    precision = (len(found) - len(spurious)) / len(found) if found else None

    r_lo, r_hi = wilson_interval(len(hits), len(marked))
    print(f"capture      {args.capture}")
    print(f"answer sha   {capture.answer_sha256[:16]}")
    print(f"marked       {len(marked)} named citation(s) by hand")
    print(f"found        {len(found)} by pattern")
    print()
    print(f"recall       {len(hits)} of {len(marked)} ({recall:.1%}, 95% CI {r_lo:.1%} to {r_hi:.1%})")
    if precision is not None:
        p_lo, p_hi = wilson_interval(len(found) - len(spurious), len(found))
        print(
            f"precision    {len(found) - len(spurious)} of {len(found)} "
            f"({precision:.1%}, 95% CI {p_lo:.1%} to {p_hi:.1%})"
        )
    print()

    if misses:
        print(f"missed by the patterns ({len(misses)}):")
        for m in misses:
            print(f"  {' '.join(m.split())}")
        print()
    if spurious:
        print(f"matched by a pattern and not marked by hand ({len(spurious)}):")
        for c in spurious:
            print(f"  [{c.kind}] {c.text}")
        print()

    print(
        "One answer, so this is a measurement of these patterns against this text and not a property of\n"
        "the patterns. The writeup reports it with its n, and keeps calling the count a floor."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
