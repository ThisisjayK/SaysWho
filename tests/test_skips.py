"""Skip-unit tests. `FINDINGS.md` item 9.

The bug being measured here is not a crash. It is a published number meaning something narrower than its
label, which is the kind of bug a test suite normally cannot see, so these tests pin the two counts apart
and assert that the gap between them is visible.
"""

from __future__ import annotations

from sayswho.claims import Claim, ClaimSet, Skipped
from sayswho.skips import analyse, is_furniture, looks_factual, segment, uncited_floor

TABLE = (
    "Drug\tTypical dose\tFrequency\n"
    "Lisinopril\t10 mg\tOnce daily\n"
    "Amlodipine\t5 mg\tOnce daily\n"
    "Metformin\t500 mg\tTwice daily\n"
)


def test_a_table_arriving_as_one_block_counts_as_its_rows():
    """One skip decision, four rows, twelve cells. The whole complaint in item 9."""
    units = segment(TABLE)
    assert len(units) == 4
    assert all(u.kind == "row" for u in units)
    assert sum(u.cells for u in units) == 12


def test_a_bullet_list_counts_as_its_items():
    text = "- File within 30 days\n- Keep the receipt\n- Appeal in writing"
    units = segment(text)
    assert len(units) == 3
    assert {u.kind for u in units} == {"item"}


def test_a_paragraph_counts_as_its_sentences():
    text = "The rule changed in 2023. Applicants now file online. The paper form was withdrawn."
    assert len(segment(text)) == 3


def test_a_heading_is_one_unit_and_so_is_a_table_under_the_block_count():
    """Side by side, which is the point: the block count cannot tell these apart and the unit count can."""
    claim_set = ClaimSet(
        claims=[Claim(id="c1", text="A cited claim.", markers=["[1]"], urls=["https://a.example/1"])],
        skipped=[Skipped(text="Dosing", reason="heading"), Skipped(text=TABLE, reason="table")],
    )
    report = analyse(claim_set)
    assert report.skipped_blocks == 2
    assert report.skipped_units == 5
    assert report.tables == 1
    assert report.skipped_cells == 12


def test_the_two_skip_rates_are_published_together():
    claim_set = ClaimSet(
        claims=[Claim(id="c1", text="A cited claim.", markers=["[1]"], urls=["https://a.example/1"])],
        skipped=[Skipped(text=TABLE, reason="table")],
    )
    report = analyse(claim_set)
    assert report.block_rate == 0.5
    assert report.unit_rate == 0.8
    text = report.render()
    assert "blocks" in text and "units" in text
    assert "table(s) skipped whole" in text


# ---------------------------------------------------------------- the factual floor


def test_a_skipped_line_carrying_a_number_is_counted_as_factual():
    assert looks_factual("Applicants must file within 30 days of the notice")


def test_a_skipped_line_carrying_two_proper_nouns_is_counted_as_factual():
    assert looks_factual("The Massachusetts Department of Revenue publishes the schedule")


def test_one_proper_noun_alone_is_not_enough():
    """A sentence's first word is capitalised, so one name proves nothing."""
    assert not looks_factual("Applicants should read the guidance carefully")


def test_interface_furniture_is_not_counted_as_factual():
    for text in ["Give feedback", "Copy", "Show more", "Sources"]:
        assert is_furniture(text)
        assert not looks_factual(text)


def test_the_uncited_floor_reports_a_measured_gap_rather_than_an_unknown_one():
    """§7 offers `uncited_claim_count` as the evidence about omission blindness, and it only counts
    sentences that survived G1. This puts a measured number under it."""
    claim_set = ClaimSet(
        claims=[
            Claim(id="c1", text="A cited claim.", markers=["[1]"], urls=["https://a.example/1"]),
            Claim(id="c2", text="An uncited claim.", markers=[], urls=[]),
        ],
        skipped=[
            Skipped(text="Give feedback", reason="interface"),
            Skipped(text="The deadline moved to 15 April 2026 for all filers.", reason="framing"),
        ],
    )
    floor = uncited_floor(claim_set)
    assert floor["uncited_claim_count"] == 1
    assert floor["measured_gap"] == 1
    assert "still a floor" in floor["note"]


def test_a_qualitative_factual_sentence_is_admitted_to_be_invisible():
    """The honest limit of this count, pinned so nobody later reports it as a total."""
    assert not looks_factual("The rule changed last year and now applies to everyone")


def test_an_empty_split_does_not_divide_by_zero():
    report = analyse(ClaimSet(claims=[], skipped=[]))
    assert report.block_rate is None
    assert report.unit_rate is None
