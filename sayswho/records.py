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

#: The response was not markup this pipeline can read: a PDF, an image, an office document. Distinct from
#: SOURCE_EMPTY on the same grounds SOURCE_ROBOTS_EXCLUDED is distinct from SOURCE_UNREACHABLE. Empty means
#: we parsed it and there was nothing there; not-html means we never had a parser for it. Both leave the
#: claim UNAUDITABLE, and the arithmetic is identical, but "the citation is a PDF we cannot read" and "the
#: citation is a blank page" are different sentences to publish next to a number.
#:
#: Before this code existed a cited PDF went through the HTML parser, which is the same shape as the gzip
#: bug in FINDINGS.md item 7: it parses without error, produces plausible-looking output, and matches
#: nothing. Government reports and papers are exactly the citations most likely to be PDFs.
SOURCE_NOT_HTML = "SOURCE_NOT_HTML"

#: The citation points at nothing. 404 or 410: the server answered, and its answer was that the document is
#: not there. This is a fact about the citation.
SOURCE_DEAD_LINK = "SOURCE_DEAD_LINK"

#: The server refused *us*. 401, 403 or 429: access denied or rate limited, from a page a person clicking
#: the link would in all likelihood see.
#:
#: Split out of SOURCE_UNREACHABLE for the same reason SOURCE_ROBOTS_EXCLUDED was, and found the same way,
#: by looking at a real run. `FINDINGS.md` item 3: aacrjournals.org returned 403 to the single link in a
#: whole research report. Folded together, "the citation is broken" and "the citation is unreadable to
#: anything automated" become one number, and only the first is a finding about the answer being audited.
#: The arithmetic is identical, since all three are UNAUDITABLE. The sentence published beside the number
#: is not.
SOURCE_BOT_BLOCKED = "SOURCE_BOT_BLOCKED"

#: Statuses that mean the document is gone rather than withheld.
_DEAD_STATUSES = frozenset({404, 410})

#: Statuses that mean we were refused rather than the document being absent.
_BLOCKED_STATUSES = frozenset({401, 403, 429})


def code_for_status(status: int) -> str:
    """The G2 code for a non-200 response. The only place this mapping exists."""
    if status in _DEAD_STATUSES:
        return SOURCE_DEAD_LINK
    if status in _BLOCKED_STATUSES:
        return SOURCE_BOT_BLOCKED
    return SOURCE_UNREACHABLE

#: Every G2 code other than SOURCE_OK makes its claim UNAUDITABLE and stops the pipeline for that claim.
#: No judge call is made against a source we do not have. Judging a claim against a page we could not read
#: would be inventing the evidence.
AUDITABLE_CODES = frozenset({SOURCE_OK})

ALL_G2_CODES = frozenset(
    {
        SOURCE_OK,
        SOURCE_UNREACHABLE,
        SOURCE_DEAD_LINK,
        SOURCE_BOT_BLOCKED,
        SOURCE_EMPTY,
        SOURCE_PAYWALLED,
        SOURCE_DRIFTED,
        SOURCE_ROBOTS_EXCLUDED,
        SOURCE_NOT_HTML,
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

    #: Characters the browser laid out, versus characters present in the DOM.
    #:
    #: These are not directly comparable and the check built on them is weak in both directions. innerText
    #: inserts newlines at block boundaries and tabs between table cells, so it often runs *longer* than
    #: textContent: a real ChatGPT capture measured 15,840 against 15,647. textContent meanwhile includes
    #: script and style text that innerText omits.
    #:
    #: So a large shortfall is evidence, and a small one is noise. This catches half a document going
    #: missing. It would not catch five percent. The scroll pass is the actual defence; this is a
    #: backstop, and the writeup should not claim more for it than that.
    rendered_chars: int = 0
    dom_chars: int = 0

    #: The stored page this capture came from. Kept local and gitignored: a full claude.ai page carries the
    #: sidebar, and therefore the titles of every other conversation.
    page_file: str = ""
    page_bytes: int = 0

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
        if self.citations_possibly_hidden > 0:
            return True
        # Five percent of slack for whitespace differences between innerText and textContent.
        return self.dom_chars > 0 and self.dom_chars > self.rendered_chars * 1.05

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

    #: What the server said it was sending, and how much of it there was. Recorded because the extraction
    #: check below is only interpretable next to them.
    content_type: str = ""
    html_bytes: int = 0

    #: Large page, almost no extracted text. A flag, never a code: see extract.extraction_looks_thin. The
    #: source stays auditable and the run says so out loud, because the alternative failure is silent.
    extraction_thin: bool = False

    #: Extracted text. Deliberately excluded from to_dict: the repo publishes verdicts and quoted spans,
    #: not copies of the pages it fetched. See DATA_CONTRACT.md §9.
    text: str = field(default="", repr=False)

    #: The permissive extraction, for the extraction check in judge.py. Dropped from to_dict for the same
    #: reason as `text`, and never written to the repo.
    #:
    #: This holds `extract.raw_text` output rather than the markup. The check compares two *extractions* of
    #: the same page, so what it needs is the wider one. Handing it raw markup, which is what the first
    #: version did, meant a claim's tokens could match a `switch` statement or a CSS class name.
    raw: str = field(default="", repr=False)

    @property
    def auditable(self) -> bool:
        return self.code in AUDITABLE_CODES

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d.pop("text", None)
        d.pop("raw", None)
        return d
