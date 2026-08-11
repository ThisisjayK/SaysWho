"""Per-domain reporting. `SCOPE.md` §0a item 9.

The risk this file guards is a published table that reads as a league table of publishers when it is really
a diagnostic about this pipeline, plus the ordinary one: a slice is still a rate, and slicing a number that
may not be printed does not make it printable.
"""

from __future__ import annotations

import pytest

from sayswho.domains import DomainRow, by_domain, registrable_domain, render
from sayswho.gates import DenominatorContract
from sayswho.judge import CONTRADICTED, NOT_FOUND_IN_SOURCE, SUPPORTED
from sayswho.rates import Pair
from sayswho.records import SOURCE_OK, SOURCE_PAYWALLED


def pair(url, verdict=SUPPORTED, code=SOURCE_OK, voided=False, reason=""):
    return Pair(claim_id="c", url=url, source_code=code, verdict=verdict, voided=voided, void_reason=reason)


class Passed:
    passed = True
    detail = ""


class Refused:
    passed = False
    detail = "gate G4: no gold set for this judge and prompt version"


# ---------------------------------------------------------------- grouping


@pytest.mark.parametrize(
    "url,expected",
    [
        ("https://www.bmc.org/patient-care/x", "bmc.org"),
        ("https://bmc.org/x", "bmc.org"),
        ("https://patients.bmc.org/x", "bmc.org"),
        ("https://www.ncbi.nlm.nih.gov/pmc/articles/PMC1", "nih.gov"),
        ("https://www.gov.uk/guidance", "www.gov.uk"),
        ("https://digital.nhs.uk/data", "digital.nhs.uk"),
        ("https://example.com.au/page", "example.com.au"),
        ("not a url at all", ""),
        ("https://192.168.0.1/x", "192.168.0.1"),
    ],
)
def test_urls_group_by_publisher(url, expected):
    assert registrable_domain(url) == expected


def test_subdomains_of_one_publisher_are_one_row():
    """Splitting www from bare would halve an already small n."""
    rows = by_domain([pair("https://www.bmc.org/a"), pair("https://bmc.org/b")], calibration=Passed())
    assert len(rows) == 1
    assert rows[0].pairs == 2


def test_rows_are_sorted_by_size():
    rows = by_domain(
        [pair("https://a.org/1"), pair("https://b.org/1"), pair("https://b.org/2")],
        calibration=Passed(),
    )
    assert [r.domain for r in rows] == ["b.org", "a.org"]


# ---------------------------------------------------------------- the denominator, per slice


def test_an_unauditable_pair_never_enters_a_domain_denominator():
    rows = by_domain(
        [
            pair("https://a.org/1"),
            pair("https://a.org/2", verdict=NOT_FOUND_IN_SOURCE),
            pair("https://a.org/3", verdict="", code=SOURCE_PAYWALLED),
        ],
        calibration=Passed(),
    )
    row = rows[0]
    assert row.pairs == 3
    assert row.standing == 2
    assert row.unauditable == 1
    assert row.rate.n == 2, "the paywalled pair is out of the denominator, not counted as unsupported"
    assert row.rate.hits == 1


def test_a_contaminated_slice_raises_like_the_aggregate_does():
    """Break attempt 6, through the per-domain door.

    `standing` cannot be true for an unauditable source by construction, so the violation has to be forced
    the same way `test_rates.py` forces it: by overriding the property. The point is that `by_domain` calls
    `standing_denominator` per group rather than counting on its own, so a contaminated denominator cannot
    enter through a slice while the aggregate stays clean.
    """

    class Contaminated(Pair):
        @property
        def standing(self) -> bool:
            return True

    bad = Contaminated(claim_id="c", url="https://a.org/1", source_code=SOURCE_PAYWALLED)
    with pytest.raises(DenominatorContract) as exc:
        by_domain([bad], calibration=Passed())
    assert "cannot enter a denominator" in str(exc.value)


def test_the_reason_a_source_could_not_be_read_is_carried_per_domain():
    """The column that makes this a diagnostic about the tool rather than a ranking of publishers."""
    rows = by_domain(
        [
            pair("https://a.org/1", verdict="", code=SOURCE_PAYWALLED),
            pair("https://a.org/2", verdict="", code=SOURCE_PAYWALLED),
        ],
        calibration=Passed(),
    )
    assert rows[0].source_codes == {SOURCE_PAYWALLED: 2}


# ---------------------------------------------------------------- G4 applies to slices


def test_no_domain_rate_is_printed_when_g4_refuses():
    """A per-domain rate is still a rate. Slicing a forbidden number does not make it printable."""
    rows = by_domain([pair("https://a.org/1"), pair("https://a.org/2")], calibration=Refused())

    assert rows[0].rate is None
    assert "gold set" in rows[0].rate_refused
    assert rows[0].standing == 2, "the counts are still reported"


def test_no_calibration_at_all_also_refuses():
    rows = by_domain([pair("https://a.org/1")], calibration=None)
    assert rows[0].rate is None
    assert "no calibration" in rows[0].rate_refused


def test_a_single_pair_is_not_a_rate():
    """The default. "100.0%" over one observation is the number that gets quoted without its n."""
    rows = by_domain([pair("https://a.org/1")], calibration=Passed())
    assert rows[0].rate is None
    assert "1 readable pair" in rows[0].rate_refused
    assert rows[0].pairs == 1, "the row still appears: a domain seen once is worth seeing"


def test_a_rate_carries_its_n_and_an_interval():
    rows = by_domain(
        [pair("https://a.org/1"), pair("https://a.org/2", verdict=NOT_FOUND_IN_SOURCE)],
        calibration=Passed(),
    )
    rate = rows[0].rate
    assert rate.n == 2 and rate.hits == 1
    assert rate.interval_95 is not None
    assert "confidence" not in str(rate.to_dict()).lower(), "the gate's rule holds here too"


def test_the_rendered_table_carries_the_caveat():
    """"Citations to this site are less supported" is a sentence a reader takes as being about the site."""
    text = render(by_domain([pair("https://a.org/1"), pair("https://a.org/2", verdict=CONTRADICTED)],
                            calibration=Passed()))
    assert "about this pipeline first" in text


def test_an_empty_run_renders_without_pretending_otherwise():
    assert "no cited sources" in render([])


def test_the_payload_has_no_confidence_field_anywhere():
    from sayswho.gates import assert_no_confidence_number

    rows = by_domain([pair("https://a.org/1"), pair("https://a.org/2")], calibration=Passed())
    assert_no_confidence_number([r.to_dict() for r in rows])
