"""Published rates, their denominators, and the two gates that stop a number being printed.

Nothing in this module estimates anything. Every value is a count over records divided by a count over
records, and every one of them carries the things `SCOPE.md` §5 promises: its n, an interval, the unit it is
counted in, and how many splits it is over.

**The unit is the claim-source pair.** Decided here rather than left implicit, because a claim citing three
sources produces three judgements and the two available units give different numbers. The pair is the unit
because it is the question the tool exists to answer: does *this* cited page say what *this* sentence claims
it says. It is also the unit a human labels in, since a labeller reads one claim against one page, so the
gold set and the rate are counted the same way and the agreement number is over the same objects.

What that costs, stated rather than discovered: a claim citing five sources weighs five times as much in the
rate as a claim citing one. `claim_level_rate` reports the other unit alongside it, and the writeup carries
both rather than picking the flattering one.

**Why the interval field is not called `confidence_interval`.** The no-confidence-number gate in `gates.py`
walks keys and rejects any containing "confidence". A confidence interval is a different object from a
confidence score, so the honest options were to weaken the gate or to rename the field. The gate stays blunt
and the field is `interval_95`. A gate with an exception list is a gate that will eventually be argued past.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

from .judge import (
    CONTRADICTED,
    NOT_FOUND_IN_SOURCE,
    PARTIALLY_SUPPORTED,
    SUPPORTED,
)
from .records import AUDITABLE_CODES

#: The unit every headline rate is counted in.
UNIT_PAIR = "claim-source pair"
UNIT_CLAIM = "claim"
UNIT_SOURCE = "source"

#: More than half an answer's cited claims had no verdict that stands. No rate is printed for that answer.
#: A rate over the surviving minority is a rate over whatever happened to be readable, which is a different
#: measurement wearing the same label.
INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"

#: Products whose results may never enter a cross-product aggregate, and why.
#:
#: The default judge is Gemini, so a Google surface is being scored by its own vendor's model. Disclosure in
#: prose is not enough on its own, because an aggregate silently carries the conflict into every number
#: derived from it. So the conflict is enforced here: these products report per-product with the conflict
#: stated beside them, and `aggregate` refuses to include them.
CONFLICTED_PRODUCTS = {
    "google": "the default judge is a Google model, so this is a vendor scoring its own product",
    "google_aio": "the default judge is a Google model, so this is a vendor scoring its own product",
    "gemini": "the default judge is a Google model, so this is a vendor scoring its own product",
}


#: Capture sources whose results may never become a published rate, and why.
#:
#: An API answer is produced by a different model with different retrieval from the one a person sees in the
#: product, and `SCOPE.md` §1 says this tool audits products. Decided on 2026-08-11 and enforced here rather
#: than in prose, for the same reason `CONFLICTED_PRODUCTS` is enforced here: a rule that lives only in a
#: document is one a tired person overrides on day 7 without noticing they did.
#:
#: Per-claim verdicts from an API capture are untouched. Those are statements about one document and one
#: sentence. A rate is a claim about a product.
UNPUBLISHABLE_SOURCES = {
    "api": (
        "this capture came from a provider API, which is a different model with different retrieval from "
        "the product a person uses. Per-claim verdicts stand; no rate derived from it is published. "
        "SCOPE.md §7"
    ),
}


class UnpublishableSource(Exception):
    """Raised when something asks for a rate over a capture whose source may not produce one."""


class ConflictedAggregate(Exception):
    """Raised when a conflicted product's results are folded into a cross-product aggregate."""


class RateNotPermitted(Exception):
    """Raised when something asks for an aggregate rate that a gate has refused."""


def wilson_interval(hits: int, n: int, z: float = 1.959963984540054) -> tuple[float, float] | None:
    """A 95% interval for a proportion, by the Wilson score method. None when n is zero.

    Wilson rather than the textbook normal approximation because the samples here are small and often near
    0 or 1, which is exactly where the normal approximation returns bounds outside [0, 1] and reads as
    precision that is not there.
    """
    if n <= 0:
        return None
    p = hits / n
    denominator = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denominator
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denominator
    return (max(0.0, centre - half), min(1.0, centre + half))


