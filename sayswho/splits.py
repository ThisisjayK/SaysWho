"""A stored split, so a gold set has something fixed to be labelled against.

`FINDINGS.md` item 8: Phase 1 is a model call and it does not return the same split twice. Eight splits of
one byte-identical capture returned between 15 and 21 claims and between 104 and 156 skipped lines. That
makes a split a *sample*, not a property of the answer, and it breaks the assumption gate G4 was written
under: that "the gold set for this judge and prompt version" identifies a fixed set of claims.

So a split is written to disk once and everything downstream refers to that file. The gold set is labelled
against a stored split, the judge runs against the stored split, and the agreement number is computed over
the same claims a human actually read.

Two protections, both refusals rather than warnings:

- A stored split records the `answer_sha256` of the capture it came from. Loading it against a different
  capture raises, because a split of one answer says nothing about another.
- A stored split records its own `split_sha256`, over the claim texts and their markers. A gold set cites
  that hash, so a relabelled or hand-edited split cannot masquerade as the one that was labelled.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .claims import CLAIM_PROMPT_VERSION, Claim, ClaimSet, Skipped
from .records import Capture, sha256


def split_digest(claims: list[Claim]) -> str:
    """Identity of a split's content: the claim texts and their markers, in order.

    Deliberately not over the whole record. Two runs that produced the same claims on different days are the
    same split for labelling purposes, and the timestamp should not say otherwise.
    """
    payload = json.dumps(
        [{"text": c.text, "markers": c.markers} for c in claims],
        ensure_ascii=False,
        sort_keys=True,
    )
    return sha256(payload)


@dataclass
class StoredSplit:
    """One split of one capture, written down so it can be labelled and re-used."""

    #: The capture this split came from. A split of one answer says nothing about another.
    answer_sha256: str
    query_id: str
    product: str
    created_at: str

    #: What produced it. The gold set is only valid for this combination, same as gate G4.
    claim_prompt_version: str
    judge_class: str
    judge_model: str

    claims: list[Claim] = field(default_factory=list)
    skipped: list[Skipped] = field(default_factory=list)

    @property
    def split_sha256(self) -> str:
        return split_digest(self.claims)

    @property
    def claim_set(self) -> ClaimSet:
        return ClaimSet(claims=list(self.claims), skipped=list(self.skipped))

    def to_dict(self) -> dict[str, Any]:
        return {
            "answer_sha256": self.answer_sha256,
            "query_id": self.query_id,
            "product": self.product,
            "created_at": self.created_at,
            "claim_prompt_version": self.claim_prompt_version,
            "judge_class": self.judge_class,
            "judge_model": self.judge_model,
            "split_sha256": self.split_sha256,
            "claims": [c.to_dict() for c in self.claims],
            "skipped": [s.to_dict() for s in self.skipped],
            "claim_count": len(self.claims),
            "skipped_count": len(self.skipped),
            "_note": (
                "A stored split. Phase 1 does not return the same split twice, so this file is the one a "
                "gold set is labelled against. See sayswho/splits.py."
            ),
        }

    def save(self, path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
        return path

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "StoredSplit":
        claims = [
            Claim(
                id=c["id"],
                text=c["text"],
                markers=list(c.get("markers", [])),
                urls=list(c.get("urls", [])),
            )
            for c in d.get("claims", [])
        ]
        skipped = [
            Skipped(text=s.get("text", ""), reason=s.get("reason", ""))
            for s in d.get("skipped", [])
        ]
        split = cls(
            answer_sha256=d["answer_sha256"],
            query_id=d.get("query_id", ""),
            product=d.get("product", ""),
            created_at=d.get("created_at", ""),
            claim_prompt_version=d.get("claim_prompt_version", ""),
            judge_class=d.get("judge_class", ""),
            judge_model=d.get("judge_model", ""),
            claims=claims,
            skipped=skipped,
        )

        recorded = d.get("split_sha256")
        if recorded and recorded != split.split_sha256:
            raise ValueError(
                "stored split: recorded split_sha256 does not match its claims. The file was edited after "
                "it was written, so it is not the split anything was labelled against."
            )
        return split

    @classmethod
    def load(cls, path) -> "StoredSplit":
        with open(path, "rb") as fh:
            return cls.from_dict(json.load(fh))

    def bind(self, capture: Capture) -> ClaimSet:
        """Return the stored claims, after checking they belong to this capture.

        Raises rather than re-splitting. Silently falling back to a fresh split is exactly the failure this
        module exists to prevent: it would produce a run that looks pinned and is not.
        """
        if self.answer_sha256 != capture.answer_sha256:
            raise ValueError(
                f"stored split is for answer {self.answer_sha256[:16]} and this capture is "
                f"{capture.answer_sha256[:16]}. A split of one answer is not a split of another."
            )
        if self.claim_prompt_version != CLAIM_PROMPT_VERSION:
            raise ValueError(
                f"stored split was made under {self.claim_prompt_version!r} and this build is "
                f"{CLAIM_PROMPT_VERSION!r}. Gate G4: a prompt change means relabelling."
            )
        return self.claim_set


def store(claim_set: ClaimSet, capture: Capture, client, created_at: str) -> StoredSplit:
    """Wrap a fresh split for writing to disk."""
    return StoredSplit(
        answer_sha256=capture.answer_sha256,
        query_id=capture.query_id,
        product=capture.product,
        created_at=created_at,
        claim_prompt_version=CLAIM_PROMPT_VERSION,
        judge_class=type(client).__name__,
        judge_model=getattr(client, "model", ""),
        claims=list(claim_set.claims),
        skipped=list(claim_set.skipped),
    )
