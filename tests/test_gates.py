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


def test_capture_carries_its_adapter_provenance():
    """An unverified adapter can miss citations, and a short capture looks exactly like a short answer."""
    c = Capture(
        query_id="PR-01",
        product="claude",
        model_id="test",
        generated_at="2026-08-07T00:00:00+00:00",
        captured_at="2026-08-07T00:00:01+00:00",
        answer_text="A claim [1].",
        citations=[Citation(marker="[1]", url="https://example.org/a")],
        adapter="claude:[data-testid=assistant-message]",
        adapter_verified=False,
    )
    d = c.to_dict()
    assert d["adapter_verified"] is False
    assert Capture.from_dict(d).adapter == c.adapter


# ---------------------------------------------------------------- URL normalisation


def test_tracking_parameters_are_stripped_for_fetching():
    """ChatGPT appends ?utm_source=chatgpt.com to every citation it emits.

    Left alone, the same page cited three times becomes three fetches and three cache entries, and the
    publisher receives an analytics tag from us that they would attribute to a product we are auditing.
    """
    from sayswho.records import normalise_url

    assert normalise_url("https://www.bmc.org/x?utm_source=chatgpt.com") == "https://www.bmc.org/x"


def test_meaningful_query_parameters_survive_normalisation():
    """Stripping the whole query string would break a citation whose parameters carry the identity."""
    from sayswho.records import normalise_url

    url = "https://www.cancer.gov/v?id=NCI-2021-00403&r=1&utm_source=chatgpt.com"
    assert normalise_url(url) == "https://www.cancer.gov/v?id=NCI-2021-00403&r=1"


def test_one_page_cited_three_times_with_different_tags_is_one_fetch():
    base = "https://www.bmc.org/navigator"
    c = Capture(
        query_id="PR-01",
        product="chatgpt",
        model_id="test",
        generated_at="2026-08-07T00:00:00+00:00",
        captured_at="2026-08-07T00:00:01+00:00",
        answer_text="A claim [1][2][3].",
        citations=[
            Citation(marker="BMC", url=f"{base}?utm_source=chatgpt.com"),
            Citation(marker="BMC +1", url=f"{base}?utm_source=chatgpt.com"),
            Citation(marker="[pos:3]", url=base),
        ],
    )
    assert c.cited_urls == [base]


# ---------------------------------------------------------------- incomplete captures


def test_a_capture_with_hidden_citations_says_so():
    """Perplexity and ChatGPT hide extra sources behind a "+N" control.

    A capture that is quietly short computes a support rate over a subset of the answer and looks entirely
    normal doing it. This is the one thing about a capture that cannot be allowed to stay silent.
    """
    c = Capture(
        query_id="PR-01",
        product="perplexity",
        model_id="test",
        generated_at="2026-08-07T00:00:00+00:00",
        captured_at="2026-08-07T00:00:01+00:00",
        answer_text="A claim.",
        citations=[Citation(marker="boston", url="https://boston.gov/a")],
        citations_possibly_hidden=6,
        expanders_seen=6,
    )
    assert c.capture_is_known_incomplete


def test_a_complete_capture_does_not_claim_to_be_incomplete():
    c = Capture(
        query_id="PR-01",
        product="claude",
        model_id="test",
        generated_at="2026-08-07T00:00:00+00:00",
        captured_at="2026-08-07T00:00:01+00:00",
        answer_text="A claim.",
        citations=[Citation(marker="[1]", url="https://example.org/a")],
    )
    assert not c.capture_is_known_incomplete
