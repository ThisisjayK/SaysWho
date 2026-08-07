"""Gate tests. Each asserts the gate fires on the bug it exists to catch.

`SCOPE.md` §2: "A gate with no failure path is decoration."
"""

from __future__ import annotations

import pytest

from sayswho.gates import (
    DenominatorContract,
    assert_no_confidence_number,
    auditable_denominator,
    g0_has_citations,
    g2_auditable,
)
from sayswho.records import (
    NO_CITATIONS,
    SOURCE_OK,
    SOURCE_PAYWALLED,
    SOURCE_UNREACHABLE,
    Capture,
    Citation,
    FetchRecord,
)


def capture(citations):
    return Capture(
        query_id="PR-00",
        product="claude",
        model_id="test",
        generated_at="2026-08-07T00:00:00+00:00",
        captured_at="2026-08-07T00:00:01+00:00",
        answer_text="Extending therapy reduced recurrence [1].",
        citations=citations,
    )


def record(code, url="https://example.org/a"):
    return FetchRecord(url=url, code=code, fetched_at="2026-08-07T00:00:02+00:00")


# ---------------------------------------------------------------- G0


def test_g0_fires_on_an_answer_with_no_citations():
    result = g0_has_citations(capture([]))
    assert not result.passed
    assert result.code == NO_CITATIONS


def test_g0_fires_on_a_citation_marker_with_no_url():
    result = g0_has_citations(capture([Citation(marker="[1]", url="  ")]))
    assert not result.passed
    assert result.code == NO_CITATIONS


def test_g0_passes_a_normal_answer():
    assert g0_has_citations(capture([Citation(marker="[1]", url="https://example.org/a")])).passed


# ---------------------------------------------------------------- G2


@pytest.mark.parametrize("code", [SOURCE_UNREACHABLE, SOURCE_PAYWALLED])
def test_g2_stops_a_claim_whose_source_is_not_readable(code):
    result = g2_auditable(record(code))
    assert not result.passed
    assert result.code == code


def test_g2_passes_only_source_ok():
    assert g2_auditable(record(SOURCE_OK)).passed


# ---------------------------------------------------------------- the denominator contract


def test_unauditable_claims_stay_out_of_the_denominator():
    records = [record(SOURCE_OK), record(SOURCE_PAYWALLED), record(SOURCE_UNREACHABLE), record(SOURCE_OK)]
    assert auditable_denominator(records) == 2


def test_forcing_an_unauditable_claim_into_the_denominator_raises():
    """Break attempt 6 in SCOPE.md §6, and it is core rather than stretch.

    A claim that reports itself auditable while carrying a non-OK code is the exact contract violation the
    check exists for. This test manufactures it.
    """
    class Contaminated(FetchRecord):
        """A record that claims to be auditable while carrying a non-OK code."""

        @property
        def auditable(self) -> bool:
            return True

    contaminated = Contaminated(
        url="https://example.org/paywalled",
        code=SOURCE_PAYWALLED,
        fetched_at="2026-08-07T00:00:02+00:00",
    )

    with pytest.raises(DenominatorContract) as exc:
        auditable_denominator([record(SOURCE_OK), contaminated])

    assert "cannot enter a denominator" in str(exc.value)


# ---------------------------------------------------------------- no confidence numbers


def test_a_confidence_field_anywhere_in_the_output_fails():
    payload = {"claims": [{"verdict": "SUPPORTED", "confidence": 0.87}]}
    with pytest.raises(AssertionError) as exc:
        assert_no_confidence_number(payload)
    assert "confidence" in str(exc.value)


def test_a_nested_trust_score_fails():
    payload = {"answer": {"summary": {"trust_score": 91}}}
    with pytest.raises(AssertionError):
        assert_no_confidence_number(payload)


def test_a_clean_payload_passes():
    payload = {
        "claims": [
            {"verdict": "SUPPORTED", "span": "the extended duration group reported more adverse events"},
            {"verdict": "UNAUDITABLE", "reason": SOURCE_PAYWALLED},
        ],
        "auditable": 1,
        "unauditable": 1,
    }
    assert_no_confidence_number(payload)


# ---------------------------------------------------------------- capture integrity


def test_a_capture_whose_answer_was_edited_after_the_fact_is_rejected():
    original = capture([Citation(marker="[1]", url="https://example.org/a")])
    payload = original.to_dict()
    payload["answer_text"] = "Extending therapy did not reduce recurrence [1]."

    with pytest.raises(ValueError) as exc:
        Capture.from_dict(payload)

    assert "not the answer that was delivered" in str(exc.value)


def test_fetch_record_does_not_serialise_page_text():
    """DATA_CONTRACT.md §9: the repo publishes verdicts and spans, not copies of the pages."""
    r = FetchRecord(
        url="https://example.org/a",
        code=SOURCE_OK,
        fetched_at="2026-08-07T00:00:02+00:00",
        text="the entire body of someone else's article",
    )
    assert "text" not in r.to_dict()
