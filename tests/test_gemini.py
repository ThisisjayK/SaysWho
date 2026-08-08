"""The Gemini judge.

Offline. The SDK is stubbed at the client boundary, because what these tests check is the behaviour around
the call: that a refusal is a refusal rather than a verdict, that a truncated answer is voided rather than
half-parsed, that a rate limit is waited out rather than dropping a claim, and that every call reaches the
meter. None of that needs a live model, and a live model could not be made to refuse on cue anyway.
"""

from __future__ import annotations

import json
import sys
import types as pytypes

import pytest

from sayswho.model import Meter, ModelRefused


class FakeUsage:
    def __init__(self, prompt=100, candidates=20, cached=0):
        self.prompt_token_count = prompt
        self.candidates_token_count = candidates
        self.cached_content_token_count = cached


class FakeCandidate:
    def __init__(self, finish="STOP"):
        self.finish_reason = f"FinishReason.{finish}"


class FakeResponse:
    def __init__(self, text="{}", finish="STOP", usage=None, model_version="gemini-2.5-flash"):
        self.text = text
        self.candidates = [FakeCandidate(finish)]
        self.usage_metadata = usage or FakeUsage()
        self.model_version = model_version


class FakeModels:
    def __init__(self, script):
        self.script = list(script)
        self.calls: list[dict] = []

    def generate_content(self, *, model, contents, config):
        self.calls.append({"model": model, "contents": contents, "config": config})
        item = self.script.pop(0) if self.script else FakeResponse()
        if isinstance(item, Exception):
            raise item
        return item


def build(script, monkeypatch, **kwargs):
    """Construct a GeminiJudge whose SDK client is the fake above."""
    from sayswho.gemini import GeminiJudge

    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    slept: list[float] = []
    judge = GeminiJudge.__new__(GeminiJudge)
    judge.client = pytypes.SimpleNamespace(models=FakeModels(script))
    judge.model = "gemini-2.5-flash"
    judge.meter = kwargs.get("meter") or Meter()
    judge.max_output_tokens = kwargs.get("max_output_tokens", 8000)
    judge.max_retries = kwargs.get("max_retries", 5)
    judge._sleep = slept.append
    judge.rate_limit_waits = 0.0
    return judge, slept


SCHEMA = {"type": "object", "properties": {"verdict": {"type": "string"}}, "required": ["verdict"]}


def call(judge):
    return judge.complete_json(
        system="you judge claims", cached_context="<document>the page</document>",
        question="judge this", schema=SCHEMA, purpose="judge", prompt_version="judge-v1", subject="c1",
    )


# ---------------------------------------------------------------- the happy path


def test_a_normal_answer_is_parsed_and_metered(monkeypatch):
    judge, _ = build([FakeResponse(text=json.dumps({"verdict": "SUPPORTED"}))], monkeypatch)

    assert call(judge) == {"verdict": "SUPPORTED"}
    assert len(judge.meter.calls) == 1
    assert judge.meter.calls[0].prompt_version == "judge-v1"
    assert judge.meter.calls[0].subject == "c1"


def test_the_free_tier_costs_nothing_but_the_tokens_are_still_recorded(monkeypatch):
    """A free run still has to be able to say how much work it did."""
    judge, _ = build([FakeResponse(text='{"verdict":"SUPPORTED"}', usage=FakeUsage(50_000, 400))], monkeypatch)
    call(judge)

    logged = judge.meter.calls[0]
    assert logged.cost_usd == 0.0, "no price is published for this model, so none is invented"
    assert logged.input_tokens == 50_000 and logged.output_tokens == 400


def test_the_document_goes_first_so_the_shared_prefix_stays_shared(monkeypatch):
    judge, _ = build([FakeResponse(text="{}")], monkeypatch)
    call(judge)

    contents = judge.client.models.calls[0]["contents"]
    assert contents[0].startswith("<document>")
    assert contents[1] == "judge this"


