"""The headless run, end to end, offline.

Real HTTP against the local server, a scripted judge, and a real gold set file. What these assert is not
that the pipeline runs, which the other suites already cover, but that the run refuses in the right places:
an unbound capture stays out of the aggregate, a Google surface stays out of the aggregate, and a stratum
with nothing eligible prints the reason rather than an absence.
"""

from __future__ import annotations

import json

import pytest


from sayswho.harness import readout, run_stratum, save, trace_table
from sayswho.judge import NOT_FOUND_IN_SOURCE, SUPPORTED
from sayswho.records import Capture, Citation

ANSWER = (
    "Extending adjuvant endocrine therapy beyond five years reduced recurrence [1].\n"
    "The extended duration group reported more musculoskeletal adverse events [1].\n"
    "No overall survival difference reached significance at the reported follow up [1].\n"
)

CLAIM_TEXTS = [
    "Extending adjuvant endocrine therapy beyond five years reduced recurrence",
    "The extended duration group reported more musculoskeletal adverse events",
    "No overall survival difference reached significance at the reported follow up",
]

#: Real spans from the conftest article, so the guard passes on them.
SPANS = [
    "reduced recurrence in the trial cohort",
    "reported more musculoskeletal adverse events",
    "No overall survival difference reached significance",
]


class ScriptedJudge:
    """A judge that splits on a fixed rule and returns verdicts from a list. No network, no model."""

    model = "scripted-1"

    def __init__(self, verdicts, spans=None):
        self.verdicts = list(verdicts)
        self.spans = list(spans or [])
        self.calls: list[dict] = []

    def complete_json(self, **kwargs):
        self.calls.append(kwargs)
        if kwargs["purpose"] == "split":
            return {
                "claims": [{"text": t, "markers": ["[1]"]} for t in CLAIM_TEXTS],
                "skipped": [{"text": "Give feedback", "reason": "interface furniture"}],
            }
        verdict = self.verdicts.pop(0) if self.verdicts else NOT_FOUND_IN_SOURCE
        span = self.spans.pop(0) if self.spans else ""
        return {"verdict": verdict, "span": span, "reasoning": "scripted", "notes": ""}


def all_supported():
    return ScriptedJudge([SUPPORTED] * 3, list(SPANS))


def scripted_split_sha() -> str:
    """The split hash this judge always produces. Deterministic, so a gold set can be built for it."""
    from sayswho.claims import Claim
    from sayswho.splits import split_digest

    return split_digest([Claim(id="", text=t, markers=["[1]"]) for t in CLAIM_TEXTS])


def gold_for(url, labels, tmp_path, name="gold.json"):
    """A gold set bound to the scripted judge's split, so gate G4 passes and a rate may be printed."""
    from sayswho.claims import claim_id
    from sayswho.goldset import GoldLabel, GoldSet

    return GoldSet(
        split_sha256=scripted_split_sha(),
        judge_class="ScriptedJudge",
        judge_model="scripted-1",
        judge_prompt_version="judge-v1",
        claim_prompt_version="claims-v1",
        created_at="2026-08-08T00:00:00+00:00",
        labels=[
            GoldLabel(
                claim_id=claim_id("PR-01", text, {}), url=url, label=label,
                labelled_at="2026-08-08T00:00:00+00:00", labeller="jayanth",
            )
            for text, label in labels
        ],
        labeller="jayanth",
    ).save(tmp_path / name)


@pytest.fixture
def capture_file(tmp_path, server):
    def make(query_id="PR-01", product="chatgpt", name="capture.json"):
        capture = Capture(
            query_id=query_id,
            product=product,
            model_id="test",
            generated_at="2026-08-08T00:00:00+00:00",
            captured_at="2026-08-08T00:00:01+00:00",
            answer_text=ANSWER,
            citations=[Citation(marker="[1]", url=server.url("/ok.html"))],
        )
        path = tmp_path / name
        path.write_text(json.dumps(capture.to_dict()))
        return path

    return make


