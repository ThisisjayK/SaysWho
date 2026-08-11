"""What gate G1 skipped, counted in a unit that is not "whatever the DOM handed us as one block".

`FINDINGS.md` item 9. The splitter returns skipped items in the shape they arrived in, and a DOM capture
hands it a whole table as one text block. So one skip decision discarded roughly ninety checkable cells
while a two-word heading also counted as one, and the published skip rate was a count of blocks wearing the
label "share of the answer that went unchecked". Those are different numbers and only one of them is what a
reader would take from it.

Two things here, both of them measurements rather than fixes:

- `segment` breaks a block into the units a reader would count: table rows, list items, sentences. The skip
  rate is then reported in those units as well as in blocks, and the two are published together because the
  gap between them is the finding.
- `looks_factual` marks skipped units that carry a number or two proper nouns. Four uncited factual lines
  were found by hand in the day 3 run, which made `uncited_claim_count` a floor with an unknown gap. This
  makes the gap measured rather than unknown. It is still a floor: a qualitative factual sentence with no
  number and no name in it is invisible to this, and `SCOPE.md` §7 keeps saying so.

Nothing here re-splits the answer or touches `answer_text`, which is hashed and verbatim. It counts.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

#: A row of a table, as innerText delivers one: cells joined by tabs.
_TABLE_ROW = re.compile(r"\t")

#: A list item, as innerText delivers one. Markdown bullets survive the DOM in every product seen so far.
_BULLET = re.compile(r"^\s*(?:[-*•–]|\d+[.)])\s+")

#: Sentence ends. Deliberately crude: a decimal point or an abbreviation will occasionally split one
#: sentence into two. That errs towards counting more units, which errs towards reporting a *higher* skip
#: rate, which is the direction an honest error should go here.
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+(?=[A-Z(\"'“])")

#: Numbers of two digits or more. Same rule as the extraction check in judge.py: a "3" is not evidence.
_NUMBER = re.compile(r"\d[\d,.]*%?")
_PROPER = re.compile(r"\b[A-Z][A-Za-z\-']{3,}\b")

#: Interface text that rides along in a DOM capture. Matched whole, case-insensitively, so a sentence that
#: merely contains one of these words is not written off as furniture.
_FURNITURE = frozenset(
    {
        "give feedback", "copy", "share", "sources", "retry", "edit", "regenerate",
        "show more", "show less", "read more", "learn more", "see all", "expand",
        "was this helpful", "good response", "bad response", "related", "people also ask",
    }
)


@dataclass
class Unit:
    """One checkable thing inside a skipped block."""

    text: str
    kind: str  # "row", "item", "sentence"
    cells: int = 1

    @property
    def factual(self) -> bool:
        return looks_factual(self.text)


def is_furniture(text: str) -> bool:
    flat = " ".join(text.split()).strip().casefold().rstrip(".:")
    return flat in _FURNITURE or len(flat) <= 2


def looks_factual(text: str) -> bool:
    """A skipped unit that asserts something checkable, by the same crude test the extraction check uses.

    One number of two digits or more, or two capitalised words. Two proper nouns rather than one, because a
    sentence's first word is capitalised and a single name proves nothing.

    A floor. "The rule changed last year" has neither and is entirely factual.
    """
    if is_furniture(text):
        return False
    if len(text.split()) < 4:
        return False
    if [t for t in _NUMBER.findall(text) if len(re.sub(r"\D", "", t)) >= 2]:
        return True
    return len(set(_PROPER.findall(text))) >= 2


def segment(text: str) -> list[Unit]:
    """Break one block into the units a reader would count.

    Order matters. A table row is a row even when it contains three sentences, and a bullet is an item even
    when it contains none, so the structural tests come before the sentence one.
    """
    if not text or not text.strip():
        return []

    units: list[Unit] = []
    for line in text.splitlines():
        if not line.strip():
            continue

        if _TABLE_ROW.search(line):
            cells = [c for c in line.split("\t") if c.strip()]
            units.append(Unit(text=" | ".join(c.strip() for c in cells), kind="row", cells=len(cells)))
            continue

        if _BULLET.match(line):
            units.append(Unit(text=_BULLET.sub("", line).strip(), kind="item"))
            continue

        parts = [p.strip() for p in _SENTENCE_END.split(line.strip()) if p.strip()]
        for part in parts:
            units.append(Unit(text=part, kind="sentence"))

    return units


@dataclass
class SkipReport:
    """The skip rate in both units, plus what the difference between them is made of."""

    skipped_blocks: int
    claim_blocks: int
    skipped_units: int
    claim_units: int
    skipped_cells: int
    tables: int
    furniture_units: int
    factual_units: int
    examples: list[str] = field(default_factory=list)

    @property
    def block_rate(self) -> float | None:
        total = self.skipped_blocks + self.claim_blocks
        return self.skipped_blocks / total if total else None

    @property
    def unit_rate(self) -> float | None:
        total = self.skipped_units + self.claim_units
        return self.skipped_units / total if total else None

    def to_dict(self) -> dict[str, Any]:
        return {
            "skipped_blocks": self.skipped_blocks,
            "claim_blocks": self.claim_blocks,
            "skipped_units": self.skipped_units,
            "claim_units": self.claim_units,
            "skipped_cells": self.skipped_cells,
            "tables_skipped_whole": self.tables,
            "furniture_units": self.furniture_units,
            "factual_units_skipped": self.factual_units,
            "block_rate": self.block_rate,
            "unit_rate": self.unit_rate,
            "factual_examples": self.examples,
            "note": (
                "Two skip rates, published together. The block rate is what the splitter returned; the unit "
                "rate counts table rows, list items and sentences. `factual_units_skipped` is a floor on "
                "the checkable content that never reached a judge: it only sees units carrying a number or "
                "two proper nouns."
            ),
        }

    def render(self) -> str:
        lines = []
        if self.block_rate is not None:
            lines.append(
                f"G1 skip      {self.skipped_blocks} of {self.skipped_blocks + self.claim_blocks} blocks "
                f"({self.block_rate:.1%}), which is the number the splitter returns"
            )
        if self.unit_rate is not None:
            lines.append(
                f"             {self.skipped_units} of {self.skipped_units + self.claim_units} units "
                f"({self.unit_rate:.1%}) counting table rows, list items and sentences"
            )
        if self.tables:
            lines.append(
                f"             {self.tables} table(s) skipped whole, holding {self.skipped_cells} cells. "
                "One skip decision, that much content"
            )
        lines.append(
            f"             {self.factual_units} skipped unit(s) carry a number or two proper nouns and were "
            "never checked. A floor: a factual sentence with neither is invisible to this count"
        )
        if self.furniture_units:
            lines.append(f"             {self.furniture_units} skipped unit(s) are interface furniture")
        return "\n".join(lines)


def analyse(claim_set, examples: int = 5) -> SkipReport:
    """Count a split's skips in blocks and in units, and find the factual content inside them."""
    skipped_units: list[Unit] = []
    tables = 0
    cells = 0
    for item in claim_set.skipped:
        units = segment(item.text)
        if any(u.kind == "row" for u in units):
            tables += 1
            cells += sum(u.cells for u in units if u.kind == "row")
        skipped_units.extend(units)

    claim_units = sum(len(segment(c.text)) or 1 for c in claim_set.claims)

    factual = [u for u in skipped_units if u.factual]
    return SkipReport(
        skipped_blocks=len(claim_set.skipped),
        claim_blocks=len(claim_set.claims),
        skipped_units=len(skipped_units),
        claim_units=claim_units,
        skipped_cells=cells,
        tables=tables,
        furniture_units=sum(1 for u in skipped_units if is_furniture(u.text)),
        factual_units=len(factual),
        examples=[" ".join(u.text.split())[:200] for u in factual[:examples]],
    )


def uncited_floor(claim_set) -> dict[str, Any]:
    """`uncited_claim_count`, restated as a floor with the gap measured rather than unknown.

    §7 offers the uncited count as the evidence about omission blindness. It counts sentences the splitter
    kept and found no citation on. It does not count the factual sentences the splitter dropped at G1, and
    four of those were found by hand in the day 3 run. This adds that second number so the floor has a
    measured distance under it instead of an unknown one.
    """
    report = analyse(claim_set)
    return {
        "uncited_claim_count": claim_set.uncited_count,
        "factual_units_skipped_at_g1": report.factual_units,
        "floor": claim_set.uncited_count,
        "measured_gap": report.factual_units,
        "note": (
            "The published uncited count is the first number. The second is factual-looking content that "
            "never became a claim at all, so the true count of unsupported assertions is at least the sum "
            "and this is still a floor: a factual sentence with no number and no proper noun in it is "
            "invisible to both."
        ),
    }
