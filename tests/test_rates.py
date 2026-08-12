"""Rate tests. Every one of these asserts a refusal, not a calculation.

The arithmetic is three lines and it is not where this can go wrong. What can go wrong is a number getting
printed that the run was not entitled to print, so that is what the tests are about.
"""

from __future__ import annotations

import pathlib

import pytest

from sayswho.claims import Claim, ClaimSet
from sayswho.gates import DenominatorContract
from sayswho.judge import (
    CONTRADICTED,
    EXTRACTION_SUSPECT,
    JUDGE_FABRICATED_SPAN,
    NOT_FOUND_IN_SOURCE,
    PARTIALLY_SUPPORTED,
    SUPPORTED,
    Judgement,
)
from sayswho.rates import (
    ConflictedAggregate,
    INSUFFICIENT_EVIDENCE,
    Pair,
    Rate,
    RateNotPermitted,
    RunRates,
    aggregate,
    claim_level_rate,
    for_run,
    insufficient_evidence,
    pairs_from,
    standing_denominator,
    support_rate,
    unauditable_rate,
    verdict_counts,
    wilson_interval,
)
from sayswho.records import (
    SOURCE_OK,
    SOURCE_PAYWALLED,
    SOURCE_UNREACHABLE,
    Capture,
    Citation,
    FetchRecord,
)


def pair(claim_id, url, code=SOURCE_OK, verdict=SUPPORTED, voided=False, reason=""):
    return Pair(
        claim_id=claim_id, url=url, source_code=code, verdict=verdict, voided=voided, void_reason=reason
    )


# ---------------------------------------------------------------- the unit


def test_the_denominator_is_claim_source_pairs_not_claims():
    """A claim citing three sources contributes three pairs. This is the decision, pinned by a test."""
    pairs = [
        pair("c1", "https://a.example/1"),
        pair("c1", "https://b.example/2", verdict=NOT_FOUND_IN_SOURCE),
        pair("c1", "https://c.example/3", verdict=NOT_FOUND_IN_SOURCE),
    ]
    rate = support_rate(pairs)
    assert (rate.hits, rate.n) == (1, 3)
    assert rate.unit == "claim-source pair"


def test_the_claim_level_rate_reports_the_same_run_in_the_other_unit():
    """Claim #009 in the day 3 run: SUPPORTED by one source, NOT_FOUND_IN_SOURCE by two.

    The two units give different numbers on the same evidence, which is why both are published.
    """
    pairs = [
        pair("c1", "https://a.example/1"),
        pair("c1", "https://b.example/2", verdict=NOT_FOUND_IN_SOURCE),
        pair("c1", "https://c.example/3", verdict=NOT_FOUND_IN_SOURCE),
    ]
    assert support_rate(pairs).value == pytest.approx(1 / 3)
    assert claim_level_rate(pairs).value == 1.0


def test_partially_supported_is_not_counted_as_supported():
    pairs = [pair("c1", "https://a.example/1", verdict=PARTIALLY_SUPPORTED)]
    assert support_rate(pairs).hits == 0
    assert verdict_counts(pairs) == {PARTIALLY_SUPPORTED: 1}


# ---------------------------------------------------------------- the denominator contract


def test_an_unauditable_pair_cannot_enter_the_denominator():
    """Break attempt 6, at the pair level. `gates.auditable_denominator` guards the source-level count."""

    class Contaminated(Pair):
        @property
        def standing(self) -> bool:
            return True

    bad = Contaminated(claim_id="c1", url="https://a.example/1", source_code=SOURCE_PAYWALLED)
    with pytest.raises(DenominatorContract) as exc:
        standing_denominator([bad])
    assert "cannot enter a denominator" in str(exc.value)


def test_a_voided_verdict_cannot_enter_the_denominator():
    class Contaminated(Pair):
        @property
        def standing(self) -> bool:
            return True

    bad = Contaminated(
        claim_id="c1", url="https://a.example/1", source_code=SOURCE_OK,
        verdict=SUPPORTED, voided=True, void_reason=JUDGE_FABRICATED_SPAN,
    )
    with pytest.raises(DenominatorContract) as exc:
        standing_denominator([bad])
    assert "no verdict" in str(exc.value)


