"""The extension and the harness must show the same thing. `SCOPE.md` §9.

The contract is that the interface never disagrees with the audited pipeline. The design that makes it true
is that `sayswho/report.py` computes every state and `extension/src/render.js` computes none, so these tests
run the real renderer, in node, over a payload the real Python built, and compare what appeared on screen
against what Python decided.

A test that only asserted "render.js contains no verdict logic" would be a test about the shape of a file.
This asserts about output, which is what a reader sees and what would actually be a lie if it diverged.

Skipped when node is missing. That is a real gap in coverage on a machine without it, so it is a skip with
a reason rather than a silent pass.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from sayswho.claims import Claim, ClaimSet, Skipped
from sayswho.judge import (
    CONTRADICTED,
    EXTRACTION_SUSPECT,
    JUDGE_FABRICATED_SPAN,
    NOT_FOUND_IN_SOURCE,
    SUPPORTED,
    Judgement,
)
from sayswho.records import SOURCE_OK, SOURCE_PAYWALLED, Capture, Citation, FetchRecord
from sayswho.report import STATE_LABELS, build

REPO = Path(__file__).resolve().parent.parent
RENDERER = REPO / "tests" / "parity" / "render_in_node.mjs"

node = shutil.which("node")
needs_node = pytest.mark.skipif(
    node is None,
    reason="node is not installed, so the extension's renderer cannot be run and the parity check is "
           "genuinely unverified on this machine rather than passing vacuously",
)

ANSWER = (
    "Extending therapy reduced recurrence [1]. "
    "The rule changed in 2023 [2]. "
    "A paywalled source backs this [3]. "
    "This sentence cites nothing at all."
)


def a_payload():
    """One answer covering all five display states, so parity is checked on each rather than on the easy one."""
    capture = Capture(
        query_id="PR-01", product="chatgpt", model_id="test",
        generated_at="2026-08-11T00:00:00+00:00", captured_at="2026-08-11T00:00:01+00:00",
        answer_text=ANSWER,
        citations=[
            Citation(marker="[1]", url="https://a.example/1"),
            Citation(marker="[2]", url="https://b.example/2"),
            Citation(marker="[3]", url="https://c.example/3"),
        ],
    )
    claim_set = ClaimSet(
        claims=[
            # SUPPORTED
            Claim(id="c1", text="Extending therapy reduced recurrence", markers=["[1]"],
                  urls=["https://a.example/1"]),
            # MIXED: one source says yes, another says no
            Claim(id="c2", text="The rule changed in 2023", markers=["[2]", "[1]"],
                  urls=["https://b.example/2", "https://a.example/1"]),
            # COULD_NOT_VERIFY: the only source is paywalled
            Claim(id="c3", text="A paywalled source backs this", markers=["[3]"],
                  urls=["https://c.example/3"]),
            # NOT_CHECKED: no citation
            Claim(id="c4", text="This sentence cites nothing at all", markers=[], urls=[]),
        ],
        skipped=[Skipped(text="Give feedback", reason="interface furniture")],
    )
    records = [
        FetchRecord(url="https://a.example/1", code=SOURCE_OK, fetched_at="t", text="x"),
        FetchRecord(url="https://b.example/2", code=SOURCE_OK, fetched_at="t", text="x"),
        FetchRecord(url="https://c.example/3", code=SOURCE_PAYWALLED, fetched_at="t",
                    detail="a paywall was detected"),
    ]
    judgements = [
        Judgement(claim_id="c1", url="https://a.example/1", verdict=SUPPORTED,
                  span="reduced recurrence in the cohort", span_verified=True),
        Judgement(claim_id="c2", url="https://b.example/2", verdict=SUPPORTED,
                  span="the rule changed in 2023", span_verified=True),
        Judgement(claim_id="c2", url="https://a.example/1", verdict=NOT_FOUND_IN_SOURCE),
    ]
    return build(capture, records, claim_set, judgements)


def render(payload, tmp_path) -> dict:
    path = tmp_path / "payload.json"
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    done = subprocess.run(
        [node, str(RENDERER), str(path)], capture_output=True, text=True, timeout=60, cwd=REPO
    )
    assert done.returncode == 0, done.stderr
    return json.loads(done.stdout)


@pytest.fixture
def rendered(tmp_path):
    report = a_payload()
    return report.payload, render(report.payload, tmp_path)


# ---------------------------------------------------------------- state parity


@needs_node
def test_every_marked_sentence_shows_the_state_python_decided(rendered):
    payload, shown = rendered
    by_text = {c["text"]: c["state"] for c in payload["claims"]}

    assert shown["marks"], "nothing was marked at all, so nothing was compared"
    for mark in shown["marks"]:
        # The renderer marks the answer's own characters, so match on what Python located rather than on
        # the claim text, which can differ in whitespace.
        matching = [state for text, state in by_text.items() if text.strip(". ") in mark["text"]]
        assert matching, f"a mark appeared for text Python never located: {mark['text']!r}"
        assert mark["state"] == matching[0], (
            f"the view shows {mark['state']} where the pipeline decided {matching[0]}"
        )


@needs_node
def test_the_claim_list_shows_pythons_label_for_every_claim(rendered):
    payload, shown = rendered
    expected = [[STATE_LABELS[c["state"]], c["text"]] for c in payload["claims"]]
    listed = [row for row in shown["rows"] if row in expected]
    assert listed == expected, "the claim list disagrees with the payload"


@needs_node
def test_the_legend_counts_match_the_payload_counts(rendered):
    payload, shown = rendered
    for state, label in STATE_LABELS.items():
        assert shown["chips"][label] == payload["counts"]["states"].get(state, 0)


@needs_node
def test_the_renderer_invents_no_state_of_its_own(rendered):
    payload, shown = rendered
    seen = {mark["state"] for mark in shown["marks"]}
    assert seen <= set(STATE_LABELS), f"the view produced states Python does not define: {seen}"


# ---------------------------------------------------------------- card parity


@needs_node
def test_a_supported_claim_shows_the_span_the_guard_verified(rendered):
    payload, shown = rendered
    supported = next(c for c in payload["claims"] if c["state"] == "SUPPORTED")
    span = supported["sources"][0]["span"]
    assert any(span in card["spans"] for card in shown["cards"]), "the verified span was not shown"


@needs_node
def test_a_mixed_claim_shows_both_verdicts_and_averages_neither(rendered):
    payload, shown = rendered
    mixed = next(c for c in payload["claims"] if c["state"] == "MIXED")
    card = next(c for c in shown["cards"] if c["heading"] == STATE_LABELS["MIXED"])
    assert len(card["verdicts"]) == len(mixed["sources"]) == 2
    assert any("states this" in v for v in card["verdicts"])
    assert any("does not state this" in v for v in card["verdicts"])


@needs_node
def test_an_unreadable_source_is_never_rendered_as_a_fact_about_the_claim(rendered):
    payload, shown = rendered
    card = next(c for c in shown["cards"] if c["heading"] == STATE_LABELS["COULD_NOT_VERIFY"])
    joined = " ".join(card["verdicts"])
    assert "Could not read this source" in joined
    assert "does not state" not in joined, "an unreadable source was rendered as a denial"


@needs_node
def test_a_voided_verdict_renders_as_no_verdict_rather_than_a_weaker_one(tmp_path):
    """The failure this guards: a fabricated span shown to a reader as evidence against the product."""
    report = a_payload()
    payload = report.payload
    for claim in payload["claims"]:
        for row in claim["sources"]:
            if row["verdict"] == SUPPORTED:
                row.update(voided=True, void_reason=JUDGE_FABRICATED_SPAN)
    shown = render(payload, tmp_path)

    voided_cards = [c for c in shown["cards"] if c["voids"]]
    assert voided_cards, "nothing rendered as voided"
    for card in voided_cards:
        assert all("No verdict." in v for v in card["voids"])
        assert not card["verdicts"] or all("states this" not in v for v in card["verdicts"])
    notes = " ".join(n for card in voided_cards for n in card["notes"])
    assert "Nothing here says the claim is wrong" in notes


@needs_node
def test_an_extraction_failure_is_rendered_as_our_fault_not_the_sources(tmp_path):
    """`FINDINGS.md` item 11 in the view: the reader is told the reader failed, not the citation."""
    report = a_payload()
    payload = report.payload
    for claim in payload["claims"]:
        for row in claim["sources"]:
            if row["verdict"] == NOT_FOUND_IN_SOURCE:
                row.update(voided=True, void_reason=EXTRACTION_SUSPECT)
    shown = render(payload, tmp_path)
    notes = " ".join(n for card in shown["cards"] for n in card["notes"])
    assert "our reader is the likelier failure, not the source" in notes


# ---------------------------------------------------------------- the refusal survives the round trip


@needs_node
def test_gate_g4s_refusal_reaches_the_reader(rendered):
    payload, shown = rendered
    assert "No overall score." in shown["fullText"]
    assert payload["no_aggregate_rate"] in shown["fullText"]


@needs_node
def test_no_percentage_reaches_the_rendered_view(rendered):
    import re

    _, shown = rendered
    assert not re.search(r"\d+(\.\d+)?\s*%", shown["fullText"])


@needs_node
def test_the_skipped_lines_are_shown_rather_than_discarded(rendered):
    payload, shown = rendered
    assert payload["skipped"][0]["text"] in shown["fullText"]
    assert "lying by omission" in shown["fullText"]


@needs_node
def test_the_standalone_html_report_embeds_the_same_renderer():
    """The harness's HTML report reads render.js off disk, so the two surfaces cannot drift apart."""
    html = a_payload().to_html()
    marker = "window.saysWhoRender = function (root, payload)"
    assert marker in html, "the report embeds something other than the extension's renderer"
    assert marker in (REPO / "extension" / "src" / "render.js").read_text()


