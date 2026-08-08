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
from .drift import DRIFT_NO_SNAPSHOT, DRIFT_NOT_CHECKED, DriftChecker, DriftRecord, apply_drift
from .fetch import Fetcher, user_agent
from .gates import auditable_denominator, g0_has_citations
from .named_citations import analyse as analyse_named
from .records import Capture


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("capture", type=Path, help="path to a capture JSON file")
    parser.add_argument("--cache", type=Path, default=Path(".cache/fetch"))
    parser.add_argument("--no-cache", action="store_true", help="refetch even if cached")
    parser.add_argument(
        "--no-drift",
        action="store_true",
        help="skip the Wayback comparison. Drift is on by default, because a run with it off measures "
        "something different and the difference would not be visible in the output",
    )
    parser.add_argument(
        "--judge",
        action="store_true",
        help="run Phase 1 and Phase 3. Costs money and needs ANTHROPIC_API_KEY. Off by default so the "
        "fetch pass can be run freely",
    )
    parser.add_argument("--budget", type=int, default=2_000_000, help="token budget; the run halts at it")
    parser.add_argument("--json", action="store_true", help="emit the run record as JSON")
    args = parser.parse_args(argv)

    capture = Capture.from_json(args.capture)

    print(f"capture      {args.capture}")
    print(f"query        {capture.query_id}  product={capture.product}  model={capture.model_id}")
    print(f"generated    {capture.generated_at}")
    print(f"answer sha   {capture.answer_sha256}")
    print(f"user-agent   {user_agent()}")
    print()

    if capture.capture_is_known_incomplete:
        print("INCOMPLETE   this capture does not hold the whole answer.")
        if capture.citations_possibly_hidden:
            print(
                f"             {capture.expanders_seen} '+N' controls hide at least "
                f"{capture.citations_possibly_hidden} more citations."
            )
        if capture.dom_chars > capture.rendered_chars:
            print(
                f"             {capture.dom_chars - capture.rendered_chars} characters were in the page "
                f"but never laid out, so they are missing from the text."
            )
        print("             Any rate computed from it is over a subset of the answer.")
        print()

    named = analyse_named(capture)
    if named.named_count:
        print(
            f"named, unlinked  {named.named_count} sources named in prose with no URL "
            f"{named.by_kind}"
        )
        print("                 A floor, not a total. These are not unsupported and not unauditable.")
        print("                 They are uncheckable, and they enter no denominator.")
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
    checker = None if args.no_drift else DriftChecker(fetcher)

    records = []
    drifts = []
    for url in capture.cited_urls:
        record = fetcher.fetch(url, use_cache=not args.no_cache)

        if checker is not None:
            drift = checker.check(record, capture.generated_at)
            drifts.append(drift)
            apply_drift(record, drift)
        else:
            drifts.append(DriftRecord(url=url, status=DRIFT_NOT_CHECKED, detail="--no-drift"))

        records.append(record)
        detail = f"  ({record.detail})" if record.detail else ""
        status = record.http_status if record.http_status is not None else "  -"
        print(f"  {record.code:<24} {str(status):>4}  {record.text_length:>6} chars  {url}{detail}")
        print(f"    drift  {drifts[-1].status:<20} {drifts[-1].detail}")

    auditable = auditable_denominator(records)
    unauditable = len(records) - auditable
    drift_unknown = sum(1 for d in drifts if d.status == DRIFT_NO_SNAPSHOT)

    print()
    print(f"auditable    {auditable} of {len(records)} sources")
    print(f"unauditable  {unauditable}, excluded from every denominator")
    if drift_unknown:
        print(
            f"drift unknown {drift_unknown}, reported as unknown rather than as unchanged. "
            "Those sources are still auditable, but nothing here shows they match what the model read."
        )

    if auditable == 0:
        print()
        print("No source could be read. Nothing here is evidence that any claim is unsupported.")

    claim_set = None
    report = None
    if args.judge and auditable:
        from .claims import split_claims
        from .judge import JudgeReport, judge_claim
        from .model import AnthropicJudge, BudgetExceeded, Meter

        meter = Meter(budget_tokens=args.budget)
        client = AnthropicJudge(meter=meter)
        by_url = {r.url: r for r in records}

        print()
        print("Phase 1   splitting the answer into claims   [model-inference]")
        claim_set = split_claims(capture, client)
        print(f"  claims   {len(claim_set.claims)}   uncited {claim_set.uncited_count}")
        print(f"  G1 skipped {len(claim_set.skipped)}, counted and reported, never dropped")

        print()
        print("Phase 3   judging each claim against its source   [model-inference]")
        judgements = []
        try:
            for claim in claim_set.claims:
                for url in claim.urls:
                    record = by_url.get(url)
                    if record is None or not record.auditable:
                        continue
                    j = judge_claim(claim, record, client)
                    judgements.append(j)
                    flag = "" if not j.voided else f"  VOID {j.void_reason}"
                    print(f"  {j.claim_id}  {j.verdict:<22}{flag}")
        except BudgetExceeded as exc:
            print(f"  HALTED  {exc}")

        report = JudgeReport(judgements)
        rate = report.fabricated_span_rate
        print()
        print(f"verdicts     {report.counts()}")
        print(
            "fabricated   "
            + (
                f"{report.fabricated_span_count} of {len([j for j in judgements if j.span])} "
                f"span-bearing verdicts ({rate:.1%})"
                if rate is not None
                else "no verdict required a span, so there is no rate"
            )
        )
        print(f"metering     {meter.to_dict()}")
        print()
        print("No aggregate support rate is printed. G4: there is no gold set for this judge and prompt")
        print("version yet, so per-claim verdicts are all this run is entitled to report.")

    if args.json:
        print()
        print(
            json.dumps(
                {
                    "capture": capture.to_dict(),
                    "fetches": [r.to_dict() for r in records],
                    "drift": [d.to_dict() for d in drifts],
                    "named_citations": named.to_dict(),
                    "auditable": auditable,
                    "unauditable": unauditable,
                },
                indent=2,
            )
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
