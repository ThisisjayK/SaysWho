#!/usr/bin/env python3
"""Split one capture N times and report how much the split moves.

    split_spread.py <capture.json> [--runs 5]

`FINDINGS.md` item 8: Phase 1 is not deterministic. The same capture returned 139, 119 and 156 skipped
lines across three runs, and the claim count moved too. `skipped_count` and `claim_count` are therefore
properties of one splitting run rather than of the answer, and `SCOPE.md` §3 publishes both.

This exists so the number that reaches the writeup carries an n instead of being whichever run was last.
It is Phase 1 only: no fetching, no judging, one model call per run.

Cheap by design. On the free-tier Gemini judge a five-run spread costs nothing and takes about a minute.
"""

from __future__ import annotations

import argparse
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sayswho.claims import split_claims  # noqa: E402
from sayswho.gemini import build_judge  # noqa: E402
from sayswho.model import Meter  # noqa: E402
from sayswho.records import Capture  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("capture", type=Path)
    parser.add_argument("--runs", type=int, default=5)
    parser.add_argument("--judge-provider", choices=["gemini", "anthropic"], default=None)
    args = parser.parse_args(argv)

    capture = Capture.from_json(args.capture)
    meter = Meter(budget_tokens=2_000_000)
    client = build_judge(args.judge_provider, meter=meter)

    print(f"capture   {args.capture.name}")
    print(f"answer    sha256 {capture.answer_sha256[:16]}  {len(capture.answer_text)} chars")
    print(f"judge     {type(client).__name__}  model={client.model}")
    print(f"runs      {args.runs}, Phase 1 only")
    print()

    claims: list[int] = []
    skipped: list[int] = []
    uncited: list[int] = []

    for i in range(1, args.runs + 1):
        result = split_claims(capture, client)
        claims.append(len(result.claims))
        skipped.append(len(result.skipped))
        uncited.append(result.uncited_count)
        print(f"  run {i}   claims {claims[-1]:>3}   skipped {skipped[-1]:>4}   uncited {uncited[-1]:>3}")

    print()
    for name, series in (("claims", claims), ("skipped", skipped), ("uncited", uncited)):
        spread = max(series) - min(series)
        # A single run is a point estimate with no spread to report, and stdev needs two.
        stdev = statistics.stdev(series) if len(series) > 1 else 0.0
        print(
            f"  {name:<8} min {min(series):>4}  max {max(series):>4}  spread {spread:>4}  "
            f"mean {statistics.mean(series):>7.1f}  stdev {stdev:>5.1f}"
        )

    print()
    print("These are one answer split N times by one judge at one prompt version. The spread is a property")
    print("of the splitter, not of the answer, and any published skip rate carries this n beside it.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
