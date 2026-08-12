"""Gold set tests.

The arithmetic here is standard and the refusals are not, so the refusals are what these test: a set bound
to the wrong split, a label written after the judge answered, an edited file, and a supplement quietly
counted as if it had been blind.
"""

from __future__ import annotations

import pytest

from sayswho.gates import NO_CALIBRATION, g4_calibration_exists
from sayswho.goldset import (
    COMPARABLE,
    GoldLabel,
    GoldSet,
    GoldSetContract,
    UNAUDITABLE,
    UNDECIDABLE,
    agreement,
    cohens_kappa,
    coverage,
)
from sayswho.judge import CONTRADICTED, NOT_FOUND_IN_SOURCE, SUPPORTED, Judgement

SPLIT = "a" * 64


def label(claim_id, value, at="2026-08-12T09:00:00+00:00", blind=True, url="https://a.example/1"):
    return GoldLabel(claim_id=claim_id, url=url, label=value, labelled_at=at, labeller="jayanth", blind=blind)


def gold(labels, split=SPLIT):
    return GoldSet(
        split_sha256s=[split],
        judge_class="GeminiJudge",
        judge_model="gemini-3.5-flash-lite",
        judge_prompt_version="judge-v1",
        claim_prompt_version="claims-v1",
        created_at="2026-08-12T09:00:00+00:00",
        labels=labels,
        labeller="jayanth",
    )


def verdict(claim_id, value, url="https://a.example/1", voided=False):
    return Judgement(claim_id=claim_id, url=url, verdict=value, span_verified=not voided, voided=voided)


# ---------------------------------------------------------------- gate G4


def test_g4_refuses_an_aggregate_rate_when_no_gold_set_exists():
    result = g4_calibration_exists(None, "GeminiJudge", "m", "judge-v1", "claims-v1", SPLIT)
    assert not result.passed
    assert result.code == NO_CALIBRATION
    assert "per-claim verdicts still emit" in result.detail.lower()


def test_g4_refuses_a_gold_set_labelled_against_a_different_split():
    """Phase 1 is nondeterministic, so a set labelled against one split is not valid for another."""
    result = g4_calibration_exists(
        gold([label("c1", SUPPORTED)], split="b" * 64),
        "GeminiJudge", "gemini-3.5-flash-lite", "judge-v1", "claims-v1", SPLIT,
    )
    assert not result.passed
    assert "valid for the splits it was labelled against" in result.detail


def test_g4_passes_for_every_split_a_multi_answer_set_covers():
    """The case that made the single-hash version useless. One answer yields roughly twenty labellable
    pairs and the target is thirty to forty, so a real set spans two or three answers, and the sampler
    stratifies across products, which needs more than one. Under equality such a set calibrated nothing."""
    across = gold([label("c1", SUPPORTED)])
    across.split_sha256s = [SPLIT, "b" * 64, "c" * 64]

    for covered in across.split_sha256s:
        result = g4_calibration_exists(
            across, "GeminiJudge", "gemini-3.5-flash-lite", "judge-v1", "claims-v1", covered,
        )
        assert result.passed, f"the set holds labels for {covered[:8]} and should calibrate it"

    stranger = g4_calibration_exists(
        across, "GeminiJudge", "gemini-3.5-flash-lite", "judge-v1", "claims-v1", "d" * 64,
    )
    assert not stranger.passed, "membership, not a free pass to every split in existence"


def test_g4_refuses_a_gold_set_bound_to_no_split_at_all():
    """What the labelling tool used to write whenever it was given more than one split. It would otherwise
    be a set that binds to nothing, and a check for equality against nothing calibrates nothing, which at
    least fails loudly. A membership check against an empty list has to refuse on purpose."""
    unbound = gold([label("c1", SUPPORTED)])
    unbound.split_sha256s = []

    result = g4_calibration_exists(
        unbound, "GeminiJudge", "gemini-3.5-flash-lite", "judge-v1", "claims-v1", SPLIT,
    )
    assert not result.passed
    assert "records no split" in result.detail


def test_g4_refuses_a_gold_set_labelled_against_a_different_judge():
    result = g4_calibration_exists(
        gold([label("c1", SUPPORTED)]),
        "AnthropicJudge", "claude-x", "judge-v1", "claims-v1", SPLIT,
    )
    assert not result.passed
    assert "AnthropicJudge" in result.detail


