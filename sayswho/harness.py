"""The headless run over a frozen stratum, and the numbers it is entitled to publish.

`SCOPE.md` §9: the same pipeline runnable headlessly over the frozen query set, so the honest run produces a
terminal transcript. §12 day 7: metric readout with n and confidence intervals, plausibility audit, per-number
trace table.

This module runs the pipeline (`pipeline.py`, the same one the CLI drives) over every capture bound to a
frozen query, then assembles the readout. It computes no rate itself. Every number comes from `rates.py`,
which is where the denominators and the refusals live, and the harness's own job is the part that is easy
to get quietly wrong: which runs are allowed into an aggregate, and what the reader is told about the ones
that were not.

**What it refuses.** A broken query freeze halts the whole run. An unbound capture is audited and its
verdicts are printed, and it is excluded from every aggregate, because a rate has to be able to say what it
is a rate over. A product whose vendor supplies the judge is reported on its own. A stratum where more than
half the pairs went unmeasured prints `INSUFFICIENT_EVIDENCE` instead of a number.

**The trace table.** Rubric row three, and the reason it is generated rather than written: a table typed by
hand next to numbers produced by code is a table that describes the numbers it described on the day it was
typed.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .cache import FetchCache, now_iso
from .claims import CLAIM_PROMPT_VERSION
from .drift import DriftChecker
from .fetch import Fetcher, user_agent
from .gates import (
    GateResult,
    assert_no_confidence_number,
    g0_has_citations,
    g4_calibration_exists,
)
from .judge import JUDGE_PROMPT_VERSION
from .pipeline import fetch_sources, judge_claims, phase1
from .queryset import binding, freeze_intact, stratum_of
from .domains import by_domain
from .domains import render as render_domains
from .rates import (
    UNPUBLISHABLE_SOURCES,
    pairs_from,
    CONFLICTED_PRODUCTS,
    ConflictedAggregate,
    RateNotPermitted,
    aggregate,
    for_run,
)
from .records import Capture
from .skips import analyse as analyse_skips
from .splits import split_digest


class FreezeBroken(Exception):
    """The query set on disk no longer matches what was frozen. Nothing runs."""


@dataclass
class CaptureRun:
    """One audited answer and everything downstream of it."""

    path: Path
    capture: Capture
    bound: Any
    records: list = field(default_factory=list)
    drifts: list = field(default_factory=list)
    claim_set: Any = None
    judgements: list = field(default_factory=list)
    rates: Any = None
    split_sha256: str = ""
    error: str = ""
    halted: str = ""

    @property
    def eligible_for_aggregate(self) -> bool:
        """Bound to a frozen query, judged, and not from a product whose vendor supplies the judge."""
        return (
            not self.error
            and self.bound.ok
            and self.rates is not None
            and self.capture.product not in CONFLICTED_PRODUCTS
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "capture": str(self.path),
            "query_id": self.capture.query_id if self.capture else "",
            "product": self.capture.product if self.capture else "",
            "answer_sha256": self.capture.answer_sha256 if self.capture else "",
            "split_sha256": self.split_sha256,
            "binding": {"ok": self.bound.ok, "code": self.bound.code, "detail": self.bound.detail},
            "sources": [r.to_dict() for r in self.records],
            "claims": self.claim_set.to_dict() if self.claim_set else None,
            "skips": analyse_skips(self.claim_set).to_dict() if self.claim_set else None,
            "judgements": [j.to_dict() for j in self.judgements],
            "rates": self.rates.to_dict() if self.rates else None,
            "eligible_for_aggregate": self.eligible_for_aggregate,
            "error": self.error,
            "halted": self.halted,
        }


@dataclass
class StratumRun:
    """A whole run: every capture, the aggregate if one is permitted, and the reasons if not."""

    started_at: str
    runs: list[CaptureRun] = field(default_factory=list)
    stratum: str = ""
    judge_class: str = ""
    judge_model: str = ""
    aggregate_rate: Any = None
    aggregate_refused: str = ""
    per_product: dict[str, Any] = field(default_factory=dict)
    #: `SCOPE.md` §0a item 9. One row per publisher, counted in claim-source pairs, gated by G4 exactly as
    #: the aggregate is. A diagnostic about this pipeline before it is anything about a publisher.
    per_domain: list = field(default_factory=list)
    #: Sources whose captures were kept out of the per-domain table, with the reason. An absence a reader
    #: cannot see the shape of is worse than a number.
    excluded_from_domains: list = field(default_factory=list)
    agreement: Any = None
    attribution: Any = None
    goldset_path: str = ""
    metering: dict[str, Any] = field(default_factory=dict)
    finished_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "generated_by": "SaysWho",
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "stratum": self.stratum,
            "judge_class": self.judge_class,
            "judge_model": self.judge_model,
            "judge_prompt_version": JUDGE_PROMPT_VERSION,
            "claim_prompt_version": CLAIM_PROMPT_VERSION,
            "user_agent": user_agent(),
            "goldset": self.goldset_path,
            "runs": [r.to_dict() for r in self.runs],
            "aggregate": self.aggregate_rate.to_dict() if self.aggregate_rate else None,
            "aggregate_refused": self.aggregate_refused,
            "per_product": {k: v.to_dict() for k, v in self.per_product.items()},
            "agreement": self.agreement.to_dict() if self.agreement else None,
            "attribution": self.attribution.to_dict() if self.attribution else None,
            "metering": self.metering,
        }


def run_stratum(
    capture_paths: list[Path],
    *,
    cache_dir: Path = Path(".cache/fetch"),
    judge: bool = False,
    provider: str | None = None,
    budget: int = 2_000_000,
    drift: bool = True,
    use_cache: bool = True,
    splits: dict[str, Path] | None = None,
    goldset_path: Path | None = None,
    skip_freeze_check: bool = False,
    on_event=lambda *a, **k: None,
) -> StratumRun:
    """Audit every capture given, then assemble what the stratum is entitled to publish."""
    if not skip_freeze_check:
        intact, why = freeze_intact()
        if not intact:
            raise FreezeBroken(why)

    from .goldset import GoldSet, agreement as compute_agreement, attribution as compute_attribution

    started = now_iso()
    run = StratumRun(started_at=started)
    gold = GoldSet.load(goldset_path) if goldset_path else None
    run.goldset_path = str(goldset_path) if goldset_path else ""

    client = None
    meter = None
    if judge:
        from .gemini import build_judge
        from .model import Meter

        meter = Meter(budget_tokens=budget)
        client = build_judge(provider, meter=meter)
        run.judge_class = type(client).__name__
        run.judge_model = client.model

    fetcher = Fetcher(FetchCache(cache_dir))
    checker = DriftChecker(fetcher) if drift else None

    for path in capture_paths:
        on_event("capture", path=path)
        try:
            capture = Capture.from_json(path)
        except Exception as exc:
            run.runs.append(
                CaptureRun(path=path, capture=None, bound=binding(_Unbound()), error=str(exc))
            )
            continue

        item = CaptureRun(path=path, capture=capture, bound=binding(capture))
        run.runs.append(item)
        if not run.stratum and item.bound.ok:
            run.stratum = stratum_of(capture.query_id)

        gate0 = g0_has_citations(capture)
        if not gate0.passed:
            item.error = f"{gate0.code}: {gate0.detail}"
            on_event("g0_failed", run=item)
            continue

        for record, drift_record in fetch_sources(capture, fetcher, checker, use_cache=use_cache):
            item.records.append(record)
            item.drifts.append(drift_record)
            on_event("source", run=item, record=record, drift=drift_record)

        if not judge or not any(r.auditable for r in item.records):
            on_event("no_judge", run=item)
            continue

        from .model import BudgetExceeded

        item.claim_set, _ = phase1(capture, client, split_path=(splits or {}).get(capture.query_id))
        item.split_sha256 = split_digest(item.claim_set.claims)
        on_event("phase1", run=item)

        try:
            for judgement in judge_claims(item.claim_set, item.records, item.drifts, client):
                item.judgements.append(judgement)
                on_event("judgement", run=item, judgement=judgement)
        except BudgetExceeded as exc:
            item.halted = str(exc)
            on_event("halted", run=item, detail=str(exc))

        item.calibration = g4_calibration_exists(
            gold, run.judge_class, run.judge_model, JUDGE_PROMPT_VERSION,
            CLAIM_PROMPT_VERSION, item.split_sha256,
        )
        item.rates = for_run(
            capture, item.claim_set, item.records, item.judgements,
            drifts=item.drifts,
            split_sha256=item.split_sha256,
            splits=1,
            calibration=item.calibration,
        )
        on_event("rates", run=item)

    # The aggregate, and the reason there is not one. An absent number invites a reader to compute their own.
    eligible = [r.rates for r in run.runs if r.eligible_for_aggregate]
    excluded = [r for r in run.runs if not r.eligible_for_aggregate]
    if not eligible:
        run.aggregate_refused = (
            "No run is eligible for an aggregate. "
            + "; ".join(
                f"{r.path.name}: " + (r.error or (r.bound.detail if not r.bound.ok else "not judged"))
                for r in excluded
            )
        )
    else:
        try:
            run.aggregate_rate = aggregate(eligible)
        except (ConflictedAggregate, RateNotPermitted) as exc:
            run.aggregate_refused = str(exc)

    # Per-product, always, including the products excluded from the aggregate. Excluded is not deleted.
    by_product: dict[str, list] = {}
    for item in run.runs:
        if item.rates is not None:
            by_product.setdefault(item.capture.product, []).append(item.rates)
    # Per-domain, over every pair in the stratum. Built from the same Pair objects the rates are, so the
    # slice and the aggregate cannot disagree about what a denominator is.
    # An unpublishable source is excluded here too. `for_run` already withholds its rates, and per-domain
    # builds from pairs directly, so without this the slice would be the one door left open to a rate the
    # aggregate refuses. A slice is still a rate.
    every_pair = [
        pair
        for item in run.runs
        if item.claim_set is not None
        and getattr(item.capture, "source", "dom") not in UNPUBLISHABLE_SOURCES
        for pair in pairs_from(item.claim_set, item.records, item.judgements)
    ]
    excluded_sources = sorted(
        {
            getattr(item.capture, "source", "dom")
            for item in run.runs
            if getattr(item.capture, "source", "dom") in UNPUBLISHABLE_SOURCES
        }
    )
    if every_pair:
        # A per-domain rate spans several captures, so it is calibrated only if every contributing run was.
        # One uncalibrated run in the stratum withholds every domain rate, which is the same rule the
        # aggregate follows rather than a stricter one invented here.
        refusals = sorted(
            {
                item.calibration.detail
                for item in run.runs
                if item.calibration is not None and not item.calibration.passed
            }
        )
        combined = GateResult(
            passed=not refusals,
            code="" if not refusals else "G4_NO_CALIBRATION",
            detail="; ".join(refusals),
        )
        run.per_domain = by_domain(every_pair, calibration=combined)
    run.excluded_from_domains = [UNPUBLISHABLE_SOURCES[s] for s in excluded_sources]

    for product, rate_list in by_product.items():
        try:
            run.per_product[product] = aggregate(rate_list, allow_conflicted=True)
        except RateNotPermitted:
            # A product where one answer withheld its rate reports no product-level number either.
            continue

    if gold is not None:
        judgements = [j for item in run.runs for j in item.judgements]
        run.agreement = compute_agreement(gold, judgements, judge_run_started_at=started)
        run.attribution = compute_attribution(gold, judgements)

    if meter is not None:
        run.metering = meter.to_dict()
    run.finished_at = now_iso()
    return run


class _Unbound:
    """Stand-in for a capture that would not parse, so the binding check has something to answer about."""

    query_id = ""


# ------------------------------------------------------------------ the readout


def readout(run: StratumRun) -> str:
    """The metric readout, `SCOPE.md` §5 and §12 day 7. Every rate with its n and its interval."""
    lines: list[str] = []
    add = lines.append

    add("=" * 96)
    add(f"SaysWho run: {run.stratum or 'unbound captures'}   started {run.started_at}")
    add(f"judge        {run.judge_class} {run.judge_model}")
    add(f"versions     {JUDGE_PROMPT_VERSION}, {CLAIM_PROMPT_VERSION}")
    add(f"gold set     {run.goldset_path or 'none labelled for this configuration'}")
    add("=" * 96)
    add("")

    add(f"captures     {len(run.runs)}")
    for item in run.runs:
        state = "ok"
        if item.error:
            state = item.error
        elif not item.bound.ok:
            state = item.bound.code
        elif item.halted:
            state = f"HALTED {item.halted}"
        add(f"  {item.path.name:<40} {item.capture.product if item.capture else '?':<12} {state}")
    add("")

    if run.aggregate_rate is not None:
        add("STRATUM RATE")
        add(f"  {run.aggregate_rate.render()}")
        add(f"  {run.aggregate_rate.note}")
    else:
        add("STRATUM RATE  withheld")
        for line in (run.aggregate_refused or "no reason recorded").split("; "):
            add(f"  {line}")
    add("")

    if run.per_product:
        add("PER PRODUCT")
        for product, rate in sorted(run.per_product.items()):
            add(f"  {product:<12} {rate.render()}")
            if product in CONFLICTED_PRODUCTS:
                add(f"               conflict: {CONFLICTED_PRODUCTS[product]}")
                add("               reported here only, never in the stratum rate above")
        add("")

    if run.excluded_from_domains:
        add("PER DOMAIN  partly excluded")
        for reason in run.excluded_from_domains:
            add(f"  {reason}")
        add("")

    if run.per_domain:
        add("PER DOMAIN")
        for line in render_domains(run.per_domain).split("\n")[1:]:
            add(line)
        add("")

    add("PER ANSWER")
    for item in run.runs:
        if item.rates is None:
            continue
        add(f"  {item.capture.query_id}  {item.capture.product}  split {item.split_sha256[:12]}")
        for rate in item.rates.rates:
            add(f"    {rate.render()}")
        for withheld in item.rates.withheld:
            add(f"    withheld: {withheld}")
        add(f"    verdicts: {item.rates.counts}")
    add("")

    if run.agreement is not None:
        add("JUDGE AGAINST HUMAN")
        for line in run.agreement.render().split("\n"):
            add(f"  {line}")
        if run.attribution is not None:
            for line in run.attribution.render().split("\n"):
                add(f"  {line}")
    else:
        add("JUDGE AGAINST HUMAN  not measured")
        add("  No gold set for this judge and prompt version. Gate G4 withholds every rate that depends on")
        add("  the judge being calibrated, and the per-claim verdicts above stand on their own.")
    add("")

    if run.metering:
        add(f"metering     {run.metering}")
    add("")
    add("Every rate above is single-stratum. It is not a rate for AI citations generally.")
    return "\n".join(lines)


TRACE_HEADER = (
    "| Published figure | Value | n | Unit | Comes from | Over which records |\n"
    "|---|---|---|---|---|---|"
)


def trace_table(run: StratumRun) -> str:
    """Every published figure traced to the record it came from. Rubric row three.

    Generated rather than typed. A hand-written trace table describes the numbers that existed on the day
    it was written, and this project's numbers have already moved twice.
    """
    rows: list[str] = []

    def row(name, rate, comes_from, over):
        value = f"{rate.value:.1%}" if rate.value is not None else "withheld"
        interval = ""
        if rate.interval_95:
            lo, hi = rate.interval_95
            interval = f" ({lo:.1%} to {hi:.1%})"
        rows.append(
            f"| {name} | {value}{interval} | {rate.n} | {rate.unit} | `{comes_from}` | {over} |"
        )

    if run.aggregate_rate is not None:
        over = ", ".join(
            f"{r.capture.query_id} split `{r.split_sha256[:12]}`"
            for r in run.runs if r.eligible_for_aggregate
        )
        row("Citation support rate, stratum", run.aggregate_rate, "rates.aggregate", over)

    for product, rate in sorted(run.per_product.items()):
        over = ", ".join(
            r.capture.query_id for r in run.runs if r.capture and r.capture.product == product
        )
        row(f"Support rate, {product}", rate, "rates.aggregate(allow_conflicted=True)", over)

    for item in run.runs:
        if item.rates is None:
            continue
        for rate in item.rates.rates:
            over = f"{item.path.name}, {len(item.records)} source(s), split `{item.split_sha256[:12]}`"
            row(f"{rate.name} ({item.capture.query_id})", rate, f"rates.{_fn_for(rate.name)}", over)

    if run.agreement is not None:
        a = run.agreement
        kappa = f"{a.kappa:.3f}" if a.kappa is not None else "not computable"
        interval = ""
        if a.kappa_interval_95:
            lo, hi = a.kappa_interval_95
            interval = f" ({lo:.3f} to {hi:.3f})"
        rows.append(
            f"| Judge-human agreement (kappa) | {kappa}{interval} | {a.compared} | blind label | "
            f"`goldset.cohens_kappa` | {run.goldset_path} |"
        )

    if not rows:
        return (
            TRACE_HEADER
            + "\n| (none) | | | | | No figure was published, so there is nothing to trace. |"
        )
    return TRACE_HEADER + "\n" + "\n".join(rows)


def _fn_for(name: str) -> str:
    return {
        "citation support rate": "support_rate",
        "citation support rate, counted in claims": "claim_level_rate",
        "unauditable rate": "unauditable_rate",
        "judge-fabricated-span rate": "fabricated_span_rate",
        "source drift rate": "drift_rate",
    }.get(name, "for_run")


def run_log(run: StratumRun) -> str:
    """`RUN_LOG.md`, the Phase 5 deliverable in `SCOPE.md` §3."""
    parts = [
        f"## Run {run.started_at}",
        "",
        f"- stratum: {run.stratum or 'unbound captures'}",
        f"- judge: {run.judge_class} {run.judge_model}, {JUDGE_PROMPT_VERSION}, {CLAIM_PROMPT_VERSION}",
        f"- gold set: {run.goldset_path or 'none'}",
        f"- user agent: {user_agent()}",
        f"- captures: {len(run.runs)}",
        f"- finished: {run.finished_at}",
        "",
        "### Metric readout",
        "",
        "```",
        readout(run),
        "```",
        "",
        "### Per-number trace",
        "",
        trace_table(run),
        "",
    ]
    return "\n".join(parts)


def save(run: StratumRun, directory: Path) -> dict[str, Path]:
    """Write the run's three artefacts and return where they went."""
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)

    payload = run.to_dict()
    # The gate walks keys over exactly what is about to be written, not over a sample of it.
    from .report import strip_for_gate_check

    assert_no_confidence_number(strip_for_gate_check(payload))

    written = {}
    written["json"] = directory / "run.json"
    written["json"].write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    written["readout"] = directory / "readout.txt"
    written["readout"].write_text(readout(run) + "\n", encoding="utf-8")

    written["log"] = directory / "RUN_LOG.md"
    written["log"].write_text(run_log(run), encoding="utf-8")

    written["trace"] = directory / "TRACE.md"
    written["trace"].write_text(trace_table(run) + "\n", encoding="utf-8")
    return written
