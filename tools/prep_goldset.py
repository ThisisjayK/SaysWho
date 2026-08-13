#!/usr/bin/env python3
"""Get the pages ready before the labelling session, and say what the session will be like.

    python3 tools/prep_goldset.py --split splits/chatgpt.split.json \
        --capture runs/chatgpt.record.json --target 35

Labelling is an hour of irreplaceable human work and it is the one input in this project classified
`your-input`. This runs beforehand, so that hour is spent reading pages and deciding, not waiting on a
fetcher that is politely sleeping a second between requests.

**It draws the same sample the labelling tool will.** Not a similar one: `label_goldset.choose_sample` is
imported rather than reimplemented, so a prep pass cannot warm the cache for pairs the session never shows
you. That failure would be worse than no prep at all, because it would report ready and then stall on exactly
the pairs that mattered.

**It fetches only what is missing, on purpose.** A page already in the cache is left alone even though
re-fetching would be trivial. The labeller's passage is checked against what `extract.py` produced from the
cached bytes, and `goldset.attribution` uses that to decide whether a disagreement belongs to the extractor
or to the judge. Fetching a fresh copy today would silently move that comparison onto a document the judge
never read, which is the same objection `tools/reaudit_spans.py` makes to re-checking spans against the live
web: it answers a different question. Pages fetched here for the first time are listed as such, because for
those the caveat applies and the labeller should know which ones they are.

**What it reports and why each line is there.** Every number below is something that, if wrong, costs the
session rather than announcing itself:

- whether the G2 codes are known at all. They come from a run record passed with `--capture`, and without one
  every pair buckets as `UNKNOWN`, so the stratification across source codes silently does not happen and the
  sample is drawn across products only. `SCOPE.md` §3 Phase 4 asks for `UNAUDITABLE` first, and this is the
  quiet way not to get it;
- how many pairs the extraction check will be able to run for. It needs cached bytes that decode and extract
  to something. Where it cannot run, `extraction_missed` stays unset and that pair can never be attributed to
  the extractor, which is a hole in the one measurement that separates a bad extractor from a bad judge;
- how much there is to read, in characters, because thirty-five pairs over five pages is not the same
  afternoon as thirty-five pairs over thirty;
- what the prior-audit scan says, so `--supplemental` is a decision made now rather than a refusal met at the
  first prompt.

**It never runs the judge and never prints a verdict.** It refuses an input carrying judge output by name,
exactly as the labelling tool does, and `tests/test_prep_goldset.py` asserts no verdict name reaches its
output.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from label_goldset import build_pool, choose_sample, extracted_pair, load_json  # noqa: E402

from sayswho.cache import FetchCache  # noqa: E402
from sayswho.fetch import Fetcher  # noqa: E402
from sayswho.goldset import GoldSet  # noqa: E402
from sayswho.prior_audit import scan as scan_for_prior_audit  # noqa: E402
from sayswho.queryset import freeze_intact  # noqa: E402
from sayswho.records import SOURCE_OK  # noqa: E402
from sayswho.splits import StoredSplit  # noqa: E402


@dataclass
class PageState:
    """One page a labeller will open, and whether the session is ready for it."""

    url: str
    #: Where the bytes came from. `cache` means they were already here, which is the good case.
    origin: str = "missing"
    code: str = ""
    cached_at: str = ""
    extracted_chars: int = 0
    #: True when the labeller's pasted passage can be checked against our extraction for this page. False
    #: means `goldset.attribution` will never be able to blame the extractor for a disagreement here.
    check_available: bool = False
    detail: str = ""


@dataclass
class Preparation:
    pairs: list[dict]
    pages: dict[str, PageState] = field(default_factory=dict)
    codes_known: bool = False
    prior_audit_render: str = ""
    prior_audit_found: bool = False
    already_labelled: int = 0
    fetched_now: list[str] = field(default_factory=list)

    @property
    def unauditable_pairs(self) -> int | None:
        """Pairs whose source this pipeline could not read, or None when no code is known for any of them.

        None rather than zero, and the distinction is the same one the whole project turns on. Without a run
        record every code is the empty string, and counting those as readable would report a clean "0 of 8
        unauditable" for a set of pages nothing has assessed.
        """
        if not self.codes_known:
            return None
        return sum(1 for p in self.pairs if self.pages[p["url"]].code not in ("", SOURCE_OK))

    @property
    def checkable_pairs(self) -> int:
        return sum(1 for p in self.pairs if self.pages[p["url"]].check_available)

    @property
    def total_chars(self) -> int:
        return sum(page.extracted_chars for page in self.pages.values())

    def render(self) -> str:
        lines = [
            "",
            f"session       {len(self.pairs)} pair(s) to label over {len(self.pages)} page(s)",
        ]
        if self.already_labelled:
            lines.append(f"              resuming: {self.already_labelled} label(s) already on disk")

        if not self.codes_known:
            lines += [
                "",
                "NOT STRATIFIED  no --capture was given, so no G2 code is known for any pair and the sample",
                "                buckets on product alone. SCOPE.md section 3 Phase 4 asks for UNAUDITABLE",
                "                first, and without a run record that half of the stratification is skipped",
                "                rather than refused. Pass the run record from the fetch pass.",
            ]

        lines += ["", "pages"]
        for url, page in sorted(self.pages.items()):
            where = {
                "cache": f"cached {page.cached_at[:19] or 'earlier'}",
                "fetched": "fetched just now",
                "missing": "NOT AVAILABLE",
            }[page.origin]
            lines.append(f"  {page.code or 'code unknown':<26} {where:<26} {url}")
            if page.detail:
                lines.append(f"      {page.detail}")

        lines += [
            "",
            f"reading       {self.total_chars:,} characters across {len(self.pages)} page(s), extracted. A",
            "              rough sense of the afternoon rather than a page count: thirty pairs over five",
            "              pages is not the session thirty pairs over thirty pages is",
            "",
        ]
        if self.unauditable_pairs is None:
            lines += [
                "unauditable   not known, because no G2 code is known. Not the same as none: see above",
            ]
        else:
            lines += [
                f"unauditable   {self.unauditable_pairs} of {len(self.pairs)} pair(s) have a source this pipeline could not read.",
                "              Those are the quick ones: the label is U, and the judge was never asked about them",
            ]
        lines += [
            "",
            f"attributable  {self.checkable_pairs} of {len(self.pairs)} pair(s) can have a pasted passage checked against our",
            "              own extraction. The rest cannot be attributed to the extractor at all, so a",
            "              disagreement there lands on the judge whether or not it belongs to it",
        ]

        if self.fetched_now:
            lines += [
                "",
                f"fetched today {len(self.fetched_now)} page(s) had no cached copy and were fetched now. For those the",
                "              extraction check compares against bytes the judge never read, which is a",
                "              weaker claim than for the rest. They are listed above as fetched just now",
            ]

        lines += ["", self.prior_audit_render]
        if self.prior_audit_found:
            lines += [
                "",
                "              Decide this now rather than at the first prompt: the labelling tool will",
                "              refuse a blind session over these answers, and --supplemental is the way",
                "              through. Those labels are excluded from kappa and reported on their own",
            ]
        return "\n".join(lines)


def prepare(splits, captures, cache: FetchCache, target: int, seed: int, out: Path | None,
            fetcher: Fetcher | None, audit_roots=None) -> Preparation:
    """Work out what the session will be, and fill the gaps that can be filled ahead of it."""
    pool = build_pool(splits, captures, cache)

    done: set[tuple[str, str]] = set()
    already = 0
    if out is not None and out.exists():
        prior = GoldSet.load(out)
        done = {(l.claim_id, l.url) for l in prior.labels}
        already = len(prior.labels)

    prep = Preparation(
        pairs=choose_sample(pool, target, seed, done),
        codes_known=any(row["source_code"] for row in pool),
        already_labelled=already,
    )

    audit = scan_for_prior_audit({s.answer_sha256 for s in splits}, roots=audit_roots)
    prep.prior_audit_render = audit.render()
    prep.prior_audit_found = audit.found

    for row in prep.pairs:
        url = row["url"]
        if url in prep.pages:
            continue
        page = PageState(url=url, code=row["source_code"])

        hit = cache.latest(url)
        if hit is None and fetcher is not None:
            # Only ever a cache miss. See the module docstring: a fresh copy of a page we already have would
            # move the extraction check onto a document the judge never read.
            record = fetcher.fetch(url)
            page.code = page.code or record.code
            hit = cache.latest(url)
            if hit is not None:
                page.origin = "fetched"
                prep.fetched_now.append(url)
            else:
                page.detail = f"{record.code}: {record.detail or 'nothing was cached, so nothing can be checked'}"
        elif hit is not None:
            page.origin = "cache"

        if hit is not None:
            page.cached_at = hit[0].get("fetched_at", "")
            pair = extracted_pair(cache, url)
            if pair is not None:
                page.extracted_chars = len(pair[0])
                # Cached bytes are not the same as a document. A 404 body caches and extracts perfectly well
                # to the words "not found", and counting that as a page a passage can be checked against
                # would report a dead link as ready. Where the code is unknown this cannot be ruled out, and
                # the "not stratified" warning above already covers that case.
                readable = page.code in ("", SOURCE_OK)
                page.check_available = bool(pair[0].strip()) and readable
                if not pair[0].strip():
                    page.detail = "cached, and this pipeline extracted nothing from it"
                elif not readable:
                    page.detail = (
                        f"cached, and the source was {page.code}, so what is here is whatever came back "
                        "rather than the document"
                    )
            else:
                page.detail = "cached, and the body could not be decoded, so no check is possible"

        prep.pages[url] = page

    return prep


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--split", type=Path, action="append", required=True,
                        help="a stored split. Repeatable, one per captured answer. The same ones the "
                             "labelling session will be given")
    parser.add_argument("--capture", type=Path, action="append", default=[],
                        help="the run record from the fetch pass, for the G2 codes. Without it the sample "
                             "is not stratified across source codes and this says so")
    parser.add_argument("--cache", type=Path, default=Path(".cache/fetch"))
    parser.add_argument("--out", type=Path, default=None,
                        help="the gold set the session will write to. Given, a resumed session is prepared "
                             "from where it stopped rather than from the beginning")
    parser.add_argument("--target", type=int, default=35, help="must match the session's --target")
    parser.add_argument("--seed", type=int, default=20260812, help="must match the session's --seed")
    parser.add_argument("--audit-scan", type=Path, action="append", default=None,
                        help="where to look for an earlier audit of these answers. Defaults to reports/ "
                             "and runs/, as the labelling tool does")
    parser.add_argument("--no-fetch", action="store_true",
                        help="report only. Says what the session would be without sending a request")
    parser.add_argument("--skip-freeze-check", action="store_true",
                        help="run without checking the query freeze. This tool fetches, and every fetching "
                             "path in this project checks the freeze first")
    args = parser.parse_args(argv)

    if not args.no_fetch and not args.skip_freeze_check:
        intact, why = freeze_intact()
        if not intact:
            print("FREEZE CHECK FAILED. Refusing to fetch.")
            print()
            print(why)
            return 2

    splits = [StoredSplit.load(p) for p in args.split]
    captures = [load_json(p) for p in args.capture]
    cache = FetchCache(args.cache)
    fetcher = None if args.no_fetch else Fetcher(cache)

    prep = prepare(splits, captures, cache, args.target, args.seed, args.out, fetcher,
                   audit_roots=args.audit_scan)
    if not prep.pairs:
        print("no pairs to label. Either the splits hold no cited claims, or the gold set is already full.",
              file=sys.stderr)
        return 2

    print(prep.render())
    print()
    if args.no_fetch:
        print("--no-fetch: nothing was requested, so any page listed as NOT AVAILABLE is still missing.")
    else:
        print(f"requests    {len(fetcher.requested)} sent, one per second per domain, robots.txt honoured.")
    print("Nothing here has run the judge or opened a verdict.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