def test_g4_refuses_after_a_prompt_version_bump():
    result = g4_calibration_exists(
        gold([label("c1", SUPPORTED)]),
        "GeminiJudge", "gemini-3.5-flash-lite", "judge-v2", "claims-v1", SPLIT,
    )
    assert not result.passed
    assert "judge-v2" in result.detail


def test_g4_passes_on_the_configuration_it_was_labelled_for():
    result = g4_calibration_exists(
        gold([label("c1", SUPPORTED)]),
        "GeminiJudge", "gemini-3.5-flash-lite", "judge-v1", "claims-v1", SPLIT,
    )
    assert result.passed


# ---------------------------------------------------------------- the timestamp check


def test_a_label_written_after_the_judge_ran_is_refused():
    """`SCOPE.md` §12 puts labelling before the judge run. A timestamp check is what makes that enforced
    rather than a claim about my own discipline."""
    g = gold([label("c1", SUPPORTED, at="2026-08-12T18:00:00+00:00")])
    with pytest.raises(GoldSetContract) as exc:
        agreement(g, [verdict("c1", SUPPORTED)], judge_run_started_at="2026-08-12T12:00:00+00:00")
    assert "not a blind label" in str(exc.value)


def test_labels_written_before_the_judge_ran_are_accepted():
    g = gold([label("c1", SUPPORTED, at="2026-08-12T09:00:00+00:00")])
    result = agreement(g, [verdict("c1", SUPPORTED)], judge_run_started_at="2026-08-12T12:00:00+00:00")
    assert result.compared == 1


def test_a_supplemental_label_may_postdate_the_run_and_is_excluded_from_kappa():
    """A supplement is chosen after seeing verdicts. It is reported, and it is not agreement."""
    g = gold([
        label("c1", SUPPORTED, at="2026-08-12T09:00:00+00:00"),
        label("c2", CONTRADICTED, at="2026-08-12T20:00:00+00:00", blind=False, url="https://b.example/2"),
    ])
    result = agreement(
        g,
        [verdict("c1", SUPPORTED), verdict("c2", CONTRADICTED, url="https://b.example/2")],
        judge_run_started_at="2026-08-12T12:00:00+00:00",
    )
    assert result.compared == 1
    assert result.supplemental_compared == 1


# ---------------------------------------------------------------- file integrity


def test_an_edited_gold_set_file_raises_rather_than_loading(tmp_path):
    path = gold([label("c1", NOT_FOUND_IN_SOURCE)]).save(tmp_path / "gold.json")
    import json

    payload = json.loads(path.read_text())
    payload["labels"][0]["label"] = SUPPORTED
    path.write_text(json.dumps(payload))

    with pytest.raises(GoldSetContract) as exc:
        GoldSet.load(path)
    assert "edited after it was written" in str(exc.value)


def test_a_gold_set_round_trips(tmp_path):
    original = gold([label("c1", SUPPORTED), label("c2", CONTRADICTED, url="https://b.example/2")])
    path = original.save(tmp_path / "gold.json")
    assert GoldSet.load(path).labels_sha256 == original.labels_sha256


def test_a_label_outside_the_vocabulary_raises(tmp_path):
    import json

    path = gold([label("c1", SUPPORTED)]).save(tmp_path / "gold.json")
    payload = json.loads(path.read_text())
    payload["labels"][0]["label"] = "PROBABLY_FINE"
    payload.pop("labels_sha256")
    path.write_text(json.dumps(payload))

    with pytest.raises(GoldSetContract) as exc:
        GoldSet.load(path)
    assert "outside the vocabulary" in str(exc.value)


# ---------------------------------------------------------------- what is compared


def test_a_pair_the_human_marked_unauditable_is_excluded_not_counted_as_disagreement():
    """The judge is never asked about an unauditable pair, so there is nothing to disagree with."""
    g = gold([label("c1", UNAUDITABLE)])
    result = agreement(g, [])
    assert result.compared == 0
    assert result.human_only_unauditable == 1


def test_an_undecidable_label_is_recorded_and_excluded_rather_than_forced():
    g = gold([label("c1", UNDECIDABLE)])
    result = agreement(g, [verdict("c1", SUPPORTED)])
    assert result.compared == 0
    assert result.undecidable == 1


