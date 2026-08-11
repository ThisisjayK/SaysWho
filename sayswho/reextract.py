"""Re-extract citations from a stored page, without going back to the product.

Every selector fix today meant asking a human to reload three tabs and capture again. That is slow, and
worse, it re-runs the query: the answer can change between captures, so a selector fix and an answer change
arrive together and cannot be told apart.

Storing the page means a selector fix is re-run over the same bytes.

**What re-extraction can recover, and what it cannot.** Citations, the container choice, and the structure
are all recoverable, because they come from the markup. The answer *text* is not, because the extension
reads `innerText`, which depends on layout and stylesheets that a stored HTML file does not carry. So
re-extraction reports citations and leaves the original captured text alone, and says so rather than
producing a slightly different text that would silently disagree with the capture it came from.

Stdlib only. The CSS support here is a deliberate subset covering exactly the selector forms the adapters
use, and it raises on anything else rather than quietly matching nothing.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from html.parser import HTMLParser

from .records import normalise_url

VOID_ELEMENTS = frozenset(
    {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}
)

#: Mirrors extension/src/adapters.js. Kept as data so a divergence between the two is a diff rather than a
#: behaviour difference nobody notices.
ADAPTERS: dict[str, list[str]] = {
    "claude": [".bg-surface-3 .standard-markdown", ".font-claude-response"],
    "chatgpt": ['[data-message-author-role="assistant"]', "div.markdown.prose"],
    "perplexity": [".prose", '[class*="answer"]'],
    "google-ai-overviews": ['[data-attrid*="AIOverview"]'],
    "generic": ["article", "main", "body"],
}

CHROME_HOSTS = frozenset(
    {
        "support.anthropic.com", "claude.ai", "chatgpt.com", "chat.openai.com", "help.openai.com",
        "www.perplexity.ai", "perplexity.ai", "policies.google.com", "support.google.com",
        "accounts.google.com",
    }
)


@dataclass
class Node:
    tag: str
    attrs: dict[str, str] = field(default_factory=dict)
    children: list["Node"] = field(default_factory=list)
    parent: "Node | None" = field(default=None, repr=False)
    text: str = ""

    @property
    def classes(self) -> set[str]:
        return set(self.attrs.get("class", "").split())

    def walk(self):
        yield self
        for child in self.children:
            yield from child.walk()

    def text_content(self) -> str:
        parts = [self.text]
        for child in self.children:
            parts.append(child.text_content())
        return "".join(parts)


class _TreeBuilder(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.root = Node("#document")
        self._stack = [self.root]

    def handle_starttag(self, tag, attrs):
        node = Node(tag, {k: (v or "") for k, v in attrs}, parent=self._stack[-1])
        self._stack[-1].children.append(node)
        if tag not in VOID_ELEMENTS:
            self._stack.append(node)

    def handle_startendtag(self, tag, attrs):
        node = Node(tag, {k: (v or "") for k, v in attrs}, parent=self._stack[-1])
        self._stack[-1].children.append(node)

    def handle_endtag(self, tag):
        for i in range(len(self._stack) - 1, 0, -1):
            if self._stack[i].tag == tag:
                del self._stack[i:]
                return

    def handle_data(self, data):
        parent = self._stack[-1]
        parent.children.append(Node("#text", parent=parent, text=data))


def parse(html: str) -> Node:
    builder = _TreeBuilder()
    builder.feed(html)
    builder.close()
    return builder.root


# ------------------------------------------------------------------ selectors

_SIMPLE = re.compile(
    r"^(?P<tag>[a-zA-Z][\w-]*)?"
    r"(?P<rest>(?:\.[\w-]+|\[[^\]]+\])*)$"
)
_ATTR = re.compile(r"\[\s*([\w-]+)\s*(?:(\^=|\*=|=)\s*(\"[^\"]*\"|'[^']*'|[^\]]+?)\s*)?\]")


@dataclass(frozen=True)
class _Simple:
    tag: str | None
    classes: tuple[str, ...]
    attrs: tuple[tuple[str, str | None, str | None], ...]


def _parse_simple(part: str) -> _Simple:
    match = _SIMPLE.match(part)
    if not match:
        raise ValueError(f"unsupported selector fragment: {part!r}")

    rest = match.group("rest") or ""
    classes = tuple(re.findall(r"\.([\w-]+)", rest))
    attrs = []
    for name, op, raw in _ATTR.findall(rest):
        value = raw.strip("\"'") if raw else None
        attrs.append((name, op or None, value))
    return _Simple(match.group("tag"), classes, tuple(attrs))


def _matches(node: Node, simple: _Simple) -> bool:
    if node.tag.startswith("#"):
        return False
    if simple.tag and node.tag != simple.tag:
        return False
    if not set(simple.classes) <= node.classes:
        return False
    for name, op, value in simple.attrs:
        if name not in node.attrs:
            return False
        actual = node.attrs[name]
        if op == "=" and actual != value:
            return False
        if op == "^=" and not actual.startswith(value or ""):
            return False
        if op == "*=" and (value or "") not in actual:
            return False
    return True


def select(root: Node, selector: str) -> list[Node]:
    """Descendant-combinator CSS, restricted to the forms the adapters use."""
    parts = [_parse_simple(p) for p in selector.split() if p]
    if not parts:
        return []

    results = []
    for node in root.walk():
        if not _matches(node, parts[-1]):
            continue
        ancestor = node.parent
        remaining = list(parts[:-1])
        while remaining and ancestor is not None:
            if _matches(ancestor, remaining[-1]):
                remaining.pop()
            ancestor = ancestor.parent
        if not remaining:
            results.append(node)
    return results


# ------------------------------------------------------------------ extraction


def _is_chrome(url: str) -> bool:
    from urllib.parse import urlsplit

    try:
        return urlsplit(url).hostname in CHROME_HOSTS if urlsplit(url).hostname else True
    except ValueError:
        return True


#: Attributes that carry a citation's URL when the citation is not a link.
#:
#: Perplexity renders every inline citation as a span with `data-pplx-citation-url` and puts no anchor on
#: the page at all, so an anchors-only rule finds none of its citations and reports a clean capture with
#: zero of them. This list is the Python half of the same rule the extension applies, and `SCOPE.md` §9
#: requires the two to agree: a citation the extension records and this cannot re-extract is a parity
#: failure, not a detail.
CITATION_URL_ATTRS = ("data-pplx-citation-url",)


def _citation_url(node: Node) -> str:
    """The URL a citation node points at, whether or not it is a link."""
    href = node.attrs.get("href", "")
    if href:
        return href
    for attr in CITATION_URL_ATTRS:
        value = node.attrs.get(attr, "")
        if value.lower().startswith(("http://", "https://")):
            return value
    return ""


def citations_in(node: Node) -> list[dict[str, str]]:
    """External citations under a node, page furniture excluded, deduplicated by normalised URL and marker.

    A citation is an anchor, or any element carrying one of `CITATION_URL_ATTRS`. Nested matches are
    skipped: Perplexity wraps its chip in a second element of the same class, and counting both would
    double every citation on the page.
    """
    out: list[dict[str, str]] = []
    seen = set()
    for candidate in node.walk():
        if candidate.tag != "a" and not any(a in candidate.attrs for a in CITATION_URL_ATTRS):
            continue
        href = _citation_url(candidate)
        if not href.lower().startswith(("http://", "https://")) or _is_chrome(href):
            continue
        marker = re.sub(r"\s*\+\d+\s*$", "", " ".join(candidate.text_content().split())).strip()
        if not marker or len(marker) > 40:
            marker = f"[pos:{len(out) + 1}]"
        key = (marker, normalise_url(href))
        if key in seen:
            continue
        seen.add(key)
        out.append({"marker": marker, "url": href})
    return out


@dataclass
class ReextractResult:
    product: str
    selector: str
    citations: list[dict[str, str]]
    candidates_considered: int

    @property
    def urls(self) -> list[str]:
        seen: dict[str, None] = {}
        for c in self.citations:
            seen.setdefault(normalise_url(c["url"]), None)
        return list(seen)


def reextract(html: str, product: str) -> ReextractResult | None:
    """Re-run container selection and citation extraction over stored page HTML.

    Container choice ranks by citation count, exactly as the extension does, so a page where two containers
    match resolves the same way on both sides.
    """
    root = parse(html)
    selectors = ADAPTERS.get(product, ADAPTERS["generic"])

    best = None
    considered = 0
    for selector in selectors:
        for node in select(root, selector):
            considered += 1
            citations = citations_in(node)
            size = len(node.text_content())
            score = (len(citations), size)
            if best is None or score > best[0]:
                best = (score, selector, node, citations)

    if best is None:
        return None

    _, selector, _, citations = best
    return ReextractResult(
        product=product, selector=selector, citations=citations, candidates_considered=considered
    )


def main(argv: list[str] | None = None) -> int:
    """python3 -m sayswho.reextract <page.html> [--capture capture.json]

    With a capture, this is the beginning of the §9 parity check: the extension extracted from the live DOM,
    this extracts from the bytes that DOM was saved as, and the two citation sets have to agree. If they
    disagree, one of them is wrong and the disagreement is the finding.
    """
    import argparse
    import json
    from pathlib import Path

    parser = argparse.ArgumentParser(description="Re-extract citations from a stored page")
    parser.add_argument("page", type=Path)
    parser.add_argument("--capture", type=Path, help="compare against the capture this page came from")
    parser.add_argument("--product", help="override the product adapter")
    args = parser.parse_args(argv)

    html = args.page.read_text(encoding="utf-8", errors="replace")

    product = args.product
    recorded = None
    if args.capture:
        recorded = json.loads(args.capture.read_text())
        product = product or recorded.get("product")

    result = reextract(html, product or "generic")
    if result is None:
        print(f"no answer container matched for product {product!r}")
        return 1

    print(f"page        {args.page.name}  ({len(html):,} chars)")
    print(f"product     {result.product}")
    print(f"selector    {result.selector}   ({result.candidates_considered} candidates considered)")
    print(f"citations   {len(result.citations)}  unique URLs {len(result.urls)}")
    for citation in result.citations:
        print(f"  {citation['marker'][:34]:<34} {citation['url'][:88]}")

    if recorded is None:
        return 0

    from .records import normalise_url

    was = {normalise_url(c["url"]) for c in recorded.get("citations", [])}
    now = set(result.urls)

    print()
    if was == now:
        print(f"PARITY OK   the stored page yields the same {len(now)} URLs the live capture did")
        return 0

    print("PARITY MISMATCH  the stored page and the live capture disagree")
    for url in sorted(was - now):
        print(f"  only in the live capture   {url}")
    for url in sorted(now - was):
        print(f"  only in the stored page    {url}")
    print()
    print("One of the two is wrong. That disagreement is the finding, not a nuisance.")
    return 1


if __name__ == "__main__":
    import sys

    sys.exit(main())
