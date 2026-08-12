#!/usr/bin/env python3
"""The ethics gate, run and shown passing.

    python3 tools/ethics_gate.py
    python3 tools/ethics_gate.py --json
    python3 tools/ethics_gate.py --no-suite      # privacy only, for a quick pre-commit check

Privacy and honesty, per `SCOPE.md` §8 and the capstone attestation row. Exits non-zero when either half
fails, so it can gate a run rather than describe one. The checks live in `sayswho/ethics.py`; this file
prints them and sets the exit code.

The output of this command is the artefact. A paragraph saying the contract holds is not evidence that it
does, which is the argument this whole project is built on, turned back on itself.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sayswho.ethics import run  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument("--json", action="store_true", help="emit the report as JSON")
    parser.add_argument(
        "--no-suite",
        action="store_true",
        help="skip the honesty tests. The report says so rather than reporting a pass it did not earn",
    )
    args = parser.parse_args(argv)

    report = run(args.repo, run_suite=not args.no_suite)

    if args.json:
        print(json.dumps(report.to_dict(), indent=2))
    else:
        print(report.render())

    return 0 if report.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
