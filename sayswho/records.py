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
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

# Phase 0, gate G0
NO_CITATIONS = "NO_CITATIONS"

#: A source named in prose with no resolvable URL. Discovered on day 2 in a real Claude Research report that
#: named at least fifteen sources and linked one. See sayswho/named_citations.py.
CITATION_NOT_LINKED = "CITATION_NOT_LINKED"

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


#: Parameters products append to citation URLs for their own analytics. ChatGPT adds
#: `?utm_source=chatgpt.com` to every citation it emits.
_TRACKING_PARAMS = frozenset(
    {
        "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
        "fbclid", "gclid", "mc_cid", "mc_eid", "igshid",
    }
)


def normalise_url(url: str) -> str:
    """Drop known tracking parameters, keeping everything else.

    Only the listed keys are removed. Stripping the whole query string would break citations whose
    parameters carry meaning, such as the cancer.gov trial link with `?id=NCI-2021-00403`.

    The citation keeps the URL exactly as the answer gave it. This normalised form is what gets fetched and
    deduplicated, so the same page cited three times with three different tracking tags is one fetch rather
    than three, and the publisher does not receive an analytics tag from us that they would then attribute
    to a product we are auditing.
    """
    try:
        parts = urlsplit(url)
    except ValueError:
        return url
    kept = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True) if k.lower() not in _TRACKING_PARAMS]
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(kept), parts.fragment))


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

    #: Which DOM adapter produced this capture, and whether that adapter has been checked against the real
    #: page. An unverified adapter can miss citation markers, which makes the support rate come out over a
    #: subset of the answer while everything downstream looks perfectly normal. A capture bug does not
    #: announce itself, so the provenance travels with the record.
    adapter: str = ""
    adapter_verified: bool = False

    #: Extension build that produced the capture. Absent means it predates version stamping, which means a
    #: stale content script: Chrome keeps running old code in already-open tabs until the page reloads.
    extension_version: str = ""

    #: Links in the answer container dropped as page furniture (product help links, same-origin nav).
    #: Recorded rather than hidden: a large value means the exclusion list is eating real citations.
    chrome_links_excluded: int = 0

    #: Citations the page showed but the capture could not reach, counted from the "+N" expanders both
    #: ChatGPT and Perplexity use to collapse extra sources behind one visible chip. This is a floor: it
    #: counts what the expanders admit to, not what is actually hidden.
    citations_possibly_hidden: int = 0
    expanders_seen: int = 0

    @property
    def answer_sha256(self) -> str:
        return sha256(self.answer_text)

    @property
    def cited_urls(self) -> list[str]:
        """Unique cited URLs, tracking parameters removed, in the order they first appear."""
        seen: dict[str, None] = {}
        for c in self.citations:
            seen.setdefault(normalise_url(c.url), None)
        return list(seen)

    @property
    def capture_is_known_incomplete(self) -> bool:
        """True when the page showed citations the capture could not reach.

        A capture that is quietly short produces a support rate over a subset of the answer and looks
        entirely normal doing it. This is the one thing about a capture that must never be silent.
        """
        return self.citations_possibly_hidden > 0

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
