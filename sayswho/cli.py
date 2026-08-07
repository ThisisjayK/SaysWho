"""Phase 0 and Phase 2 over a capture file.

    python3 -m sayswho.cli fixtures/example-capture.json

Prints the capture's hash, the G0 result, and a G2 code for every cited URL. This is the day 2 deliverable
in `TODO.md`: an answer captured, hashed, and every cited URL fetched with a code attached.

There is deliberately no verdict here yet. Phase 1 and Phase 3 arrive on day 3, and until then this tool can
tell you whether a source is readable and nothing at all about whether it supports anything.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .cache import FetchCache
from .fetch import Fetcher, user_agent
from .gates import auditable_denominator, g0_has_citations
from .records import Capture


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("capture", type=Path, help="path to a capture JSON file")
    parser.add_argument("--cache", type=Path, default=Path(".cache/fetch"))
    parser.add_argument("--no-cache", action="store_true", help="refetch even if cached")
    parser.add_argument("--json", action="store_true", help="emit the run record as JSON")
    args = parser.parse_args(argv)

    capture = Capture.from_json(args.capture)

    print(f"capture      {args.capture}")
    print(f"query        {capture.query_id}  product={capture.product}  model={capture.model_id}")
    print(f"generated    {capture.generated_at}")
    print(f"answer sha   {capture.answer_sha256}")
    print(f"user-agent   {user_agent()}")
    print()

    gate0 = g0_has_citations(capture)
    if not gate0.passed:
        print(f"G0 FAILED    {gate0.code}: {gate0.detail}")
        print()
        print("This answer is uncitable. It is not scored, and it is not a zero percent answer.")
        return 1

    print(f"G0 passed    {len(capture.citations)} citations, {len(capture.cited_urls)} unique URLs")
    print()

    fetcher = Fetcher(FetchCache(args.cache))
    records = []
    for url in capture.cited_urls:
        record = fetcher.fetch(url, use_cache=not args.no_cache)
        records.append(record)
        detail = f"  ({record.detail})" if record.detail else ""
        status = record.http_status if record.http_status is not None else "  -"
        print(f"  {record.code:<24} {str(status):>4}  {record.text_length:>6} chars  {url}{detail}")

    auditable = auditable_denominator(records)
    unauditable = len(records) - auditable

    print()
    print(f"auditable    {auditable} of {len(records)} sources")
    print(f"unauditable  {unauditable}, excluded from every denominator")

    if auditable == 0:
        print()
        print("No source could be read. Nothing here is evidence that any claim is unsupported.")

    if args.json:
        print()
        print(
            json.dumps(
                {
                    "capture": capture.to_dict(),
                    "fetches": [r.to_dict() for r in records],
                    "auditable": auditable,
                    "unauditable": unauditable,
                },
                indent=2,
            )
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
