"""Phase 4, the human gold set, and the agreement numbers computed from it.

`SCOPE.md` §3 Phase 4: a hand-labelled sample measures the judge's agreement with a human. This module holds
the file format, the checks that keep the sample honest, and the arithmetic. It does no labelling: that is
`tools/label_goldset.py`, and the labels are the one field in the whole project classified `your-input`.

Four refusals, all of them structural rather than advisory:

- A gold set is bound to the splits it was labelled against, and G4 asks whether the split in front of it is
  one of them. Phase 1 does not return the same split twice, so a set labelled against one split says nothing
  about another. It records a list rather than a single hash because one answer yields perhaps twenty
  labellable pairs and the target is thirty to forty, so a real set spans two or three answers, and the
  sampler stratifies across products, which needs more than one. The single-hash version made the set the
  sampler is built to produce satisfy G4 against nothing at all.
- The recorded splits are the ones that actually produced a label, not the ones offered to the sampler. A set
  claiming an answer nobody got to before quitting would calibrate a run over that answer on no evidence.
- A blind label carries the time it was written, and `agreement` refuses to run if any blind label postdates
  the judge run it is being compared against. Labelling after seeing the judge's answer is not labelling.
- An edited file raises, the same way a stored split does, so a set cannot be quietly corrected after the
  disagreements are known.
- Labels are either blind or supplemental, never mixed in one number. See below.

**Blind versus supplemental, and why the stratification in `SCOPE.md` §3 cannot be done as written.**
The plan says to stratify across verdict classes and fill `CONTRADICTED` first. That is not possible while
labelling blind, because the verdict classes are the judge's output and the point of labelling first is not
to have seen it. What *is* knowable before the judge runs is the product and the G2 source code, so the
blind sample stratifies on those.

If a class comes back empty, the honest move is a clearly separated supplement: pairs chosen after seeing
verdicts, labelled and reported on their own. Those labels carry `blind: false`, they are excluded from
kappa, and their per-class numbers are reported next to the blind ones rather than pooled with them. A kappa
computed over a sample selected using the judge's own output is not an agreement measurement.
"""

from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .judge import CONTRADICTED, NOT_FOUND_IN_SOURCE, PARTIALLY_SUPPORTED, SUPPORTED
from .records import sha256

#: The human may also say the source could not be read. That is a label about the source, not about the
#: claim, and it never enters the agreement arithmetic: the judge is never asked about an unauditable pair,
#: so there is nothing to agree or disagree with.
UNAUDITABLE = "UNAUDITABLE"

#: The human labelled it and could not decide. Recorded rather than forced, and excluded from kappa with
#: the count published. A forced label on an ambiguous pair is noise entered as signal.
UNDECIDABLE = "UNDECIDABLE"

LABELS = (SUPPORTED, PARTIALLY_SUPPORTED, NOT_FOUND_IN_SOURCE, CONTRADICTED, UNAUDITABLE, UNDECIDABLE)

#: Labels that can be compared with a judge verdict.
COMPARABLE = (SUPPORTED, PARTIALLY_SUPPORTED, NOT_FOUND_IN_SOURCE, CONTRADICTED)


class GoldSetContract(Exception):
    """Raised when a gold set is used in a way that would make its numbers mean something else."""


@dataclass
class GoldLabel:
    """One human judgement of one claim against one source. `SCOPE.md` §4 classification: your-input."""

    claim_id: str
    url: str
    label: str
    labelled_at: str
    labeller: str = ""
    #: False for labels chosen after seeing judge output. Excluded from kappa. See the module docstring.
    blind: bool = True
    notes: str = ""

    #: The passage the human found on the real page, when they found one. Their evidence, in their words,
    #: recorded for the same reason the judge has to quote: a label with no passage behind it is an opinion.
    human_span: str = ""

    #: Set by a script, not by the labeller: the human's passage is on the page and is missing from what
    #: this tool extracted. `TODO.md` day 3: "a bad extractor and a bad judge are different problems with
    #: the same symptom", and without this field they arrive at the agreement number as the same symptom.
    #: A human reading the real page marks SUPPORTED, the pipeline said NOT_FOUND_IN_SOURCE, and the
    #: disagreement lands on the judge when it belongs to `extract.py`.
    #:
    #: None means it was not checked: no passage was given, or the fetched text was not available.
    extraction_missed: bool | None = None

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["source"] = "your-input"
        # Except this one, which is a script's answer about the labeller's passage rather than the
        # labeller's judgement. §4 keeps the two apart everywhere else and this record is no exception.
        d["extraction_missed_source"] = "script-output"
        return d


