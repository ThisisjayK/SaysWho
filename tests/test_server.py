"""Local audit server tests, over real HTTP against the real server.

A local server is a real surface, so most of these are about what it refuses: a foreign origin, a wildcard
CORS header, a capture whose hash does not verify, and a capture carrying more URLs than anyone should be
able to make it fetch.
"""

from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request

import pytest

from sayswho.judge import SUPPORTED
from sayswho.records import Capture, Citation
from sayswho.server import ALLOWED_ORIGINS, HOST, MAX_CITATIONS, AuditService, serve

ANSWER = "Extending adjuvant endocrine therapy beyond five years reduced recurrence [1].\n"


@pytest.fixture
def audit_server(tmp_path):
    """The real server on a real ephemeral port, no judge, drift off.

    `captures_dir` is pinned to the temporary directory. Without it these tests write real files into the
    repo's own captures folder every run, which is both litter and a way to smuggle test data into a real
    stratum run.
    """
    service = AuditService(
        cache_dir=tmp_path / "cache", judge=False, drift=False, captures_dir=tmp_path / "captures"
    )
    httpd = serve(service, HOST, 0)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    host, port = httpd.server_address

    class Client:
        base = f"http://{host}:{port}"
        service = None

        def post(self, path, payload, origin="https://chatgpt.com"):
            request = urllib.request.Request(
                self.base + path,
                data=json.dumps(payload).encode(),
                headers={"Content-Type": "application/json", **({"Origin": origin} if origin else {})},
                method="POST",
            )
            try:
                with urllib.request.urlopen(request, timeout=30) as response:
                    return response.status, json.loads(response.read()), dict(response.headers)
            except urllib.error.HTTPError as exc:
                return exc.code, json.loads(exc.read()), dict(exc.headers)

        def get(self, path, origin="https://chatgpt.com"):
            request = urllib.request.Request(
                self.base + path, headers=({"Origin": origin} if origin else {})
            )
            try:
                with urllib.request.urlopen(request, timeout=10) as response:
                    return response.status, json.loads(response.read()), dict(response.headers)
            except urllib.error.HTTPError as exc:
                return exc.code, json.loads(exc.read()), dict(exc.headers)

    client = Client()
    client.service = service
    yield client
    httpd.shutdown()
    httpd.server_close()


def capture_payload(server, answer=ANSWER, path="/ok.html"):
    capture = Capture(
        query_id="UNASSIGNED", product="chatgpt", model_id="test",
        generated_at="2026-08-11T00:00:00+00:00", captured_at="2026-08-11T00:00:01+00:00",
        answer_text=answer,
        citations=[Citation(marker="[1]", url=server.url(path))],
    )
    return capture.to_dict()


# ---------------------------------------------------------------- it works


def test_health_says_whether_the_judge_is_on(audit_server):
    status, body, _ = audit_server.get("/health")
    assert status == 200
    assert body == {"ok": True, "judge": False}


def test_a_capture_comes_back_as_a_report_payload(audit_server, server):
    status, body, _ = audit_server.post("/audit", capture_payload(server))
    assert status == 200
    assert body["answer"] == ANSWER
    assert body["sources"][0]["code"] == "SOURCE_OK"
    assert body["labels"], "the renderer needs its labels in the payload"


def test_the_payload_is_what_render_js_expects(audit_server, server):
    """The same shape report.py produces for the standalone file, so one renderer serves both."""
    from sayswho.report import STATE_LABELS

    _, body, _ = audit_server.post("/audit", capture_payload(server))
    assert set(body["labels"]) == set(STATE_LABELS)
    assert "no_aggregate_rate" in body
    assert "claims" in body and "counts" in body


def test_an_unbound_capture_is_audited_and_says_it_is_unbound(audit_server, server):
    _, body, _ = audit_server.post("/audit", capture_payload(server))
    assert body["binding"]["ok"] is False
    assert body["binding"]["code"] == "CAPTURE_UNBOUND"


def test_the_no_confidence_gate_runs_over_what_is_actually_sent(audit_server, server):
    from sayswho.gates import assert_no_confidence_number
    from sayswho.report import strip_for_gate_check

    _, body, _ = audit_server.post("/audit", capture_payload(server))
    assert_no_confidence_number(strip_for_gate_check(body))


# ---------------------------------------------------------------- what it refuses