def test_a_voided_verdict_is_not_counted_as_unsupported():
    """The failure this is here to prevent: a fabricated span quietly becoming evidence against a product."""
    pairs = [
        pair("c1", "https://a.example/1"),
        pair("c2", "https://b.example/2", verdict=SUPPORTED, voided=True, reason=JUDGE_FABRICATED_SPAN),
    ]
    rate = support_rate(pairs)
    assert (rate.hits, rate.n) == (1, 1)


def test_an_extraction_failure_lands_in_the_unauditable_rate_not_the_unsupported_count():
    """`FINDINGS.md` item 11. A page we could not read is not a citation that failed."""
    pairs = [
        pair("c1", "https://a.example/1"),
        pair(
            "c2", "https://b.example/2", verdict=NOT_FOUND_IN_SOURCE, voided=True,
            reason=EXTRACTION_SUSPECT,
        ),
    ]
    assert support_rate(pairs).n == 1
    assert unauditable_rate(pairs).hits == 1


# ---------------------------------------------------------------- INSUFFICIENT_EVIDENCE


def test_more_than_half_unauditable_withholds_the_rate():
    pairs = [
        pair("c1", "https://a.example/1"),
        pair("c2", "https://b.example/2", code=SOURCE_PAYWALLED, verdict=""),
        pair("c3", "https://c.example/3", code=SOURCE_UNREACHABLE, verdict=""),
    ]
    assert insufficient_evidence(pairs)


def test_exactly_half_is_still_insufficient():
    """A rate over half an answer is a rate over whatever happened to be readable. The boundary is inclusive."""
    pairs = [
        pair("c1", "https://a.example/1"),
        pair("c2", "https://b.example/2", code=SOURCE_PAYWALLED, verdict=""),
    ]
    assert insufficient_evidence(pairs)


def test_a_mostly_readable_answer_is_not_withheld():
    pairs = [
        pair("c1", "https://a.example/1"),
        pair("c2", "https://b.example/2"),
        pair("c3", "https://c.example/3", code=SOURCE_PAYWALLED, verdict=""),
    ]
    assert not insufficient_evidence(pairs)


def test_a_claim_measured_by_one_of_its_sources_counts_as_measured():
    pairs = [
        pair("c1", "https://a.example/1"),
        pair("c1", "https://b.example/2", code=SOURCE_PAYWALLED, verdict=""),
    ]
    assert not insufficient_evidence(pairs)


# ---------------------------------------------------------------- intervals


def test_every_rate_carries_an_interval_and_its_n():
    rate = support_rate([pair("c1", "https://a.example/1")])
    assert rate.n == 1
    lo, hi = rate.interval_95
    assert 0.0 <= lo <= hi <= 1.0
    assert "n=1" in rate.render()
    assert "95% CI" in rate.render()


def test_a_wilson_interval_stays_inside_zero_and_one_at_the_extremes():
    """The reason it is Wilson and not the normal approximation: 3 of 3 at n=3 is where that one breaks."""
    lo, hi = wilson_interval(3, 3)
    assert lo > 0.0
    assert hi <= 1.0


def test_an_empty_rate_says_so_rather_than_dividing_by_zero():
    rate = support_rate([])
    assert rate.value is None
    assert "no claim-source pairs" in rate.render()


def test_a_rate_states_how_many_splits_it_is_over():
    """Phase 1 does not return the same split twice, so a rate over one split is a rate over one sample."""
    rate = support_rate([pair("c1", "https://a.example/1")], splits=1)
    assert "over 1 split" in rate.render()
    assert rate.to_dict()["splits"] == 1


def test_the_interval_field_is_not_called_confidence_interval():
    """The no-confidence-number gate walks keys, and it must not need an exception list to pass."""
    from sayswho.gates import assert_no_confidence_number

    assert_no_confidence_number(support_rate([pair("c1", "https://a.example/1")]).to_dict())


# ---------------------------------------------------------------- the conflict guard


def capture_for(product):
    return Capture(
        query_id="PR-01",
        product=product,
        model_id="test",
        generated_at="2026-08-11T00:00:00+00:00",
        captured_at="2026-08-11T00:00:01+00:00",
        answer_text="A claim [1].",
        citations=[Citation(marker="[1]", url="https://a.example/1")],
    )