@pytest.fixture
def frozen(tmp_path, monkeypatch):
    """A frozen stratum with PR-01 in it, patched in place of the repo's own."""
    import sayswho.queryset as queryset

    queries = tmp_path / "queries"
    queries.mkdir()
    (queries / "professional.toml").write_text(
        '[stratum]\nid = "professional_research"\nid_prefix = "PR"\nstatus = "ready"\n\n'
        '[[query]]\nid = "PR-01"\ndomain = "competitive"\ntext = "A real question."\n'
        'cost_of_error = "Concrete."\n'
    )
    manifest = tmp_path / "FREEZE.json"
    manifest.write_text(json.dumps({
        "version": 1, "unfreezes": [],
        "frozen": {"professional.toml": {
            "frozen_at": "2026-08-11T00:00:00+00:00", "file_sha256": "x",
            "stratum_id": "professional_research", "query_count": 1,
            "query_hashes": {"PR-01": "hash"},
        }},
    }))
    monkeypatch.setattr(queryset, "QUERIES_DIR", queries)
    monkeypatch.setattr(queryset, "MANIFEST", manifest)
    return queries, manifest


def go(paths, cache_root, judge=None, **kw):
    """Run the harness with drift off and the freeze check skipped, both of which need the network."""
    if judge is not None:
        import sayswho.gemini as gemini

        kw.setdefault("judge", True)
        original = gemini.build_judge
        gemini.build_judge = lambda provider=None, meter=None: judge
        try:
            return run_stratum(
                paths, cache_dir=cache_root, drift=False, skip_freeze_check=True, **kw
            )
        finally:
            gemini.build_judge = original
    return run_stratum(paths, cache_dir=cache_root, drift=False, skip_freeze_check=True, **kw)


# ---------------------------------------------------------------- the run itself


def test_without_a_gold_set_every_rate_that_needs_a_calibrated_judge_is_withheld(
    tmp_path, server, capture_file, frozen
):
    """Gate G4, at the level a reader sees. The verdicts are all there and no percentage is."""
    run = go([capture_file()], tmp_path / "cache", judge=all_supported())

    assert len(run.runs[0].judgements) == 3
    assert run.aggregate_rate is None
    assert any("NO_CALIBRATION" in w for w in run.runs[0].rates.withheld)
    assert "per-claim verdicts still emit" in readout(run).lower()


def test_a_bound_capture_with_a_gold_set_produces_a_stratum_rate(
    tmp_path, server, capture_file, frozen
):
    gold = gold_for(server.url("/ok.html"), [(t, SUPPORTED) for t in CLAIM_TEXTS], tmp_path)
    run = go([capture_file()], tmp_path / "cache", judge=all_supported(), goldset_path=gold)

    assert run.runs[0].bound.ok
    assert run.runs[0].eligible_for_aggregate
    assert run.aggregate_rate is not None
    assert (run.aggregate_rate.hits, run.aggregate_rate.n) == (3, 3)
    assert "single-stratum" in run.aggregate_rate.note.lower()


def test_an_unbound_capture_is_audited_and_kept_out_of_the_aggregate(tmp_path, server, capture_file, frozen):
    """Per-claim verdicts stand. The rate does not, because a rate has to say what it is a rate over."""
    gold = gold_for(server.url("/ok.html"), [(t, SUPPORTED) for t in CLAIM_TEXTS], tmp_path)
    run = go(
        [capture_file(query_id="UNASSIGNED")], tmp_path / "cache",
        judge=all_supported(), goldset_path=gold,
    )

    assert run.runs[0].judgements, "it was still audited"
    assert not run.runs[0].eligible_for_aggregate
    assert run.aggregate_rate is None
    assert "not bound to a query" in run.aggregate_refused