def test_a_foreign_origin_is_refused(audit_server, server):
    status, body, _ = audit_server.post("/audit", capture_payload(server), origin="https://evil.example")
    assert status == 403
    assert body["error"] == "ORIGIN_NOT_ALLOWED"


def test_a_request_with_no_origin_at_all_is_refused(audit_server, server):
    status, body, _ = audit_server.post("/audit", capture_payload(server), origin=None)
    assert status == 403


def test_the_cors_header_is_the_requesting_origin_and_never_a_wildcard(audit_server, server):
    """A wildcard would let any page in the browser read an audit, and an audit contains the answer text."""
    _, _, headers = audit_server.post("/audit", capture_payload(server))
    assert headers["Access-Control-Allow-Origin"] == "https://chatgpt.com"
    assert headers.get("Vary") == "Origin"


@pytest.mark.parametrize("origin", sorted(ALLOWED_ORIGINS))
def test_every_allowed_origin_is_accepted(audit_server, server, origin):
    status, _, headers = audit_server.post("/audit", capture_payload(server), origin=origin)
    assert status == 200
    assert headers["Access-Control-Allow-Origin"] == origin


def test_an_edited_answer_is_refused_by_the_hash(audit_server, server):
    payload = capture_payload(server)
    payload["answer_text"] = "Extending therapy did NOT reduce recurrence [1].\n"
    status, body, _ = audit_server.post("/audit", payload)
    assert status == 400
    assert body["error"] == "BAD_CAPTURE"
    assert "not the answer that was delivered" in body["detail"]


def test_an_answer_with_no_citations_halts_at_g0(audit_server, server):
    payload = capture_payload(server)
    payload["citations"] = []
    status, body, _ = audit_server.post("/audit", payload)
    assert status == 200
    assert body["error"] == "NO_CITATIONS"
    assert "not a zero percent answer" in body["note"]


def test_a_capture_with_too_many_citations_is_refused(audit_server, server):
    """A capture is a list of URLs this server will then fetch, so there is a cap on how many."""
    capture = Capture(
        query_id="UNASSIGNED", product="chatgpt", model_id="test",
        generated_at="2026-08-11T00:00:00+00:00", captured_at="2026-08-11T00:00:01+00:00",
        answer_text=ANSWER,
        citations=[
            Citation(marker=f"[{i}]", url=server.url(f"/ok.html?i={i}"))
            for i in range(MAX_CITATIONS + 1)
        ],
    )
    status, body, _ = audit_server.post("/audit", capture.to_dict())
    assert status == 400 or body.get("error") == "TOO_MANY_CITATIONS"
    assert server.paths.count("/ok.html") == 0, "nothing was fetched"


def test_an_unknown_path_is_a_404(audit_server):
    status, body, _ = audit_server.get("/secrets")
    assert status == 404


def test_malformed_json_is_a_400_not_a_crash(audit_server):
    request = urllib.request.Request(
        audit_server.base + "/audit", data=b"{not json",
        headers={"Content-Type": "application/json", "Origin": "https://chatgpt.com"}, method="POST",
    )
    try:
        urllib.request.urlopen(request, timeout=10)
        raise AssertionError("should have failed")
    except urllib.error.HTTPError as exc:
        assert exc.code == 400
        assert json.loads(exc.read())["error"] == "BAD_JSON"


# ---------------------------------------------------------------- the bind address


def test_the_server_binds_to_localhost_only(tmp_path):
    """Not 0.0.0.0. This is the one line where a mistake would put an audit endpoint on the network."""
    service = AuditService(cache_dir=tmp_path / "cache", judge=False, drift=False)
    httpd = serve(service, HOST, 0)
    try:
        assert httpd.server_address[0] == "127.0.0.1"
    finally:
        httpd.server_close()


def test_the_default_host_constant_is_loopback():
    assert HOST == "127.0.0.1"


# ---------------------------------------------------------------- the judge path