def test_the_pipeline_schema_is_passed_through_unchanged(monkeypatch):
    """Both judges are asked the same question, or the gold set calibrates nothing."""
    judge, _ = build([FakeResponse(text="{}")], monkeypatch)
    call(judge)

    config = judge.client.models.calls[0]["config"]
    assert config.response_json_schema == SCHEMA
    assert config.response_mime_type == "application/json"


# ---------------------------------------------------------------- refusals and truncation


@pytest.mark.parametrize("reason", ["SAFETY", "PROHIBITED_CONTENT", "BLOCKLIST", "RECITATION"])
def test_a_declined_answer_is_a_refusal_not_a_verdict(monkeypatch, reason):
    judge, _ = build([FakeResponse(text="", finish=reason)], monkeypatch)

    with pytest.raises(ModelRefused):
        call(judge)

    assert judge.meter.calls[0].stop_reason == reason, "the refusal is still logged"


def test_a_truncated_answer_is_voided_rather_than_half_parsed(monkeypatch):
    """Half a verdict is not a smaller verdict."""
    judge, _ = build([FakeResponse(text='{"verdict": "SUPPO', finish="MAX_TOKENS")], monkeypatch)

    with pytest.raises(ModelRefused) as exc:
        call(judge)
    assert "truncated" in str(exc.value)


def test_an_empty_answer_is_voided(monkeypatch):
    judge, _ = build([FakeResponse(text="   ")], monkeypatch)
    with pytest.raises(ModelRefused):
        call(judge)


# ---------------------------------------------------------------- the free tier's rate limit


class FakeClientError(Exception):
    def __init__(self, code):
        super().__init__(f"HTTP {code}")
        self.code = code


@pytest.fixture(autouse=True)
def _patch_error_types(monkeypatch):
    """Point the module's `errors.ClientError` at the local fake."""
    from google.genai import errors

    monkeypatch.setattr(errors, "ClientError", FakeClientError, raising=False)
    yield


def test_a_rate_limit_is_waited_out_rather_than_dropping_the_claim(monkeypatch):
    """A claim skipped for quota is a hole in the denominator, and holes are what this project refuses."""
    judge, slept = build(
        [FakeClientError(429), FakeClientError(429), FakeResponse(text='{"verdict":"SUPPORTED"}')],
        monkeypatch,
    )

    assert call(judge) == {"verdict": "SUPPORTED"}
    assert slept == [2.0, 4.0], "exponential backoff between attempts"
    assert judge.rate_limit_waits == 6.0, "time spent waiting is recorded, not silently absorbed"


def test_backoff_covers_a_per_minute_quota_before_giving_up():
    """The free tier limits per minute, so the retry schedule has to be able to outlast a minute."""
    from sayswho.gemini import GeminiJudge  # noqa: F401

    schedule = [min(60.0, 2.0 ** attempt) for attempt in range(1, 6)]
    assert sum(schedule) > 60, f"total backoff {sum(schedule)}s would give up inside one quota window"


def test_a_rate_limit_that_never_clears_raises_rather_than_looping_forever(monkeypatch):
    judge, _ = build([FakeClientError(429)] * 10, monkeypatch, max_retries=2)

    with pytest.raises(FakeClientError):
        call(judge)


def test_a_non_rate_limit_client_error_is_not_retried(monkeypatch):
    """A 400 is an answer about the request, not a queue to wait in."""
    judge, slept = build([FakeClientError(400)], monkeypatch)

    with pytest.raises(FakeClientError):
        call(judge)
    assert slept == []


# ---------------------------------------------------------------- picking a judge


def test_an_unknown_provider_is_rejected_rather_than_defaulted(monkeypatch):
    from sayswho.gemini import build_judge

    with pytest.raises(ValueError) as exc:
        build_judge("mistral")
    assert "gemini" in str(exc.value) and "anthropic" in str(exc.value)
