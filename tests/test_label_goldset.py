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


def test_quitting_at_the_first_prompt_leaves_no_file_and_does_not_crash(tmp_path, monkeypatch, capsys):
    """Opening the tool to see what it asks for, and quitting, is a reasonable thing to do. It used to end
    in a FileNotFoundError printed under the words "saved 0 label(s)", which reads like the save failed."""
    s = split(product="chatgpt", n=4)
    p = tmp_path / "split.json"
    s.save(p)

    out = tmp_path / "gold.json"
    monkeypatch.setattr("builtins.input", lambda *_: "q")

    assert label_goldset.main(["--split", str(p), "--out", str(out),
                               "--cache", str(tmp_path / "cache"), "--target", "5"]) == 0
    assert not out.exists(), "nothing was labelled, so there is no set to write"
    assert "Nothing was lost" in capsys.readouterr().out


def test_quitting_after_one_label_still_reports_coverage(tmp_path, monkeypatch, capsys):
    """The other side of it: a session that produced something must still print what it produced."""
    s = split(product="chatgpt", n=4)
    p = tmp_path / "split.json"
    s.save(p)

    out = tmp_path / "gold.json"
    answers = iter(["S", "", "", "q"])
    monkeypatch.setattr("builtins.input", lambda *_: next(answers))

    assert label_goldset.main(["--split", str(p), "--out", str(out),
                               "--cache", str(tmp_path / "cache"), "--target", "5"]) == 0
    assert out.exists()
    printed = capsys.readouterr().out
    assert "saved 1 label(s)" in printed
    assert "coverage by class" in printed


def test_the_banner_claims_only_what_the_tool_can_check(tmp_path, monkeypatch, capsys):
    """It used to open with "nothing here has been judged yet", which is a claim about the world rather
    than about this process, and it was false the first time anyone read it: every capture on disk had
    already been audited.

    Then it said this tool had opened no file containing a verdict, and the prior-audit scan made that false
    in turn, because the scan opens exactly those files. What is true of both is that neither shows the
    labeller one, so that is what it says now. The old sentences are asserted absent, because a claim that
    stopped being true is worse than one that was never made."""
    s = split(product="chatgpt", n=4)
    p = tmp_path / "split.json"
    s.save(p)
    monkeypatch.setattr("builtins.input", lambda *_: "q")

    label_goldset.main(["--split", str(p), "--out", str(tmp_path / "g.json"),
                        "--cache", str(tmp_path / "cache"), "--target", "3",
                        "--audit-scan", str(tmp_path / "reports")])
    blind = capsys.readouterr().out
    assert "No verdict has been shown to you here" in blind
    assert "has not opened any file containing a verdict" not in blind
    assert "Nothing here has been judged yet" not in blind
    assert "--supplemental" in blind, "the blind path has to name the way out of it"

    label_goldset.main(["--split", str(p), "--out", str(tmp_path / "g2.json"),
                        "--cache", str(tmp_path / "cache"), "--target", "3", "--supplemental",
                        "--audit-scan", str(tmp_path / "reports")])
    supplemental = capsys.readouterr().out
    assert "SUPPLEMENTAL" in supplemental
    assert "excluded from kappa" in supplemental


# ---------------------------------------------------------------- the prior-audit refusal


def audited(directory, answer, verdict="SUPPORTED"):
    """A report of the kind `sayswho/report.py` writes, over one answer. What the scan is looking for."""
    directory.mkdir(parents=True, exist_ok=True)
    (directory / f"report-{answer[:8]}.json").write_text(json.dumps({
        "meta": {"product": "chatgpt", "answer_sha256": answer},
        "claims": [{"id": "c0", "sources": [{"verdict": verdict, "judged": True}]}],
        "judged": True,
    }))


def test_a_blind_session_over_an_already_audited_answer_is_refused(tmp_path, monkeypatch):
    """The fault this closes. `goldset.agreement` compares label times against the run they are compared
    with, so labels written today pass against a run made tomorrow, and G4 ties to the split, which differs
    because Phase 1 does not repeat itself. An answer judged last week therefore leaves verdicts that anchor
    a labeller and trip nothing at all.

    The refusal has to land before the first question, which is what the input trap here asserts: a labeller
    who has already read three claims has spent the blindness this was protecting."""
    s = split(product="chatgpt", n=4)
    p = tmp_path / "split.json"
    s.save(p)
    audited(tmp_path / "reports", s.answer_sha256)

    def never(*_):
        raise AssertionError("the refusal must come before the first prompt")

    monkeypatch.setattr("builtins.input", never)

    out = tmp_path / "gold.json"
    code = label_goldset.main(["--split", str(p), "--out", str(out),
                               "--cache", str(tmp_path / "cache"), "--target", "3",
                               "--audit-scan", str(tmp_path / "reports")])
    assert code == 3, "a distinct exit code, so a script can tell this refusal from a usage error"
    assert not out.exists()


def test_the_refusal_names_the_file_and_the_way_through(tmp_path, monkeypatch, capsys):
    """A refusal a person cannot act on gets worked around. It names the file, so the claim can be checked,
    and it names --supplemental, so there is somewhere to go."""
    s = split(product="chatgpt", n=4)
    p = tmp_path / "split.json"
    s.save(p)
    audited(tmp_path / "reports", s.answer_sha256)
    monkeypatch.setattr("builtins.input", lambda *_: "q")

    label_goldset.main(["--split", str(p), "--out", str(tmp_path / "gold.json"),
                        "--cache", str(tmp_path / "cache"), "--target", "3",
                        "--audit-scan", str(tmp_path / "reports")])
    printed = capsys.readouterr().out
    assert "PRIOR AUDIT" in printed
    assert "report-" in printed, "the file has to be named or the refusal cannot be argued with"
    assert "--supplemental" in printed
    assert "SUPPORTED" not in printed, "the refusal must not print the verdict it found"


