"""The stretch break attempts, 1 to 4.

These tests are about the harness, not about the results. They assert that each attempt declares its failure
mode before it runs, that the criterion is mechanical rather than reinterpreted afterwards, and that an
attempt with no judge reports no result instead of a pass. The results themselves need a live judge and go in
`BREAK_ATTEMPTS.md` when they exist.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

from break_attempts import ATTEMPTS, BY_ID, _assess, main, render, run_attempt
from sayswho.judge import (
    CONTRADICTED,
    NOT_FOUND_IN_SOURCE,
    SUPPORTED,
    Judgement,
)
from sayswho.records import SOURCE_PAYWALLED


def judgement(verdict, **kw):
    return Judgement(claim_id="BREAK", url="https://example.org", verdict=verdict, **kw)


# ---------------------------------------------------------------- the attempts are declared, not decided


def test_all_four_stretch_attempts_are_present():
    """Plus 1b, which asks attempt 1's declared question against a fixture that can answer it."""
    assert sorted(BY_ID) == ["1", "1b", "2", "3", "4"]


@pytest.mark.parametrize("attempt", ATTEMPTS, ids=lambda a: f"{a.id}-{a.name}")
def test_every_attempt_declares_what_it_is_looking_for(attempt):
    """An attempt whose success criterion is chosen after seeing the output is not an attempt."""
    assert len(attempt.looking_for) > 60, "the failure mode has to be described, not named"
    assert len(attempt.holds_if) > 30, "and so does the outcome that would count as holding"
    assert attempt.claim.strip()
    assert attempt.document.strip()


def test_the_criterion_is_not_reinterpreted_after_the_fact():
    """`_assess` reads the declared criterion mechanically. Attempt 1 holds on NOT_FOUND_IN_SOURCE and on
    nothing else, whatever the reasoning attached to another verdict might argue."""
    held, why = _assess(BY_ID["1"], judgement(NOT_FOUND_IN_SOURCE))
    assert held
    held, why = _assess(BY_ID["1"], judgement(SUPPORTED, span="x", span_verified=True))
    assert not held
    assert "the span guard cannot catch it" in why


@pytest.mark.parametrize("attempt_id", ["1", "1b"])
def test_breaking_into_a_different_failure_is_not_reported_as_the_declared_one(attempt_id):
    """The bug this pins fired on the first live run. Attempt 1 declared it was looking for SUPPORTED or
    PARTIALLY_SUPPORTED, the judge returned CONTRADICTED, and `_assess` reported that as "the failure the
    attempt was looking for" because it had one message for every verdict that was not NOT_FOUND_IN_SOURCE.

    Held is still decided by `holds_if` alone, so the correction cannot flatter a result: CONTRADICTED failed
    the criterion before and it fails it now. What changes is the sentence recorded beside it."""
    held, why = _assess(BY_ID[attempt_id], judgement(CONTRADICTED, span="x", span_verified=True))
    assert not held, "CONTRADICTED is not NOT_FOUND_IN_SOURCE, so the attempt did not hold"
    assert "not the failure the attempt declared" in why
    assert "the failure the attempt was looking for" not in why


def test_attempt_four_holds_only_on_contradicted():
    assert _assess(BY_ID["4"], judgement(CONTRADICTED))[0]
    assert not _assess(BY_ID["4"], judgement(SUPPORTED))[0]
    assert not _assess(BY_ID["4"], judgement(NOT_FOUND_IN_SOURCE))[0]


def test_attempt_three_treats_unknown_as_a_weak_pass_and_says_so():
    """No archived copy means no claim either way, which is the correct outcome and not a strong one."""
    held, why = _assess(BY_ID["3"], judgement(SUPPORTED, span_predates_generation=None))
    assert held
    assert "not a strong pass" in why


def test_attempt_three_breaks_if_a_later_span_is_allowed_to_stand():
    held, why = _assess(BY_ID["3"], judgement(SUPPORTED, span_predates_generation=False))
    assert not held
    assert "postdates" in why


# ---------------------------------------------------------------- what happens without a judge


def test_the_paywall_attempt_is_a_real_result_with_no_judge(tmp_path):
    """It is the one attempt of the four that does not need one: holding means the judge is never called."""
    result = run_attempt(BY_ID["2"], tmp_path / "cache", use_judge=False, provider=None)

    assert result["source_code"] == SOURCE_PAYWALLED
    assert result["judge_called"] is False
    assert result["held"] is True
    assert "UNAUDITABLE" in result["why"]