def test_a_google_capture_reports_per_product_and_never_in_the_stratum_rate(
    tmp_path, server, capture_file, frozen
):
    gold = gold_for(server.url("/ok.html"), [(t, SUPPORTED) for t in CLAIM_TEXTS], tmp_path)
    run = go(
        [capture_file(product="google")], tmp_path / "cache",
        judge=all_supported(), goldset_path=gold,
    )

    assert not run.runs[0].eligible_for_aggregate
    assert run.aggregate_rate is None
    assert "google" in run.per_product, "excluded from the aggregate, not deleted"
    assert run.per_product["google"].n == 3


def test_a_fabricated_span_leaves_the_numerator_and_the_denominator_together(
    tmp_path, server, capture_file, frozen
):
    gold = gold_for(server.url("/ok.html"), [(t, SUPPORTED) for t in CLAIM_TEXTS], tmp_path)
    judge = ScriptedJudge(
        [SUPPORTED, SUPPORTED, SUPPORTED],
        [SPANS[0], SPANS[1], "a sentence that is nowhere on this page"],
    )
    run = go([capture_file()], tmp_path / "cache", judge=judge, goldset_path=gold)

    rate = run.aggregate_rate
    assert (rate.hits, rate.n) == (2, 2), "the voided verdict left both sides, not just the numerator"
    fabricated = next(
        r for r in run.runs[0].rates.rates if r.name == "judge-fabricated-span rate"
    )
    assert (fabricated.hits, fabricated.n) == (1, 3)


def test_more_than_half_unmeasurable_withholds_the_rate_even_with_a_gold_set(
    tmp_path, server, capture_file, frozen
):
    """INSUFFICIENT_EVIDENCE. Two of three verdicts voided, so what is left is a rate over whatever
    happened to survive rather than a rate over the answer."""
    gold = gold_for(server.url("/ok.html"), [(t, SUPPORTED) for t in CLAIM_TEXTS], tmp_path)
    judge = ScriptedJudge([SUPPORTED] * 3, [SPANS[0], "not on the page", "also not on the page"])
    run = go([capture_file()], tmp_path / "cache", judge=judge, goldset_path=gold)

    assert run.aggregate_rate is None
    assert any("INSUFFICIENT_EVIDENCE" in w for w in run.runs[0].rates.withheld)


def test_the_judge_is_never_called_on_an_unreadable_source(tmp_path, server, frozen):
    """Not "the verdict is discarded". No call at all."""
    capture = Capture(
        query_id="PR-01", product="chatgpt", model_id="test",
        generated_at="2026-08-08T00:00:00+00:00", captured_at="2026-08-08T00:00:01+00:00",
        answer_text=ANSWER,
        citations=[Citation(marker="[1]", url=server.url("/missing.html"))],
    )
    path = tmp_path / "c.json"
    path.write_text(json.dumps(capture.to_dict()))

    judge = ScriptedJudge([SUPPORTED])
    run = go([path], tmp_path / "cache", judge=judge)

    assert not run.runs[0].judgements
    assert not any(c["purpose"] == "judge" for c in judge.calls)


def test_a_run_with_no_captures_says_which_kind_of_nothing_it_is(tmp_path):
    run = run_stratum([], cache_dir=tmp_path / "cache", drift=False, skip_freeze_check=True)
    assert run.aggregate_rate is None
    assert "No run is eligible" in run.aggregate_refused


def test_a_broken_freeze_halts_the_whole_run(tmp_path, monkeypatch):
    from sayswho import harness

    monkeypatch.setattr(harness, "freeze_intact", lambda: (False, "PR-02 was EDITED after the freeze"))
    with pytest.raises(harness.FreezeBroken) as exc:
        run_stratum([], cache_dir=tmp_path / "cache")
    assert "EDITED after the freeze" in str(exc.value)


# ---------------------------------------------------------------- the readout and the artefacts


def test_the_readout_carries_n_and_an_interval_for_every_rate(tmp_path, server, capture_file, frozen):
    gold = gold_for(server.url("/ok.html"), [(t, SUPPORTED) for t in CLAIM_TEXTS], tmp_path)
    text = readout(go([capture_file()], tmp_path / "cache", judge=all_supported(), goldset_path=gold))
    assert "95% CI" in text
    assert "n=" in text
    assert "single-stratum" in text


