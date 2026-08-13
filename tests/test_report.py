"""The marking view.

The view is where a careful pipeline can still tell a lie, because a reader takes a mark at face value and
never sees the record behind it. So these tests are mostly about what must not appear: a claim whose source
could not be read must not look unsupported, a voided verdict must not look supported, and nothing anywhere
may carry a confidence number.
"""

from __future__ import annotations

import json
import pathlib

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
    PARTIAL,
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


def test_a_decomposed_accent_in_the_answer_still_marks_the_right_characters():
    """The reason the accent fold in `extract.py` was left undone for a week. Folding accents means a folded
    character count that no longer matches the raw one, and this index is what would have broken: it maps
    folded positions back to real ones so the highlight lands on the right words.

    It holds because the fold decomposes rather than composes, so one input character still produces zero or
    more output characters and the mapping stays one way. Here the answer carries "Rene" plus a combining
    acute, five characters, and the claim carries a precomposed one, four. The offsets returned have to be the
    answer's, not the claim's, or a reader gets a mark one character short of the sentence."""
    sentence = "The trial by Rene\u0301 Dubois reported a fall."
    answer = sentence + "\n\nA second paragraph follows."
    claim_text = "The trial by Ren\u00e9 Dubois reported a fall."
    assert len(claim_text) < len(sentence), "the two forms have to differ in length or this proves nothing"

    start, end = locate(answer, claim_text)
    assert answer[start:end] == sentence
    assert answer[end:].startswith("\n\nA second"), "the mark stopped where the sentence did"


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


def test_partial_support_is_neither_a_failure_nor_a_full_support():
    """It used to roll up into SUPPORTED, so a claim whose only verdict was "supports part of this" was
    marked green and labelled "Supported by the cited source". `missing_qualifiers` made that indefensible
    on screen: the card read "Supported by the cited source" above a list saying "association, claim says
    reduction". Rounding a verdict up while the evidence underneath says otherwise is the move the honesty
    rules exist to forbid.

    The other direction matters just as much, which is what this test was originally guarding: partial
    support is not a citation failure and must not be shown as one."""
    state = claim_state([row(PARTIALLY_SUPPORTED)], has_citation=True)
    assert state == PARTIAL
    assert state != SUPPORTED_STATE
    assert state != NOT_SUPPORTED


def test_one_full_support_does_not_cancel_a_partial_one():
    """Never round up. Two sources, one stating the claim and one stating a weaker version, is not the same
    finding as two sources stating it."""
    assert claim_state([row(SUPPORTED), row(PARTIALLY_SUPPORTED)], has_citation=True) == PARTIAL


def test_two_partials_do_not_add_up_to_a_full_support():
    assert claim_state([row(PARTIALLY_SUPPORTED), row(PARTIALLY_SUPPORTED)], has_citation=True) == PARTIAL


def test_every_state_has_a_label_and_a_help_line():
    """A state with no words is a colour, and colour is never the only carrier here."""
    from sayswho.report import STATE_HELP, STATE_LABELS

    for state in (SUPPORTED_STATE, PARTIAL, NOT_SUPPORTED, MIXED, COULD_NOT_VERIFY, NOT_CHECKED):
        assert STATE_LABELS.get(state), state
        assert STATE_HELP.get(state), state


def test_not_found_and_contradicted_both_read_as_not_supported():
    assert claim_state([row(NOT_FOUND_IN_SOURCE)], has_citation=True) == NOT_SUPPORTED
    assert claim_state([row(CONTRADICTED)], has_citation=True) == NOT_SUPPORTED


