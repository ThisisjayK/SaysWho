#!/usr/bin/env python3
"""The honest run: the whole pipeline over every capture bound to a frozen query.

    python3 tools/run_stratum.py --captures captures/ --judge --out runs/2026-08-12
    python3 tools/run_stratum.py --captures captures/ --judge --goldset goldset/professional.gold.json \
        --out runs/2026-08-12

`SCOPE.md` §12 day 7. Prints the transcript that gets pasted into the writeup, and writes four files: the
full run record as JSON, the metric readout, `RUN_LOG.md`, and the per-number trace table.

It halts before doing anything if the query freeze check fails, because a run against a moved query set is
not measuring what the freeze recorded, and this is the one path where nobody is watching every line.

**Running it today prints an honest nothing.** The professional stratum is empty until real queries are
transcribed and scrubbed, so there is nothing bound to run over. That output is the correct output, and it
says which of the two reasons it is: no captures, or captures that are not bound to a frozen query.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sayswho.harness import FreezeBroken, readout, run_stratum, save  # noqa: E402
from sayswho.queryset import frozen_query_ids  # noqa: E402


def collect(paths: list[Path]) -> list[Path]:
    out: list[Path] = []
    for path in paths:
        if path.is_dir():
            out.extend(sorted(p for p in path.glob("*.json") if not p.name.endswith(".split.json")))
        else:
            out.append(path)
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--captures", type=Path, action="append", required=True,
                        help="a capture file or a directory of them. Repeatable")
    parser.add_argument("--split", type=Path, action="append", default=[],
                        help="a stored split, matched to a capture by its query id. Repeatable. Without "
                             "one, Phase 1 re-splits, and a re-split answer is a different sample of it")
    parser.add_argument("--goldset", type=Path, default=None)
    parser.add_argument("--out", type=Path, default=None, help="directory for the run's four artefacts")
    parser.add_argument("--cache", type=Path, default=Path(".cache/fetch"))
    parser.add_argument("--judge", action="store_true",
                        help="run Phase 1 and Phase 3. Without it this is a fetch and liveness pass only")
    parser.add_argument("--judge-provider", choices=["gemini", "anthropic"], default=None)
    parser.add_argument("--budget", type=int, default=2_000_000)
    parser.add_argument("--no-drift", action="store_true")
    parser.add_argument("--no-cache", action="store_true")
    parser.add_argument("--skip-ethics-gate", action="store_true",
                        help="run without the privacy and honesty gate. The honest run never uses this, and "
                             "a run that did is not one whose output belongs in the writeup")
    parser.add_argument("--fast-ethics-gate", action="store_true",
                        help="privacy checks only, skipping the honesty tests. The report says which half "
                             "it did not check rather than reporting a pass it did not earn")
    parser.add_argument("--skip-freeze-check", action="store_true",
                        help="for auditing captures outside the frozen set entirely. No rate from such a "
                             "run may be published, and the readout says so")
    args = parser.parse_args(argv)

    # The ethics gate, before anything is fetched or judged. SCOPE.md §8 and the capstone attestation row
    # both say the same thing: if privacy or honesty fails, the run does not happen. That sentence is worth
    # nothing printed in a document, so it is enforced on the one path where nobody watches every line.
    if not args.skip_ethics_gate:
        from sayswho.ethics import run as ethics_run

        report = ethics_run(Path(__file__).resolve().parent.parent, run_suite=not args.fast_ethics_gate)
        print(report.render())
        print()
        if not report.passed:
            print("Refusing to run. Fix the checks above, or explain in the writeup why a run happened")
            print("with the gate failing, which is a harder sentence to write than the fix.")
            return 2

    captures = collect(args.captures)
    if not captures:
        print("No capture files found. Nothing to run.")
        print()
        print(f"The freeze manifest holds {len(frozen_query_ids())} frozen quer(ies).")
        print("A run needs captures bound to them: capture an answer with the extension, then")
        print("bind it with tools/bind_capture.py.")
        return 0

    splits = {}
    for path in args.split:
        from sayswho.splits import StoredSplit

        stored = StoredSplit.load(path)
        splits[stored.query_id] = path

    def on_event(kind, **kw):
        if kind == "capture":
            print(f"\n{'=' * 96}\ncapture   {kw['path']}")
        elif kind == "g0_failed":
            print(f"  G0 FAILED  {kw['run'].error}")
        elif kind == "source":
            record = kw["record"]
            status = record.http_status if record.http_status is not None else "  -"
            print(f"  {record.code:<24} {str(status):>4}  {record.text_length:>6} chars  {record.url}")
            if kw["drift"].status not in ("DRIFT_NOT_CHECKED",):
                print(f"    drift  {kw['drift'].status}  {kw['drift'].detail}")
        elif kind == "phase1":
            run = kw["run"]
            print(
                f"  Phase 1   {len(run.claim_set.claims)} claims, {len(run.claim_set.skipped)} skipped   "
                f"[model-inference]"
            )
        elif kind == "judgement":
            j = kw["judgement"]
            flag = f"  VOID {j.void_reason}" if j.voided else ""
            print(f"  {j.claim_id}  {j.verdict:<22}{flag}")
        elif kind == "halted":
            print(f"  HALTED  {kw['detail']}")

    try:
        run = run_stratum(
            captures,
            cache_dir=args.cache,
            judge=args.judge,
            provider=args.judge_provider,
            budget=args.budget,
            drift=not args.no_drift,
            use_cache=not args.no_cache,
            splits=splits,
            goldset_path=args.goldset,
            skip_freeze_check=args.skip_freeze_check,
            on_event=on_event,
        )
    except FreezeBroken as exc:
        print("FREEZE CHECK FAILED. Nothing was run.")
        print()
        print(exc)
        return 2

    print()
    print(readout(run))

    if args.out:
        written = save(run, args.out)
        print()
        for name, path in written.items():
            print(f"{name:<10} {path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
