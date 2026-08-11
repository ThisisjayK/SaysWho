#!/usr/bin/env python3
"""Break attempts 1 to 4: build the adversarial fixture, run the real pipeline against it, report.

    python3 tools/break_attempts.py --list
    python3 tools/break_attempts.py --attempt 1 --judge
    python3 tools/break_attempts.py --all --judge --out runs/break

`SCOPE.md` §6, stretch items 1 to 4. Attempts 5 and 6 are core and already have written results in
`BREAK_ATTEMPTS.md`; they are tests rather than a script, because both are about code paths and neither
needs a live judge.

**Why these four need a script and a judge.** Each one asks whether the *judge* can be fooled by a document
constructed to fool it. A fake judge cannot answer that: it would return whatever the fixture author
expected, which measures the author's assumption and calls it a result. So each attempt here serves a real
document over real HTTP through the real fetch layer, and asks the configured judge. Without `--judge` the
script builds and serves the fixture and reports the source outcome only, which is a genuine partial result
for attempt 2 and no result at all for the others.

**Each attempt declares the failure it is looking for before it runs.** That is written into `LOOKING_FOR`
below rather than decided after seeing the output, because an attempt whose success criterion is chosen
afterwards is not an attempt. The script prints that line above every result.

**A pass here is not proof of anything.** Each attempt is one document. Confirming the tool survives one
adversarial page says the mechanism handles that page, and `BREAK_ATTEMPTS.md` reports it in exactly those
words.
"""

from __future__ import annotations

import argparse
import json
import sys
import threading
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sayswho.cache import FetchCache
from sayswho.claims import Claim, ClaimSet
from sayswho.fetch import Fetcher
from sayswho.judge import (
    CONTRADICTED,
    JUDGE_PROMPT_VERSION,
    NOT_FOUND_IN_SOURCE,
    PARTIALLY_SUPPORTED,
    SUPPORTED,
    judge_claim,
)
from sayswho.records import Capture, Citation


@dataclass
class Attempt:
    """One adversarial document, the claim cited to it, and the failure being looked for."""

    number: int
    name: str
    #: The failure mode, declared before the run. Printed above every result.
    looking_for: str
    #: What the tool should do instead, if it holds.
    holds_if: str
    claim: str
    document: str
    #: Serve it with these headers, so attempt 2 can present a real paywall shape.
    headers: dict[str, str] = field(default_factory=lambda: {"Content-Type": "text/html; charset=utf-8"})
    #: For attempt 3: the document as it stood when the answer was written, supplied directly rather than
    #: fetched from Wayback. The live document differs, and the claim rests on a sentence that exists only in
    #: the live one.
    archived: str | None = None
    notes: str = ""