def test_disagreeing_sources_are_not_averaged():
    """Claim #009 on the first real run: supported by one source, not-found by two."""
    state = claim_state([row(SUPPORTED), row(NOT_FOUND_IN_SOURCE), row(NOT_FOUND_IN_SOURCE)],
                        has_citation=True)
    assert state == MIXED, (
        "the rollup names the disagreement; the rate counts all three pairs rather than averaging them"
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


# ---------------------------------------------------------------- the unit, in the payload


def test_the_payload_states_the_unit_and_its_n():
    """Every rate is over claim-source pairs, so the view carries the unit and the denominator rather than
    leaving a reader to infer which one a number was counted in."""
    pairs = _report().payload["counts"]["pairs"]

    assert pairs["unit"] == "claim-source pair"
    assert pairs["standing"] <= pairs["total"]
    assert pairs["standing"] + pairs["unauditable"] == pairs["total"]


def test_the_denominator_comes_from_the_one_function_that_owns_it():
    """report.py used to grow its own pair counter. A second implementation of a denominator is what
    standing_denominator exists to prevent, and one file away is the easiest place for it to appear."""
    source = pathlib.Path(__file__).resolve().parent.parent.joinpath("sayswho", "report.py").read_text()
    assert "from .rates import" in source
    assert "standing_denominator(pairs)" in source
    assert "def pair_counts" not in source, "the duplicate is gone"


def test_a_claim_with_three_sources_contributes_three_pairs():
    """The reason the unit matters. Claim #009 came back SUPPORTED by one source and NOT_FOUND by two, and
    the claim-level rollup has to pick one colour for the sentence while the rate counts all three."""
    from sayswho.claims import Claim, ClaimSet
    from sayswho.judge import NOT_FOUND_IN_SOURCE, SUPPORTED, Judgement
    from sayswho.records import SOURCE_OK, Capture, Citation, FetchRecord

    urls = [f"https://example.org/{n}" for n in "abc"]
    text = "Screening uptake rose in the intervention group."
    capture = Capture(
        query_id="PR-01", product="chatgpt", model_id="m",
        generated_at="2026-08-11T00:00:00+00:00", captured_at="2026-08-11T00:00:01+00:00",
        answer_text=text + " [1][2][3]",
        citations=[Citation(marker=f"[{i}]", url=u) for i, u in enumerate(urls, start=1)],
    )
    records = [
        FetchRecord(url=u, code=SOURCE_OK, fetched_at="t", text=text, text_length=len(text))
        for u in urls
    ]
    claims = ClaimSet(claims=[Claim(id="PR-01#009", text=text, markers=["[1]"], urls=urls)], skipped=[])
    judgements = [
        Judgement(claim_id="PR-01#009", url=urls[0], verdict=SUPPORTED, span=text, span_verified=True),
        Judgement(claim_id="PR-01#009", url=urls[1], verdict=NOT_FOUND_IN_SOURCE),
        Judgement(claim_id="PR-01#009", url=urls[2], verdict=NOT_FOUND_IN_SOURCE),
    ]

    payload = build(capture, records, claims, judgements).payload

    assert payload["counts"]["claims"] == 1
    assert payload["counts"]["pairs"]["total"] == 3
    assert payload["counts"]["pairs"]["standing"] == 3
    assert payload["counts"]["pairs"]["multi_source_claims"] == 1
    assert payload["counts"]["states"] == {"MIXED": 1}, "the rollup names the disagreement honestly"


def test_missing_qualifiers_reach_the_view():
    """The field only earns its keep if the reader sees it."""
    from sayswho.claims import Claim, ClaimSet
    from sayswho.judge import PARTIALLY_SUPPORTED, Judgement
    from sayswho.records import SOURCE_OK, Capture, Citation, FetchRecord

    text = "Screening uptake rose in the intervention group."
    url = "https://example.org/a"
    capture = Capture(
        query_id="PR-01", product="chatgpt", model_id="m",
        generated_at="2026-08-11T00:00:00+00:00", captured_at="2026-08-11T00:00:01+00:00",
        answer_text=text + " [1]", citations=[Citation(marker="[1]", url=url)],
    )
    payload = build(
        capture,
        [FetchRecord(url=url, code=SOURCE_OK, fetched_at="t", text=text, text_length=len(text))],
        ClaimSet(claims=[Claim(id="c1", text=text, markers=["[1]"], urls=[url])], skipped=[]),
        [Judgement(
            claim_id="c1", url=url, verdict=PARTIALLY_SUPPORTED, span=text, span_verified=True,
            missing_qualifiers=["observational, not causal", "US sample only"],
        )],
    ).payload

    row = payload["claims"][0]["sources"][0]
    assert row["missing_qualifiers"] == ["observational, not causal", "US sample only"]
    assert row["partial_without_qualifiers"] is False
