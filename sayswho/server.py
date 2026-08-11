"""A local audit server, so the marks appear without leaving the page.

    python3 -m sayswho.server            # fetch and liveness only, no key needed
    python3 -m sayswho.server --judge    # full audit, needs GEMINI_API_KEY

The extension posts a capture here and gets back a report payload, which it renders with the same
`render.js` the standalone report uses. That removes the terminal step from the loop. It does not move any
of the pipeline into JavaScript: the gates, the span guard and the denominators stay in Python, which is
the whole reason this server exists rather than a rewrite of the pipeline in the content script. A
JavaScript reimplementation would be the second implementation the §9 parity check exists to compare, and
the two would drift apart under maintenance.

**What this is not.** It does not mark the product's own sentences in place. The payload carries character
offsets into the answer text, and mapping those onto a live DOM that re-renders as you scroll is a separate
piece of work with its own failure modes. The panel shows the marked answer next to the page instead.
`SCOPE.md` §1a says capture and render, and this makes the render local and immediate rather than making
the claim bigger.

**Security posture, stated because a local server is a real surface.**

- Binds to 127.0.0.1 only. Never to 0.0.0.0, and there is a test that asserts the bind address.
- Requires an `Origin` header from one of the audited products, and echoes only that origin back in
  `Access-Control-Allow-Origin`. A page on any other origin cannot read a response.
- Refuses to start if the query freeze check fails, same as every other path into the pipeline.
- Reads the API key from its own environment. The key never goes into a file, a plist or a request, per
  `DATA_CONTRACT.md` §8.
- The residual risk, written down rather than left implicit: any process on this machine can post to this
  port, and a capture is a list of URLs this server will then fetch. It is a research tool, run by hand,
  for as long as an audit takes. It is not something to leave running.
"""

from __future__ import annotations

import argparse
import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from .cache import FetchCache
from .drift import DriftChecker
from .fetch import Fetcher
from .gates import assert_no_confidence_number, g0_has_citations
from .pipeline import fetch_sources, judge_claims, phase1
from .queryset import binding, freeze_intact
from .records import Capture
from .report import build as build_report, strip_for_gate_check
from .skips import analyse as analyse_skips
from .splits import split_digest

HOST = "127.0.0.1"
PORT = 8765

#: Only these origins may talk to the server, and only the requesting one is echoed back. The list is the
#: same set of products the extension runs on.
ALLOWED_ORIGINS = frozenset(
    {
        "https://claude.ai",
        "https://chatgpt.com",
        "https://chat.openai.com",
        "https://www.perplexity.ai",
        "https://www.google.com",
    }
)

#: A capture is a list of URLs this server will fetch. A cap on how many, so one posted capture cannot turn
#: the server into an afternoon of requests.
MAX_CITATIONS = 60


class AuditService:
    """The pipeline behind the server. Holds the fetcher, so the cache and the rate limiter are shared."""

    def __init__(self, cache_dir: Path, judge: bool = False, provider: str | None = None,
                 budget: int = 2_000_000, drift: bool = True,
                 captures_dir: Path | None = None) -> None:
        self.captures_dir = Path(captures_dir) if captures_dir else Path("captures")
        self.fetcher = Fetcher(FetchCache(cache_dir))
        self.checker = DriftChecker(self.fetcher) if drift else None
        self.judge = judge
        self.provider = provider
        self.budget = budget
        #: One audit at a time. Two concurrent audits would interleave their requests to the same host and
        #: break the one-request-per-second rule, which is a promise made to the sites being fetched.
        self.lock = threading.Lock()

    def save_capture(self, capture: Capture, payload: dict) -> str:
        """Write the capture where the harness reads captures from.

        The extension used to download a copy to ~/Downloads on every audit, which meant a directory full
        of JSON nobody asked for and a file in the wrong place: `tools/run_stratum.py` and
        `tools/bind_capture.py` both work over a captures directory in the repo. Writing it here puts it
        where the next step expects it, once.

        Never overwrites. A capture is a record of something that happened, and two answers to the same
        question in the same second are two records.
        """
        self.captures_dir.mkdir(parents=True, exist_ok=True)
        stamp = capture.captured_at.replace(":", "").replace("-", "").replace("+", "")
        base = f"capture-{capture.product}-{stamp}"
        path = self.captures_dir / f"{base}.json"
        n = 1
        while path.exists():
            path = self.captures_dir / f"{base}-{n}.json"
            n += 1
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        return str(path)

    def audit(self, payload: dict) -> dict:
        capture = Capture.from_dict(payload)

        gate0 = g0_has_citations(capture)
        if not gate0.passed:
            return {
                "error": gate0.code,
                "detail": gate0.detail,
                "note": "This answer is uncitable. It is not scored, and it is not a zero percent answer.",
            }

        if len(capture.citations) > MAX_CITATIONS:
            return {
                "error": "TOO_MANY_CITATIONS",
                "detail": f"{len(capture.citations)} citations, limit {MAX_CITATIONS}",
            }

        # Saved before the fetching starts, not after. An audit takes a minute or two and can be
        # interrupted; the capture is the irreplaceable half and the audit can always be re-run.
        saved = self.save_capture(capture, payload)

        with self.lock:
            records, drifts = [], []
            for record, drift in fetch_sources(capture, self.fetcher, self.checker):
                records.append(record)
                drifts.append(drift)

            claim_set = None
            judgements = []
            if self.judge and any(r.auditable for r in records):
                from .gemini import build_judge
                from .model import BudgetExceeded, Meter

                client = build_judge(self.provider, meter=Meter(budget_tokens=self.budget))
                claim_set, _ = phase1(capture, client)
                try:
                    judgements = list(judge_claims(claim_set, records, drifts, client))
                except BudgetExceeded as exc:
                    judgements = []
                    print(f"  budget halt: {exc}")

        if claim_set is None:
            from .claims import ClaimSet

            claim_set = ClaimSet(claims=[], skipped=[])

        report = build_report(
            capture, records, claim_set, judgements,
            drifts=drifts, split_sha256=split_digest(claim_set.claims),
        )
        bound = binding(capture)
        report.payload["binding"] = {"ok": bound.ok, "code": bound.code, "detail": bound.detail}
        report.payload["skips"] = analyse_skips(claim_set).to_dict()
        report.payload["judged"] = self.judge
        report.payload["saved_to"] = saved

        # The gate runs over exactly what is about to be sent, not over a sample of it.
        assert_no_confidence_number(strip_for_gate_check(report.payload))
        return report.payload