@dataclass(frozen=True)
class Rate:
    """One published number, with everything a reader needs to judge it attached.

    Never constructed with a bare float. A rate without its n is a claim without evidence, and the point of
    keeping the counts in the object is that nothing downstream can print the percentage without them.
    """

    name: str
    hits: int
    n: int
    unit: str
    #: How many Phase 1 splits this is counted over. Phase 1 is a model call and does not return the same
    #: split twice, so a rate derived from one split is a rate over one sample of the answer. `FINDINGS.md`
    #: item 8. Zero means the number does not come from a split at all, such as a source-level rate.
    splits: int = 0
    split_sha256: str = ""
    note: str = ""

    @property
    def value(self) -> float | None:
        return self.hits / self.n if self.n else None

    @property
    def interval_95(self) -> tuple[float, float] | None:
        return wilson_interval(self.hits, self.n)

    def render(self) -> str:
        """The only formatting of a rate anywhere in the project, so no surface can print a bare percentage."""
        if not self.n:
            return f"{self.name}: no {self.unit}s, so there is no rate"
        lo, hi = self.interval_95
        splits = ""
        if self.splits:
            splits = f", over {self.splits} split" + ("s" if self.splits != 1 else "")
        return (
            f"{self.name}: {self.hits} of {self.n} {self.unit}s "
            f"({self.value:.1%}, 95% CI {lo:.1%} to {hi:.1%}, n={self.n}{splits})"
        )

    def to_dict(self) -> dict[str, Any]:
        interval = self.interval_95
        return {
            "name": self.name,
            "hits": self.hits,
            "n": self.n,
            "unit": self.unit,
            "value": self.value,
            # Not `confidence_interval`: see the module docstring.
            "interval_95": list(interval) if interval else None,
            "splits": self.splits,
            "split_sha256": self.split_sha256,
            "note": self.note,
            "rendered": self.render(),
        }


@dataclass
class Pair:
    """One claim judged against one cited source. The unit of the support rate.

    `standing` is the whole of the arithmetic: a voided verdict is not a weaker verdict, it is no verdict,
    so it leaves the numerator and the denominator together.
    """

    claim_id: str
    url: str
    source_code: str
    verdict: str = ""
    voided: bool = False
    void_reason: str = ""

    @property
    def source_auditable(self) -> bool:
        return self.source_code in AUDITABLE_CODES

    @property
    def standing(self) -> bool:
        return self.source_auditable and bool(self.verdict) and not self.voided


def pairs_from(claim_set, records, judgements) -> list[Pair]:
    """Every (claim, cited source) pair in a run, judged or not.

    Pairs with no judgement are kept. A claim whose source was unreachable is a pair that exists and could
    not be measured, and dropping it here would make the unauditable rate uncountable.
    """
    by_url = {r.url: r for r in records}
    judged: dict[tuple[str, str], Any] = {}
    for j in judgements or []:
        judged[(j.claim_id, j.url)] = j

    out: list[Pair] = []
    for claim in claim_set.claims:
        for url in claim.urls:
            record = by_url.get(url)
            match = judged.get((claim.id, url))
            out.append(
                Pair(
                    claim_id=claim.id,
                    url=url,
                    source_code=record.code if record else "",
                    verdict=match.verdict if match else "",
                    voided=bool(match.voided) if match else False,
                    void_reason=match.void_reason if match else "",
                )
            )
    return out


def standing_denominator(pairs: list[Pair]) -> int:
    """The one place a support-rate denominator is computed.

    Same reasoning as `gates.auditable_denominator`, which counts sources: one function, so a denominator
    computed anywhere else in the codebase would have to bypass it deliberately rather than by accident.
    """
    from .gates import DenominatorContract

    for pair in pairs:
        if pair.standing and not pair.source_auditable:
            raise DenominatorContract(
                f"{pair.claim_id} against {pair.url} has source code {pair.source_code} and is counted as "
                "standing. An unauditable pair cannot enter a denominator."
            )
        if pair.standing and pair.voided:
            raise DenominatorContract(
                f"{pair.claim_id} against {pair.url} was voided as {pair.void_reason} and is counted as "
                "standing. A voided verdict is not a weaker verdict, it is no verdict."
            )
    return sum(1 for p in pairs if p.standing)


def insufficient_evidence(pairs: list[Pair]) -> bool:
    """True when more than half the cited claims in an answer have no verdict that stands.

    Counted in claims rather than in pairs on purpose. The question this answers is "how much of this answer
    could be checked at all", and a reader thinks in sentences. A claim counts as measured if any one of its
    cited sources produced a verdict that stands.
    """
    by_claim: dict[str, bool] = {}
    for pair in pairs:
        by_claim[pair.claim_id] = by_claim.get(pair.claim_id, False) or pair.standing
    if not by_claim:
        return True
    measured = sum(1 for ok in by_claim.values() if ok)
    return measured * 2 <= len(by_claim)


def support_rate(pairs: list[Pair], splits: int = 1, split_sha256: str = "") -> Rate:
    """`SUPPORTED / standing claim-source pairs`.

    `PARTIALLY_SUPPORTED` is not in the numerator. It is reported separately by `verdict_counts`, because
    folding it in would be a judgement call about how much support counts as support, made silently inside
    an arithmetic function.
    """
    n = standing_denominator(pairs)
    hits = sum(1 for p in pairs if p.standing and p.verdict == SUPPORTED)
    return Rate(
        name="citation support rate",
        hits=hits,
        n=n,
        unit=UNIT_PAIR,
        splits=splits,
        split_sha256=split_sha256,
        note=(
            "SUPPORTED over claim-source pairs whose verdict stands. Unauditable sources and voided "
            "verdicts are excluded from the denominator, never counted as unsupported."
        ),
    )