def test_a_google_product_cannot_enter_a_cross_product_aggregate():
    """A Gemini judge scoring a Google surface is a vendor grading its own homework.

    Disclosure in prose does not survive being copied into a slide, so the refusal is in the code.
    """
    runs = [
        RunRates(product="chatgpt", query_id="PR-01", pairs=[pair("c1", "https://a.example/1")]),
        RunRates(product="google", query_id="PR-02", pairs=[pair("c2", "https://b.example/2")]),
    ]
    with pytest.raises(ConflictedAggregate) as exc:
        aggregate(runs)
    assert "vendor scoring its own product" in str(exc.value)


def test_the_same_google_run_still_reports_per_product():
    """Excluded from the aggregate, not deleted. The evidence is kept and the conflict is stated beside it."""
    run = for_run(
        capture_for("google"),
        ClaimSet(claims=[Claim(id="c1", text="A claim.", markers=["[1]"], urls=["https://a.example/1"])], skipped=[]),
        [FetchRecord(url="https://a.example/1", code=SOURCE_OK, fetched_at="2026-08-11T00:00:02+00:00")],
        [Judgement(claim_id="c1", url="https://a.example/1", verdict=SUPPORTED, span_verified=True)],
    )
    d = run.to_dict()
    assert d["conflicted"] is True
    assert "vendor scoring its own product" in d["conflict_reason"]
    assert any(r["name"] == "citation support rate" for r in d["rates"])


def test_an_aggregate_over_a_withheld_run_is_refused():
    runs = [
        RunRates(product="chatgpt", query_id="PR-01", pairs=[pair("c1", "https://a.example/1")]),
        RunRates(
            product="claude", query_id="PR-02", pairs=[pair("c2", "https://b.example/2")],
            withheld=[f"{INSUFFICIENT_EVIDENCE}: most of this answer was unreadable"],
        ),
    ]
    with pytest.raises(RateNotPermitted):
        aggregate(runs)


# ---------------------------------------------------------------- end to end over a run


def test_for_run_withholds_the_support_rate_when_the_judge_is_uncalibrated():
    from sayswho.gates import g4_calibration_exists

    claim_set = ClaimSet(
        claims=[Claim(id="c1", text="A claim.", markers=["[1]"], urls=["https://a.example/1"])],
        skipped=[],
    )
    records = [FetchRecord(url="https://a.example/1", code=SOURCE_OK, fetched_at="2026-08-11T00:00:02+00:00")]
    judgements = [Judgement(claim_id="c1", url="https://a.example/1", verdict=SUPPORTED, span_verified=True)]

    run = for_run(
        capture_for("chatgpt"), claim_set, records, judgements,
        calibration=g4_calibration_exists(None, "GeminiJudge", "m", "judge-v1", "claims-v1", "abc"),
    )
    assert any("NO_CALIBRATION" in w for w in run.withheld)
    assert not any(r.name == "citation support rate" for r in run.rates)


def test_the_fabricated_span_rate_survives_an_uncalibrated_judge():
    """G4 withholds the support rate. How often the judge invented a span is a fact about the judge that a
    gold set is not needed to establish, and it is the finding the project promises to publish."""
    from sayswho.gates import g4_calibration_exists

    claim_set = ClaimSet(
        claims=[Claim(id="c1", text="A claim.", markers=["[1]"], urls=["https://a.example/1"])],
        skipped=[],
    )
    records = [FetchRecord(url="https://a.example/1", code=SOURCE_OK, fetched_at="2026-08-11T00:00:02+00:00")]
    judgements = [
        Judgement(
            claim_id="c1", url="https://a.example/1", verdict=SUPPORTED, voided=True,
            void_reason=JUDGE_FABRICATED_SPAN,
        )
    ]

    run = for_run(
        capture_for("chatgpt"), claim_set, records, judgements,
        calibration=g4_calibration_exists(None, "GeminiJudge", "m", "judge-v1", "claims-v1", "abc"),
    )
    fabricated = next(r for r in run.rates if r.name == "judge-fabricated-span rate")
    assert (fabricated.hits, fabricated.n) == (1, 1)


