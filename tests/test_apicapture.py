"""Capturing from a provider API rather than from a rendered page.

The risk this file guards is the one that made the API path worth building: a capture that quietly holds a
subset of an answer's citations, which nothing downstream can detect because the rate comes out over whatever
was captured and looks normal.

So these tests are mostly about the walk *reporting* what it did not take. A parser that returns two
citations out of five is a bug; a parser that returns two and says it left three URLs on the floor is a bug
that announces itself, and the second is what this file requires.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

from sayswho.apicapture import (
    CITATION_LIST_KEYS,
    PROVIDERS,
    ask,
    build,
    walk_answer_text,
    walk_citations,
)

# Four response shapes, deliberately different from each other. They are hand-built from documented shapes
# and are NOT captured from live calls, which is exactly why nothing here asserts that any provider returns
# one of them. What they test is that the walk does not need to know which provider produced which.
ANNOTATED_BLOCK = {
    "output": [
        {
            "content": [
                {
                    "text": "Boston reported 77.0 percent screening participation among female residents.",
                    "annotations": [
                        {
                            "type": "url_citation",
                            "url": "https://www.boston.gov/a.pdf",
                            "title": "boston.gov",
                            "start_index": 0,
                            "end_index": 20,
                        }
                    ],
                }
            ]
        }
    ]
}

BARE_LIST = {
    "choices": [{"message": {"content": "Uptake rose in the intervention group relative to usual care."}}],
    "citations": ["https://example.org/one", "https://example.org/two"],
}

NESTED_CHUNKS = {
    "candidates": [
        {
            "content": {"parts": [{"text": "Navigation improved timeliness of treatment in the cohort."}]},
            "groundingMetadata": {
                "groundingChunks": [{"web": {"uri": "https://aacrjournals.org/x", "title": "aacr"}}]
            },
        }
    ]
}

TOOL_BLOCKS = {
    "content": [
        {"type": "text", "text": "The programme ran across eleven sites over four years in total."},
        {
            "type": "web_search_tool_result",
            "content": [{"type": "web_search_result", "url": "https://bmc.org/y", "title": "BMC"}],
        },
    ]
}

ALL_SHAPES = {
    "annotated block": (ANNOTATED_BLOCK, 1),
    "bare list": (BARE_LIST, 2),
    "nested chunks": (NESTED_CHUNKS, 1),
    "tool blocks": (TOOL_BLOCKS, 1),
}


# ---------------------------------------------------------------- the walk


@pytest.mark.parametrize("name", sorted(ALL_SHAPES))
def test_citations_are_found_without_knowing_the_schema(name):
    payload, expected = ALL_SHAPES[name]
    found, unclaimed = walk_citations(payload)
    assert len(found) == expected
    assert not unclaimed, "nothing should be left on the floor for these shapes"


@pytest.mark.parametrize("name", sorted(ALL_SHAPES))
def test_the_answer_text_is_found_and_its_path_is_recorded(name):
    payload, _ = ALL_SHAPES[name]
    text, path = walk_answer_text(payload)
    assert len(text) > 40
    assert path.startswith("$"), "the path is how a person confirms the right field was taken"
    assert not text.startswith("http")


def test_every_citation_carries_the_path_it_was_found_at():
    """Verification for an API capture is reading the stored response against the capture. Without the path
    that means searching a response by eye."""
    found, _ = walk_citations(NESTED_CHUNKS)
    assert found[0].path == "$.candidates[0].groundingMetadata.groundingChunks[0].web"


def test_offsets_are_taken_only_when_the_provider_supplies_them():
    """An offset this code invented would put a mark beside the wrong sentence."""
    annotated, _ = walk_citations(ANNOTATED_BLOCK)
    assert (annotated[0].start, annotated[0].end) == (0, 20)
    bare, _ = walk_citations(BARE_LIST)
    assert bare[0].start is None and bare[0].end is None


def test_a_url_under_an_unrecognised_key_is_reported_not_dropped():
    """The whole design. The first version of this walk returned zero citations for the bare-list shape, and
    the only reason that was visible is that the two URLs were counted as not taken."""
    payload = {"text": "an answer with several words in it", "evidence": [{"webAddress": "https://a.org/1"}]}
    found, unclaimed = walk_citations(payload)
    assert found == []
    assert unclaimed == ["https://a.org/1"]


def test_a_list_of_urls_that_is_not_citations_is_not_taken_as_citations():
    """`CITATION_LIST_KEYS` is a guess from a key name, so it must not be a greedy one."""
    payload = {"text": "an answer with words", "debug": {"trace_urls": ["https://internal.example/log"]}}
    found, unclaimed = walk_citations(payload)
    assert found == []
    assert unclaimed == ["https://internal.example/log"]


def test_urls_inside_a_citation_object_are_not_double_counted():
    payload = {
        "text": "an answer with words in it",
        "citations": [{"url": "https://a.org/1", "cached": "https://cache.example/a"}],
    }
    found, unclaimed = walk_citations(payload)
    assert [f.url for f in found] == ["https://a.org/1"]
    assert unclaimed == [], "the cached copy belongs to the citation, not to the floor"


def test_the_same_url_twice_is_one_citation():
    payload = {"text": "an answer with words", "citations": ["https://a.org/1", "https://a.org/1"]}
    found, _ = walk_citations(payload)
    assert len(found) == 1


# ---------------------------------------------------------------- the capture it builds


def test_an_api_capture_is_an_ordinary_capture_the_pipeline_can_audit():
    result = build(ANNOTATED_BLOCK, "openai", query_id="PR-01", model="test-model")
    record = result.capture

    assert record.source == "api"
    assert record.product == "api:openai"
    assert record.query_id == "PR-01"
    assert [c.url for c in record.citations] == ["https://www.boston.gov/a.pdf"]
    assert record.answer_sha256, "hashed like any other capture"


def test_an_api_capture_is_never_born_verified():
    """Structured is easier to read correctly, not automatically read correctly. Same rule as a DOM adapter."""
    result = build(NESTED_CHUNKS, "gemini")
    assert result.capture.adapter_verified is False
    assert result.provenance()["verified"] is False


def test_the_provenance_records_what_was_taken_and_what_was_not():
    payload = {"text": "an answer with words", "evidence": [{"webAddress": "https://a.org/1"}]}
    result = build(payload, "mystery")
    prov = result.provenance()

    assert prov["citations_found"] == 0
    assert prov["urls_not_taken_as_citations"] == 1
    assert prov["answer_path"] == "$.text"


def test_a_marker_falls_back_to_a_position_rather_than_being_invented():
    result = build(BARE_LIST, "perplexity")
    assert [c.marker for c in result.capture.citations] == ["[pos:1]", "[pos:2]"]


def test_a_title_becomes_the_marker_when_there_is_one():
    result = build(NESTED_CHUNKS, "gemini")
    assert result.capture.citations[0].marker == "aacr"


def test_the_rendered_report_says_it_is_unverified():
    text = build(ANNOTATED_BLOCK, "openai").render()
    assert "verified   False" in text
    assert "Read the stored response against this capture" in text


# ---------------------------------------------------------------- live calls


def test_only_providers_with_a_written_request_builder_can_be_called():
    """A request builder that has never been executed is a guess wearing the same clothes as working code."""
    with pytest.raises(ValueError) as exc:
        ask("perplexity", "a question")
    assert "--from" in str(exc.value), "it has to point at the path that does work"


def test_a_live_call_with_no_key_says_which_variable(monkeypatch):
    for name in PROVIDERS["gemini"]["env"]:
        monkeypatch.delenv(name, raising=False)
    with pytest.raises(RuntimeError) as exc:
        ask("gemini", "a question")
    assert "GEMINI_API_KEY" in str(exc.value)
    assert "never written to a file" in str(exc.value)


def test_the_gemini_request_asks_for_grounding():
    """Without a search tool the answer has no citations, and G0 would correctly halt on every capture."""
    source = (Path(__file__).resolve().parent.parent / "sayswho" / "apicapture.py").read_text()
    assert '"tools": [{"google_search": {}}]' in source


def test_gemini_is_marked_conflicted():
    """A Google model answering and a Google model judging. `rates.CONFLICTED_PRODUCTS` already refuses to
    put a Google surface in a cross-product aggregate."""
    assert PROVIDERS["gemini"]["conflicted"] is True


def test_no_test_here_makes_a_network_call():
    """Recorded shapes only. A suite that calls a paid API is a suite nobody runs, and one that calls a free
    one is a suite that fails when the rate limit is hit.

    Checked by imports rather than by scanning for the call, because a test asserting a string is absent from
    its own file cannot mention that string. Which is what the first version of this did.
    """
    import ast

    tree = ast.parse(Path(__file__).read_text())
    imported = {
        node.module.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    } | {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    assert not imported & {"urllib", "requests", "http", "socket"}, f"network imports: {imported}"


# ---------------------------------------------------------------- the fidelity comparison


def dom_record(urls, answer="Boston reported high screening participation among female residents."):
    from sayswho.records import Capture, Citation

    return Capture(
        query_id="PR-01", product="perplexity", model_id="sonar",
        generated_at="2026-08-11T21:00:00+00:00", captured_at="2026-08-11T21:00:01+00:00",
        answer_text=answer,
        citations=[Citation(marker="m", url=u) for u in urls],
        adapter="perplexity:.prose", adapter_verified=False,
    ).to_dict()


def test_the_comparison_names_what_the_dom_capture_missed():
    """The number that has never existed for this project: how much of an answer the scraper did not see."""
    from compare_capture import report

    dom = dom_record(["https://a.org/1"])
    api = build(
        {"text": "Boston reported high screening participation among female residents.",
         "citations": ["https://a.org/1", "https://b.org/2"]},
        "perplexity",
    ).capture.to_dict()

    text = report(dom, api)
    assert "api only      1" in text
    assert "b.org" in text


def test_a_url_differing_only_in_tracking_is_not_counted_as_missed():
    """`?utm_source=chatgpt.com` is on half the citations these products emit."""
    from compare_capture import report

    dom = dom_record(["https://a.org/1?utm_source=chatgpt.com"])
    api = build({"text": "an answer with several words", "citations": ["https://a.org/1"]},
                "perplexity").capture.to_dict()
    assert "in both       1" in report(dom, api)


def test_two_unrelated_answers_are_reported_as_not_comparable():
    """Same question is not same answer. Without this the api-only column reads as a scraper fault when it is
    two models citing different things."""
    from compare_capture import report

    dom = dom_record(["https://a.org/1"], answer="Screening uptake in Massachusetts rose over the period.")
    api = build(
        {"text": "Entirely different prose concerning municipal transport funding and bus routes.",
         "citations": ["https://b.org/2"]},
        "perplexity",
    ).capture.to_dict()

    text = report(dom, api)
    assert "barely overlap" in text
    assert "Read this as almost nothing" in text


def test_the_comparison_never_claims_to_be_ground_truth():
    from compare_capture import report

    text = report(dom_record(["https://a.org/1"]), build({"text": "an answer here", "citations": []},
                                                         "perplexity").capture.to_dict())
    assert "Not a ground truth" in text


def test_already_known_hidden_citations_are_kept_separate():
    """The "+N" chips are a subset the capture already declared. Folding them in would double-count."""
    from compare_capture import report

    dom = dom_record(["https://a.org/1"])
    dom["citations_possibly_hidden"] = 2
    dom["expanders_seen"] = 1
    api = build({"text": "an answer with words", "citations": ["https://a.org/1"]},
                "perplexity").capture.to_dict()

    text = report(dom, api)
    assert "already reported 2 citation(s) hidden" in text
    assert "separate from anything above" in text
