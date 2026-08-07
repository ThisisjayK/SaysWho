"""Record types and reason codes.

Every field here is either a record of something that happened or a code assigned by a deterministic rule.
Nothing in this module is a model judgment. `SCOPE.md` §4 draws that line and the pipeline keeps it by putting
model output in separate types entirely.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from typing import Any

# Phase 0, gate G0
NO_CITATIONS = "NO_CITATIONS"

# Phase 2, gate G2. See DATA_CONTRACT.md §4.
SOURCE_OK = "SOURCE_OK"
SOURCE_UNREACHABLE = "SOURCE_UNREACHABLE"
SOURCE_EMPTY = "SOURCE_EMPTY"
SOURCE_PAYWALLED = "SOURCE_PAYWALLED"
SOURCE_DRIFTED = "SOURCE_DRIFTED"
SOURCE_ROBOTS_EXCLUDED = "SOURCE_ROBOTS_EXCLUDED"

#: Every G2 code other than SOURCE_OK makes its claim UNAUDITABLE and stops the pipeline for that claim.
#: No judge call is made against a source we do not have. Judging a claim against a page we could not read
#: would be inventing the evidence.
AUDITABLE_CODES = frozenset({SOURCE_OK})

ALL_G2_CODES = frozenset(
    {
        SOURCE_OK,
        SOURCE_UNREACHABLE,
        SOURCE_EMPTY,
        SOURCE_PAYWALLED,
        SOURCE_DRIFTED,
        SOURCE_ROBOTS_EXCLUDED,
    }
)


def sha256(data: bytes | str) -> str:
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


@dataclass(frozen=True)
class Citation:
    """A citation marker in an answer, and the URL it points at."""

    marker: str
    url: str


@dataclass
class Capture:
    """One AI answer, recorded as delivered.

    `answer_text` is stored verbatim. `answer_sha256` is over the verbatim text, so a later run can prove it
    audited the same answer rather than a re-generated one.
    """

    query_id: str
    product: str
    model_id: str
    generated_at: str
    captured_at: str
    answer_text: str
    citations: list[Citation] = field(default_factory=list)
    source: str = "dom"

    @property
    def answer_sha256(self) -> str:
        return sha256(self.answer_text)

    @property
    def cited_urls(self) -> list[str]:
        """Unique cited URLs, in the order they first appear."""
        seen: dict[str, None] = {}
        for c in self.citations:
            seen.setdefault(c.url, None)
        return list(seen)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["answer_sha256"] = self.answer_sha256
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Capture":
        # Keys starting with an underscore are annotations for a human reader, not data. Fixtures use them
        # to say what they are, and dropping them here keeps that possible without widening the schema.
        payload = {k: v for k, v in d.items() if k != "answer_sha256" and not k.startswith("_")}
        payload["citations"] = [Citation(**c) for c in d.get("citations", [])]
        capture = cls(**payload)

        recorded = d.get("answer_sha256")
        if recorded and recorded != capture.answer_sha256:
            raise ValueError(
                f"capture {capture.query_id}: recorded answer_sha256 does not match the answer text. "
                "The answer was edited after capture, so this is not the answer that was delivered."
            )
        return capture

    @classmethod
    def from_json(cls, path) -> "Capture":
        with open(path, "rb") as fh:
            return cls.from_dict(json.load(fh))


@dataclass
class FetchRecord:
    """What one cited URL actually returned. All record, no judgment."""

    url: str
    code: str
    fetched_at: str
    http_status: int | None = None
    content_sha256: str | None = None
    text_length: int = 0
    final_url: str | None = None
    attempts: int = 0
    detail: str = ""

    #: Extracted text. Deliberately excluded from to_dict: the repo publishes verdicts and quoted spans,
    #: not copies of the pages it fetched. See DATA_CONTRACT.md §9.
    text: str = field(default="", repr=False)

    @property
    def auditable(self) -> bool:
        return self.code in AUDITABLE_CODES

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d.pop("text", None)
        return d
