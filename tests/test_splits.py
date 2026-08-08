"""The stored split, and the refusals that make it worth storing.

A split is a sample, not a property of the answer: eight splits of one capture gave 15 to 21 claims
(`FINDINGS.md` item 8). So the gold set is labelled against a file, and these tests are about what happens
when that file and the thing being judged do not match. Every one of them asserts a raise, because a run
that looks pinned and is not is worse than a run that stops.
"""

from __future__ import annotations

import json

import pytest

from sayswho.claims import CLAIM_PROMPT_VERSION, Claim, ClaimSet, Skipped, claim_id
from sayswho.records import Capture, Citation
from sayswho.splits import StoredSplit, split_digest, store


class FakeClient:
    model = "test-model-1"


def capture(answer="The programme screened 4,120 residents in 2022.", query_id="PR-01"):
    return Capture(
        query_id=query_id,
        product="chatgpt",
        model_id="test",
        generated_at="2026-08-08T00:00:00+00:00",
        captured_at="2026-08-08T00:00:00+00:00",
        answer_text=answer,
        citations=[Citation(marker="[1]", url="https://example.org/a")],
    )


def claim_set(texts=("The programme screened 4,120 residents in 2022.",)):
    seen: dict[str, int] = {}
    return ClaimSet(
        claims=[
            Claim(id=claim_id("PR-01", t, seen), text=t, markers=["[1]"], urls=["https://example.org/a"])
            for t in texts
        ],
        skipped=[Skipped(text="A heading", reason="heading")],
    )


# ---------------------------------------------------------------- content-addressed ids


def test_the_same_sentence_gets_the_same_id_in_a_different_split():
    """Ids used to be positional, so #009 meant a different sentence in every run."""
    a = claim_id("PR-01", "Uptake reached 78% in 2022.", {})
    b = claim_id("PR-01", "Uptake reached 78% in 2022.", {})
    assert a == b


def test_a_reflowed_claim_is_the_same_claim():
    assert claim_id("PR-01", "Uptake reached\n  78% in 2022.", {}) == claim_id(
        "PR-01", "Uptake reached 78% in 2022.", {}
    )


def test_different_sentences_get_different_ids():
    seen: dict[str, int] = {}
    assert claim_id("PR-01", "Uptake reached 78%.", seen) != claim_id("PR-01", "Uptake fell.", seen)


def test_a_repeated_sentence_still_gets_two_distinct_ids():
    seen: dict[str, int] = {}
    first = claim_id("PR-01", "Screening is covered.", seen)
    second = claim_id("PR-01", "Screening is covered.", seen)
    assert first != second
    assert second == f"{first}.2", "the second occurrence is numbered, the first is implicit"


def test_the_id_carries_the_query_it_came_from():
    assert claim_id("PR-07", "Anything.", {}).startswith("PR-07#")


# ---------------------------------------------------------------- round trip


def test_a_stored_split_round_trips(tmp_path):
    original = store(claim_set(), capture(), FakeClient(), created_at="2026-08-08T01:00:00+00:00")
    path = original.save(tmp_path / "split.json")

    loaded = StoredSplit.load(path)

    assert loaded.split_sha256 == original.split_sha256
    assert [c.id for c in loaded.claims] == [c.id for c in original.claims]
    assert [c.urls for c in loaded.claims] == [c.urls for c in original.claims]
    assert loaded.skipped[0].reason == "heading"
    assert loaded.judge_model == "test-model-1"


def test_binding_returns_the_stored_claims_not_a_fresh_split(tmp_path):
    original = store(claim_set(), capture(), FakeClient(), created_at="2026-08-08T01:00:00+00:00")
    path = original.save(tmp_path / "split.json")

    bound = StoredSplit.load(path).bind(capture())

    assert [c.text for c in bound.claims] == [c.text for c in original.claims]


def test_the_digest_ignores_when_the_split_was_made():
    """Two runs that produced the same claims are the same split for labelling purposes."""
    a = store(claim_set(), capture(), FakeClient(), created_at="2026-08-08T01:00:00+00:00")
    b = store(claim_set(), capture(), FakeClient(), created_at="2027-01-01T00:00:00+00:00")
    assert a.split_sha256 == b.split_sha256


def test_the_digest_changes_when_a_claim_changes():
    a = store(claim_set(), capture(), FakeClient(), created_at="2026-08-08T01:00:00+00:00")
    b = store(claim_set(("A different claim entirely.",)), capture(), FakeClient(),
              created_at="2026-08-08T01:00:00+00:00")
    assert a.split_sha256 != b.split_sha256


# ---------------------------------------------------------------- the refusals


def test_a_split_of_a_different_answer_is_refused(tmp_path):
    """The whole point. A split of one answer says nothing about another."""
    path = store(claim_set(), capture(), FakeClient(),
                 created_at="2026-08-08T01:00:00+00:00").save(tmp_path / "split.json")

    with pytest.raises(ValueError, match="not a split of another"):
        StoredSplit.load(path).bind(capture(answer="A completely different answer."))


def test_a_split_made_under_another_prompt_version_is_refused(tmp_path):
    """Gate G4: a prompt change means relabelling, and it must not be possible to skip that silently."""
    record = store(claim_set(), capture(), FakeClient(), created_at="2026-08-08T01:00:00+00:00")
    record.claim_prompt_version = "claims-v0"
    path = record.save(tmp_path / "split.json")

    with pytest.raises(ValueError, match="relabelling"):
        StoredSplit.load(path).bind(capture())


def test_an_edited_split_file_is_refused(tmp_path):
    """A hand-edited split must not be able to pass as the one a human labelled."""
    path = store(claim_set(), capture(), FakeClient(),
                 created_at="2026-08-08T01:00:00+00:00").save(tmp_path / "split.json")

    payload = json.loads(path.read_text())
    payload["claims"][0]["text"] = "A claim nobody labelled."
    path.write_text(json.dumps(payload))

    with pytest.raises(ValueError, match="edited after it was written"):
        StoredSplit.load(path)


def test_the_stored_prompt_version_matches_the_build():
    """Guards against the record being written with a stale constant."""
    record = store(claim_set(), capture(), FakeClient(), created_at="2026-08-08T01:00:00+00:00")
    assert record.claim_prompt_version == CLAIM_PROMPT_VERSION
