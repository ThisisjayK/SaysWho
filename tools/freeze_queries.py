#!/usr/bin/env python3
"""Freeze the query set, and detect any later change to it.

    freeze_queries.py status          what is frozen, what isn't
    freeze_queries.py freeze          freeze every 'ready' stratum not already frozen
    freeze_queries.py check           recompute hashes, exit non-zero if anything moved

SCOPE.md §10: "Written before any capture, frozen, and committed. No query is added or dropped after the
first run. That is how benchmarks get quietly tuned."

`check` is what turns that from a promise into a gate. It runs before every capture run. If a query was
added, removed, or edited after the freeze, the run fails instead of quietly producing a better number.

Breaking a freeze requires --force and a written reason, and the old entry is retained in an `unfreezes`
record rather than overwritten. The point is not that a freeze can never be broken. Sometimes it has to be.
The point is that it cannot be broken invisibly, including by me.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from validate_queries import QUERIES_DIR, load_strata, query_hash, validate  # noqa: E402

MANIFEST = QUERIES_DIR / "FREEZE.json"


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_manifest() -> dict:
    if not MANIFEST.exists():
        return {"version": 1, "frozen": {}, "unfreezes": []}
    return json.loads(MANIFEST.read_text())


def save_manifest(manifest: dict) -> None:
    MANIFEST.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")


def snapshot(filename: str, doc: dict) -> dict:
    return {
        "frozen_at": now(),
        "file_sha256": file_sha256(QUERIES_DIR / filename),
        "stratum_id": doc["stratum"]["id"],
        "query_count": len(doc.get("query", [])),
        "query_hashes": {q["id"]: query_hash(q) for q in doc.get("query", [])},
    }


def require_valid(strata: dict) -> None:
    findings = validate(strata)
    if findings.errors:
        for err in findings.errors:
            print(f"FAIL  {err}", file=sys.stderr)
        print("\nValidation failed. Nothing frozen.", file=sys.stderr)
        raise SystemExit(1)


def cmd_status(args: argparse.Namespace) -> int:
    strata = load_strata()
    manifest = load_manifest()
    for filename, doc in strata.items():
        entry = manifest["frozen"].get(filename)
        stratum = doc.get("stratum", {})
        n = len(doc.get("query", []))
        if entry:
            print(f"  FROZEN   {filename:<20} n={n:<3} at {entry['frozen_at']}")
        elif stratum.get("status") == "ready":
            print(f"  ready    {filename:<20} n={n:<3} not yet frozen")
        else:
            print(f"  draft    {filename:<20} n={n:<3} not freezable while status is draft")
    if manifest["unfreezes"]:
        print(f"\n  {len(manifest['unfreezes'])} recorded unfreeze(s). See FREEZE.json.")
    return 0


def cmd_freeze(args: argparse.Namespace) -> int:
    strata = load_strata()
    require_valid(strata)
    manifest = load_manifest()

    targets = [args.file] if args.file else list(strata)
    froze_any = False

    for filename in targets:
        if filename not in strata:
            print(f"FAIL  no such stratum file: {filename}", file=sys.stderr)
            return 1
        doc = strata[filename]
        stratum = doc["stratum"]

        if filename in manifest["frozen"]:
            if not args.force:
                print(f"  skip     {filename} is already frozen. --force --reason to break it")
                continue
            if not args.reason:
                print("FAIL  --force requires --reason", file=sys.stderr)
                return 1
            manifest["unfreezes"].append(
                {
                    "file": filename,
                    "unfrozen_at": now(),
                    "reason": args.reason,
                    "previous": manifest["frozen"][filename],
                }
            )
            print(f"  UNFREEZE {filename}: {args.reason}")

        if stratum["status"] != "ready":
            print(f"  skip     {filename} status is {stratum['status']!r}, not 'ready'")
            continue

        manifest["frozen"][filename] = snapshot(filename, doc)
        print(f"  FROZEN   {filename} n={len(doc.get('query', []))}")
        froze_any = True

    if froze_any or args.force:
        save_manifest(manifest)
        print(f"\nManifest written to {MANIFEST.relative_to(QUERIES_DIR.parent)}")
    else:
        print("\nNothing to freeze.")
    return 0


def cmd_check(args: argparse.Namespace) -> int:
    strata = load_strata()
    manifest = load_manifest()
    problems: list[str] = []

    if not manifest["frozen"]:
        print("FAIL  nothing is frozen. Run `freeze` before capturing.", file=sys.stderr)
        return 1

    for filename, entry in manifest["frozen"].items():
        if filename not in strata:
            problems.append(f"{filename}: frozen file is missing from the queries directory")
            continue

        doc = strata[filename]
        current = {q["id"]: query_hash(q) for q in doc.get("query", [])}
        recorded = entry["query_hashes"]

        added = sorted(set(current) - set(recorded))
        removed = sorted(set(recorded) - set(current))
        modified = sorted(qid for qid in set(current) & set(recorded) if current[qid] != recorded[qid])

        for qid in added:
            problems.append(f"{filename}: {qid} was ADDED after the freeze")
        for qid in removed:
            problems.append(f"{filename}: {qid} was REMOVED after the freeze")
        for qid in modified:
            problems.append(f"{filename}: {qid} was EDITED after the freeze")

        if not (added or removed or modified):
            byte_drift = file_sha256(QUERIES_DIR / filename) != entry["file_sha256"]
            suffix = "  (comments or formatting changed; no query content did)" if byte_drift else ""
            print(f"  OK       {filename} n={len(current)}{suffix}")

    unfrozen = [
        f
        for f, doc in strata.items()
        if f not in manifest["frozen"] and doc.get("stratum", {}).get("status") == "ready"
    ]
    for filename in unfrozen:
        problems.append(f"{filename}: status is 'ready' but it was never frozen")

    if problems:
        print()
        for p in problems:
            print(f"FAIL  {p}", file=sys.stderr)
        print(
            "\nThe frozen query set does not match what is on disk. A capture run against this set "
            "would not be measuring what the freeze recorded.",
            file=sys.stderr,
        )
        return 1

    print("\nOK  frozen query set matches disk.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("status", help="show what is frozen").set_defaults(fn=cmd_status)

    p_freeze = sub.add_parser("freeze", help="freeze ready strata")
    p_freeze.add_argument("--file", help="freeze only this file")
    p_freeze.add_argument("--force", action="store_true", help="break an existing freeze")
    p_freeze.add_argument("--reason", help="required with --force, recorded permanently")
    p_freeze.set_defaults(fn=cmd_freeze)

    sub.add_parser("check", help="verify disk still matches the freeze").set_defaults(fn=cmd_check)

    args = parser.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