def labels_digest(labels: list[GoldLabel]) -> str:
    """Identity of a gold set's content: every field of every label.

    Over the whole record rather than over the decision alone, so a passage or an extraction finding cannot
    be edited after the disagreements are known while the file still verifies.
    """
    payload = json.dumps(
        sorted(json.dumps(asdict(l), ensure_ascii=False, sort_keys=True) for l in labels),
        ensure_ascii=False,
    )
    return sha256(payload)


def _splits_from(d: dict[str, Any]) -> list[str]:
    """Read the split binding from either shape.

    The field was a single `split_sha256` before a set was ever labelled with it, and a file written then
    would silently bind to nothing under the list reader. There are no such files, and reading both costs
    four lines.
    """
    if "split_sha256s" in d:
        return [s for s in d["split_sha256s"] if s]
    one = d.get("split_sha256", "")
    return [one] if one else []


@dataclass
class GoldSet:
    """A labelled sample, bound to the splits it covers and to one configuration of the pipeline."""

    #: Every split this set carries at least one label for. G4 checks membership, not equality.
    split_sha256s: list[str]
    judge_class: str
    judge_model: str
    judge_prompt_version: str
    claim_prompt_version: str
    created_at: str
    labels: list[GoldLabel] = field(default_factory=list)
    labeller: str = ""
    note: str = ""

    @property
    def labels_sha256(self) -> str:
        return labels_digest(self.labels)

    @property
    def blind(self) -> list[GoldLabel]:
        return [l for l in self.labels if l.blind]

    @property
    def supplemental(self) -> list[GoldLabel]:
        return [l for l in self.labels if not l.blind]

    def to_dict(self) -> dict[str, Any]:
        return {
            "split_sha256s": list(self.split_sha256s),
            "judge_class": self.judge_class,
            "judge_model": self.judge_model,
            "judge_prompt_version": self.judge_prompt_version,
            "claim_prompt_version": self.claim_prompt_version,
            "created_at": self.created_at,
            "labeller": self.labeller,
            "labels_sha256": self.labels_sha256,
            "label_count": len(self.labels),
            "blind_count": len(self.blind),
            "supplemental_count": len(self.supplemental),
            "labels": [l.to_dict() for l in self.labels],
            "note": self.note,
            "_note": (
                "A hand-labelled gold set. Valid only for the split, judge and prompt versions recorded "
                "above. See sayswho/goldset.py."
            ),
        }

    def save(self, path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
        return path

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "GoldSet":
        labels = [
            GoldLabel(
                claim_id=l["claim_id"],
                url=l["url"],
                label=l["label"],
                labelled_at=l.get("labelled_at", ""),
                labeller=l.get("labeller", ""),
                blind=bool(l.get("blind", True)),
                notes=l.get("notes", ""),
                human_span=l.get("human_span", ""),
                extraction_missed=l.get("extraction_missed"),
            )
            for l in d.get("labels", [])
        ]
        unknown = sorted({l.label for l in labels} - set(LABELS))
        if unknown:
            raise GoldSetContract(f"gold set contains labels outside the vocabulary: {unknown}")

        gold = cls(
            split_sha256s=_splits_from(d),
            judge_class=d.get("judge_class", ""),
            judge_model=d.get("judge_model", ""),
            judge_prompt_version=d.get("judge_prompt_version", ""),
            claim_prompt_version=d.get("claim_prompt_version", ""),
            created_at=d.get("created_at", ""),
            labels=labels,
            labeller=d.get("labeller", ""),
            note=d.get("note", ""),
        )

        recorded = d.get("labels_sha256")
        if recorded and recorded != gold.labels_sha256:
            raise GoldSetContract(
                "gold set: recorded labels_sha256 does not match its labels. The file was edited after it "
                "was written, so it is not the set anything was labelled as."
            )
        return gold

    @classmethod
    def load(cls, path) -> "GoldSet":
        with open(path, "rb") as fh:
            return cls.from_dict(json.load(fh))


# ------------------------------------------------------------------ agreement


@dataclass(frozen=True)
class ClassMetrics:
    label: str
    tp: int
    fp: int
    fn: int

    @property
    def precision(self) -> float | None:
        return self.tp / (self.tp + self.fp) if (self.tp + self.fp) else None

    @property
    def recall(self) -> float | None:
        return self.tp / (self.tp + self.fn) if (self.tp + self.fn) else None

    def to_dict(self) -> dict[str, Any]:
        from .rates import wilson_interval

        p_interval = wilson_interval(self.tp, self.tp + self.fp)
        r_interval = wilson_interval(self.tp, self.tp + self.fn)
        return {
            "label": self.label,
            "tp": self.tp,
            "fp": self.fp,
            "fn": self.fn,
            "precision": self.precision,
            "precision_n": self.tp + self.fp,
            "precision_interval_95": list(p_interval) if p_interval else None,
            "recall": self.recall,
            "recall_n": self.tp + self.fn,
            "recall_interval_95": list(r_interval) if r_interval else None,
        }


def cohens_kappa(pairs: list[tuple[str, str]]) -> tuple[float | None, tuple[float, float] | None]:
    """Cohen's kappa and a large-sample interval, over (human, judge) label pairs.

    Returns (None, None) when there is nothing to compute. Returns a kappa with no interval when the raters
    agree perfectly and chance agreement is 1, where the standard error is undefined rather than zero.

    At the core's n this is a wide-interval estimate and `SCOPE.md` §3 says so. It is evidence that the check
    was built and run, not a precise agreement figure, and the writeup does not round it into one.
    """
    n = len(pairs)
    if n == 0:
        return None, None

    classes = sorted({c for pair in pairs for c in pair})
    observed = sum(1 for a, b in pairs if a == b) / n

    human = {c: sum(1 for a, _ in pairs if a == c) / n for c in classes}
    judge = {c: sum(1 for _, b in pairs if b == c) / n for c in classes}
    expected = sum(human[c] * judge[c] for c in classes)

    if expected >= 1.0:
        return (1.0 if observed >= 1.0 else 0.0), None

    kappa = (observed - expected) / (1 - expected)
    variance = observed * (1 - observed) / (n * (1 - expected) ** 2)
    if variance <= 0:
        return kappa, None
    half = 1.959963984540054 * math.sqrt(variance)
    return kappa, (max(-1.0, kappa - half), min(1.0, kappa + half))


@dataclass
class Agreement:
    """What the gold set measured. Every number here is script-output over your-input."""

    compared: int
    human_only_unauditable: int
    undecidable: int
    unmatched: int
    kappa: float | None
    kappa_interval_95: tuple[float, float] | None
    per_class: list[ClassMetrics]
    confusion: dict[str, dict[str, int]]
    supplemental_compared: int = 0
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "compared": self.compared,
            "human_only_unauditable": self.human_only_unauditable,
            "undecidable": self.undecidable,
            "unmatched": self.unmatched,
            "kappa": self.kappa,
            "kappa_interval_95": list(self.kappa_interval_95) if self.kappa_interval_95 else None,
            "per_class": [c.to_dict() for c in self.per_class],
            "confusion": self.confusion,
            "supplemental_compared": self.supplemental_compared,
            "note": self.note,
        }

    def render(self) -> str:
        lines = [f"gold set     {self.compared} blind labels compared against the judge"]
        if self.kappa is None:
            lines.append("kappa        not computable: nothing to compare")
        elif self.kappa_interval_95 is None:
            lines.append(f"kappa        {self.kappa:.3f}, interval undefined at this n")
        else:
            lo, hi = self.kappa_interval_95
            lines.append(
                f"kappa        {self.kappa:.3f}  95% CI {lo:.3f} to {hi:.3f}, n={self.compared}. "
                "A wide-interval estimate, not a calibration"
            )
        for c in self.per_class:
            p = f"{c.precision:.1%}" if c.precision is not None else "n/a"
            r = f"{c.recall:.1%}" if c.recall is not None else "n/a"
            lines.append(
                f"  {c.label:<22} precision {p} (n={c.tp + c.fp})   recall {r} (n={c.tp + c.fn})"
            )
        if self.human_only_unauditable:
            lines.append(
                f"  {self.human_only_unauditable} pair(s) the human marked UNAUDITABLE, excluded: the judge "
                "was never asked about them"
            )
        if self.undecidable:
            lines.append(
                f"  {self.undecidable} pair(s) the human could not decide, recorded and excluded rather "
                "than forced"
            )
        if self.unmatched:
            lines.append(
                f"  {self.unmatched} labelled pair(s) had no standing verdict in this run, excluded"
            )
        if self.supplemental_compared:
            lines.append(
                f"  {self.supplemental_compared} supplemental label(s) reported separately and excluded "
                "from kappa: they were chosen after seeing verdicts"
            )
        return "\n".join(lines)