def make_handler(service: AuditService):
    class Handler(BaseHTTPRequestHandler):
        server_version = "SaysWho"

        def log_message(self, fmt, *args):
            print(f"  {self.address_string()}  {fmt % args}")

        # -------------------------------------------------------------- helpers

        def _origin(self) -> str | None:
            origin = self.headers.get("Origin", "")
            if not origin:
                return None
            parts = urlsplit(origin)
            normalised = f"{parts.scheme}://{parts.netloc}"
            return normalised if normalised in ALLOWED_ORIGINS else None

        def _send(self, status: int, payload: dict, origin: str | None = None):
            body = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            if origin:
                # Only the requesting origin, never a wildcard. A wildcard would let any page in the
                # browser read an audit, and an audit contains the answer text.
                self.send_header("Access-Control-Allow-Origin", origin)
                self.send_header("Vary", "Origin")
            self.end_headers()
            self.wfile.write(body)

        # -------------------------------------------------------------- routes

        def do_OPTIONS(self):
            origin = self._origin()
            if origin is None:
                return self._send(403, {"error": "ORIGIN_NOT_ALLOWED"})
            self.send_response(204)
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
            self.send_header("Vary", "Origin")
            self.end_headers()

        def do_GET(self):
            if self.path != "/health":
                return self._send(404, {"error": "NOT_FOUND"})
            # No origin check on health: it carries nothing, and the extension needs it to tell "the server
            # is not running" from "the audit failed", which are different things to tell a user.
            self._send(200, {"ok": True, "judge": service.judge}, self._origin())

        def do_POST(self):
            origin = self._origin()
            if origin is None:
                return self._send(
                    403,
                    {
                        "error": "ORIGIN_NOT_ALLOWED",
                        "detail": "this server answers the audited products and nothing else",
                    },
                )
            if self.path != "/audit":
                return self._send(404, {"error": "NOT_FOUND"}, origin)

            length = int(self.headers.get("Content-Length") or 0)
            if length <= 0 or length > 8_000_000:
                return self._send(413, {"error": "BAD_LENGTH"}, origin)

            try:
                payload = json.loads(self.rfile.read(length))
            except Exception as exc:
                return self._send(400, {"error": "BAD_JSON", "detail": str(exc)}, origin)

            try:
                result = service.audit(payload)
            except ValueError as exc:
                # A capture whose answer hash does not verify lands here, and it should: an edited answer is
                # not the answer that was delivered.
                return self._send(400, {"error": "BAD_CAPTURE", "detail": str(exc)}, origin)
            except Exception as exc:  # pragma: no cover - reported rather than swallowed
                return self._send(500, {"error": type(exc).__name__, "detail": str(exc)}, origin)

            self._send(200, result, origin)

    return Handler


def serve(service: AuditService, host: str = HOST, port: int = PORT) -> ThreadingHTTPServer:
    """Start the server. Returns it so a test can shut it down; the CLI below blocks instead."""
    return ThreadingHTTPServer((host, port), make_handler(service))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--port", type=int, default=PORT)
    parser.add_argument("--cache", type=Path, default=Path(".cache/fetch"))
    parser.add_argument("--captures", type=Path, default=Path("captures"),
                        help="where posted captures are written. This is where tools/run_stratum.py and "
                             "tools/bind_capture.py read them from")
    parser.add_argument("--judge", action="store_true",
                        help="run Phase 1 and Phase 3. Needs a key in this shell's environment")
    parser.add_argument("--judge-provider", choices=["gemini", "anthropic"], default=None)
    parser.add_argument("--budget", type=int, default=2_000_000)
    parser.add_argument("--no-drift", action="store_true")
    parser.add_argument("--skip-freeze-check", action="store_true")
    args = parser.parse_args(argv)

    if not args.skip_freeze_check:
        intact, why = freeze_intact()
        if not intact:
            print("FREEZE CHECK FAILED. The server will not start.")
            print()
            print(why)
            return 2

    service = AuditService(
        cache_dir=args.cache, judge=args.judge, provider=args.judge_provider,
        budget=args.budget, drift=not args.no_drift, captures_dir=args.captures,
    )
    httpd = serve(service, HOST, args.port)

    print(f"SaysWho audit server on http://{HOST}:{args.port}")
    print(f"  judge      {'on' if args.judge else 'off, fetch and liveness only'}")
    print(f"  captures   {args.captures}/  (posted captures are written here, never overwritten)")
    print(f"  origins    {', '.join(sorted(ALLOWED_ORIGINS))}")
    print("  bound to 127.0.0.1 only. Stop it when you are done; it is not something to leave running.")
    print()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")
    finally:
        httpd.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
