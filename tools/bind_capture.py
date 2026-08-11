#!/usr/bin/env python3
"""Bind a capture to the frozen query that produced it.

    python3 tools/bind_capture.py captures/2026-08-12-chatgpt.json --query PR-07
    python3 tools/bind_capture.py captures/*.json --list

The extension stamps `query_id: "UNASSIGNED"` because it cannot know which frozen query a person typed into
the box. Somebody has to say, and that somebody is a human. This tool is the place they say it, so the
assignment is recorded once, in the capture, rather than reconstructed later from filenames and memory.

Three checks before it writes anything:

- the id must be in the freeze manifest, so a capture cannot be bound to a query that was added afterwards
- the capture's `answer_sha256` must still verify, so binding cannot be the moment an edited answer slips in
- a capture already bound to a different id is refused without `--rebind`, which records the previous id in
  the capture rather than overwriting it silently
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sayswho.queryset import (  # noqa: E402
    UNASSIGNED,
    frozen_query_ids,
    query_text,
    stratum_of,
)
from sayswho.records import Capture  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("captures", nargs="+", type=Path)
    parser.add_argument("--query", help="the frozen query id to bind to, such as PR-07")
    parser.add_argument("--list", action="store_true", help="show the frozen ids and each capture's binding")
    parser.add_argument("--rebind", action="store_true", help="allow changing an existing binding")
    args = parser.parse_args(argv)

    frozen = frozen_query_ids()

    if args.list or not args.query:
        print(f"frozen query ids ({len(frozen)}):")
        for qid in sorted(frozen):
            text = " ".join(query_text(qid).split())
            print(f"  {qid:<8} {text[:88]}")
        print()
        print("captures:")
        for path in args.captures:
            try:
                capture = Capture.from_json(path)
            except Exception as exc:
                print(f"  {path}: unreadable ({exc})")
                continue
            state = "unbound" if capture.query_id in ("", UNASSIGNED) else capture.query_id
            print(f"  {path.name:<44} {state:<10} {capture.product}  {capture.generated_at}")
        if not args.query:
            print()
            print("Nothing was changed. Pass --query <id> to bind.")
        return 0

    if args.query not in frozen:
        print(
            f"FAIL  {args.query} is not in the freeze manifest. Bind only to a frozen query: a rate over an "
            "unfrozen one would be a rate over a set that can still move.",
            file=sys.stderr,
        )
        return 1

    if len(args.captures) > 1:
        print("FAIL  --query binds one capture at a time. Two captures of one query is fine; say so twice.",
              file=sys.stderr)
        return 1

    path = args.captures[0]
    with open(path, "rb") as fh:
        payload = json.load(fh)

    # Verifies the answer hash on the way in. Binding is not the moment an edited answer slips through.
    capture = Capture.from_dict(payload)

    if capture.query_id not in ("", UNASSIGNED) and capture.query_id != args.query:
        if not args.rebind:
            print(
                f"FAIL  {path.name} is already bound to {capture.query_id}. Use --rebind to change it; the "
                "previous id is kept in the file.",
                file=sys.stderr,
            )
            return 1
        history = payload.setdefault("_rebound_from", [])
        history.append(capture.query_id)

    payload["query_id"] = args.query
    payload["answer_sha256"] = capture.answer_sha256
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"bound  {path.name}  ->  {args.query}  ({stratum_of(args.query) or 'unknown stratum'})")
    print(f"       {' '.join(query_text(args.query).split())[:96]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