def agreement(gold: GoldSet, judgements, judge_run_started_at: str = "") -> Agreement:
    """Compare a gold set with a run's verdicts.

    Refuses if any blind label was written after the judge run began. `SCOPE.md` §12 puts the labelling on
    day 5 specifically so it precedes the judge output, and a timestamp check is the only thing that makes
    that an enforced property rather than a claim about my own discipline.
    """
    if judge_run_started_at:
        late = [l for l in gold.blind if l.labelled_at and l.labelled_at > judge_run_started_at]
        if late:
            raise GoldSetContract(
                f"{len(late)} blind label(s) were written after the judge run started "
                f"({judge_run_started_at}). A label written after seeing the judge's answer is not a blind "
                f"label. First offender: {late[0].claim_id} at {late[0].labelled_at}"
            )

    standing = {
        (j.claim_id, j.url): j.verdict
        for j in (judgements or [])
        if not j.voided and j.verdict in COMPARABLE
    }

    compared: list[tuple[str, str]] = []
    unmatched = 0
    human_only_unauditable = 0
    undecidable = 0

    for label in gold.blind:
        if label.label == UNAUDITABLE:
            human_only_unauditable += 1
            continue
        if label.label == UNDECIDABLE:
            undecidable += 1
            continue
        verdict = standing.get((label.claim_id, label.url))
        if verdict is None:
            unmatched += 1
            continue
        compared.append((label.label, verdict))

    kappa, interval = cohens_kappa(compared)

    per_class = []
    for cls in COMPARABLE:
        tp = sum(1 for h, j in compared if h == cls and j == cls)
        fp = sum(1 for h, j in compared if h != cls and j == cls)
        fn = sum(1 for h, j in compared if h == cls and j != cls)
        if tp or fp or fn:
            per_class.append(ClassMetrics(label=cls, tp=tp, fp=fp, fn=fn))

    confusion: dict[str, dict[str, int]] = {}
    for h, j in compared:
        confusion.setdefault(h, {})
        confusion[h][j] = confusion[h].get(j, 0) + 1

    supplemental = sum(
        1 for l in gold.supplemental
        if l.label in COMPARABLE and (l.claim_id, l.url) in standing
    )

    return Agreement(
        compared=len(compared),
        human_only_unauditable=human_only_unauditable,
        undecidable=undecidable,
        unmatched=unmatched,
        kappa=kappa,
        kappa_interval_95=interval,
        per_class=per_class,
        confusion=confusion,
        supplemental_compared=supplemental,
        note=(
            "Single-rater unless a second labeller appears in the labels. One person's labels are a "
            "single-rater ceiling, not ground truth."
        ),
    )