def claim_level_rate(pairs: list[Pair], splits: int = 1, split_sha256: str = "") -> Rate:
    """The same run counted in claims, so a reader can see what the choice of unit did.

    A claim counts as supported if any cited source supports it. Reported alongside the pair rate and never
    instead of it: this unit hides disagreement, and claim #009 in the day 3 run was SUPPORTED by one source
    and NOT_FOUND_IN_SOURCE by two.
    """
    standing: dict[str, list[Pair]] = {}
    for pair in pairs:
        if pair.standing:
            standing.setdefault(pair.claim_id, []).append(pair)
    hits = sum(1 for rows in standing.values() if any(p.verdict == SUPPORTED for p in rows))
    return Rate(
        name="citation support rate, counted in claims",
        hits=hits,
        n=len(standing),
        unit=UNIT_CLAIM,
        splits=splits,
        split_sha256=split_sha256,
        note=(
            "Secondary figure. A claim counts as supported if any one cited source supports it, so this "
            "number cannot show a claim whose sources disagreed."
        ),
    )


def unauditable_rate(pairs: list[Pair], splits: int = 1, split_sha256: str = "") -> Rate:
    """Pairs that could not be measured, over all pairs.

    `SCOPE.md` §5: a high value is a finding about the web, not a tool failure. It is also partly a finding
    about this tool's extractor, which is why `EXTRACTION_SUSPECT` voids into this number rather than into
    the unsupported count.
    """
    n = len(pairs)
    hits = sum(1 for p in pairs if not p.standing)
    return Rate(
        name="unauditable rate",
        hits=hits,
        n=n,
        unit=UNIT_PAIR,
        splits=splits,
        split_sha256=split_sha256,
        note=(
            "Pairs with no verdict that stands: source unreadable, verdict voided, or never judged. "
            "Includes this tool's own extraction failures, which are not a fact about the citation."
        ),
    )


def fabricated_span_rate(judgements, splits: int = 1, split_sha256: str = "") -> Rate:
    """How often the judge quoted something that is not on the page it was given.

    A finding about the judge, published rather than fixed quietly. `SCOPE.md` §3 gate G3.
    """
    from .judge import JUDGE_FABRICATED_SPAN, SPAN_REQUIRED

    eligible = [j for j in judgements or [] if j.verdict in SPAN_REQUIRED]
    hits = sum(1 for j in eligible if j.void_reason == JUDGE_FABRICATED_SPAN)
    return Rate(
        name="judge-fabricated-span rate",
        hits=hits,
        n=len(eligible),
        unit="span-bearing verdict",
        splits=splits,
        split_sha256=split_sha256,
        note="A finding about the judge, not a bug that was fixed quietly.",
    )


def drift_rate(drifts) -> Rate:
    """Share of cited pages that differ from their archived copy.

    Sources with no snapshot are excluded from the denominator rather than counted as unchanged. Converting
    missing data into a clean result is the move this project refuses.
    """
    from .drift import DRIFT_NO_SNAPSHOT, DRIFT_NOT_CHECKED

    known = [
        d for d in (drifts or [])
        if d.status not in (DRIFT_NO_SNAPSHOT, DRIFT_NOT_CHECKED)
    ]
    hits = sum(1 for d in known if d.status == "DRIFT_PAGE_CHANGED")
    unknown = sum(1 for d in (drifts or []) if d.status == DRIFT_NO_SNAPSHOT)
    return Rate(
        name="source drift rate",
        hits=hits,
        n=len(known),
        unit=UNIT_SOURCE,
        note=(
            f"{unknown} source(s) had no archived snapshot and are excluded from this denominator rather "
            "than counted as unchanged."
        ),
    )


def verdict_counts(pairs: list[Pair]) -> dict[str, int]:
    """Every verdict class and every void reason, counted. Nothing is collapsed."""
    out: dict[str, int] = {}
    for pair in pairs:
        if not pair.source_auditable:
            key = pair.source_code or "NOT_FETCHED"
        elif not pair.verdict:
            key = "NOT_JUDGED"
        elif pair.voided:
            key = f"VOID:{pair.void_reason}"
        else:
            key = pair.verdict
        out[key] = out.get(key, 0) + 1
    return out


