#!/usr/bin/env python3
"""Capture an answer from a provider API, or replay a stored response.

    # one live call, Gemini's free tier, grounded so there are citations to audit
    python3 tools/api_capture.py --provider gemini --prompt "..." --query-id PR-01

    # any provider: get the JSON however you like, then replay it
    python3 tools/api_capture.py --from raw.json --provider perplexity --query-id PR-01

    # what the walk found, without writing anything
    python3 tools/api_capture.py --from raw.json --provider openai --dry-run

The raw response is written before anything is parsed, and never overwritten. That order matters: a parser
can be fixed and re-run against a stored response, and a response that was reshaped before storage cannot be
recovered. It is the same rule the fetch cache follows.

The capture it writes is an ordinary capture with `source="api"`, so `sayswho.cli`, `tools/run_stratum.py`
and the report all work on it unchanged. `adapter_verified` is False until a person has read the stored
response against the capture, exactly as for a DOM adapter.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sayswho.apicapture import PROVIDERS, ask, build


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--provider", required=True,
                        help=f"any name; live calls only for {sorted(PROVIDERS)}")
    parser.add_argument("--prompt", default="", help="for a live call")
    parser.add_argument("--from", dest="replay", type=Path, default=None,
                        help="a stored JSON response to replay instead of calling anything")
    parser.add_argument("--model", default="")
    parser.add_argument("--query-id", default="UNASSIGNED",
                        help="bind this capture to a frozen query. Leave unset and the binding gate says so")
    parser.add_argument("--captures", type=Path, default=Path("captures"))
    parser.add_argument("--raw", type=Path, default=Path("captures/raw"),
                        help="where raw API responses are stored, never overwritten")
    parser.add_argument("--dry-run", action="store_true", help="report what was found, write nothing")
    args = parser.parse_args(argv)

    if not args.replay and not args.prompt:
        parser.error("give --prompt for a live call, or --from to replay a stored response")

    raw_path = ""
    if args.replay:
        payload = json.loads(args.replay.read_text())
        raw_path = str(args.replay)
    else:
        payload = ask(args.provider, args.prompt, args.model)
        if not args.dry_run:
            args.raw.mkdir(parents=True, exist_ok=True)
            stem = f"{args.provider}-{args.query_id}"
            target = args.raw / f"{stem}.json"
            n = 1
            while target.exists():
                target = args.raw / f"{stem}-{n}.json"
                n += 1
            target.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
            raw_path = str(target)
            print(f"raw response  {raw_path}")

    result = build(payload, args.provider, query_id=args.query_id, model=args.model, raw_path=raw_path)
    print(result.render())

    if not result.capture.citations:
        print()
        print("No citations found in this response. Gate G0 will halt on this capture, which is correct if")
        print("the answer really has none. If it has some, the walk missed them: check the paths above and")
        print("the urls-not-taken count, and add the key to URL_KEYS or CITATION_LIST_KEYS.")

    if args.dry_run:
        print("\n--dry-run, nothing written")
        return 0

    args.captures.mkdir(parents=True, exist_ok=True)
    stem = f"capture-api-{args.provider}-{args.query_id}"
    target = args.captures / f"{stem}.json"
    n = 1
    while target.exists():
        target = args.captures / f"{stem}-{n}.json"
        n += 1

    record = result.capture.to_dict()
    record["api_provenance"] = result.provenance()
    target.write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\ncapture       {target}")
    print(f"audit it      python3 -m sayswho.cli {target} --judge")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