ATTEMPTS: list[Attempt] = [
    Attempt(
        number=1,
        name="topical-match false positive",
        looking_for=(
            "SUPPORTED or PARTIALLY_SUPPORTED. The page is entirely about this subject, shares most of the "
            "claim's vocabulary, and never states the claim. A judge matching on topic rather than on "
            "assertion returns support and the span guard cannot catch it, because the span it quotes is "
            "really on the page."
        ),
        holds_if="NOT_FOUND_IN_SOURCE. Topical overlap is not support, which the prompt says in those words.",
        claim="Patient navigation reduced time to diagnosis by 21 days in the Boston cohort.",
        document="""<html><body><article>
<h1>Patient navigation and time to diagnosis in urban cohorts</h1>
<p>Patient navigation programmes have become a standard component of cancer care delivery in Boston and in
comparable metropolitan areas. This review discusses time to diagnosis, the Boston cohort, and the design of
navigation interventions at length.</p>
<p>Time to diagnosis is widely used as an outcome measure in navigation research. Reported intervals vary
considerably across cohorts, and the Boston cohort has been described in several publications examining
navigation and diagnostic delay.</p>
<p>The literature on patient navigation and diagnostic timeliness is extensive. Studies differ in how they
define the diagnostic interval, in whether navigation begins before or after an abnormal result, and in the
populations enrolled. Days elapsed between abnormal screening and diagnostic resolution is the most common
formulation of the outcome.</p>
<p>This paper does not report an effect size. It is a narrative review of study designs and outcome
definitions in patient navigation research, and it makes no estimate of any reduction in time to diagnosis
for the Boston cohort or for any other.</p>
</article></body></html>""",
        notes=(
            "Every content word in the claim appears on the page: navigation, time to diagnosis, Boston "
            "cohort, days, reduced. The number 21 does not, and neither does any effect estimate."
        ),
    ),
    Attempt(
        number=2,
        name="paywall misread",
        looking_for=(
            "NOT_FOUND_IN_SOURCE. A paywall teaser carries the article's title and abstract-shaped opening "
            "and not its body. If the wall is not detected, the judge reads the teaser as the document and "
            "reports the claim as absent, which accuses the citation of something the paywall did."
        ),
        holds_if=(
            "SOURCE_PAYWALLED, and the judge never called at all. The claim becomes UNAUDITABLE and leaves "
            "every denominator."
        ),
        claim="The trial reported a 21-day reduction in time to diagnosis.",
        document="""<html><body><article>
<h1>Navigation and diagnostic timeliness in an urban cohort</h1>
<p class="teaser">Background. Diagnostic delay after abnormal screening remains common. We report a
randomised evaluation of patient navigation in an urban safety-net setting, with time to diagnostic
resolution as the primary outcome and enrolment across eleven participating sites.</p>
<div class="paywall">
  <p>Subscribe to continue reading this article.</p>
  <p>Already a subscriber? Sign in to access the full text, figures and tables.</p>
</div>
</article></body></html>""",
        notes=(
            "The detector is deliberately conservative, so the expected failure direction is a wall missed "
            "rather than one invented. A missed wall produces exactly the wrong verdict."
        ),
    ),
    Attempt(
        number=3,
        name="post-hoc drift",
        looking_for=(
            "A standing SUPPORTED resting on a sentence that was added to the page after the answer was "
            "written. The model cannot have read it, so a verdict built on it is evidence about today's "
            "page and not about the citation."
        ),
        holds_if=(
            "The verdict is voided as SPAN_ADDED_AFTER_GENERATION, or the span check finds the passage "
            "absent from the archived copy. Unknown must stay unknown: no archived copy means no claim "
            "either way."
        ),
        claim="The programme reduced time to diagnosis by 21 days.",
        document="""<html><body><article>
<h1>Programme evaluation</h1>
<p>The programme operated across eleven sites over four years, with navigation delivered by nurses and lay
navigators working to a shared protocol agreed at the outset.</p>
<p>A subsequent analysis found the programme reduced time to diagnosis by 21 days relative to usual care,
a result added to this page in a later revision.</p>
</article></body></html>""",
        archived="""<html><body><article>
<h1>Programme evaluation</h1>
<p>The programme operated across eleven sites over four years, with navigation delivered by nurses and lay
navigators working to a shared protocol agreed at the outset.</p>
<p>Outcome analyses are ongoing and no effect estimate is available at the time of writing.</p>
</article></body></html>""",
        notes=(
            "The drift layer was rebuilt on day 3 after a false positive, so this attempt is against the "
            "rebuilt version: page-level containment is no longer a gate and the decision is per claim."
        ),
    ),
    Attempt(
        number=4,
        name="shared-vocabulary contradiction",
        looking_for=(
            "SUPPORTED. The page states the opposite of the claim using almost exactly the claim's words, "
            "so any similarity-shaped reading of the passage matches it. Only a judge reading the polarity "
            "of the sentence gets this right."
        ),
        holds_if="CONTRADICTED, with a span quoting the sentence that states the opposite.",
        claim="Navigation reduced time to diagnosis in the intervention group.",
        document="""<html><body><article>
<h1>Navigation and time to diagnosis</h1>
<p>Navigation did not reduce time to diagnosis in the intervention group. The difference between groups was
not statistically significant, and the point estimate favoured usual care.</p>
<p>Time to diagnosis in the intervention group was longer than in the comparison group, by a margin the
authors attribute to scheduling capacity rather than to navigation itself.</p>
</article></body></html>""",
        notes=(
            "The claim and the contradicting sentence share every content word. The only difference is the "
            "negation."
        ),
    ),
]

BY_NUMBER = {a.number: a for a in ATTEMPTS}