@dataclass
class RunRates:
    """Every rate one run is entitled to publish, plus the reasons any of them are withheld."""

    product: str
    query_id: str
    #: Where the capture came from. `dom` is a rendered page; `api` is a provider API, which may not produce
    #: a published rate. Carried here so `aggregate` can refuse without being handed the capture.
    source: str = "dom"
    pairs: list[Pair] = field(default_factory=list)
    rates: list[Rate] = field(default_factory=list)
    withheld: list[str] = field(default_factory=list)
    counts: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "product": self.product,
            "query_id": self.query_id,
            "conflicted": self.product in CONFLICTED_PRODUCTS,
            "conflict_reason": CONFLICTED_PRODUCTS.get(self.product, ""),
            "rates": [r.to_dict() for r in self.rates],
            "withheld": self.withheld,
            "verdict_counts": self.counts,
        }


def for_run(
    capture,
    claim_set,
    records,
    judgements,
    drifts=None,
    split_sha256: str = "",
    splits: int = 1,
    calibration=None,
) -> RunRates:
    """Everything one answer is entitled to publish, with the gates already applied.

    `calibration` is a `GateResult` from `gates.g4_calibration_exists`. When it has not passed, the rates
    that depend on a calibrated judge are withheld and the reason is carried in the record rather than left
    for a reader to infer from an absence.
    """
    pairs = pairs_from(claim_set, records, judgements)
    run = RunRates(
        product=capture.product,
        query_id=capture.query_id,
        source=getattr(capture, "source", "dom"),
        pairs=pairs,
        counts=verdict_counts(pairs),
    )

    # Before any rate is computed, not after. An unpublishable source withholds every rate including the
    # ones that do not depend on the judge, because "how often the judge invented a span on an API answer"
    # is still a number about a surface nobody uses.
    if run.source in UNPUBLISHABLE_SOURCES:
        run.withheld.append(f"UNPUBLISHABLE_SOURCE: {UNPUBLISHABLE_SOURCES[run.source]}")
        return run

    # Rates that do not depend on the judge being calibrated. How often the judge invented a span is a fact
    # about the judge that a gold set is not needed to establish, and drift is a fact about the web.
    run.rates.append(fabricated_span_rate(judgements, splits=splits, split_sha256=split_sha256))
    run.rates.append(drift_rate(drifts))
    run.rates.append(unauditable_rate(pairs, splits=splits, split_sha256=split_sha256))

    if insufficient_evidence(pairs):
        run.withheld.append(
            f"{INSUFFICIENT_EVIDENCE}: more than half this answer's cited claims produced no verdict that "
            "stands, so a support rate over the remainder would be a rate over whatever happened to be "
            "readable rather than over the answer."
        )
        return run

    if calibration is not None and not calibration.passed:
        run.withheld.append(f"{calibration.code}: {calibration.detail}")
        return run

    run.rates.append(support_rate(pairs, splits=splits, split_sha256=split_sha256))
    run.rates.append(claim_level_rate(pairs, splits=splits, split_sha256=split_sha256))
    return run


def aggregate(runs: list[RunRates], allow_conflicted: bool = False) -> Rate:
    """The support rate across several answers.

    Refuses to include a product whose vendor also supplies the judge. The refusal is here rather than in
    the writeup because prose disclosure does not survive being copied into a slide, and an aggregate
    carries the conflict into every number derived from it.
    """
    # No override parameter, deliberately. `allow_conflicted` exists because a conflicted product is still
    # reported per-product with the conflict stated beside it, which is a real and useful thing to publish.
    # There is no equivalent for an API capture: the decision is that no rate comes from one, so an escape
    # hatch here would only ever be used to defeat it.
    unpublishable = sorted({r.source for r in runs if r.source in UNPUBLISHABLE_SOURCES})
    if unpublishable:
        raise UnpublishableSource(
            "cannot aggregate: " + "; ".join(UNPUBLISHABLE_SOURCES[s] for s in unpublishable)
        )

    conflicted = [r.product for r in runs if r.product in CONFLICTED_PRODUCTS]
    if conflicted and not allow_conflicted:
        raise ConflictedAggregate(
            f"{sorted(set(conflicted))} cannot enter a cross-product aggregate: "
            f"{CONFLICTED_PRODUCTS[conflicted[0]]}. Report it per-product with the conflict stated."
        )

    pairs = [p for run in runs for p in run.pairs]
    if any(run.withheld for run in runs):
        raise RateNotPermitted(
            "one or more runs withheld their support rate, so an aggregate over them would be an "
            "aggregate over the runs that happened to be measurable: "
            + "; ".join(w for run in runs for w in run.withheld)
        )
    rate = support_rate(pairs, splits=len(runs))
    return Rate(
        name="citation support rate, stratum",
        hits=rate.hits,
        n=rate.n,
        unit=UNIT_PAIR,
        splits=len(runs),
        note=(
            f"Over {len(runs)} answer(s), one stored split each. Single-stratum: this is not a rate for AI "
            "citations generally."
        ),
    )
