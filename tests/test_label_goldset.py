"""Tests for the labelling tool.

The tool's job is to keep the sample honest, so these test the two things that would make it dishonest: an
input carrying judge output, and a sample that was steered rather than drawn.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

import label_goldset  # noqa: E402

from sayswho.claims import Claim, ClaimSet  # noqa: E402
from sayswho.records import SOURCE_OK, SOURCE_PAYWALLED  # noqa: E402
from sayswho.splits import StoredSplit  # noqa: E402


def split(product="chatgpt", n=6, prefix="c"):
    return StoredSplit(
        answer_sha256="a" * 64,
        query_id="PR-01",
        product=product,
        created_at="2026-08-12T09:00:00+00:00",
        claim_prompt_version="claims-v1",
        judge_class="GeminiJudge",
        judge_model="gemini-3.5-flash-lite",
        claims=[
            Claim(id=f"{prefix}{i}", text=f"Claim number {i}.", markers=["[1]"],
                  urls=[f"https://example.org/{i}"])
            for i in range(n)
        ],
        skipped=[],
    )


# ---------------------------------------------------------------- the blindness refusal


@pytest.mark.parametrize("key", ["verdict", "judgements", "void_reason", "span_verified"])
def test_a_file_carrying_judge_output_is_refused(tmp_path, key):
    """Passing the run record instead of the capture is the mistake this catches, and it is a quiet one:
    the labelling would proceed normally and the resulting kappa would mean nothing."""
    path = tmp_path / "run.json"
    path.write_text(json.dumps({"fetches": [{"url": "https://example.org/1", key: "SUPPORTED"}]}))
    with pytest.raises(label_goldset.NotBlind) as exc:
        label_goldset.load_json(path)
    assert "not a blind gold set" in str(exc.value)


def test_a_judge_key_nested_deep_in_the_file_is_still_caught(tmp_path):
    path = tmp_path / "run.json"
    path.write_text(json.dumps({"a": {"b": [{"c": {"verdict": "SUPPORTED"}}]}}))
    with pytest.raises(label_goldset.NotBlind):
        label_goldset.load_json(path)


def test_a_plain_fetch_record_is_accepted(tmp_path):
    """A run without --judge carries fetch codes and no verdicts, which is exactly what labelling needs."""
    path = tmp_path / "run.json"
    path.write_text(json.dumps({"fetches": [{"url": "https://example.org/1", "code": SOURCE_OK}]}))
    assert label_goldset.load_json(path)["fetches"][0]["code"] == SOURCE_OK


# ---------------------------------------------------------------- the sample


def test_the_sample_is_reproducible_from_its_seed():
    pool = label_goldset.build_pool([split()], [], None)
    first = label_goldset.stratify(pool, 4, seed=7)
    second = label_goldset.stratify(pool, 4, seed=7)
    assert [r["claim_id"] for r in first] == [r["claim_id"] for r in second]


def test_a_different_seed_gives_a_different_sample():
    pool = label_goldset.build_pool([split(n=12)], [], None)
    a = [r["claim_id"] for r in label_goldset.stratify(pool, 4, seed=1)]
    b = [r["claim_id"] for r in label_goldset.stratify(pool, 4, seed=2)]
    assert a != b


def test_the_sample_spreads_across_products():
    pool = label_goldset.build_pool(
        [split(product="chatgpt", prefix="a"), split(product="claude", prefix="b")], [], None
    )
    picked = label_goldset.stratify(pool, 4, seed=3)
    assert {r["product"] for r in picked} == {"chatgpt", "claude"}


def test_unauditable_pairs_are_reached_first():
    """`SCOPE.md` §3 Phase 4 asks for UNAUDITABLE to be filled first, and it is the half of that instruction
    a blind sample can actually follow: the G2 code is known before any model runs."""
    fetches = {"fetches": [
        {"url": "https://example.org/0", "code": SOURCE_PAYWALLED},
        {"url": "https://example.org/1", "code": SOURCE_OK},
        {"url": "https://example.org/2", "code": SOURCE_OK},
        {"url": "https://example.org/3", "code": SOURCE_OK},
        {"url": "https://example.org/4", "code": SOURCE_OK},
        {"url": "https://example.org/5", "code": SOURCE_OK},
    ]}
    pool = label_goldset.build_pool([split()], [fetches], None)
    picked = label_goldset.stratify(pool, 2, seed=5)
    assert picked[0]["source_code"] == SOURCE_PAYWALLED


def test_the_plan_mode_labels_nothing(tmp_path, capsys):
    """A dry run has to be possible without a person sitting at the prompt."""
    split_path = tmp_path / "split.json"
    split().save(split_path)
    code = label_goldset.main([
        "--split", str(split_path), "--out", str(tmp_path / "gold.json"),
        "--target", "3", "--plan",
    ])
    assert code == 0
    assert not (tmp_path / "gold.json").exists()
    assert "3 selected" in capsys.readouterr().out


# ---------------------------------------------------------------- the extraction check


def test_a_passage_the_extractor_dropped_is_detected(tmp_path):
    """The whole point of asking the labeller for a passage: it separates a bad extractor from a bad judge."""
    from sayswho.cache import FetchCache

    from sayswho.judge import span_is_present

    cache = FetchCache(tmp_path / "cache")
    # A pull-quote in an `aside`. `extract_text` drops asides as furniture; `raw_text` keeps them. A human
    # reading the page sees the number, so they mark SUPPORTED, and the pipeline never had the sentence.
    markup = (
        "<html><body><nav>Home</nav>"
        "<article><p>The trial ran for ten years.</p></article>"
        "<aside>Recurrence fell by 38% in the extended arm.</aside>"
        "</body></html>"
    )
    cache.put("https://example.org/t", 200, {"Content-Type": "text/html"}, markup.encode())

    text, raw = label_goldset.extracted_pair(cache, "https://example.org/t")
    passage = "Recurrence fell by 38% in the extended arm"

    assert span_is_present(passage, raw), "the permissive pass should still see it"
    assert not span_is_present(passage, text), "the strict pass drops it, which is the failure being caught"


def test_a_url_with_nothing_cached_returns_none(tmp_path):
    from sayswho.cache import FetchCache

    assert label_goldset.extracted_pair(FetchCache(tmp_path / "cache"), "https://example.org/x") is None


# ---------------------------------------------------------------- which splits the saved set claims


def test_the_saved_set_records_only_the_splits_that_produced_a_label(tmp_path, monkeypatch):
    """The bug this pins made the whole tool useless for its own purpose.

    Reaching thirty to forty pairs takes two or three answers, and the sampler stratifies across products,
    which needs more than one split. Given more than one, the tool used to record `split_sha256 = ""`, and
    G4 compares that against the split of the run in front of it, so an afternoon of labelling calibrated
    nothing at all. It now records the splits its labels actually came from, which is also not the same as
    the splits it was handed: quitting after one label must not claim the answer never reached."""
    from sayswho.goldset import GoldSet

    a, b = split(product="chatgpt", n=6), split(product="perplexity", n=5)
    assert a.split_sha256 != b.split_sha256, "two identical splits would make this test vacuous"

    paths = []
    for n, s in enumerate((a, b)):
        p = tmp_path / f"split{n}.json"
        s.save(p)
        paths.append(str(p))

    out = tmp_path / "gold.json"
    # One label, then quit: S, the passage prompt, the notes prompt, then q.
    answers = iter(["S", "", "", "q"])
    monkeypatch.setattr("builtins.input", lambda *_: next(answers))

    label_goldset.main(["--split", paths[0], "--split", paths[1], "--out", str(out),
                        "--cache", str(tmp_path / "cache"), "--target", "10"])

    gold = GoldSet.load(out)
    assert len(gold.labels) == 1
    assert gold.split_sha256s, "a set bound to no split calibrates nothing, which was the bug"
    assert len(gold.split_sha256s) == 1, "only one pair was labelled, so only one split is covered"
    assert gold.split_sha256s[0] in (a.split_sha256, b.split_sha256)


def test_resuming_keeps_the_splits_the_earlier_session_recorded(tmp_path, monkeypatch):
    """A labelling session is resumable, and the splits are accumulated across sessions rather than
    recomputed from whatever the second invocation happened to be given."""
    from sayswho.goldset import GoldSet

    a, b = split(product="chatgpt", n=6), split(product="perplexity", n=5)
    paths = []
    for n, s in enumerate((a, b)):
        p = tmp_path / f"split{n}.json"
        s.save(p)
        paths.append(str(p))

    out = tmp_path / "gold.json"
    args = ["--split", paths[0], "--split", paths[1], "--out", str(out),
            "--cache", str(tmp_path / "cache"), "--target", "10"]

    session_one = iter(["S", "", "", "q"])
    monkeypatch.setattr("builtins.input", lambda *_: next(session_one))
    label_goldset.main(args)
    first = GoldSet.load(out).split_sha256s

    answers = iter(["S", "", "", "S", "", "", "q"])
    monkeypatch.setattr("builtins.input", lambda *_: next(answers))
    label_goldset.main(args)

    after = GoldSet.load(out).split_sha256s
    assert set(first) <= set(after), "resuming dropped a split the first session had labelled"
