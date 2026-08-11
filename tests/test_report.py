"""The marking view.

The view is where a careful pipeline can still tell a lie, because a reader takes a mark at face value and
never sees the record behind it. So these tests are mostly about what must not appear: a claim whose source
could not be read must not look unsupported, a voided verdict must not look supported, and nothing anywhere
may carry a confidence number.
"""

from __future__ import annotations

import json

from sayswho.claims import Claim, ClaimSet, Skipped
from sayswho.gates import assert_no_confidence_number
from sayswho.judge import (
    CONTRADICTED,
    EXTRACTION_SUSPECT,
    JUDGE_FABRICATED_SPAN,
    NOT_FOUND_IN_SOURCE,
    PARTIALLY_SUPPORTED,
    SUPPORTED,
    Judgement,
)
from sayswho.records import SOURCE_OK, SOURCE_PAYWALLED, Capture, Citation, FetchRecord
from sayswho.report import (
    COULD_NOT_VERIFY,
    MIXED,
    NOT_CHECKED,
    NOT_SUPPORTED,
    SUPPORTED_STATE,
    build,
    claim_state,
    locate,
)

ANSWER = (
    "Screening uptake reached 78% in 2022.\n\n"
    "The programme also offers transport help.\n\n"
    "Boston has six hospitals running navigation programmes."
)


def capture(answer=ANSWER):
    return Capture(
        query_id="PR-01", product="chatgpt", model_id="test",
        generated_at="2026-08-08T00:00:00+00:00", captured_at="2026-08-08T00:00:00+00:00",
        answer_text=answer,
        citations=[Citation(marker="[1]", url="https://example.org/a")],
        adapter="chatgpt", adapter_verified=True,
    )


def source(url="https://example.org/a", code=SOURCE_OK):
    return FetchRecord(url=url, code=code, fetched_at="2026-08-08T00:00:00+00:00", http_status=200,
                       text="Uptake reached 78% in 2022.", text_length=27)


def claim(text="Screening uptake reached 78% in 2022.", urls=("https://example.org/a",)):
    return Claim(id="PR-01#abc12345", text=text, markers=["[1]"], urls=list(urls))


def row(verdict="", voided=False, void_reason=""):
    return {"verdict": verdict, "voided": voided, "void_reason": void_reason}


# ---------------------------------------------------------------- locating a claim in the answer


def test_a_claim_is_located_in_the_answer():
    start, end = locate(ANSWER, "Screening uptake reached 78% in 2022.")
    assert ANSWER[start:end] == "Screening uptake reached 78% in 2022."


def test_a_reflowed_claim_still_locates():
    """The splitter quotes the answer but may normalise its whitespace."""
    start, end = locate(ANSWER, "Screening uptake\n   reached 78%  in 2022.")
    assert ANSWER[start:end] == "Screening uptake reached 78% in 2022."


def test_a_claim_that_is_not_in_the_answer_returns_none():
    assert locate(ANSWER, "A sentence from somewhere else entirely.") is None


def test_unlocatable_claims_are_counted_not_dropped():
    """Claims quoted across a flattened table cannot be marked. They must still be audited and listed."""
    cs = ClaimSet(claims=[claim(text="A sentence that is not in the answer.")], skipped=[])
    report = build(capture(), [source()], cs, [])

    assert report.payload["counts"]["unlocatable"] == 1
    assert len(report.payload["claims"]) == 1, "the claim is still in the record"
    assert report.payload["claims"][0]["start"] is None


# ---------------------------------------------------------------- the state each claim gets


def test_a_supported_claim_reads_as_supported():
    assert claim_state([row(SUPPORTED)], has_citation=True) == SUPPORTED_STATE


def test_partial_support_is_not_a_failure():
    assert claim_state([row(PARTIALLY_SUPPORTED)], has_citation=True) == SUPPORTED_STATE


def test_not_found_and_contradicted_both_read_as_not_supported():
    assert claim_state([row(NOT_FOUND_IN_SOURCE)], has_citation=True) == NOT_SUPPORTED
    assert claim_state([row(CONTRADICTED)], has_citation=True) == NOT_SUPPORTED


def test_disagreeing_sources_are_not_averaged():
    """Claim #009 on the first real run: supported by one source, not-found by two."""
    state = claim_state([row(SUPPORTED), row(NOT_FOUND_IN_SOURCE), row(NOT_FOUND_IN_SOURCE)],
                        has_citation=True)
    assert state == MIXED, (
        "collapsing this would pre-empt the unit-of-the-support-rate decision that is still open"
    )


def test_an_unreadable_source_is_not_an_unsupported_claim():
    """The distinction the whole project rests on, at the surface where a reader would lose it."""
    assert claim_state([row()], has_citation=True) == COULD_NOT_VERIFY


def test_a_fabricated_span_leaves_no_verdict_at_all():
    """A voided SUPPORTED is not supported, and it is not unsupported either."""
    state = claim_state([row(SUPPORTED, voided=True, void_reason=JUDGE_FABRICATED_SPAN)], has_citation=True)
    assert state == COULD_NOT_VERIFY


def test_an_extraction_suspect_void_does_not_accuse_the_source():
    state = claim_state([row(NOT_FOUND_IN_SOURCE, voided=True, void_reason=EXTRACTION_SUSPECT)],
                        has_citation=True)
    assert state == COULD_NOT_VERIFY


def test_a_claim_with_no_citation_is_not_checked():
    assert claim_state([], has_citation=False) == NOT_CHECKED


# ---------------------------------------------------------------- the payload


