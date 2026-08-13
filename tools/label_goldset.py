#!/usr/bin/env python3
"""Label a gold set by hand, blind, before the judge has said anything.

    python3 tools/label_goldset.py --split runs/PR-01.split.json --capture captures/PR-01.json \
        --out goldset/PR-01.gold.json --target 35

`SCOPE.md` §3 Phase 4 and §12 day 5. The labels are the one field in the project classified `your-input`,
and everything this tool does is in service of them being worth that classification.

**What it refuses to do.** It will not open a file containing judge output, and it checks rather than trusts:
an input carrying a `verdict`, `judgements` or `void_reason` key is rejected by name. Labelling with the
judge's answer visible in another window is still possible and no tool can prevent it, but the tool will not
be the thing that puts it there.

**And it will not start a blind session over an answer that has already been audited.** That is a separate
refusal with a separate failure behind it, and until it existed the two guards above both missed it: an
answer judged last week leaves a report on disk, a fresh split of it carries a different `split_sha256`, and
G4 compares hashes rather than answers. So the session runs, the labels say blind, and nothing raises.
`sayswho/prior_audit.py` scans `reports/` and `runs/` for a verdict over the same `answer_sha256` and this
tool exits 3 rather than asking the first question. The way through is `--supplemental`, which is not a
weaker version of blind: those labels are excluded from kappa and reported on their own.

**How the sample is chosen.** Round-robin across products and then across G2 source codes, from a shuffle
with a recorded seed, so the selection is reproducible and was not steered by hand toward interesting pairs.

`SCOPE.md` §3 also asks for stratification across verdict classes, filling `CONTRADICTED` and `UNAUDITABLE`
first. Only half of that is possible blind. `UNAUDITABLE` is deterministic, known from the G2 code before any
model runs, so it is stratified on. The verdict classes are the judge's output, so a blind sample cannot be
stratified on them at all, and a sample that were would not be blind. If `CONTRADICTED` comes back empty the
answer is a supplement labelled afterwards, entered with `--supplemental`, excluded from kappa and reported
on its own. See `sayswho/goldset.py`.

**What it asks for besides the label.** The passage the labeller found, in the page's own words. Two reasons.
A label with no passage behind it is an opinion, and the judge is held to a quoted span so the human should
be too. And a passage lets a script separate an extractor failure from a judge failure: if the labeller's
passage is on the page and missing from what `extract.py` produced, the resulting disagreement belongs to
this tool's extraction layer rather than to the judge, and `goldset.attribution` reports it that way.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sayswho.cache import FetchCache, now_iso  # noqa: E402
from sayswho.extract import extract_text, raw_text  # noqa: E402
from sayswho.fetch import decode_body  # noqa: E402
from sayswho.goldset import LABELS, UNAUDITABLE, UNDECIDABLE, GoldLabel, GoldSet, coverage  # noqa: E402
from sayswho.judge import JUDGE_PROMPT_VERSION, span_is_present  # noqa: E402
from sayswho.prior_audit import JUDGE_KEYS, scan as scan_for_prior_audit  # noqa: E402
from sayswho.records import SOURCE_OK, Capture  # noqa: E402
from sayswho.splits import StoredSplit  # noqa: E402

#: `JUDGE_KEYS` is imported rather than restated. One module owns what judge output looks like in a file, and
#: it holds both rules: presence for refusing an input here, a truthy value for the prior-audit scan. They are
#: different tests of the same list and keeping the list in two places is how they would stop being that.


class NotBlind(Exception):
    """Raised when an input file carries judge output."""


def refuse_judge_output(payload, path) -> None:
    """Walk a loaded file and refuse it if a judge key appears anywhere in it."""

    def walk(node):
        if isinstance(node, dict):
            for key, value in node.items():
                if str(key) in JUDGE_KEYS:
                    raise NotBlind(
                        f"{path} contains a {key!r} field, so it carries judge output. A gold set labelled "
                        "with the judge's answer in view is not a blind gold set. Pass the stored split and "
                        "the capture, not a run record."
                    )
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(payload)


def load_json(path: Path):
    with open(path, "rb") as fh:
        payload = json.load(fh)
    refuse_judge_output(payload, path)
    return payload


def extracted_pair(cache: FetchCache, url: str) -> tuple[str, str] | None:
    """What this tool extracted from the cached copy of a page, and the permissive version of it.

    Cache only, deliberately. Labelling is not a fetch pass, and a labelling session should not be sending
    requests to the sources while a person reads them.
    """
    hit = cache.latest(url)
    if hit is None:
        return None
    meta, body = hit
    decoded, _ = decode_body(body, meta.get("headers", {}))
    if decoded is None:
        return None
    markup = decoded.decode("utf-8", errors="replace")
    return extract_text(markup), raw_text(markup)


def build_pool(splits, captures, cache) -> list[dict]:
    """Every (claim, source) pair available to label, with the facts known before any model runs."""
    codes: dict[str, str] = {}
    for payload in captures:
        for row in payload.get("fetches", []):
            codes[row["url"]] = row.get("code", "")

    pool = []
    for split in splits:
        for claim in split.claims:
            for url in claim.urls:
                pool.append(
                    {
                        # Which split this pair came from, so the saved set records the answers it actually
                        # holds a label for rather than the ones the sampler was handed.
                        "split_sha256": split.split_sha256,
                        "claim_id": claim.id,
                        "text": claim.text,
                        "markers": claim.markers,
                        "url": url,
                        "product": split.product,
                        "query_id": split.query_id,
                        "source_code": codes.get(url, ""),
                    }
                )
    return pool


def stratify(pool: list[dict], target: int, seed: int) -> list[dict]:
    """Round-robin across products, then across G2 codes, from a seeded shuffle.

    Reproducible from the seed, which is recorded in the output. A sample picked by scrolling a list and
    choosing interesting rows is not a sample.
    """
    rng = random.Random(seed)
    buckets: dict[tuple[str, str], list[dict]] = {}
    for row in pool:
        buckets.setdefault((row["product"], row["source_code"] or "UNKNOWN"), []).append(row)
    for rows in buckets.values():
        rng.shuffle(rows)

    # Unauditable codes first, so the class that is knowable before the judge runs is the one that gets
    # filled rather than the one that gets left to chance. SCOPE.md §3 Phase 4.
    order = sorted(buckets, key=lambda k: (k[1] == SOURCE_OK, k[0], k[1]))
    picked: list[dict] = []
    while len(picked) < target and any(buckets[k] for k in order):
        for key in order:
            if not buckets[key]:
                continue
            picked.append(buckets[key].pop())
            if len(picked) >= target:
                break
    return picked


def choose_sample(pool: list[dict], target: int, seed: int, done=frozenset()) -> list[dict]:
    """The pairs a session will actually put in front of a labeller, resumed sessions included.

    Split out so `tools/prep_goldset.py` can prepare the same pairs this tool is about to ask about. A prep
    pass that warmed the cache for a different sample would be worse than none: it would report the session
    as ready and leave the labeller waiting on the network for the pairs that mattered, which is the failure
    that makes an hour of human work evaporate.

    `done` is what a resumed session has already labelled. The over-draw and the slice together mean a second
    session picks up where the first stopped rather than redrawing from scratch.
    """
    return [
        row for row in stratify(pool, target + len(done), seed)
        if (row["claim_id"], row["url"]) not in done
    ][: max(0, target - len(done))]


class NoLabeller(Exception):
    """Raised when there is nobody at the keyboard. Not an error: a session that cannot happen."""


def ask(prompt: str, options: tuple[str, ...] | None = None) -> str:
    """Read one answer, or raise NoLabeller when input has run out.

    EOF is the normal case rather than a broken one: it means this was launched without a terminal, from a
    Run button or a pipe. The labels are the one field classified `your-input` and no amount of tooling
    substitutes for a person, so the honest response is to say so and stop rather than emit a traceback that
    looks like the tool is broken.
    """
    while True:
        try:
            answer = input(prompt).strip()
        except EOFError as exc:
            raise NoLabeller("no input available") from exc
        except KeyboardInterrupt as exc:
            raise NoLabeller("interrupted") from exc
        if options is None or answer in options:
            return answer
        print(f"  one of: {', '.join(options)}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--split", type=Path, action="extend", nargs="+", required=True,
                        help="a stored split. Repeatable, one per captured answer")
    parser.add_argument("--capture", type=Path, action="extend", nargs="+", default=[],
                        help="a run record holding the fetch results, for the G2 codes. Repeatable")
    parser.add_argument("--cache", type=Path, default=Path(".cache/fetch"))
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--target", type=int, default=35, help="how many pairs to label. SCOPE.md §0a: 30 to 40")
    parser.add_argument("--seed", type=int, default=20260812, help="recorded in the output, so the sample is reproducible")
    parser.add_argument("--labeller", default="jayanth")
    parser.add_argument("--judge-model", default="gemini-3.5-flash-lite",
                        help="the judge this set will be valid for. Gate G4 ties the two together")
    parser.add_argument("--judge-class", default="GeminiJudge")
    parser.add_argument("--supplemental", action="store_true",
                        help="label a supplement after seeing verdicts. These are excluded from kappa and "
                             "reported on their own, because a sample chosen using the judge's output is "
                             "not an agreement measurement")
    parser.add_argument("--plan", action="store_true", help="print the sample and exit, labelling nothing")
    parser.add_argument(
        "--audit-scan", type=Path, action="append", default=None,
        help="where to look for an earlier audit of these answers. Repeatable. Defaults to reports/ and "
             "runs/, which is where the server and the harness write. There is no flag to skip the scan: a "
             "prior audit is answered with --supplemental, not with an override",
    )
    args = parser.parse_args(argv)

    splits = [StoredSplit.load(p) for p in args.split]
    captures = [load_json(p) for p in args.capture]
    cache = FetchCache(args.cache)

    if len({s.split_sha256 for s in splits}) != len(splits):
        print("two of the given splits are identical. Pass one per captured answer.", file=sys.stderr)
        return 2

    pool = build_pool(splits, captures, cache)
    if not pool:
        print("no claim-source pairs in these splits. Nothing to label.", file=sys.stderr)
        return 2

    # Before anything is printed about the sample, and long before the first question. A refusal that arrives
    # after a labeller has read three claims has already cost them the blindness it was protecting.
    prior_audit = scan_for_prior_audit({s.answer_sha256 for s in splits}, roots=args.audit_scan)
    print()
    print(prior_audit.render())
    if prior_audit.found and not args.supplemental and not args.plan:
        print()
        print("A blind label written now would not be blind. The verdicts for this answer already exist on")
        print("disk, so labelling it and calling the result agreement measures nothing: a labeller who has")
        print("seen them cannot unsee them, and this tool cannot tell whether you have.")
        print()
        print("Two ways forward, and neither is an override:")
        print("  1. label a different answer, one that has never been judged. --split-only makes the split")
        print("  2. rerun with --supplemental. Those labels carry blind: false, they are excluded from kappa,")
        print("     and they are reported on their own, which is the honest thing they can still be")
        print()
        print("There is no flag to skip this check, for the same reason rates.py has no override for an")
        print("API-sourced rate: a decision that lives in a flag is one a tired person overrides at 2am.")
        return 3
    if prior_audit.found and args.plan and not args.supplemental:
        # --plan writes nothing, so it is allowed to continue. Saying so is not the same as passing.
        print()
        print("  --plan labels nothing, so it continues. A blind session here would be refused.")

    existing: list[GoldLabel] = []
    labelled_splits: set[str] = set()
    if args.out.exists():
        prior = GoldSet.load(args.out)
        existing = prior.labels
        labelled_splits = set(prior.split_sha256s)
        print(f"resuming: {len(existing)} label(s) already in {args.out}")
    done = {(l.claim_id, l.url) for l in existing}
    sample = choose_sample(pool, args.target, args.seed, done)

    if args.plan:
        print(f"{len(pool)} pairs available, {len(sample)} selected, seed {args.seed}")
        for row in sample:
            print(f"  {row['product']:<10} {row['source_code'] or 'UNKNOWN':<24} {row['claim_id']}  {row['url']}")
        return 0

    print()
    # It used to say "nothing here has been judged yet", which is a claim about the world rather than about
    # this process, and it was false the first time anyone read it: every capture on disk had already been
    # audited. Then it said this tool had opened no file containing a verdict, which the prior-audit scan made
    # false in turn: the scan opens exactly those files. What is true of both is that neither shows you one.
    print(f"{len(sample)} pairs to label. No verdict has been shown to you here: an input carrying judge")
    print("output is refused by name, and the scan above reads reports without printing what is in them.")
    if args.supplemental:
        print("These labels are SUPPLEMENTAL: they carry blind: false, they are excluded from kappa, and")
        print("they are reported on their own. Use this whenever the verdicts for this answer already")
        print("exist, whether or not you believe you have read them.")
    else:
        print("Recorded as blind. The scan above checked the artefacts on disk and found none for these")
        print("answers. It cannot see what you have read, so this is still partly a claim about you: if a")
        print("verdict for this answer exists somewhere it could not look, rerun with --supplemental.")
    print()
    print("For each pair: open the URL, read the page, and say whether it supports the claim.")
    print("Labels: S supported, P partially, N not found in source, C contradicted,")
    print("        U source unreadable (paywall, dead, not English), ? undecidable, q save and quit")
    print()

    keys = {"S": "SUPPORTED", "P": "PARTIALLY_SUPPORTED", "N": "NOT_FOUND_IN_SOURCE",
            "C": "CONTRADICTED", "U": UNAUDITABLE, "?": UNDECIDABLE}

    labels = list(existing)
    for n, row in enumerate(sample, start=1):
        print("-" * 100)
        print(f"[{n}/{len(sample)}]  {row['product']}  {row['query_id']}  {row['claim_id']}")
        print(f"  source code (this tool's): {row['source_code'] or 'not fetched'}")
        print(f"  url:    {row['url']}")
        print()
        print(f"  claim:  {' '.join(row['text'].split())}")
        print()

        try:
            choice = ask("  label [S/P/N/C/U/?/q]: ", tuple(keys) + ("q",))
        except NoLabeller as stop:
            print()
            print(f"  stopped: {stop}. Labelling needs a person at a terminal, so run this in a shell")
            print(f"  rather than through anything that pipes input. {len(labels)} label(s) kept.")
            break
        if choice == "q":
            break

        value = keys[choice]
        passage = ""
        missed = None
        if value in ("SUPPORTED", "PARTIALLY_SUPPORTED", "CONTRADICTED"):
            passage = ask("  paste the passage you found (blank to skip): ")
            if passage:
                pair = extracted_pair(cache, row["url"])
                if pair is not None:
                    text, raw = pair
                    if span_is_present(passage, text):
                        missed = False
                    elif span_is_present(passage, raw):
                        missed = True
                        print("  noted: that passage is on the page and missing from what this tool")
                        print("         extracted. The disagreement, if any, is the extractor's.")
                    else:
                        print("  noted: that passage is in neither the extracted text nor the raw markup.")
                        print("         Recorded as unchecked rather than as an extraction failure.")

        notes = ask("  notes (optional): ")
        labelled_splits.add(row["split_sha256"])
        labels.append(
            GoldLabel(
                claim_id=row["claim_id"],
                url=row["url"],
                label=value,
                labelled_at=now_iso(),
                labeller=args.labeller,
                blind=not args.supplemental,
                notes=notes,
                human_span=passage,
                extraction_missed=missed,
            )
        )

        # Written after every label. A labelling session is an hour of irreplaceable human work and it is
        # not going to be lost to a terminal closing.
        GoldSet(
            split_sha256s=sorted(labelled_splits),
            judge_class=args.judge_class,
            judge_model=args.judge_model,
            judge_prompt_version=JUDGE_PROMPT_VERSION,
            claim_prompt_version=splits[0].claim_prompt_version,
            created_at=now_iso(),
            labels=labels,
            labeller=args.labeller,
            note=(
                f"Sampled with seed {args.seed} across products and G2 source codes. Verdict-class "
                "stratification is not possible in a blind sample; see tools/label_goldset.py. "
                f"Prior-audit scan: {prior_audit.summary()}."
            ),
        ).save(args.out)

    print()
    if not labels:
        # The file is written after each label, so quitting at the first prompt leaves nothing on disk and
        # the coverage summary below has nothing to load. Opening the tool to see what it asks for, and
        # quitting, is a reasonable thing to do and used to end in a traceback under the words "saved 0
        # label(s)", which reads like the save is what failed.
        print(f"no labels written, so {args.out} was not created. Nothing was lost.")
        return 0

    print(f"saved {len(labels)} label(s) to {args.out}")
    counts = coverage(GoldSet.load(args.out))
    print("coverage by class, published whatever it says:")
    for name in LABELS:
        print(f"  {name:<22} {counts.get(name, 0)}")
    empty = [n for n in ("SUPPORTED", "NOT_FOUND_IN_SOURCE", "CONTRADICTED") if not counts.get(n)]
    if empty:
        print()
        print(f"  empty: {', '.join(empty)}. A class the set never contains cannot be calibrated.")
        print("  Either report it empty, or add a supplement with --supplemental and report it separately.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