@dataclass
class Attribution:
    """Which of the judge's disagreements are the extractor's fault rather than the judge's.

    `TODO.md` day 3: as designed, an extraction failure folds into the judge's error rate, because a human
    reading the real page marks SUPPORTED where the pipeline said NOT_FOUND_IN_SOURCE and the disagreement
    lands on the judge. This separates them using a deterministic fact rather than a second opinion: the
    labeller's own quoted passage is on the page, and it is missing from what `extract.py` produced.

    It is a floor on both counts. It only sees pairs where the labeller pasted a passage, and it cannot see
    a case where the extractor dropped evidence the labeller also missed.

    **`attributable_to_extraction` is a numerator over `disagreements_checked`, not over `disagreements`.**
    Until day 10 it had no denominator of its own and was read against `disagreements`, which is how the day
    9 run reported "0 of 13 attributed to the extractor" over a set where the check had run on none of the
    13. `extraction_missed` is a tri-state: `True` is an extractor fault, `False` is the extractor cleared,
    and `None` is a check that never happened, because `label_goldset.py` can only run it when the page is
    in the fetch cache. The old code tested `if l.extraction_missed`, which is false for the last two alike,
    so a cold cache and an exonerated extractor produced the same 0. `FINDINGS.md` item 24.
    """

    disagreements: int
    attributable_to_extraction: int
    unattributed: int
    labels_with_a_passage: int
    #: Disagreements where `extraction_missed` is not `None`, so the comparison actually produced an answer.
    #: The denominator `attributable_to_extraction` is over. Zero means this reports nothing about
    #: `extract.py` in either direction.
    disagreements_checked: int = 0
    #: Disagreements carrying a pasted passage. The ceiling on `disagreements_checked`, and distinct from
    #: `labels_with_a_passage`, which counts agreements too. The day 9 record held two different 13s and the
    #: writeup read one as the other.
    disagreements_with_a_passage: int = 0
    kappa_excluding_extraction: float | None = None
    kappa_excluding_extraction_interval_95: tuple[float, float] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "disagreements": self.disagreements,
            "attributable_to_extraction": self.attributable_to_extraction,
            "unattributed": self.unattributed,
            "labels_with_a_passage": self.labels_with_a_passage,
            "disagreements_checked": self.disagreements_checked,
            "disagreements_with_a_passage": self.disagreements_with_a_passage,
            "kappa_excluding_extraction": self.kappa_excluding_extraction,
            "kappa_excluding_extraction_interval_95": (
                list(self.kappa_excluding_extraction_interval_95)
                if self.kappa_excluding_extraction_interval_95 else None
            ),
            "note": (
                "attributable_to_extraction is over disagreements_checked, never over disagreements: "
                "extraction_missed is None when the page was not cached at labelling time, and an "
                "unchecked pair is not a cleared one. A floor even then, since evidence the labeller also "
                "missed is invisible here."
            ),
        }

    def render(self) -> str:
        if not self.disagreements:
            return "attribution   no disagreements to attribute"

        # The check never produced an answer on a single disagreement. Printing "0 of 13" here is what the
        # day 9 writeup did, and it read as an exoneration of `extract.py` that nothing had earned.
        if not self.disagreements_checked:
            return "\n".join([
                f"attribution   not run. 0 of {self.disagreements} judge-human disagreement(s) could be "
                f"checked against our extraction, so this says nothing about extract.py either way",
                f"              {self.disagreements_with_a_passage} carried a pasted passage and none of "
                f"them could be checked, which means the page was not in the fetch cache when it was "
                f"labelled. Run tools/prep_goldset.py without --no-fetch before a session",
            ])

        lines = [
            f"attribution   {self.attributable_to_extraction} of {self.disagreements_checked} checkable "
            f"judge-human disagreements are the extractor's, not the judge's: the labeller's own passage "
            f"is on the page and missing from what we extracted",
            f"              {self.disagreements_checked} of {self.disagreements} disagreement(s) could be "
            f"checked at all, {self.disagreements_with_a_passage} carried a passage. A floor, not a total",
        ]
        if self.kappa_excluding_extraction is not None:
            if self.attributable_to_extraction:
                lines.append(
                    f"              kappa excluding those pairs: {self.kappa_excluding_extraction:.3f}. "
                    "Reported beside the headline kappa, never instead of it"
                )
            else:
                lines.append(
                    f"              kappa excluding those pairs: {self.kappa_excluding_extraction:.3f}, "
                    "identical to the headline because nothing was removed"
                )
        return "\n".join(lines)