def _report():
    cs = ClaimSet(
        claims=[claim(), claim(text="The programme also offers transport help.", urls=())],
        skipped=[Skipped(text="1. Boston market landscape", reason="heading")],
    )
    judgements = [
        Judgement(claim_id="PR-01#abc12345", url="https://example.org/a", verdict=SUPPORTED,
                  span="Uptake reached 78% in 2022.", span_verified=True),
    ]
    return build(capture(), [source()], cs, judgements, split_sha256="deadbeef")


def test_the_payload_carries_the_span_the_guard_verified():
    payload = _report().payload
    assert payload["claims"][0]["sources"][0]["span"] == "Uptake reached 78% in 2022."


def test_an_uncited_claim_is_marked_not_checked_in_the_payload():
    payload = _report().payload
    assert payload["claims"][1]["state"] == NOT_CHECKED


def test_skipped_lines_travel_into_the_view():
    """G1's promise is that skipped lines are reported, and the view is where a reader would look."""
    payload = _report().payload
    assert payload["counts"]["skipped"] == 1
    assert payload["skipped"][0]["reason"] == "heading"


def test_the_payload_states_why_there_is_no_overall_score():
    payload = _report().payload
    assert "G4" in payload["no_aggregate_rate"]


def test_no_confidence_number_anywhere_in_the_payload():
    """SCOPE.md §1b, enforced at the surface a reader actually sees."""
    from sayswho.report import strip_for_gate_check

    assert_no_confidence_number(strip_for_gate_check(_report().payload))


def test_the_payload_is_json_serialisable():
    json.loads(_report().to_json())


# ---------------------------------------------------------------- the rendered page


def test_the_html_is_standalone_and_embeds_the_shared_renderer():
    html = _report().to_html()
    assert "saysWhoRender" in html, "the harness must call the same renderer the extension loads"
    assert "<script src=" not in html, "a report has to open with no network and no build step"
    assert "sw-mark" in html or "sw-answer" in html


def test_the_payload_cannot_close_the_script_tag_early():
    """A fetched span containing </script> would end the block and spill the rest as markup."""
    cs = ClaimSet(claims=[claim()], skipped=[])
    judgements = [
        Judgement(claim_id="PR-01#abc12345", url="https://example.org/a", verdict=SUPPORTED,
                  span="</script><h1>injected</h1>", span_verified=True),
    ]
    html = build(capture(), [source()], cs, judgements).to_html()

    assert "</script><h1>injected</h1>" not in html
    assert "<\\/script>" in html


def test_a_paywalled_source_renders_as_unverifiable_rather_than_unsupported():
    cs = ClaimSet(claims=[claim()], skipped=[])
    report = build(capture(), [source(code=SOURCE_PAYWALLED)], cs, [])

    assert report.payload["claims"][0]["state"] == COULD_NOT_VERIFY
    assert report.payload["claims"][0]["sources"][0]["source_code"] == SOURCE_PAYWALLED


# ---------------------------------------------------------------- span focus


def test_the_focus_marks_the_sentence_that_bears_on_the_claim():
    """`TODO.md` day 2: one verified span ran to about 500 characters and included "Like us on Facebook".

    The whole span still ships, because a shortened span is not evidence. This says where to look in it.
    """
    from sayswho.report import span_focus

    span = (
        "Home About Subscribe Donate. "
        "Extending adjuvant endocrine therapy beyond five years reduced recurrence in the trial cohort. "
        "Like us on Facebook."
    )
    lo, hi = span_focus(span, "Extending therapy reduced recurrence")
    assert span[lo:hi].startswith("Extending adjuvant")
    assert span[lo:hi].endswith("trial cohort.")


def test_a_single_sentence_span_gets_no_focus():
    """Marking all of it would say nothing, and would look like a decision that was made."""
    from sayswho.report import span_focus

    assert span_focus("Recurrence fell in the extended arm.", "recurrence fell") is None


def test_a_span_with_no_overlap_gets_no_focus_rather_than_a_guess():
    from sayswho.report import span_focus

    assert span_focus("Home. About. Subscribe.", "adjuvant endocrine therapy recurrence") is None


def test_stopwords_alone_never_choose_a_sentence():
    """Otherwise the furniture sentence with the most "the" in it wins."""
    from sayswho.report import span_focus

    span = "The and of the. Recurrence fell in the extended arm of the trial."
    assert span_focus(span, "the of and") is None


def test_the_focus_offsets_reach_the_payload():
    from sayswho.claims import Claim, ClaimSet
    from sayswho.judge import SUPPORTED, Judgement
    from sayswho.records import SOURCE_OK, Capture, Citation, FetchRecord
    from sayswho.report import build

    span = "Home About. Extending therapy reduced recurrence in the cohort. Like us on Facebook."
    capture = Capture(
        query_id="PR-01", product="chatgpt", model_id="test",
        generated_at="2026-08-11T00:00:00+00:00", captured_at="2026-08-11T00:00:01+00:00",
        answer_text="Extending therapy reduced recurrence [1].",
        citations=[Citation(marker="[1]", url="https://a.example/1")],
    )
    claim_set = ClaimSet(
        claims=[Claim(id="c1", text="Extending therapy reduced recurrence", markers=["[1]"],
                      urls=["https://a.example/1"])],
        skipped=[],
    )
    records = [FetchRecord(url="https://a.example/1", code=SOURCE_OK, fetched_at="t", text=span)]
    judgements = [Judgement(claim_id="c1", url="https://a.example/1", verdict=SUPPORTED,
                            span=span, span_verified=True)]

    row = build(capture, records, claim_set, judgements).payload["claims"][0]["sources"][0]
    lo, hi = row["span_focus"]
    assert span[lo:hi] == "Extending therapy reduced recurrence in the cohort."
    assert row["span"] == span, "the whole span still ships"
