"""Tests for the pre-labelling pass.

This tool exists to protect an hour of human work, so what it must not do is report a session as ready when
it is not. Three ways it could:

- prepare a different sample from the one the session will show, which would leave the labeller waiting on
  the network for exactly the pairs that mattered;
- re-fetch a page already in the cache, which moves the extraction check onto bytes the judge never read and
  quietly changes what `goldset.attribution` is measuring;
- report a clean zero where it means "nothing was assessed", which is the failure this whole project is
  organised against.

Plus the one it shares with the labelling tool: it opens artefacts on behalf of somebody who must not see a
verdict, so no verdict may reach its output.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

import label_goldset  # noqa: E402
import prep_goldset  # noqa: E402

from sayswho.cache import FetchCache  # noqa: E402
from sayswho.claims import Claim  # noqa: E402
from sayswho.fetch import Fetcher  # noqa: E402
from sayswho.judge import CONTRADICTED, SUPPORTED  # noqa: E402
from sayswho.records import SOURCE_OK, SOURCE_PAYWALLED  # noqa: E402
from sayswho.splits import StoredSplit  # noqa: E402


def split(urls, product="chatgpt", prefix="c"):
    return StoredSplit(
        answer_sha256="a" * 64,
        query_id="PR-01",
        product=product,
        created_at="2026-08-12T09:00:00+00:00",
        claim_prompt_version="claims-v1",
        judge_class="GeminiJudge",
        judge_model="gemini-3.5-flash-lite",
        claims=[
            Claim(id=f"{prefix}{i}", text=f"Claim number {i}.", markers=["[1]"], urls=[url])
            for i, url in enumerate(urls)
        ],
        skipped=[],
    )


def fetch_record(urls_and_codes):
    return {"fetches": [{"url": url, "code": code} for url, code in urls_and_codes]}


# ---------------------------------------------------------------- the same sample, not a similar one


def test_prep_prepares_the_pairs_the_session_will_actually_show(tmp_path):
    """The load-bearing property. Both call `choose_sample`, and this asserts they land on the same pairs
    rather than asserting that they both call it, because the second is a test about the shape of the code."""
    urls = [f"https://example.org/{i}" for i in range(12)]
    s = split(urls)
    pool = label_goldset.build_pool([s], [], None)

    prep = prep_goldset.prepare([s], [], FetchCache(tmp_path / "c"), target=5, seed=7, out=None,
                                fetcher=None, audit_roots=[tmp_path / "none"])
    session = label_goldset.choose_sample(pool, 5, 7)

    assert [(p["claim_id"], p["url"]) for p in prep.pairs] == [(r["claim_id"], r["url"]) for r in session]


def test_a_resumed_session_prepares_only_what_is_left(tmp_path):
    """A second sitting picks up where the first stopped, so preparing the whole sample again would warm the
    wrong half of it."""
    from sayswho.goldset import GoldLabel, GoldSet

    urls = [f"https://example.org/{i}" for i in range(12)]
    s = split(urls)
    pool = label_goldset.build_pool([s], [], None)
    first = label_goldset.choose_sample(pool, 5, 7)

    out = tmp_path / "gold.json"
    GoldSet(
        split_sha256s=[s.split_sha256], judge_class="GeminiJudge", judge_model="m",
        judge_prompt_version="judge-v2", claim_prompt_version="claims-v1",
        created_at="2026-08-12T10:00:00+00:00",
        labels=[GoldLabel(claim_id=first[0]["claim_id"], url=first[0]["url"], label="SUPPORTED",
                          labelled_at="2026-08-12T10:00:00+00:00")],
    ).save(out)

    prep = prep_goldset.prepare([s], [], FetchCache(tmp_path / "c"), target=5, seed=7, out=out,
                                fetcher=None, audit_roots=[tmp_path / "none"])
    assert prep.already_labelled == 1
    assert len(prep.pairs) == 4
    assert (first[0]["claim_id"], first[0]["url"]) not in [(p["claim_id"], p["url"]) for p in prep.pairs]


# ---------------------------------------------------------------- what it fetches, and what it leaves alone


def test_a_missing_page_is_fetched_and_a_cached_one_is_left_alone(server, cache):
    """Both halves in one test, because the second is the one that would be tempting to skip. Re-fetching a
    page we already have would compare the labeller's passage against a document the judge never read, which
    is the objection `tools/reaudit_spans.py` makes to re-checking spans against the live web."""
    already = server.url("/article")
    missing = server.url("/other")
    warm = Fetcher(cache, rate_limit=0.0)
    warm.fetch(already)

    fetcher = Fetcher(cache, rate_limit=0.0)
    prep = prep_goldset.prepare([split([already, missing])], [], cache, target=2, seed=1, out=None,
                                fetcher=fetcher, audit_roots=[Path("nonexistent-audit-root")])

    pages_requested = [u for u in fetcher.requested if not u.endswith("/robots.txt")]
    assert pages_requested == [missing], "the cached page must not be requested again"
    assert any(u.endswith("/robots.txt") for u in fetcher.requested), (
        "the contract applies to robots.txt too, and this tool fetches through the same fetcher"
    )
    assert prep.pages[already].origin == "cache"
    assert prep.pages[missing].origin == "fetched"
    assert prep.fetched_now == [missing]
    assert "fetched today" in prep.render(), "the weaker claim for those pages has to be visible"


def test_no_fetch_sends_nothing(server, cache):
    prep = prep_goldset.prepare([split([server.url("/article")])], [], cache, target=1, seed=1, out=None,
                                fetcher=None, audit_roots=[Path("nonexistent-audit-root")])
    assert server.paths == []
    assert prep.pages[server.url("/article")].origin == "missing"
    assert "NOT AVAILABLE" in prep.render()


def test_a_page_that_cannot_be_fetched_is_named_rather_than_counted_as_ready(server, cache):
    dead = server.url("/missing-page")
    fetcher = Fetcher(cache, rate_limit=0.0)
    prep = prep_goldset.prepare([split([dead])], [], cache, target=1, seed=1, out=None,
                                fetcher=fetcher, audit_roots=[Path("nonexistent-audit-root")])
    assert prep.checkable_pairs == 0
    assert prep.pages[dead].detail


# ---------------------------------------------------------------- not knowing is not a clean result


def test_without_a_run_record_the_sample_is_not_stratified_and_says_so(tmp_path):
    """The quiet failure this tool was built to surface. `build_pool` takes the G2 codes from a run record,
    and without one every pair buckets as UNKNOWN, so `SCOPE.md` section 3's "UNAUDITABLE first" silently does
    not happen and the sample is drawn across products alone."""
    urls = [f"https://example.org/{i}" for i in range(6)]
    prep = prep_goldset.prepare([split(urls)], [], FetchCache(tmp_path / "c"), target=3, seed=1, out=None,
                                fetcher=None, audit_roots=[tmp_path / "none"])
    assert not prep.codes_known
    assert "NOT STRATIFIED" in prep.render()


def test_unauditable_is_reported_as_unknown_rather_than_as_zero(tmp_path):
    """Zero would read as "every source is readable" for a set of pages nothing has assessed. The same
    distinction as a missing snapshot making drift unknown rather than unchanged."""
    prep = prep_goldset.prepare([split(["https://example.org/1"])], [], FetchCache(tmp_path / "c"),
                                target=1, seed=1, out=None, fetcher=None, audit_roots=[tmp_path / "none"])
    assert prep.unauditable_pairs is None
    assert "unauditable   not known" in prep.render()


def test_with_a_run_record_the_codes_come_through_and_unauditable_is_counted(tmp_path):
    urls = ["https://example.org/1", "https://example.org/2"]
    record = fetch_record([(urls[0], SOURCE_OK), (urls[1], SOURCE_PAYWALLED)])
    prep = prep_goldset.prepare([split(urls)], [record], FetchCache(tmp_path / "c"), target=2, seed=1,
                                out=None, fetcher=None, audit_roots=[tmp_path / "none"])
    assert prep.codes_known
    assert prep.unauditable_pairs == 1
    assert "NOT STRATIFIED" not in prep.render()


# ---------------------------------------------------------------- the blindness it shares with the session


def test_no_verdict_reaches_the_output(tmp_path, capsys):
    """It reads the same artefacts the prior-audit scan reads, on behalf of somebody who must not see one."""
    reports = tmp_path / "reports"
    reports.mkdir()
    (reports / "r.json").write_text(json.dumps({
        "meta": {"answer_sha256": "a" * 64},
        "claims": [{"sources": [{"verdict": SUPPORTED, "judged": True},
                                {"verdict": CONTRADICTED, "judged": True}]}],
        "judged": True,
    }))

    s = split(["https://example.org/1"])
    path = tmp_path / "split.json"
    s.save(path)

    code = prep_goldset.main(["--split", str(path), "--target", "1", "--no-fetch",
                              "--cache", str(tmp_path / "c"), "--audit-scan", str(reports)])
    printed = capsys.readouterr().out
    assert code == 0
    assert "PRIOR AUDIT" in printed, "it still has to say what it found"
    for verdict in (SUPPORTED, CONTRADICTED):
        assert verdict not in printed


def test_an_input_carrying_judge_output_is_refused(tmp_path):
    """Passing the judged run record where the fetch record was meant. Same refusal as the labelling tool,
    because it is the same mistake and this tool takes the same argument."""
    path = tmp_path / "run.json"
    path.write_text(json.dumps({"fetches": [{"url": "https://example.org/1", "verdict": SUPPORTED}]}))
    with pytest.raises(label_goldset.NotBlind):
        prep_goldset.load_json(path)


def test_the_prior_audit_refusal_is_surfaced_before_the_session(tmp_path, capsys):
    """The point of running this first: --supplemental becomes a decision made now rather than a refusal met
    at the first prompt, after the terminal is already open."""
    reports = tmp_path / "reports"
    reports.mkdir()
    (reports / "r.json").write_text(json.dumps({
        "meta": {"answer_sha256": "a" * 64},
        "claims": [{"sources": [{"verdict": SUPPORTED, "judged": True}]}],
        "judged": True,
    }))
    s = split(["https://example.org/1"])
    path = tmp_path / "split.json"
    s.save(path)

    prep_goldset.main(["--split", str(path), "--target", "1", "--no-fetch",
                       "--cache", str(tmp_path / "c"), "--audit-scan", str(reports)])
    printed = capsys.readouterr().out
    assert "--supplemental is the way" in printed


def test_it_never_runs_the_judge(tmp_path, capsys):
    """Asserted by what it says rather than only by what it imports, because the sentence is what a reader
    of the terminal has to be able to trust."""
    s = split(["https://example.org/1"])
    path = tmp_path / "split.json"
    s.save(path)
    prep_goldset.main(["--split", str(path), "--target", "1", "--no-fetch",
                       "--cache", str(tmp_path / "c"), "--audit-scan", str(tmp_path / "none")])
    assert "has run the judge or opened a verdict" in capsys.readouterr().out
