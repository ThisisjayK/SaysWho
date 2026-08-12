"""Capture an answer from a provider API instead of from a rendered page.

Stdlib only, like the rest of the capture and fetch layers. A provider API returns citations as data rather
than as DOM, which removes the entire class of failure the `adapter_verified` flag exists to warn about: the
Perplexity adapter found zero of eight citations for four days and passed every test, because the tests
asserted the anchors-only rule the adapter implemented.

**This measures a different object, and that is not a detail.** An API answer is produced by a different
model, with different retrieval and different post-processing, from the one a person sees in the product. A
rate measured here is a rate about that API, not about claude.ai or perplexity.ai as products. `SCOPE.md` §7
says so, and `source="api"` travels in every record so no reader has to take that on trust.

**No schema is hardcoded, on purpose.** Four providers return citations in four shapes, those shapes change,
and the documentation for at least one of them describes a structure that did not match what this file was
first written to expect. Guessing a schema and then asserting a hand-built fixture matches it would produce
a parser that is confidently wrong, in a project whose subject is confidently wrong citations. So this walks
the response for citation-shaped objects, reports the JSON path it found each one at, and counts the URLs it
did not take. Both numbers are in the record. A walk that is eating too much or too little says so.

**Nothing here is verified until a human has looked.** `adapter_verified` is False for every API capture
until someone reads a stored response against the capture built from it, exactly the rule the DOM adapters
follow. `tools/api_capture.py --from` replays a stored response so that check is repeatable.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any

from .cache import now_iso
from .records import Capture, Citation

#: Keys whose value may be a citation's URL. Ordered by how specific they are, so a nested object carrying
#: both `url` and `uri` resolves the same way every time.
URL_KEYS = ("url", "uri", "link", "source_url", "sourceUrl", "web_url", "canonical_url")

#: Keys whose value may be a citation's visible label. The label becomes the marker, which is what a reader
#: sees beside a sentence, so a missing one falls back to a positional marker rather than being invented.
TITLE_KEYS = ("title", "name", "site", "domain", "source", "publisher", "displayed_text")

#: Keys whose value may be a list of bare URL strings rather than a list of objects. Perplexity returns
#: `"citations": ["https://...", "https://..."]`, with no titles and no offsets, and the first version of
#: this walk reported zero citations for it. It did not report zero *quietly*, which is the only reason the
#: gap was visible: the two URLs landed in `unclaimed_urls` and the count said so.
CITATION_LIST_KEYS = ("citations", "sources", "references", "search_results", "urls", "links")

#: Keys under which an answer's prose may sit. Used only to rank candidates; the longest wins and the path
#: it was found at is recorded.
TEXT_KEYS = ("text", "output_text", "content", "answer", "message", "response")

#: Live calls this file knows how to build. Everything else arrives through `--from`, which replays a stored
#: response and needs no knowledge of how to ask for one.
#:
#: Only Gemini is here, and the reason is worth stating rather than leaving as an omission: it is the only
#: provider with a free tier this project can run, and a request builder that has never been executed is a
#: guess wearing the same clothes as working code.
PROVIDERS = {
    "gemini": {
        "env": ("GEMINI_API_KEY", "GOOGLE_API_KEY"),
        "endpoint": (
            "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        ),
        "default_model": "gemini-2.5-flash",
        #: A Google model answering, and later a Google model judging. `rates.CONFLICTED_PRODUCTS` already
        #: refuses to put a Google surface in a cross-product aggregate, and that applies here too.
        "conflicted": True,
    },
}


def _is_http_url(value: Any) -> bool:
    return isinstance(value, str) and value.lower().startswith(("http://", "https://"))


@dataclass
class Found:
    """One citation-shaped object, and where in the response it was."""

    url: str
    title: str
    path: str
    #: Character offsets into the answer, when the provider supplied them. Not computed here: an offset this
    #: file invented would put a mark beside the wrong sentence.
    start: int | None = None
    end: int | None = None

    def to_dict(self) -> dict:
        return {
            "url": self.url, "title": self.title, "path": self.path,
            "start": self.start, "end": self.end,
        }


def _first(obj: dict, keys) -> Any:
    for key in keys:
        if key in obj:
            return obj[key]
    return None


def walk_citations(payload: Any, path: str = "$") -> tuple[list[Found], list[str]]:
    """Every citation-shaped object in a response, and every URL that was not taken as one.

    A citation-shaped object is a dict carrying an http URL under one of `URL_KEYS`. The second return value
    is the URLs found somewhere else: a bare string in a list, a URL under a key this does not recognise.
    That count is the equivalent of `chrome_links_excluded` on the DOM side. If it is large, this walk is
    missing citations, and the record says so instead of looking complete.
    """
    found: list[Found] = []
    unclaimed: list[str] = []

    def visit(node: Any, here: str, inside_citation: bool) -> None:
        if isinstance(node, dict):
            url = _first(node, URL_KEYS)
            if _is_http_url(url):
                title = _first(node, TITLE_KEYS)
                found.append(
                    Found(
                        url=url,
                        title=title if isinstance(title, str) else "",
                        path=here,
                        start=node.get("start_index") if isinstance(node.get("start_index"), int) else None,
                        end=node.get("end_index") if isinstance(node.get("end_index"), int) else None,
                    )
                )
                # Descend, but everything below is part of this citation, so its URLs are not unclaimed.
                for key, value in node.items():
                    visit(value, f"{here}.{key}", True)
                return
            for key, value in node.items():
                visit(value, f"{here}.{key}", inside_citation)
            return

        if isinstance(node, list):
            # A list reached through a citation-ish key, holding bare URL strings, is a citation list. The
            # key name is the only signal available: a bare string carries no title and no offsets.
            bare_list = here.rsplit(".", 1)[-1] in CITATION_LIST_KEYS
            for index, value in enumerate(node):
                if bare_list and _is_http_url(value):
                    found.append(Found(url=value, title="", path=f"{here}[{index}]"))
                    continue
                visit(value, f"{here}[{index}]", inside_citation)
            return

        if _is_http_url(node) and not inside_citation:
            unclaimed.append(node)

    visit(payload, path, False)

    # Deduplicate by URL, keeping the first path each was seen at.
    seen: set[str] = set()
    unique: list[Found] = []
    for item in found:
        if item.url in seen:
            continue
        seen.add(item.url)
        unique.append(item)
    return unique, [u for u in unclaimed if u not in seen]


def walk_answer_text(payload: Any) -> tuple[str, str]:
    """The longest plausible answer string in a response, and the path it was found at.

    Ranking by length rather than by a known key, for the same reason the citation walk is structural. The
    path is returned so a person can confirm the right field was taken, which is the whole of what
    verification means for an API capture.
    """
    best: tuple[int, str, str] = (0, "", "")

    def visit(node: Any, here: str) -> None:
        nonlocal best
        if isinstance(node, str):
            # A URL, an id or a mime type is not an answer.
            if len(node) > best[0] and not _is_http_url(node) and " " in node:
                best = (len(node), node, here)
            return
        if isinstance(node, dict):
            for key, value in node.items():
                visit(value, f"{here}.{key}")
            return
        if isinstance(node, list):
            for index, value in enumerate(node):
                visit(value, f"{here}[{index}]")

    visit(payload, "$")
    return best[1], best[2]


@dataclass
class ApiCapture:
    """A capture built from an API response, with the provenance to argue with it."""

    capture: Capture
    provider: str
    model: str
    answer_path: str
    citations: list[Found] = field(default_factory=list)
    unclaimed_urls: list[str] = field(default_factory=list)
    raw_path: str = ""

    def provenance(self) -> dict:
        return {
            "source": "api",
            "provider": self.provider,
            "model": self.model,
            "answer_path": self.answer_path,
            "citations_found": len(self.citations),
            "citation_paths": sorted({c.path.rsplit("[", 1)[0] for c in self.citations}),
            "urls_not_taken_as_citations": len(self.unclaimed_urls),
            "raw_response": self.raw_path,
            "verified": self.capture.adapter_verified,
        }

    def render(self) -> str:
        lines = [
            f"provider   {self.provider}  model {self.model}",
            f"answer     {len(self.capture.answer_text)} chars, found at {self.answer_path}",
            f"citations  {len(self.citations)}",
        ]
        for item in self.citations:
            label = item.title or "(no title)"
            lines.append(f"  {label[:40]:<40} {item.url[:80]}")
            lines.append(f"      at {item.path}")
        if self.unclaimed_urls:
            lines.append(
                f"urls not taken as citations: {len(self.unclaimed_urls)}. If any of these are real "
                f"citations, this walk is missing them:"
            )
            for url in self.unclaimed_urls[:10]:
                lines.append(f"  {url[:100]}")
        lines.append(
            "verified   False. Read the stored response against this capture before trusting anything "
            "computed from it."
        )
        return "\n".join(lines)


def build(
    payload: dict,
    provider: str,
    query_id: str = "UNASSIGNED",
    model: str = "",
    raw_path: str = "",
) -> ApiCapture:
    """Turn a stored or freshly fetched API response into a `Capture` the existing pipeline can audit."""
    answer_text, answer_path = walk_answer_text(payload)
    found, unclaimed = walk_citations(payload)

    citations = [
        Citation(marker=item.title or f"[pos:{index + 1}]", url=item.url)
        for index, item in enumerate(found)
    ]

    capture = Capture(
        query_id=query_id,
        product=f"api:{provider}",
        model_id=model or "unknown",
        generated_at=now_iso(),
        captured_at=now_iso(),
        answer_text=answer_text,
        citations=citations,
        source="api",
        adapter=f"api:{provider}",
        # False until a person has read the stored response against this capture. An API response is
        # structured, which makes it easier to read correctly, not automatically read correctly.
        adapter_verified=False,
    )
    return ApiCapture(
        capture=capture, provider=provider, model=model or "unknown", answer_path=answer_path,
        citations=found, unclaimed_urls=unclaimed, raw_path=raw_path,
    )


def ask(provider: str, prompt: str, model: str = "", timeout: int = 120) -> dict:
    """Make one live call and return the raw JSON, unmodified.

    The raw response is what gets stored and what every later run replays, so nothing here reshapes it. A
    parser can be fixed against a stored response; a response that was normalised before storage cannot be
    recovered.
    """
    if provider not in PROVIDERS:
        raise ValueError(
            f"no request builder for {provider!r}. Obtain the response yourself and replay it with --from: "
            f"the parser does not need to know how the call was made. Buildable: {sorted(PROVIDERS)}"
        )

    spec = PROVIDERS[provider]
    key = next((os.environ[name] for name in spec["env"] if os.environ.get(name)), None)
    if not key:
        raise RuntimeError(
            f"set one of {', '.join(spec['env'])}. DATA_CONTRACT.md §8: the key is read from the "
            f"environment and never written to a file."
        )

    model = model or spec["default_model"]
    body = json.dumps(
        {
            "contents": [{"parts": [{"text": prompt}]}],
            # Grounding is the point: without a search tool the answer has no citations to audit, and G0
            # would correctly halt on it.
            "tools": [{"google_search": {}}],
        }
    ).encode()

    request = urllib.request.Request(
        spec["endpoint"].format(model=model),
        data=body,
        headers={
            "Content-Type": "application/json",
            "x-goog-api-key": key,
            "User-Agent": "SaysWho/0.8 (research; citation audit)",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read())
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:500]
        raise RuntimeError(f"{provider} returned {exc.code}: {detail}") from exc
