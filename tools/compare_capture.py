#!/usr/bin/env python3
"""How many citations did the DOM capture miss? Compare it against an API capture of the same question.

    python3 tools/compare_capture.py --dom captures/capture-perplexity-2026...json \\
                                     --api captures/capture-api-perplexity-PR-01.json

**This is the point of having an API path at all.** The largest unquantified risk in this project is that a
DOM capture silently holds a subset of an answer's citations. Nothing downstream can detect it: the support
rate comes out over whatever was captured and looks entirely normal. The Perplexity adapter found zero of
eight citations for four days and passed every test, because the tests asserted the rule the adapter
implemented. A test suite cannot catch a wrong model of the page.

An API response carries citations as data. So asking the same question both ways and comparing the two sets
measures the scraper against something that is not the scraper. That number has never existed for this
project and it belongs in §7 next to the support rate, because a rate over 8 of 10 citations is a different
measurement from a rate over 10 of 10 and only one of them is the one being claimed.

**What this is not.** It is not a ground truth. The two answers were produced by different models with
different retrieval, so a URL in one and not the other can mean the scraper missed it *or* that the two
answers genuinely cited different things. Same-question is not same-answer. The comparison is a floor on the
undercount and an upper bound on nothing, and it is only worth reading at all when the two answer texts are
close enough to be about the same thing, which is why the overlap of the prose is reported beside it.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sayswho.domains import registrable_domain
from sayswho.drift import compare as text_overlap
from sayswho.records import normalise_url


def load(path: Path) -> dict:
    return json.loads(path.read_text())


def urls_of(record: dict) -> dict[str, str]:
    """Normalised URL to the marker it was captured under."""
    return {normalise_url(c["url"]): c.get("marker", "") for c in record.get("citations", [])}


def report(dom: dict, api: dict) -> str:
    dom_urls, api_urls = urls_of(dom), urls_of(api)
    both = sorted(set(dom_urls) & set(api_urls))
    api_only = sorted(set(api_urls) - set(dom_urls))
    dom_only = sorted(set(dom_urls) - set(api_urls))

    containment, jaccard = text_overlap(api.get("answer_text", ""), dom.get("answer_text", ""))

    lines = [
        "CAPTURE FIDELITY",
        "",
        f"  dom capture   {dom.get('product')}  {len(dom_urls)} citation(s)  "
        f"adapter {dom.get('adapter')}  verified {dom.get('adapter_verified')}",
        f"  api capture   {api.get('product')}  {len(api_urls)} citation(s)  "
        f"model {api.get('model_id')}",
        "",
        f"  in both       {len(both)}",
        f"  api only      {len(api_only)}   <- candidates for citations the DOM capture missed",
        f"  dom only      {len(dom_only)}",
        "",
        f"  answer overlap  containment {containment:.2f}, jaccard {jaccard:.2f}",
    ]

    if jaccard < 0.3:
        lines.append(
            "  The two answers barely overlap, so most of the difference above is two models citing "
            "different things rather than a scraper fault. Read this as almost nothing."
        )
    else:
        lines.append(
            "  The two answers overlap enough that the api-only column is worth investigating as a "
            "capture gap, though it is still a floor and not a measurement."
        )

    if api_only:
        lines += ["", "  api only, by publisher:"]
        for url in api_only:
            lines.append(f"    {registrable_domain(url):<28} {url[:90]}")
    if dom_only:
        lines += ["", "  dom only:"]
        for url in dom_only:
            lines.append(f"    {registrable_domain(url):<28} {url[:90]}")

    hidden = dom.get("citations_possibly_hidden") or 0
    if hidden:
        lines += [
            "",
            f"  The DOM capture already reported {hidden} citation(s) hidden behind "
            f"{dom.get('expanders_seen') or 0} \"+N\" control(s). That is a known subset, separate from "
            f"anything above.",
        ]

    lines += [
        "",
        "  Not a ground truth. Same question is not same answer: the two were produced by different models "
        "with different retrieval.",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--dom", type=Path, required=True)
    parser.add_argument("--api", type=Path, required=True)
    parser.add_argument("--json", type=Path, default=None)
    args = parser.parse_args(argv)

    dom, api = load(args.dom), load(args.api)
    text = report(dom, api)
    print(text)

    if args.json:
        dom_urls, api_urls = urls_of(dom), urls_of(api)
        containment, jaccard = text_overlap(api.get("answer_text", ""), dom.get("answer_text", ""))
        args.json.write_text(
            json.dumps(
                {
                    "dom_citations": len(dom_urls),
                    "api_citations": len(api_urls),
                    "in_both": sorted(set(dom_urls) & set(api_urls)),
                    "api_only": sorted(set(api_urls) - set(dom_urls)),
                    "dom_only": sorted(set(dom_urls) - set(api_urls)),
                    "answer_containment": round(containment, 4),
                    "answer_jaccard": round(jaccard, 4),
                    "note": "not a ground truth: same question is not same answer",
                },
                indent=2,
            ),
            encoding="utf-8",
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
