"""Named citation detection.

The examples below are lifted from a real Claude Research report captured on 2026-08-07. The false positive
tests matter more than the true positive ones: this count gets published, so a pattern that fires on ordinary
prose inflates a finding.
"""

from __future__ import annotations

import pytest

from sayswho.named_citations import (
    AUTHOR_ETAL_YEAR,
    DOI,
    PUBLISHED_IN,
    TRIAL_ID,
    YEAR_JOURNAL_STUDY,
    find_named_citations,
)


def kinds(text):
    return [c.kind for c in find_named_citations(text)]


def texts(text):
    return [c.text for c in find_named_citations(text)]


# ---------------------------------------------------------------- real examples


@pytest.mark.parametrize(
    "sentence",
    [
        "a peer-reviewed assessment (LeClair et al., Supportive Care in Cancer, 2022) found variation",
        "TRIP navigation economics (Rajabiun et al., Cancer, 2025;131(1):e35671): across 223 patients",
        "the model (Yala, Mikhael, Lehman, Barzilay et al., Science Translational Medicine, 2021)",
        "TRIP effectiveness (AACR Abstract A039, 2023, Battaglia et al.) across 1,732 women",
    ],
)
def test_author_et_al_with_a_year_is_detected(sentence):
    assert find_named_citations(sentence), f"missed a named citation in: {sentence}"


def test_trial_registration_id():
    found = find_named_citations("The TRIP protocol (clinicaltrials.gov NCT03514433) documents a ratio")
    assert TRIAL_ID in [c.kind for c in found]
    assert "NCT03514433" in texts("clinicaltrials.gov NCT03514433")


def test_bare_doi():
    assert DOI in kinds("See 10.1200/JCO.2021.39.15_suppl.1503 for the full results.")


def test_published_in_journal_and_year():
    assert PUBLISHED_IN in kinds("Its ASSURE study, published in Nature Health (Nov 2025), compared")


def test_year_then_journal_then_study():
    assert YEAR_JOURNAL_STUDY in kinds("Boston ranked fifth (2014 Cancer Epidemiology study).")


def test_the_real_report_yields_a_meaningful_count():
    """A condensed excerpt of the captured report. The point is that it is many, not one."""
    excerpt = """
    A peer-reviewed assessment (LeClair et al., Supportive Care in Cancer, 2022) found significant variation.
    The TRIP protocol (clinicaltrials.gov NCT03514433) documents a Boston mortality rate ratio of 1.36.
    Its ASSURE study, published in Nature Health (Nov 2025), compared an AI-driven workflow.
    Mirai (Yala, Mikhael, Lehman, Barzilay et al., Science Translational Medicine, 2021) was trained on MGH data.
    TRIP navigation economics (Rajabiun et al., Cancer, 2025;131(1):e35671) reported cost per patient.
    Boston ranked fifth among major US cities (2014 Cancer Epidemiology study).
    """
    found = find_named_citations(excerpt)
    assert len(found) >= 6, f"expected at least six, got {[c.text for c in found]}"


# ---------------------------------------------------------------- false positives


@pytest.mark.parametrize(
    "sentence",
    [
        # Straight from the captured report. Years in ordinary prose are everywhere.
        "founded 2014 by Dana-Farber and the Boston Public Health Commission",
        "Its Mammography Van (since April 2002, a joint venture with the City of Boston)",
        "a fixed Mammography Suite at Whittier Street Health Center (since 2013, open Mon/Wed)",
        "Clairity, Inc. (Boston) was founded 2020 by Dr. Connie Lehman",
        "The US breast cancer screening tests market was estimated at ~$4.75B in 2025",
        "MGB's United Against Racism initiative (launched Fall 2020)",
        "Whittier Street Health Center (Roxbury FQHC, founded 1933, $28.4M FY2020 revenue)",
    ],
)
def test_ordinary_prose_with_a_year_is_not_a_citation(sentence):
    """A false positive inflates a published number, so the patterns stay narrow."""
    assert find_named_citations(sentence) == [], f"false positive on: {sentence}"


def test_a_sentence_with_no_year_and_no_identifier_is_not_a_citation():
    assert find_named_citations("Dana-Farber owns the mobile and community access niche.") == []


# ---------------------------------------------------------------- overlaps


def test_one_source_matched_by_two_patterns_is_counted_once():
    """Double counting would inflate the finding just as badly as a false positive."""
    sentence = "published in Nature Health (Nov 2025), Smith et al., Nature Health, 2025 reported"
    found = find_named_citations(sentence)
    spans = [(c.start, c.end) for c in found]
    for a, b in zip(spans, spans[1:]):
        assert a[1] <= b[0], "overlapping matches were kept"


def test_results_come_back_in_document_order():
    text = "First (Alpha et al., Journal, 2020). Later NCT12345678 appears."
    found = find_named_citations(text)
    assert [c.start for c in found] == sorted(c.start for c in found)