def test_the_readout_states_the_conflict_next_to_the_google_number(
    tmp_path, server, capture_file, frozen
):
    gold = gold_for(server.url("/ok.html"), [(t, SUPPORTED) for t in CLAIM_TEXTS], tmp_path)
    text = readout(
        go([capture_file(product="google")], tmp_path / "cache", judge=all_supported(), goldset_path=gold)
    )
    assert "vendor scoring its own product" in text
    assert "never in the stratum rate above" in text


def test_the_trace_table_names_the_function_and_the_records_behind_each_figure(
    tmp_path, server, capture_file, frozen
):
    gold = gold_for(server.url("/ok.html"), [(t, SUPPORTED) for t in CLAIM_TEXTS], tmp_path)
    table = trace_table(go([capture_file()], tmp_path / "cache", judge=all_supported(), goldset_path=gold))
    assert "rates.aggregate" in table
    assert "rates.support_rate" in table
    assert "capture.json" in table
    assert "PR-01" in table


def test_the_trace_table_of_an_empty_run_says_there_is_nothing_to_trace(tmp_path):
    table = trace_table(run_stratum([], cache_dir=tmp_path / "cache", drift=False, skip_freeze_check=True))
    assert "nothing to trace" in table


def test_the_artefacts_are_written_and_pass_the_no_confidence_gate(
    tmp_path, server, capture_file, frozen
):
    judge = ScriptedJudge([SUPPORTED, NOT_FOUND_IN_SOURCE, SUPPORTED], [SPANS[0], "", SPANS[2]])
    run = go([capture_file()], tmp_path / "cache", judge=judge)
    written = save(run, tmp_path / "out")

    assert set(written) == {"json", "readout", "log", "trace"}
    for path in written.values():
        assert path.exists() and path.stat().st_size > 0
    assert "## Run" in written["log"].read_text()


def test_the_run_record_never_carries_page_text(tmp_path, server, capture_file, frozen):
    """DATA_CONTRACT.md §9. The repo publishes verdicts and spans, not copies of the pages."""
    run = go([capture_file()], tmp_path / "cache", judge=all_supported())
    blob = json.dumps(run.to_dict())
    assert "musculoskeletal adverse events, and that discontinuation rates rose" not in blob


# ---------------------------------------------------------------- the gold set, wired in


def test_a_gold_set_labelled_before_the_run_produces_an_agreement_number(
    tmp_path, server, capture_file, frozen
):
    from sayswho.claims import claim_id
    from sayswho.goldset import GoldLabel, GoldSet

    text_a = "Extending adjuvant endocrine therapy beyond five years reduced recurrence"
    text_b = "The extended duration group reported more musculoskeletal adverse events"
    url = server.url("/ok.html")

    gold = GoldSet(
        split_sha256="unchecked-here",
        judge_class="ScriptedJudge", judge_model="scripted-1",
        judge_prompt_version="judge-v1", claim_prompt_version="claims-v1",
        created_at="2026-08-08T00:00:00+00:00",
        labels=[
            GoldLabel(claim_id=claim_id("PR-01", text_a, {}), url=url, label=SUPPORTED,
                      labelled_at="2026-08-08T00:00:00+00:00", labeller="jayanth"),
            GoldLabel(claim_id=claim_id("PR-01", text_b, {}), url=url, label=NOT_FOUND_IN_SOURCE,
                      labelled_at="2026-08-08T00:00:00+00:00", labeller="jayanth"),
        ],
    )
    path = gold.save(tmp_path / "gold.json")

    judge = ScriptedJudge([SUPPORTED, SUPPORTED], ["reduced recurrence", "adverse events"])
    run = go([capture_file()], tmp_path / "cache", judge=judge, goldset_path=path)

    assert run.agreement is not None
    assert run.agreement.compared == 2
    assert "kappa" in readout(run)