def test_a_voided_verdict_is_not_compared_against_a_human_label():
    """A voided verdict is no verdict, so counting it as a disagreement would blame the judge twice."""
    g = gold([label("c1", SUPPORTED)])
    result = agreement(g, [verdict("c1", SUPPORTED, voided=True)])
    assert result.compared == 0
    assert result.unmatched == 1


# ---------------------------------------------------------------- kappa


def test_perfect_agreement_on_a_single_class_reports_no_interval():
    """Chance agreement is 1 when both raters only ever say one thing, so the standard error is undefined.

    Reporting kappa = 1.0 with a tight interval here would be the most flattering possible reading of the
    least informative possible sample.
    """
    kappa, interval = cohens_kappa([(SUPPORTED, SUPPORTED)] * 10)
    assert kappa == 1.0
    assert interval is None


def test_kappa_on_a_mixed_sample_carries_a_wide_interval_at_small_n():
    pairs = [(SUPPORTED, SUPPORTED)] * 8 + [(NOT_FOUND_IN_SOURCE, NOT_FOUND_IN_SOURCE)] * 7
    pairs += [(SUPPORTED, NOT_FOUND_IN_SOURCE)] * 2
    kappa, interval = cohens_kappa(pairs)
    lo, hi = interval
    assert 0 < kappa < 1
    assert hi - lo > 0.15, "at n=17 the interval should be visibly wide, not a decoration"


def test_total_disagreement_is_negative_kappa():
    pairs = [(SUPPORTED, NOT_FOUND_IN_SOURCE)] * 5 + [(NOT_FOUND_IN_SOURCE, SUPPORTED)] * 5
    kappa, _ = cohens_kappa(pairs)
    assert kappa < 0


def test_kappa_over_nothing_is_none_rather_than_zero():
    assert cohens_kappa([]) == (None, None)


# ---------------------------------------------------------------- per class and coverage


def test_per_class_precision_and_recall_are_reported_with_their_own_n():
    g = gold([
        label("c1", SUPPORTED),
        label("c2", SUPPORTED, url="https://b.example/2"),
        label("c3", NOT_FOUND_IN_SOURCE, url="https://c.example/3"),
    ])
    judgements = [
        verdict("c1", SUPPORTED),
        verdict("c2", NOT_FOUND_IN_SOURCE, url="https://b.example/2"),
        verdict("c3", NOT_FOUND_IN_SOURCE, url="https://c.example/3"),
    ]
    result = agreement(g, judgements)
    supported = next(c for c in result.per_class if c.label == SUPPORTED)
    assert (supported.tp, supported.fp, supported.fn) == (1, 0, 1)
    assert supported.recall == 0.5
    assert supported.to_dict()["recall_n"] == 2
    assert supported.to_dict()["recall_interval_95"] is not None


def test_coverage_reports_the_empty_classes_rather_than_hiding_them():
    """A class the set never contains cannot be calibrated, and that gets published."""
    g = gold([label("c1", SUPPORTED), label("c2", SUPPORTED, url="https://b.example/2")])
    counts = coverage(g)
    assert counts[SUPPORTED] == 2
    assert counts[CONTRADICTED] == 0


def test_the_agreement_record_passes_the_no_confidence_number_gate():
    from sayswho.gates import assert_no_confidence_number

    g = gold([label("c1", SUPPORTED)])
    assert_no_confidence_number(agreement(g, [verdict("c1", SUPPORTED)]).to_dict())


def test_the_rendered_agreement_names_itself_a_wide_interval_estimate():
    pairs = [(SUPPORTED, SUPPORTED)] * 8 + [(NOT_FOUND_IN_SOURCE, NOT_FOUND_IN_SOURCE)] * 7
    g = gold(
        [label(f"c{i}", h) for i, (h, _) in enumerate(pairs)]
    )
    # Labels and verdicts lined up one to one, so the render path has something to say.
    judgements = [verdict(f"c{i}", j) for i, (_, j) in enumerate(pairs)]
    text = agreement(g, judgements).render()
    assert "single-rater" in agreement(g, judgements).note.lower()
    assert "wide-interval estimate" in text or "interval undefined" in text