@pytest.mark.parametrize("number", ["1", "1b", "3", "4"])
def test_the_others_report_no_result_rather_than_a_pass(tmp_path, number):
    """The failure this guards: an attempt that never reached the judge reporting as though the tool held."""
    result = run_attempt(BY_ID[number], tmp_path / "cache", use_judge=False, provider=None)

    assert result["source_code"] == "SOURCE_OK", "the fixture has to be readable, or the attempt is broken"
    assert result["held"] is None, "no judge, no result"
    assert "no result" in result["why"]


def test_the_readout_counts_no_result_separately_from_holding(tmp_path):
    results = [
        run_attempt(BY_ID[n], tmp_path / "cache", use_judge=False, provider=None) for n in ("1", "2")
    ]
    text = render(results)
    assert "NO RESULT" in text
    assert "1 held, 0 broke, 1 no result" in text
    assert "not that it cannot be broken" in text, "one document is not a general claim"


# ---------------------------------------------------------------- the fixtures are actually adversarial


def test_the_topical_fixture_shares_the_claim_vocabulary_and_omits_the_number():
    """If the page did not share the claim's words, the attempt would not be testing anything."""
    attempt = BY_ID["1"]
    page = attempt.document.lower()
    for word in ("navigation", "time to diagnosis", "boston cohort", "days", "reduc"):
        assert word in page
    assert "21" not in page, "the number the claim rests on must not be on the page"


def test_the_deconfounded_fixture_is_silent_rather_than_denying():
    """Attempt 1's page ends by denying that it reports any effect estimate, and the judge read that denial
    as a contradiction. So the attempt measured whether a disclaimer is read as a contradiction, not whether
    topical overlap is read as support. 1b has to be silent for its result to mean what it claims."""
    attempt = BY_ID["1b"]
    page = attempt.document.lower()

    for word in ("navigation", "time to diagnosis", "boston cohort", "days", "reduc"):
        assert word in page, "without the shared vocabulary there is no topical match to be fooled by"
    assert "21" not in page

    # This assertion is why 1b adds a sentence instead of only deleting one. In attempt 1 the claim's verb
    # appeared nowhere except inside the denial, so removing the confound removed the overlap with it.
    before_the_denial = BY_ID["1"].document.lower().split("<p>this paper does not report")[0]
    assert "this paper does not report" in BY_ID["1"].document.lower(), "the split marker has to exist"
    assert "reduc" not in before_the_denial

    for denial in ("does not report", "makes no estimate", "no effect", "not report"):
        assert denial not in page, "a page announcing its own silence is a different fixture, that is 1"

    assert attempt.claim == BY_ID["1"].claim, "same claim, or it is not the same question"


def test_the_contradiction_fixture_uses_the_claim_words_with_a_negation():
    attempt = BY_ID["4"]
    assert "did not reduce time to diagnosis in the intervention group" in attempt.document
    assert attempt.claim == "Navigation reduced time to diagnosis in the intervention group."


def test_the_drift_fixture_puts_the_claim_only_in_the_live_copy():
    """Otherwise there is no drift to detect and the attempt proves nothing."""
    from sayswho.extract import extract_text

    attempt = BY_ID["3"]
    live = extract_text(attempt.document)
    archived = extract_text(attempt.archived)
    assert "reduced time to diagnosis by 21 days" in live
    assert "reduced time to diagnosis by 21 days" not in archived


def test_the_drift_attempt_does_not_depend_on_wayback():
    """A result that depends on whether a third party holds a snapshot of a local fixture is not a result."""
    source = (Path(__file__).resolve().parent.parent / "tools" / "break_attempts.py").read_text()
    assert "archived_text=archived_text" in source
    assert "nearest_snapshot" not in source


# ---------------------------------------------------------------- the command line


def test_list_prints_every_attempt_without_running_anything(capsys):
    assert main(["--list"]) == 0
    out = capsys.readouterr().out
    for attempt in ATTEMPTS:
        assert attempt.name in out


def test_asking_for_nothing_is_an_error():
    with pytest.raises(SystemExit):
        main([])


def test_a_judge_that_cannot_be_built_stops_before_pretending_to_run(monkeypatch, capsys):
    """Otherwise the readout would show three no-results and read like a completed run."""
    import sayswho.gemini as gemini

    monkeypatch.setattr(gemini, "build_judge", lambda provider=None, meter=None: (_ for _ in ()).throw(
        ImportError("No module named 'google'")
    ))
    assert main(["--all", "--judge"]) == 2
    assert "would have no result" in capsys.readouterr().out
