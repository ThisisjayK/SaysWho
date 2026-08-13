#!/usr/bin/env python3
"""Bind a capture to the frozen query that produced it.

    python3 tools/bind_capture.py captures/2026-08-12-chatgpt.json --query PR-07
    python3 tools/bind_capture.py captures/*.json --list
    python3 tools/bind_capture.py captures/*.json --in-order --stratum consumer

The extension stamps `query_id: "UNASSIGNED"` because it cannot know which frozen query a person typed into
the box. Somebody has to say, and that somebody is a human. This tool is the place they say it, so the
assignment is recorded once, in the capture, rather than reconstructed later from filenames and memory.

Three checks before it writes anything:

- the id must be in the freeze manifest, so a capture cannot be bound to a query that was added afterwards
- the capture's `answer_sha256` must still verify, so binding cannot be the moment an edited answer slips in
- a capture already bound to a different id is refused without `--rebind`, which records the previous id in
  the capture rather than overwriting it silently

**`--in-order` exists because binding twenty-four captures one at a time is twenty-four chances to be off by
one, and a misbound capture is a rate computed over the wrong question with nothing anywhere to show it.** It
pairs captures sorted by capture time with a stratum's query ids in id order, which is only correct if the
questions were asked in that order, so it does not trust that: it prints the pairing with each query beside
the first sentence of the answer it is being bound to, and writes nothing without `--confirm`. That table is
the check. A human reading "how long is the STEM OPT extension" next to an answer about security deposits can
see it in a second, and no amount of hashing can.

It is deliberately not the default and deliberately not silent. Ordering is a fact about how a person worked,
which is exactly the kind of fact this project refuses to infer everywhere else.
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


def bind_one(path: Path, query_id: str, rebind: bool = False) -> tuple[bool, str]:
    """Write one binding, with the checks that make it safe. The only place a capture's query_id changes.

    Returns (ok, message). Factored out of `main` when `--in-order` arrived: two callers writing the binding
    would have meant two places deciding what a rebind does to the record, and the answer-hash check is the
    kind of thing a second implementation quietly omits.
    """
    with open(path, "rb") as fh:
        payload = json.load(fh)

    # Verifies the answer hash on the way in. Binding is not the moment an edited answer slips through.
    capture = Capture.from_dict(payload)

    if capture.query_id not in ("", UNASSIGNED) and capture.query_id != query_id:
        if not rebind:
            return False, (
                f"{path.name} is already bound to {capture.query_id}. Use --rebind to change it; the "
                "previous id is kept in the file."
            )
        payload.setdefault("_rebound_from", []).append(capture.query_id)

    payload["query_id"] = query_id
    payload["answer_sha256"] = capture.answer_sha256
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return True, f"bound  {path.name}  ->  {query_id}  ({stratum_of(query_id) or 'unknown stratum'})"


def first_sentence(text: str, limit: int = 96) -> str:
    """The opening of an answer, for the pairing table. The half of the eyeball check that is not the query."""
    flat = " ".join((text or "").split())
    for end in (". ", "? ", "! "):
        cut = flat.find(end)
        if 0 < cut < limit:
            return flat[: cut + 1]
    return (flat[:limit] + "...") if len(flat) > limit else flat


def bind_in_order(args, frozen: set[str]) -> int:
    """Pair captures with a stratum's queries by order, show the pairing, and write only on --confirm."""
    if not args.stratum:
        print("FAIL  --in-order needs --stratum, since the ids it pairs against come from one stratum",
              file=sys.stderr)
        return 1

    ids = sorted(qid for qid in frozen if stratum_of(qid) == args.stratum)
    if not ids:
        print(f"FAIL  no frozen queries in stratum {args.stratum!r}. Frozen strata carry ids; this one has "
              "none, so either the name is wrong or the stratum was never frozen", file=sys.stderr)
        return 1

    loaded = []
    for path in args.captures:
        try:
            loaded.append((path, Capture.from_json(path)))
        except Exception as exc:
            print(f"FAIL  {path.name} could not be read: {exc}", file=sys.stderr)
            print("      Nothing was bound. A run with one unreadable capture in it is a run with a hole.",
                  file=sys.stderr)
            return 1

    # Capture time, not filename. A filename is whatever the browser wrote; captured_at is in the record.
    loaded.sort(key=lambda pair: (pair[1].captured_at or pair[1].generated_at, pair[0].name))

    if len(loaded) > len(ids):
        print(f"FAIL  {len(loaded)} captures against {len(ids)} queries in {args.stratum}. More captures than "
              "questions means at least one question was asked twice, and order cannot say which.",
              file=sys.stderr)
        return 1
    if len(loaded) < len(ids) and not args.allow_partial:
        print(f"FAIL  {len(loaded)} captures against {len(ids)} queries in {args.stratum}. If the run stopped "
              "early that is normal: pass --allow-partial and the unbound ids are named.", file=sys.stderr)
        return 1

    print(f"pairing {len(loaded)} capture(s) with the first {len(loaded)} of {len(ids)} {args.stratum} queries,")
    print("in capture-time order. This is only right if the questions were asked in id order, so read it:")
    print()
    for qid, (path, capture) in zip(ids, loaded):
        print(f"  {qid}  {' '.join(query_text(qid).split())[:92]}")
        print(f"    <- {path.name}  ({capture.product}, {len(capture.citations)} citation(s))")
        print(f"       answer opens: {first_sentence(capture.answer_text)}")
        print()

    unbound = ids[len(loaded):]
    if unbound:
        print(f"not bound, because no capture reached them: {', '.join(unbound)}")
        print()

    if not args.confirm:
        print("Nothing was written. Read the pairing above, then pass --confirm.")
        return 0

    for qid, (path, _capture) in zip(ids, loaded):
        ok, message = bind_one(path, qid, rebind=args.rebind)
        if not ok:
            print(f"FAIL  {message}", file=sys.stderr)
            print("      Bindings written before this one stand. Fix this file and rerun.", file=sys.stderr)
            return 1
        print(message)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("captures", nargs="+", type=Path)
    parser.add_argument("--query", help="the frozen query id to bind to, such as PR-07")
    parser.add_argument("--list", action="store_true", help="show the frozen ids and each capture's binding")
    parser.add_argument("--rebind", action="store_true", help="allow changing an existing binding")
    parser.add_argument("--in-order", action="store_true",
                        help="pair captures, sorted by capture time, with a stratum's ids in id order. Prints "
                             "the pairing and writes nothing without --confirm")
    parser.add_argument("--stratum", help="which stratum's ids --in-order pairs against, such as consumer")
    parser.add_argument("--confirm", action="store_true",
                        help="actually write the bindings --in-order proposed. Without it this is a dry run")
    parser.add_argument("--allow-partial", action="store_true",
                        help="permit fewer captures than queries. The first N ids are used and the rest are "
                             "named as unbound, since a short run is a normal thing and a silent one is not")
    args = parser.parse_args(argv)

    frozen = frozen_query_ids()

    if args.in_order:
        return bind_in_order(args, frozen)

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

    ok, message = bind_one(args.captures[0], args.query, rebind=args.rebind)
    if not ok:
        print(f"FAIL  {message}", file=sys.stderr)
        return 1
    print(message)
    print(f"       {' '.join(query_text(args.query).split())[:96]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
