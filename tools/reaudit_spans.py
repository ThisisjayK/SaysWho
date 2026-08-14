#!/usr/bin/env python3
"""Re-check every voided span against the page it was voided on, under the current normalisation.

    python3 tools/reaudit_spans.py reports/*.json
    python3 tools/reaudit_spans.py reports/*.json --json runs/span-reaudit.json

`JUDGE_FABRICATED_SPAN` is published as a finding about the judge: the judge quoted a passage that is not in
the document it was given. That claim is only true if the check is right. Until the typographic fold landed,
the check compared on whitespace and case alone, so a page using curly quotes and a judge typing straight ones
disagreed and the verdict was thrown out. Three of five typographic variants failed.

So a share of the published rate may have been measuring the checker and attributing it to the model. This
re-runs the check with the current fold, over the fetched bytes still in the cache, and reports which voids
survive. A void that survives is a finding about the judge. One that does not was never one.

**It reads the cache, not the live web.** The point is to re-check against the same bytes the verdict was
made on. A page fetched today is a different document, and re-checking against it would answer a different
question. A span whose page is no longer cached is reported as unrecheckable rather than guessed at.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sayswho.cache import FetchCache
from sayswho.extract import normalise_for_span
from sayswho.fetch import text_pair
from sayswho.judge import JUDGE_FABRICATED_SPAN

#: Void reasons this tool can re-check. The others are not about string comparison: a span that postdates the
#: answer or a judge that refused are facts the fold cannot change.
RECHECKABLE = {JUDGE_FABRICATED_SPAN}


@dataclass
class Outcome:
    report: str
    claim_id: str
    url: str
    span: str
    verdict: str
    status: str
    detail: str = ""


@dataclass
class Summary:
    outcomes: list[Outcome] = field(default_factory=list)

    def of(self, status: str) -> list[Outcome]:
        return [o for o in self.outcomes if o.status == status]

    def render(self) -> str:
        survived = self.of("still fabricated")
        overturned = self.of("was really on the page")
        unrecheckable = self.of("page not in the cache")
        other = self.of("not a string-comparison void")

        lines = ["VOIDED SPAN RE-AUDIT", ""]
        if not self.outcomes:
            lines.append("  No voided spans found in these reports. Nothing to re-audit.")
            return "\n".join(lines)

        for outcome in self.outcomes:
            lines.append(f"  {outcome.status:<28} {outcome.claim_id}  {outcome.url[:60]}")
            if outcome.detail:
                lines.append(f"      {outcome.detail}")
            if outcome.span:
                lines.append(f"      span: {outcome.span[:110]}")

        checked = len(survived) + len(overturned)
        lines += [
            "",
            f"  {len(self.outcomes)} voided span(s) in these reports.",
            f"  {checked} re-checkable against cached bytes: {len(survived)} still fabricated, "
            f"{len(overturned)} were really on the page.",
        ]
        if unrecheckable:
            lines.append(f"  {len(unrecheckable)} could not be re-checked: the page is not in the cache.")
        if other:
            lines.append(f"  {len(other)} voided for a reason string comparison cannot change.")

        if overturned:
            lines += [
                "",
                "  Every overturned void was a verdict thrown away and a number published about the judge",
                "  that this tool caused. The fabricated-span rate has to be recomputed, and the writeup has",
                "  to say the earlier figure was partly an artefact of the checker.",
            ]
        elif checked:
            lines += [
                "",
                "  No void was overturned, so the fold did not manufacture the earlier figure. That is a",
                f"  statement about {checked} span(s) and not a rate.",
            ]
        return "\n".join(lines)


def text_of(meta: dict, body: bytes) -> tuple[str | None, str]:
    """The document text, extracted the same way the pipeline extracted it.

    Not always the HTML extractor, which is what the first version of this file assumed. The boston.gov
    citation in these reports is a PDF that the pipeline read successfully, and running the HTML extractor
    over PDF bytes produces noise. Every span would then read as absent and the re-audit would confirm four
    voids that it had itself manufactured, which is the same failure this whole exercise is about, committed
    by the tool built to check for it.

    That PDF reads as 54,811 characters as of 2026-08-12. The figure is dated because it is a measurement of
    this reader rather than a property of the document: this line said 57,067 until today, and it was true
    when written and stopped being true twice, as each fix removed characters the reader had been inventing.
    """
    strict, _permissive, kind = text_pair(meta.get("headers") or {}, body)
    if not strict:
        # No parser, an unreadable PDF, or bytes we could not decode. Which of those it was is the `kind`,
        # and the caller reports it rather than treating an unreadable source as an absent span.
        return None, kind
    return strict, kind


def recheck(report_paths: list[Path], cache_dir: Path) -> Summary:
    cache = FetchCache(cache_dir)
    summary = Summary()

    for path in report_paths:
        try:
            payload = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError):
            continue

        for claim in payload.get("claims", []):
            for row in claim.get("sources", []):
                if not row.get("voided"):
                    continue
                reason = row.get("void_reason", "")
                span = row.get("span") or ""
                url = row.get("url", "")

                if reason not in RECHECKABLE:
                    summary.outcomes.append(Outcome(
                        report=path.name, claim_id=claim.get("id", "?"), url=url, span=span,
                        verdict=row.get("verdict", ""), status="not a string-comparison void",
                        detail=reason,
                    ))
                    continue

                entry = cache.latest(url)
                if entry is None:
                    summary.outcomes.append(Outcome(
                        report=path.name, claim_id=claim.get("id", "?"), url=url, span=span,
                        verdict=row.get("verdict", ""), status="page not in the cache",
                        detail="re-checking against a page fetched today would answer a different question",
                    ))
                    continue

                _meta, body = entry
                document, kind = text_of(_meta, body)
                if document is None:
                    summary.outcomes.append(Outcome(
                        report=path.name, claim_id=claim.get("id", "?"), url=url, span=span,
                        verdict=row.get("verdict", ""), status="page not in the cache",
                        detail=f"cached as {kind}, which this tool has no reader for",
                    ))
                    continue
                present = normalise_for_span(span) in normalise_for_span(document)
                summary.outcomes.append(Outcome(
                    report=path.name, claim_id=claim.get("id", "?"), url=url, span=span,
                    verdict=row.get("verdict", ""),
                    status="was really on the page" if present else "still fabricated",
                    detail=(
                        "the void was an artefact of the old whitespace-and-case comparison"
                        if present
                        else "absent from the fetched document under the current fold as well"
                    ),
                ))
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("reports", type=Path, nargs="+")
    parser.add_argument("--cache", type=Path, default=Path(".cache/fetch"))
    parser.add_argument("--json", type=Path, default=None)
    args = parser.parse_args(argv)

    summary = recheck(args.reports, args.cache)
    print(summary.render())

    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(
            json.dumps([o.__dict__ for o in summary.outcomes], indent=2), encoding="utf-8"
        )
        print(f"\nwritten to {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