def test_supplemental_proceeds_over_an_audited_answer_and_says_what_it_is(tmp_path, monkeypatch, capsys):
    """The way through is not a weaker kind of blind. These labels carry blind: false, which excludes them
    from kappa in `goldset.agreement` rather than merely annotating them."""
    from sayswho.goldset import GoldSet

    s = split(product="chatgpt", n=4)
    p = tmp_path / "split.json"
    s.save(p)
    audited(tmp_path / "reports", s.answer_sha256)

    answers = iter(["S", "", "", "q"])
    monkeypatch.setattr("builtins.input", lambda *_: next(answers))

    out = tmp_path / "gold.json"
    code = label_goldset.main(["--split", str(p), "--out", str(out), "--supplemental",
                               "--cache", str(tmp_path / "cache"), "--target", "3",
                               "--audit-scan", str(tmp_path / "reports")])
    assert code == 0
    gold = GoldSet.load(out)
    assert gold.labels and not gold.labels[0].blind
    assert not gold.blind, "a supplemental label must not reach the kappa sample"
    assert "PRIOR AUDIT" in capsys.readouterr().out, "it still says what it found"


def test_plan_mode_is_not_refused_but_says_the_session_would_be(tmp_path, capsys):
    """--plan writes nothing, so blocking it would only stop somebody looking at the sample. Letting it
    through silently would read as the check having passed."""
    s = split(product="chatgpt", n=4)
    p = tmp_path / "split.json"
    s.save(p)
    audited(tmp_path / "reports", s.answer_sha256)

    code = label_goldset.main(["--split", str(p), "--out", str(tmp_path / "gold.json"),
                               "--target", "3", "--plan",
                               "--audit-scan", str(tmp_path / "reports")])
    assert code == 0
    printed = capsys.readouterr().out
    assert "A blind session here would be refused" in printed
    assert "selected" in printed, "the plan still printed"


def test_a_clean_scan_is_recorded_in_the_saved_set(tmp_path, monkeypatch):
    """The gold set carries the scan's own summary, so a set read a month later says whether the check ran
    and over how much. Provenance rather than a hash, and it is not treated as one."""
    from sayswho.goldset import GoldSet

    s = split(product="chatgpt", n=4)
    p = tmp_path / "split.json"
    s.save(p)
    (tmp_path / "reports").mkdir()
    audited(tmp_path / "reports", "f" * 64)  # a real audit, of a different answer

    answers = iter(["S", "", "", "q"])
    monkeypatch.setattr("builtins.input", lambda *_: next(answers))

    out = tmp_path / "gold.json"
    assert label_goldset.main(["--split", str(p), "--out", str(out),
                               "--cache", str(tmp_path / "cache"), "--target", "3",
                               "--audit-scan", str(tmp_path / "reports")]) == 0

    note = GoldSet.load(out).note
    assert "Prior-audit scan" in note
    assert "1 file(s)" in note, "how many files were read is the part that makes the claim checkable"


def test_a_scan_that_could_not_look_anywhere_says_so_in_the_saved_set(tmp_path, monkeypatch):
    """Not checked is not clean, and the set has to carry which of the two it was."""
    from sayswho.goldset import GoldSet

    s = split(product="chatgpt", n=4)
    p = tmp_path / "split.json"
    s.save(p)

    answers = iter(["S", "", "", "q"])
    monkeypatch.setattr("builtins.input", lambda *_: next(answers))

    out = tmp_path / "gold.json"
    label_goldset.main(["--split", str(p), "--out", str(out),
                        "--cache", str(tmp_path / "cache"), "--target", "3",
                        "--audit-scan", str(tmp_path / "absent")])
    assert "not checked" in GoldSet.load(out).note


# ---------------------------------------------------------------- when there is nobody at the keyboard


def test_no_terminal_stops_cleanly_instead_of_a_traceback(tmp_path, monkeypatch, capsys):
    """Found in the rehearsal, which is what a rehearsal is for. Launched without a terminal, from a Run
    button or a pipe, the tool used to reach the first prompt and raise EOFError. A traceback at that moment
    reads as "the tool is broken" rather than "there is nobody here to label", and a labeller who has just
    been told to run this would have no way to tell the two apart."""
    a = split(product="chatgpt", n=6)
    path = tmp_path / "split.json"
    a.save(path)
    out = tmp_path / "gold.json"

    def no_input(*_):
        raise EOFError

    monkeypatch.setattr("builtins.input", no_input)

    assert label_goldset.main(["--split", str(path), "--out", str(out),
                               "--cache", str(tmp_path / "cache"), "--target", "5"]) == 0

    printed = capsys.readouterr().out
    assert "Labelling needs a person at a terminal" in printed
    assert not out.exists(), "nothing was labelled, so nothing should have been written"


def test_an_interrupt_keeps_the_labels_already_made(tmp_path, monkeypatch, capsys):
    """A labelling session is an hour of irreplaceable human work. Ctrl-C after three labels keeps three."""
    a = split(product="chatgpt", n=6)
    path = tmp_path / "split.json"
    a.save(path)
    out = tmp_path / "gold.json"

    answers = iter(["S", "", ""])

    def then_interrupt(*_):
        try:
            return next(answers)
        except StopIteration:
            raise KeyboardInterrupt

    monkeypatch.setattr("builtins.input", then_interrupt)
    assert label_goldset.main(["--split", str(path), "--out", str(out),
                               "--cache", str(tmp_path / "cache"), "--target", "5"]) == 0

    from sayswho.goldset import GoldSet

    assert "1 label(s) kept" in capsys.readouterr().out
    assert GoldSet.load(out).labels, "the label made before the interrupt was lost"