class _Handler(BaseHTTPRequestHandler):
    """Serves the attempt's document, and the archived version on a separate path."""

    attempt: Attempt = None  # type: ignore[assignment]

    def log_message(self, *args):
        pass

    def do_GET(self):
        if self.path.startswith("/archived") and self.attempt.archived is not None:
            body, headers = self.attempt.archived, {"Content-Type": "text/html; charset=utf-8"}
        else:
            body, headers = self.attempt.document, dict(self.attempt.headers)
        payload = body.encode("utf-8")
        self.send_response(200)
        for key, value in headers.items():
            self.send_header(key, value)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_HEAD(self):
        self.do_GET()


def serve(attempt: Attempt) -> tuple[ThreadingHTTPServer, str]:
    handler = type("Bound", (_Handler,), {"attempt": attempt})
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, f"http://127.0.0.1:{httpd.server_address[1]}"


def run_attempt(attempt: Attempt, cache_dir: Path, use_judge: bool, provider: str | None) -> dict:
    """Fetch the fixture through the real fetch layer, then judge it if a judge is available."""
    httpd, base = serve(attempt)
    try:
        url = f"{base}/article.html"
        fetcher = Fetcher(FetchCache(cache_dir))
        record = fetcher.fetch(url)

        result = {
            "attempt": attempt.number,
            "name": attempt.name,
            "looking_for": attempt.looking_for,
            "holds_if": attempt.holds_if,
            "notes": attempt.notes,
            "claim": attempt.claim,
            "source_code": record.code,
            "source_detail": record.detail,
            "judge_called": False,
            "judge_prompt_version": JUDGE_PROMPT_VERSION,
        }

        if not record.auditable:
            # For attempt 2 this is the whole result and a good one: the judge is never asked about a
            # source the pipeline could not read.
            result["outcome"] = "source not auditable, judge never called"
            result["held"] = attempt.number == 2
            result["why"] = (
                "the wall was detected, so the claim is UNAUDITABLE and out of every denominator"
                if attempt.number == 2
                else "the document could not be read, so this attempt did not reach the judge and has no "
                     "result. That is a fixture problem, not a finding."
            )
            return result

        if not use_judge:
            result["outcome"] = "source read, no judge configured"
            result["held"] = None
            result["why"] = "run again with --judge for a verdict. Without one there is no result here."
            return result

        from sayswho.gemini import build_judge
        from sayswho.model import Meter

        client = build_judge(provider, meter=Meter())
        claim = Claim(id=f"BREAK-{attempt.number}", text=attempt.claim, markers=["[1]"], urls=[url])

        # Attempt 3 needs the drift layer, and the drift layer normally finds its archived copy through
        # Wayback. Depending on Wayback here would make the attempt's result depend on whether a third
        # party happens to hold a snapshot of a fixture it has never seen. So the archived text is supplied
        # directly: the same DriftRecord the checker would build, with the archived body this attempt
        # defines as the page the answer was written against.
        drift = None
        if attempt.archived is not None:
            from sayswho.drift import DriftRecord, compare
            from sayswho.extract import extract_text

            archived_text = extract_text(attempt.archived)
            containment, jaccard = compare(archived_text, record.text)
            drift = DriftRecord(
                url=url,
                status="DRIFT_PAGE_CHANGED",
                containment=containment,
                jaccard=jaccard,
                snapshot_url=f"{base}/archived",
                snapshot_timestamp="20260810000000",
                archived_text=archived_text,
            )

        judgement = judge_claim(claim, record, client, drift=drift)

        result["judge_called"] = True
        result["verdict"] = judgement.verdict
        result["voided"] = judgement.voided
        result["void_reason"] = judgement.void_reason
        result["span"] = judgement.span
        result["span_verified"] = judgement.span_verified
        result["missing_qualifiers"] = list(judgement.missing_qualifiers)
        result["reasoning"] = judgement.reasoning
        result["notes_from_judge"] = judgement.notes

        result["held"], result["why"] = _assess(attempt, judgement)
        result["outcome"] = f"{judgement.verdict}{' (voided)' if judgement.voided else ''}"
        return result
    finally:
        httpd.shutdown()
        httpd.server_close()


