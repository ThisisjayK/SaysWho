"""No confidence number appears in any output surface. `SCOPE.md` §1b, day 4 in `TODO.md`.

The invariant is not "we did not add a confidence score". It is that adding one later has to fail a test.
So this walks every surface that reaches a reader and asserts two different things about each:

- every structured payload passes the key gate in `gates.assert_no_confidence_number`
- every rendered surface contains no confidence vocabulary at all, with one deliberate exception: the word
  "score" appears in the extension and in the report, always inside a sentence that refuses to produce one.
  Those sentences are listed here by hand. A new use of the word fails this test, which is the point: the
  allowlist is the review step.

A test that only checked the payloads would miss a percentage rendered into HTML. A test that only grepped
the HTML would miss a field added to the JSON that a future surface then displays.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from sayswho.claims import Claim, ClaimSet, Skipped
from sayswho.gates import assert_no_confidence_number
from sayswho.goldset import GoldLabel, GoldSet, agreement, attribution, coverage
from sayswho.judge import SUPPORTED, Judgement
from sayswho.rates import Pair, for_run, support_rate, unauditable_rate
from sayswho.records import SOURCE_OK, SOURCE_PAYWALLED, Capture, Citation, FetchRecord
from sayswho.report import build as build_report, strip_for_gate_check
from sayswho.skips import analyse as analyse_skips, uncited_floor

REPO = Path(__file__).resolve().parent.parent

#: Vocabulary that must not reach a reader, in any surface.
BANNED_WORDS = ("confidence", "certainty", "probability", "likelihood", "trust score", "reliability score")

#: The only sentences in the project allowed to contain the word "score". Every one of them refuses to
#: produce one. Adding a use of the word means adding it here, deliberately, in a diff someone reviews.
SCORE_ALLOWLIST = (
    "No overall score. ",
    "G0 will return NO_CITATIONS and refuse to score it.",
    "No support rate is shown.",
    "The judge declined to answer, so this claim was not scored.",
)

SURFACE_FILES = [
    "extension/src/popup.html",
    "extension/src/popup.css",
    "extension/src/popup.js",
    "extension/src/render.js",
    "extension/src/render.css",
    "extension/src/report.html",
    "extension/src/report-page.js",
    "extension/src/content.js",
    "extension/src/capture.js",
    "extension/src/background.js",
    "extension/src/adapters.js",
]


# ---------------------------------------------------------------- fixtures for a full payload


def a_run():
    capture = Capture(
        query_id="PR-01", product="chatgpt", model_id="test",
        generated_at="2026-08-11T00:00:00+00:00", captured_at="2026-08-11T00:00:01+00:00",
        answer_text="Extending therapy reduced recurrence [1]. A paywalled thing [2].",
        citations=[
            Citation(marker="[1]", url="https://a.example/1"),
            Citation(marker="[2]", url="https://b.example/2"),
        ],
    )
    claim_set = ClaimSet(
        claims=[
            Claim(id="c1", text="Extending therapy reduced recurrence", markers=["[1]"],
                  urls=["https://a.example/1"]),
            Claim(id="c2", text="A paywalled thing", markers=["[2]"], urls=["https://b.example/2"]),
        ],
        skipped=[Skipped(text="Give feedback", reason="interface furniture")],
    )
    records = [
        FetchRecord(url="https://a.example/1", code=SOURCE_OK, fetched_at="t",
                    text="Extending therapy reduced recurrence in the cohort."),
        FetchRecord(url="https://b.example/2", code=SOURCE_PAYWALLED, fetched_at="t"),
    ]
    judgements = [
        Judgement(claim_id="c1", url="https://a.example/1", verdict=SUPPORTED,
                  span="reduced recurrence in the cohort", span_verified=True),
    ]
    return capture, claim_set, records, judgements


# ---------------------------------------------------------------- structured payloads


def test_the_report_payload_passes_the_gate():
    capture, claim_set, records, judgements = a_run()
    payload = build_report(capture, records, claim_set, judgements).payload
    assert_no_confidence_number(strip_for_gate_check(payload))


def test_the_rates_record_passes_the_gate():
    capture, claim_set, records, judgements = a_run()
    assert_no_confidence_number(for_run(capture, claim_set, records, judgements).to_dict())


def test_the_skip_and_uncited_records_pass_the_gate():
    _, claim_set, _, _ = a_run()
    assert_no_confidence_number(analyse_skips(claim_set).to_dict())
    assert_no_confidence_number(uncited_floor(claim_set))


def test_the_gold_set_records_pass_the_gate():
    gold = GoldSet(
        split_sha256="a" * 64, judge_class="X", judge_model="y",
        judge_prompt_version="judge-v1", claim_prompt_version="claims-v1",
        created_at="2026-08-11T00:00:00+00:00",
        labels=[GoldLabel(claim_id="c1", url="https://a.example/1", label=SUPPORTED,
                          labelled_at="2026-08-11T00:00:00+00:00")],
    )
    judgements = [Judgement(claim_id="c1", url="https://a.example/1", verdict=SUPPORTED, span_verified=True)]
    assert_no_confidence_number(gold.to_dict())
    assert_no_confidence_number(agreement(gold, judgements).to_dict())
    assert_no_confidence_number(attribution(gold, judgements).to_dict())
    assert_no_confidence_number(coverage(gold))


def test_a_single_rate_passes_the_gate():
    pairs = [Pair(claim_id="c1", url="https://a.example/1", source_code=SOURCE_OK, verdict=SUPPORTED)]
    assert_no_confidence_number(support_rate(pairs).to_dict())
    assert_no_confidence_number(unauditable_rate(pairs).to_dict())


def test_the_capture_and_fetch_records_pass_the_gate():
    capture, _, records, _ = a_run()
    assert_no_confidence_number(capture.to_dict())
    for record in records:
        assert_no_confidence_number(record.to_dict())


# ---------------------------------------------------------------- rendered surfaces


def visible_text(path: Path) -> str:
    return (REPO / path).read_text(encoding="utf-8")


@pytest.mark.parametrize("filename", SURFACE_FILES)
def test_no_confidence_vocabulary_in_the_extension(filename):
    text = visible_text(Path(filename)).lower()
    for word in BANNED_WORDS:
        assert word not in text, f"{filename} contains {word!r}"


@pytest.mark.parametrize("filename", SURFACE_FILES)
def test_every_use_of_the_word_score_is_a_refusal(filename):
    """The allowlist is the review step. A new use of the word has to be added here on purpose."""
    text = visible_text(Path(filename))
    for match in re.finditer(r"[Ss]cor(e|ing|ed)", text):
        window = text[max(0, match.start() - 60): match.end() + 40]
        assert any(allowed in window for allowed in SCORE_ALLOWLIST), (
            f"{filename} uses the word 'score' outside the allowlist: ...{window.strip()}..."
        )


def test_the_rendered_html_report_carries_no_confidence_vocabulary():
    capture, claim_set, records, judgements = a_run()
    html = build_report(capture, records, claim_set, judgements).to_html().lower()
    for word in BANNED_WORDS:
        assert word not in html, f"the rendered report contains {word!r}"


def test_the_rendered_html_report_shows_no_percentage_at_all():
    """Gate G4 withholds the aggregate rate, and the view is what a reader actually looks at. A percentage
    appearing here would be a number the run refused to print, rendered anyway.

    The stylesheet is cut out first: `width: 50%` is a layout rule, not a claim about anything. What is
    left is the renderer's own strings and the payload, which is where a rate would have to come from.
    """
    capture, claim_set, records, judgements = a_run()
    html = build_report(capture, records, claim_set, judgements).to_html()
    body = re.sub(r"<style>.*?</style>", "", html, flags=re.S)
    hit = re.search(r"\d+(\.\d+)?\s*%", body)
    assert not hit, f"a percentage reached the report view: {body[max(0, hit.start() - 80):hit.end() + 20]}"


def test_the_harness_readout_and_trace_carry_no_confidence_vocabulary(tmp_path):
    from sayswho.harness import readout, run_log, run_stratum, trace_table

    run = run_stratum([], cache_dir=tmp_path / "cache", drift=False, skip_freeze_check=True)
    for text in (readout(run), trace_table(run), run_log(run)):
        lowered = text.lower()
        for word in BANNED_WORDS:
            assert word not in lowered, f"the readout contains {word!r}"


def test_the_cli_json_payload_passes_the_gate(capsys):
    """The real surface, produced by the real command, not a reconstruction of it."""
    from sayswho.cli import main

    code = main([str(REPO / "fixtures" / "example-capture.json"), "--no-drift", "--json"])
    assert code == 0
    out = capsys.readouterr().out
    payload = json.loads(out[out.index("{"):])
    assert_no_confidence_number(strip_for_gate_check(payload))


# ---------------------------------------------------------------- the gate itself still fires


def test_the_gate_would_catch_a_confidence_field_added_to_the_report():
    """If this ever passes silently, every test above is decoration."""
    capture, claim_set, records, judgements = a_run()
    payload = build_report(capture, records, claim_set, judgements).payload
    payload["claims"][0]["confidence"] = 0.87
    with pytest.raises(AssertionError):
        assert_no_confidence_number(strip_for_gate_check(payload))