def test_pairs_are_built_from_the_split_and_not_from_the_judgements():
    """A pair that was never judged still exists. Dropping it would make the unauditable rate uncountable."""
    claim_set = ClaimSet(
        claims=[
            Claim(id="c1", text="A.", markers=["[1]"], urls=["https://a.example/1"]),
            Claim(id="c2", text="B.", markers=["[2]"], urls=["https://b.example/2"]),
        ],
        skipped=[],
    )
    records = [
        FetchRecord(url="https://a.example/1", code=SOURCE_OK, fetched_at="t"),
        FetchRecord(url="https://b.example/2", code=SOURCE_PAYWALLED, fetched_at="t"),
    ]
    pairs = pairs_from(claim_set, records, [])
    assert len(pairs) == 2
    assert sum(1 for p in pairs if p.standing) == 0


# ---------------------------------------------------------------- unpublishable sources


def api_capture(**kw):
    from sayswho.records import Capture, Citation

    defaults = dict(
        query_id="PR-01", product="api:perplexity", model_id="sonar",
        generated_at="2026-08-11T00:00:00+00:00", captured_at="2026-08-11T00:00:01+00:00",
        answer_text="Boston reported high screening participation [1].",
        citations=[Citation(marker="[1]", url="https://a.example/1")],
        source="api",
    )
    defaults.update(kw)
    return Capture(**defaults)


def one_supported_run(capture):
    """A run that would produce a support rate if its source allowed one."""
    from sayswho.claims import Claim, ClaimSet
    from sayswho.records import SOURCE_OK, FetchRecord

    claim = Claim(id="c1", text="Boston reported high screening participation",
                  markers=["[1]"], urls=["https://a.example/1"])
    record = FetchRecord(url="https://a.example/1", code=SOURCE_OK, fetched_at="t", text="x")
    judgement = Judgement(claim_id="c1", url="https://a.example/1", verdict=SUPPORTED,
                          span="x", span_verified=True)
    return for_run(capture, ClaimSet(claims=[claim], skipped=[]), [record], [judgement],
                   calibration=None)


def test_an_api_capture_produces_no_rate_at_all():
    """Decided 2026-08-11 and enforced here rather than in prose. Not even the rates that need no gold set:
    "how often the judge invented a span on an API answer" is still a number about a surface nobody uses."""
    run = one_supported_run(api_capture())

    assert run.rates == []
    assert any("UNPUBLISHABLE_SOURCE" in w for w in run.withheld)
    assert "different model with different retrieval" in " ".join(run.withheld)


def test_the_per_claim_verdicts_survive():
    """The decision is about rates. A verdict is a statement about one document and one sentence."""
    run = one_supported_run(api_capture())

    assert len(run.pairs) == 1
    assert run.pairs[0].verdict == SUPPORTED
    assert run.counts.get(SUPPORTED) == 1


def test_a_dom_capture_is_unaffected():
    run = one_supported_run(api_capture(source="dom", product="perplexity"))
    assert run.rates, "the ordinary path still produces rates"


def test_an_aggregate_over_an_api_run_raises():
    from sayswho.rates import UnpublishableSource

    with pytest.raises(UnpublishableSource) as exc:
        aggregate([one_supported_run(api_capture())])
    assert "different model with different retrieval" in str(exc.value)


def test_there_is_no_override_flag_for_an_unpublishable_source():
    """`allow_conflicted` exists because a conflicted product is still reported per-product with the conflict
    stated. There is no equivalent here, so an escape hatch would only ever be used to defeat the rule."""
    import inspect

    from sayswho.rates import aggregate as aggregate_fn

    params = set(inspect.signature(aggregate_fn).parameters)
    assert not {"allow_api", "allow_unpublishable", "allow_source"} & params


def test_mixing_an_api_run_into_a_dom_aggregate_still_raises():
    """The likely accident: a captures directory with one API capture in it among twenty DOM ones."""
    from sayswho.rates import UnpublishableSource

    runs = [one_supported_run(api_capture(source="dom", product="perplexity")),
            one_supported_run(api_capture())]
    with pytest.raises(UnpublishableSource):
        aggregate(runs)


def test_the_per_domain_slice_is_closed_too():
    """A slice is still a rate. Per-domain builds from pairs directly, so it was the one door left open."""
    source = (pathlib.Path(__file__).resolve().parent.parent / "sayswho" / "harness.py").read_text()
    assert "not in UNPUBLISHABLE_SOURCES" in source
    assert "excluded_from_domains" in source, "and the exclusion is reported, not silent"