def test_the_judge_runs_when_it_is_switched_on(tmp_path, server, monkeypatch):
    """The server holds no pipeline of its own: it drives the same generators the CLI does."""
    import sayswho.gemini as gemini

    class ScriptedJudge:
        model = "scripted-1"

        def complete_json(self, **kwargs):
            if kwargs["purpose"] == "split":
                return {
                    "claims": [{
                        "text": "Extending adjuvant endocrine therapy beyond five years reduced recurrence",
                        "markers": ["[1]"],
                    }],
                    "skipped": [],
                }
            return {
                "verdict": SUPPORTED,
                "span": "reduced recurrence in the trial cohort",
                "reasoning": "scripted", "notes": "",
            }

    monkeypatch.setattr(gemini, "build_judge", lambda provider=None, meter=None: ScriptedJudge())

    service = AuditService(
        cache_dir=tmp_path / "cache", judge=True, drift=False, captures_dir=tmp_path / "captures"
    )
    payload = service.audit(capture_payload(server))

    assert payload["judged"] is True
    row = payload["claims"][0]["sources"][0]
    assert payload["claims"][0]["state"] == "SUPPORTED"
    assert row["voided"] is False, "the span guard passed, so the verdict stands"
    assert "reduced recurrence in the trial cohort" in row["span"]


def test_a_fabricated_span_is_voided_on_this_path_too(tmp_path, server, monkeypatch):
    """The guard is not a property of the CLI. It is in the pipeline, and this proves the server uses it."""
    import sayswho.gemini as gemini

    class LyingJudge:
        model = "scripted-1"

        def complete_json(self, **kwargs):
            if kwargs["purpose"] == "split":
                return {
                    "claims": [{
                        "text": "Extending adjuvant endocrine therapy beyond five years reduced recurrence",
                        "markers": ["[1]"],
                    }],
                    "skipped": [],
                }
            return {
                "verdict": SUPPORTED,
                "span": "a sentence that is nowhere on this page",
                "reasoning": "scripted", "notes": "",
            }

    monkeypatch.setattr(gemini, "build_judge", lambda provider=None, meter=None: LyingJudge())

    service = AuditService(
        cache_dir=tmp_path / "cache", judge=True, drift=False, captures_dir=tmp_path / "captures"
    )
    payload = service.audit(capture_payload(server))

    row = payload["claims"][0]["sources"][0]
    assert row["voided"] is True
    assert row["void_reason"] == "JUDGE_FABRICATED_SPAN"
    assert payload["claims"][0]["state"] == "COULD_NOT_VERIFY"


# ---------------------------------------------------------------- captures on disk


def test_a_posted_capture_is_written_where_the_harness_reads_them(tmp_path, server):
    """The extension used to download a copy of every audited capture to ~/Downloads. That is a directory
    full of JSON nobody asked for, and it is the wrong directory: the harness reads a captures folder."""
    service = AuditService(
        cache_dir=tmp_path / "cache", judge=False, drift=False, captures_dir=tmp_path / "captures"
    )
    payload = service.audit(capture_payload(server))

    written = sorted((tmp_path / "captures").glob("*.json"))
    assert len(written) == 1
    assert payload["saved_to"] == str(written[0])
    assert json.loads(written[0].read_text())["answer_text"] == ANSWER


def test_two_captures_in_the_same_second_are_two_files(tmp_path, server):
    """A capture is a record of something that happened. Two answers to one question are two records."""
    service = AuditService(
        cache_dir=tmp_path / "cache", judge=False, drift=False, captures_dir=tmp_path / "captures"
    )
    service.audit(capture_payload(server))
    service.audit(capture_payload(server))
    assert len(sorted((tmp_path / "captures").glob("*.json"))) == 2


def test_the_capture_is_saved_before_any_fetching_starts(tmp_path, server):
    """An audit takes a minute and can be interrupted. The capture is the irreplaceable half."""
    service = AuditService(
        cache_dir=tmp_path / "cache", judge=False, drift=False, captures_dir=tmp_path / "captures"
    )

    seen = {}
    original = service.fetcher.fetch

    def watching(url, **kw):
        seen["files_at_first_fetch"] = len(list((tmp_path / "captures").glob("*.json")))
        return original(url, **kw)

    service.fetcher.fetch = watching
    service.audit(capture_payload(server))
    assert seen["files_at_first_fetch"] == 1


def test_an_uncitable_answer_is_not_written(tmp_path, server):
    """G0 halts before anything else, and there is nothing to audit later."""
    service = AuditService(
        cache_dir=tmp_path / "cache", judge=False, drift=False, captures_dir=tmp_path / "captures"
    )
    payload = capture_payload(server)
    payload["citations"] = []
    result = service.audit(payload)
    assert result["error"] == "NO_CITATIONS"
    assert not (tmp_path / "captures").exists() or not list((tmp_path / "captures").glob("*.json"))