def _assess(attempt: Attempt, judgement) -> tuple[bool, str]:
    """Did the tool hold, by the criterion declared before the run.

    Deliberately mechanical. The criterion is `holds_if` and it is not reinterpreted here in the light of
    what actually happened.
    """
    verdict = judgement.verdict
    if attempt.number == 1:
        if verdict == NOT_FOUND_IN_SOURCE:
            return True, "topical overlap was not read as support"
        return False, (
            f"the judge returned {verdict} for a claim the page never states. This is the failure the "
            "attempt was looking for, and the span guard cannot catch it: the quoted passage is really "
            "on the page."
        )
    if attempt.number == 2:
        return False, (
            "the paywall was not detected, so the judge was asked about a teaser as though it were the "
            f"article, and returned {verdict}. A missed wall produces exactly the wrong verdict."
        )
    if attempt.number == 3:
        if judgement.voided:
            return True, f"voided as {judgement.void_reason}"
        if judgement.span_predates_generation is None:
            return True, (
                "no archived copy, so the run reports unknown rather than assuming the passage was there. "
                "Unknown staying unknown is the correct outcome, and it is not a strong pass."
            )
        if judgement.span_predates_generation is False:
            return False, "the span postdates the answer and the verdict was allowed to stand"
        return False, "the span was treated as predating the answer"
    if attempt.number == 4:
        if verdict == CONTRADICTED:
            return True, "the polarity of the sentence was read, not just its vocabulary"
        if verdict in (SUPPORTED, PARTIALLY_SUPPORTED):
            return False, (
                f"the judge returned {verdict} for a page stating the opposite in the same words. This is "
                "the failure the attempt was looking for."
            )
        return False, f"expected CONTRADICTED, got {verdict}"
    return False, "no criterion for this attempt"


def render(results: list[dict]) -> str:
    lines = ["BREAK ATTEMPTS 1 TO 4", ""]
    for r in results:
        held = {True: "HELD", False: "BROKE", None: "NO RESULT"}[r.get("held")]
        lines.append(f"Attempt {r['attempt']}: {r['name']}  ->  {held}")
        lines.append(f"  looking for : {r['looking_for']}")
        lines.append(f"  holds if    : {r['holds_if']}")
        lines.append(f"  claim       : {r['claim']}")
        lines.append(f"  source      : {r['source_code']} {r['source_detail']}".rstrip())
        if r.get("judge_called"):
            lines.append(f"  verdict     : {r['outcome']}")
            if r.get("span"):
                lines.append(f"  span        : {r['span'][:160]}")
            if r.get("missing_qualifiers"):
                lines.append(f"  qualifiers  : {'; '.join(r['missing_qualifiers'])}")
        else:
            lines.append(f"  verdict     : {r['outcome']}")
        lines.append(f"  why         : {r['why']}")
        lines.append("")
    broke = [r for r in results if r.get("held") is False]
    none = [r for r in results if r.get("held") is None]
    lines.append(f"{len(results) - len(broke) - len(none)} held, {len(broke)} broke, {len(none)} no result")
    lines.append(
        "Each attempt is one document. Holding means the mechanism handled that document, not that it "
        "cannot be broken."
    )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--attempt", type=int, action="append", default=[], choices=sorted(BY_NUMBER))
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--judge", action="store_true",
                        help="ask the configured judge. Without this there is no result for 1, 3 or 4")
    parser.add_argument("--judge-provider", default=None)
    parser.add_argument("--cache", type=Path, default=Path(".cache/break"))
    parser.add_argument("--out", type=Path, default=None, help="directory for results.json and readout.txt")
    args = parser.parse_args(argv)

    if args.list:
        for attempt in ATTEMPTS:
            print(f"{attempt.number}. {attempt.name}")
            print(f"   looking for: {attempt.looking_for}")
            print(f"   holds if   : {attempt.holds_if}")
            print()
        return 0

    numbers = sorted(set(args.attempt)) or (sorted(BY_NUMBER) if args.all else [])
    if not numbers:
        parser.error("choose --attempt N, or --all, or --list")

    if args.judge:
        from sayswho.server import check_judge

        ok, why = check_judge(args.judge_provider)
        if not ok:
            print("THE JUDGE CANNOT BE BUILT, so these attempts would have no result.")
            print()
            print(why)
            return 2

    results = [
        run_attempt(BY_NUMBER[n], args.cache, args.judge, args.judge_provider) for n in numbers
    ]
    readout = render(results)
    print(readout)

    if args.out:
        args.out.mkdir(parents=True, exist_ok=True)
        (args.out / "results.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
        (args.out / "readout.txt").write_text(readout + "\n", encoding="utf-8")
        print(f"\nwritten to {args.out}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