@needs_node
def test_the_span_focus_is_marked_and_nothing_is_hidden(tmp_path):
    """The reader gets the whole verified span and a pointer at the part that matters.

    Both halves are the test. Truncating would be tidier and would mean the evidence a reader is shown is
    not the evidence the guard checked.
    """
    report = a_payload()
    payload = report.payload
    span = "Home About Subscribe. Extending therapy reduced recurrence in the cohort. Like us on Facebook."
    focus = "Extending therapy reduced recurrence in the cohort."
    for claim in payload["claims"]:
        for row in claim["sources"]:
            if row["verdict"] == SUPPORTED:
                row["span"] = span
                row["span_focus"] = [span.index(focus), span.index(focus) + len(focus)]

    shown = render(payload, tmp_path)
    marked = [f for card in shown["cards"] for f in card["focus"]]
    assert focus in marked, "the relevant sentence was not marked"

    quoted = " ".join(s for card in shown["cards"] for s in card["spans"])
    for fragment in ("Home About Subscribe.", "Like us on Facebook."):
        assert fragment in quoted, f"{fragment!r} was dropped from the quoted span"


@needs_node
def test_a_span_with_no_focus_still_renders_whole(tmp_path):
    report = a_payload()
    payload = report.payload
    for claim in payload["claims"]:
        for row in claim["sources"]:
            if row["verdict"] == SUPPORTED:
                row["span"] = "Recurrence fell in the extended arm."
                row["span_focus"] = None

    shown = render(payload, tmp_path)
    assert not [f for card in shown["cards"] for f in card["focus"]]
    assert any("Recurrence fell in the extended arm." in s for card in shown["cards"] for s in card["spans"])