def attribution(gold: GoldSet, judgements) -> Attribution:
    """Split the judge-human disagreements into extractor failures and everything else."""
    standing = {
        (j.claim_id, j.url): j.verdict
        for j in (judgements or [])
        if not j.voided and j.verdict in COMPARABLE
    }

    disagreements = 0
    attributable = 0
    checked = 0
    disagreements_with_passage = 0
    with_passage = 0
    remaining: list[tuple[str, str]] = []

    for l in gold.blind:
        if l.label not in COMPARABLE:
            continue
        verdict = standing.get((l.claim_id, l.url))
        if verdict is None:
            continue
        if l.human_span:
            with_passage += 1
        if verdict == l.label:
            remaining.append((l.label, verdict))
            continue
        disagreements += 1
        if l.human_span:
            disagreements_with_passage += 1
        # Tri-state, and the middle case is the one that matters. `None` is a check that never ran, which is
        # not the same fact as an extractor cleared, and folding them together is what made the day 9
        # attribution unreadable. Only a non-`None` value counts towards the denominator.
        if l.extraction_missed is not None:
            checked += 1
        if l.extraction_missed:
            attributable += 1
        else:
            remaining.append((l.label, verdict))

    kappa, interval = cohens_kappa(remaining) if remaining else (None, None)
    return Attribution(
        disagreements=disagreements,
        attributable_to_extraction=attributable,
        unattributed=disagreements - attributable,
        labels_with_a_passage=with_passage,
        disagreements_checked=checked,
        disagreements_with_a_passage=disagreements_with_passage,
        kappa_excluding_extraction=kappa,
        kappa_excluding_extraction_interval_95=interval,
    )


def coverage(gold: GoldSet) -> dict[str, int]:
    """How many blind labels landed in each class. The thing the stratification was trying to control.

    Published whatever it says. A class the set never contains cannot be calibrated, and reporting that is
    the alternative to quietly presenting a kappa dominated by one easy class.
    """
    out = {label: 0 for label in LABELS}
    for label in gold.blind:
        out[label.label] = out.get(label.label, 0) + 1
    return out
