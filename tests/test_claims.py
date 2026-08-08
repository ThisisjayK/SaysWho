"""Claim splitting and gate G1."""

from __future__ import annotations

import pytest

from sayswho.claims import split_claims
from sayswho.model import BudgetExceeded, Meter, ModelCall
from sayswho.records import Capture, Citation


class FakeSplitter:
    def __init__(self, reply):
        self.reply = reply
        self.calls: list[dict] = []

    def complete_json(self, **kwargs):
        self.calls.append(kwargs)
        return self.reply


def capture():
    return Capture(
        query_id="PR-01",
        product="chatgpt",
        model_id="test",
        generated_at="2026-08-08T00:00:00+00:00",
        captured_at="2026-08-08T00:00:01+00:00",
        answer_text="Give feedback\n\nBoston screening rates are roughly equal. Navigation helps.",
        citations=[
            Citation(marker="PubMed", url="https://pubmed.ncbi.nlm.nih.gov/34767089/?utm_source=chatgpt.com"),
            Citation(marker="Cancer.gov", url="https://www.cancer.gov/v?id=NCI-2021-00403"),
        ],
    )


def test_claims_are_bound_to_the_urls_their_markers_point_at():
    splitter = FakeSplitter({
        "claims": [
            {"text": "Boston screening rates are roughly equal.", "markers": ["PubMed"]},
        ],
        "skipped": [],
    })
    result = split_claims(capture(), splitter)

    assert len(result.claims) == 1
    assert result.claims[0].urls == ["https://pubmed.ncbi.nlm.nih.gov/34767089/"], (
        "tracking parameters are stripped, so the claim points at the page the fetcher will get"
    )


def test_marker_matching_ignores_whitespace_and_case():
    splitter = FakeSplitter({
        "claims": [{"text": "A claim.", "markers": ["pubmed"]}],
        "skipped": [],
    })
    assert split_claims(capture(), splitter).claims[0].is_cited


def test_a_claim_whose_marker_matches_nothing_stays_uncited_rather_than_guessed_at():
    splitter = FakeSplitter({
        "claims": [{"text": "A claim.", "markers": ["SomeOtherSource"]}],
        "skipped": [],
    })
    result = split_claims(capture(), splitter)

    assert result.claims[0].urls == []
    assert result.uncited_count == 1


def test_skipped_lines_are_counted_and_kept_not_dropped():
    """G1. A system that quietly discards what it cannot handle is lying by omission."""
    splitter = FakeSplitter({
        "claims": [{"text": "Boston screening rates are roughly equal.", "markers": ["PubMed"]}],
        "skipped": [
            {"text": "Give feedback", "reason": "interface text captured with the answer"},
            {"text": "Navigation helps.", "reason": "recommendation, not a factual claim"},
        ],
    })
    result = split_claims(capture(), splitter)

    assert len(result.skipped) == 2
    assert result.to_dict()["skipped_count"] == 2
    assert [s.code for s in result.skipped] == ["NOT_A_FACTUAL_CLAIM"] * 2
    assert result.skipped[0].reason, "a skip without a reason is a silent drop with extra steps"


def test_the_answer_goes_in_the_cached_block_so_repeat_calls_are_cheap():
    splitter = FakeSplitter({"claims": [], "skipped": []})
    split_claims(capture(), splitter)

    assert "Boston screening rates" in splitter.calls[0]["cached_context"]
    assert splitter.calls[0]["prompt_version"] == "claims-v1"


# ---------------------------------------------------------------- the meter


def test_the_budget_cap_halts_the_run_and_records_that_it_halted():
    """DATA_CONTRACT.md §8. A truncated run reported as complete puts a wrong denominator under every rate."""
    meter = Meter(budget_tokens=1000)
    meter.record(ModelCall(at="x", purpose="judge", model="claude-opus-5", prompt_version="judge-v1",
                           input_tokens=900, output_tokens=200))

    with pytest.raises(BudgetExceeded):
        meter.check()

    assert meter.halted
    assert "budget cap" in meter.halt_reason
    assert meter.to_dict()["halted"] is True


def test_cost_is_estimated_from_the_model_that_actually_answered():
    meter = Meter()
    call = meter.record(ModelCall(at="x", purpose="judge", model="claude-opus-5",
                                  prompt_version="judge-v1", input_tokens=1_000_000, output_tokens=0))
    assert call.cost_usd == pytest.approx(5.00)


def test_an_unknown_model_costs_zero_rather_than_guessing():
    meter = Meter()
    call = meter.record(ModelCall(at="x", purpose="judge", model="some-other-model",
                                  prompt_version="v", input_tokens=1_000_000, output_tokens=1_000_000))
    assert call.cost_usd == 0.0, "an invented price is worse than an absent one"
