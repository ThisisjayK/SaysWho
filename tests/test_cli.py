"""The interactive CLI, and specifically `--split-only`.

The gold set has to be labelled before the judge has said anything: `goldset.agreement` refuses a blind
label that postdates the run it is compared against. But the artefact a labeller works from is a stored
split, and until this flag existed the only way to produce one was `--judge --save-split`, which runs Phase 3
and prints every verdict on the way past. Three refusals guarded blindness and the one mandatory step handed
you the answers.

So these tests are about what the flag does not do. The important one asserts the judge was never asked for a
verdict, by counting what the model was actually called for rather than by reading the output.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sayswho import cli  # noqa: E402

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "example-capture.json"


class CountingJudge:
    """Records what it was asked to do. Splits when asked; a verdict request would be a failure."""

    model = "counting-1"

    def __init__(self):
        self.purposes: list[str] = []
        self.probes = 0

    def probe(self):
        """The preflight, which every `JudgeClient` answers. Recorded, not counted as a purpose: it is not
        a model call and it must never look like one to the assertion below about what was asked."""
        self.probes += 1

    def complete_json(self, **kwargs):
        self.purposes.append(kwargs["purpose"])
        if kwargs["purpose"] == "split":
            return {
                "claims": [{"text": "Screening uptake rose in the reported period.", "markers": ["[1]"]}],
                "skipped": [{"text": "Share this page", "reason": "interface furniture"}],
            }
        return {"verdict": "NOT_FOUND_IN_SOURCE", "span": "", "reasoning": "", "notes": ""}


@pytest.fixture
def judge(monkeypatch):
    client = CountingJudge()
    from sayswho import gemini

    monkeypatch.setattr(gemini, "build_judge", lambda provider=None, meter=None: client)
    return client


# ---------------------------------------------------------------- what it refuses to be combined with


@pytest.mark.parametrize(
    "extra, expected",
    [
        (["--judge"], "opposites"),
        (["--goldset", "g.json"], "needs verdicts"),
        (["--report", "r.html"], "needs verdicts"),
        (["--report-json", "r.json"], "needs verdicts"),
    ],
)
def test_split_only_refuses_every_flag_that_would_show_a_verdict(extra, expected, tmp_path, capsys):
    """Each of these would put a verdict in front of the person about to label blind."""
    with pytest.raises(SystemExit):
        cli.main([str(FIXTURE), "--split-only", "--save-split", str(tmp_path / "s.json"),
                  "--skip-freeze-check", *extra])
    assert expected in capsys.readouterr().err


def test_split_only_without_save_split_is_an_error(tmp_path, capsys):
    """It produces one artefact and nothing else, so discarding it means the run did nothing."""
    with pytest.raises(SystemExit):
        cli.main([str(FIXTURE), "--split-only", "--skip-freeze-check"])
    assert "needs --save-split" in capsys.readouterr().err


def test_saving_a_split_still_needs_a_phase_that_produces_one():
    """The original guard, kept: --save-split alone would be accepted and silently ignored."""
    with pytest.raises(SystemExit):
        cli.main([str(FIXTURE), "--save-split", "x.json", "--skip-freeze-check"])


# ---------------------------------------------------------------- what it actually does


def test_split_only_writes_a_split_and_never_asks_for_a_verdict(tmp_path, judge, capsys):
    """The whole point. Phase 1 runs, Phase 3 does not, and the assertion is on what the model was asked
    for rather than on what got printed."""
    out = tmp_path / "PR-01.split.json"
    assert cli.main([str(FIXTURE), "--split-only", "--save-split", str(out), "--skip-freeze-check"]) == 0

    assert judge.purposes == ["split"], "Phase 3 ran, so the split cannot be labelled blind"
    assert judge.probes == 1, "the preflight ran, and it is not a model call, so it is counted separately"
    assert out.exists()

    stored = json.loads(out.read_text())
    assert stored["claims"], "a split with no claims gives a labeller nothing to label"

    printed = capsys.readouterr().out
    assert "Phase 3   not run" in printed
    for verdict in ("SUPPORTED", "NOT_FOUND_IN_SOURCE", "CONTRADICTED"):
        assert verdict not in printed, "a verdict name reached the terminal of someone about to label"


def test_the_split_it_writes_is_accepted_by_the_labelling_tool(tmp_path, judge):
    """The two halves have to fit: the labelling tool refuses any file carrying judge output, and this is
    the file it will be handed."""
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
    import label_goldset

    out = tmp_path / "PR-01.split.json"
    cli.main([str(FIXTURE), "--split-only", "--save-split", str(out), "--skip-freeze-check"])

    label_goldset.refuse_judge_output(json.loads(out.read_text()), out)


def test_split_only_runs_even_when_no_source_could_be_read(tmp_path, judge, monkeypatch):
    """Phase 1 splits the answer, which does not need a readable source, and the gold set stratifies
    UNAUDITABLE pairs first. Gating this on `auditable` would withhold exactly the pairs the sampler
    reaches for first."""
    from sayswho import fetch

    class DeadFetcher:
        def __init__(self, *a, **kw):
            pass

        def fetch(self, url, **kw):
            from sayswho.records import SOURCE_DEAD_LINK, FetchRecord

            return FetchRecord(
                url=url, code=SOURCE_DEAD_LINK, fetched_at="2026-08-12T00:00:00+00:00",
                http_status=404, detail="404",
            )

    monkeypatch.setattr(cli, "Fetcher", DeadFetcher, raising=False)
    monkeypatch.setattr(fetch, "Fetcher", DeadFetcher)

    out = tmp_path / "s.json"
    assert cli.main([str(FIXTURE), "--split-only", "--save-split", str(out), "--skip-freeze-check"]) == 0
    assert judge.purposes == ["split"]
    assert out.exists()


# ---------------------------------------------------------------- the run record as a file


def test_json_out_writes_a_file_the_labelling_tool_can_load(tmp_path):
    """`--json` prints the readout and then the JSON, both to stdout, so `--json > file` produces a page of
    prose in front of the JSON and nothing can load it. That was step one of the documented gold set
    workflow, and it could never have worked."""
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
    import label_goldset

    out = tmp_path / "record.json"
    assert cli.main([str(FIXTURE), "--json-out", str(out), "--skip-freeze-check"]) == 0

    record = json.loads(out.read_text())
    assert record["fetches"], "the labelling tool reads this for its G2 codes"
    label_goldset.refuse_judge_output(record, out)


def test_json_out_without_a_judge_carries_no_verdict(tmp_path):
    """It is handed to the labelling tool, which refuses any file carrying judge output. A fetch pass has
    none, and this asserts the payload does not grow one by accident."""
    out = tmp_path / "record.json"
    cli.main([str(FIXTURE), "--json-out", str(out), "--skip-freeze-check"])

    text = out.read_text()
    for key in ("judgements", "void_reason", "span_verified"):
        assert f'"{key}"' not in text
    assert json.loads(text)["claims"] is None, "no judge, no split, so no claims"


def test_json_and_json_out_agree(tmp_path, capsys):
    """Two surfaces for one record is two chances to disagree about what the run found."""
    out = tmp_path / "record.json"
    cli.main([str(FIXTURE), "--json", "--json-out", str(out), "--skip-freeze-check"])

    printed = capsys.readouterr().out
    start = printed.index("{\n")
    assert json.loads(printed[start:]) == json.loads(out.read_text())


# ------------------------------------------- the judge, checked before the fetch pass rather than after it


def _never_fetch(*args, **kwargs):
    raise AssertionError("a source was fetched before the judge was known to be able to work")


def test_a_judge_that_cannot_be_built_stops_the_run_before_a_single_fetch(monkeypatch, capsys):
    """The judge is built at the bottom of `main`, after every cited page has been fetched. Until this check
    existed, a run with no key spent the whole fetch pass first and said so afterwards."""
    import sayswho.gemini as gemini

    monkeypatch.setattr(cli, "fetch_sources", _never_fetch)
    monkeypatch.setattr(gemini, "build_judge", lambda provider=None, meter=None: (_ for _ in ()).throw(
        RuntimeError("set GEMINI_API_KEY")
    ))

    code = cli.main([str(FIXTURE), "--judge", "--skip-freeze-check"])

    assert code == 2
    out = capsys.readouterr().out
    assert "THE JUDGE CANNOT BE BUILT" in out
    assert "export GEMINI_API_KEY" in out
    assert "needs no" in out, "the fetch-only half of the tool is still worth offering"


def test_a_key_the_provider_rejects_is_caught_here_too(monkeypatch, capsys):
    """The day 10 failure on the harness path. `your-key-here` builds a client, so building one proves
    nothing and only the provider can settle it."""
    import sayswho.gemini as gemini
    from sayswho.model import JudgeUnavailable

    class Rejected:
        model = "rejected-1"

        def probe(self):
            raise JudgeUnavailable("the provider rejected the key: 400 API_KEY_INVALID", kind="rejected")

        def complete_json(self, **kwargs):
            raise AssertionError("the run continued past a judge that cannot work")

    monkeypatch.setattr(cli, "fetch_sources", _never_fetch)
    monkeypatch.setattr(gemini, "build_judge", lambda provider=None, meter=None: Rejected())

    code = cli.main([str(FIXTURE), "--judge", "--skip-freeze-check"])

    assert code == 2
    assert "your-key-here" in capsys.readouterr().out


def test_the_advice_names_the_command_that_was_actually_run(monkeypatch, capsys):
    """The message used to tell everyone to run the server, because that is where this check was born. A
    reader who typed `sayswho.cli` and is told to fix `sayswho.server` has been sent somewhere else."""
    import sayswho.gemini as gemini

    monkeypatch.setattr(cli, "fetch_sources", _never_fetch)
    monkeypatch.setattr(gemini, "build_judge", lambda provider=None, meter=None: (_ for _ in ()).throw(
        ImportError("No module named 'google'")
    ))

    cli.main([str(FIXTURE), "--judge", "--skip-freeze-check"])

    out = capsys.readouterr().out
    assert f".venv/bin/python -m sayswho.cli {FIXTURE} --judge" in out
    assert "sayswho.server" not in out


def test_split_only_is_checked_too_because_phase_1_is_a_model_call(monkeypatch, capsys, tmp_path):
    """`--judge` is not the flag that decides this. --split-only runs Phase 1, which is a model call, and a
    run that fetches everything and then cannot split has produced nothing to label."""
    import sayswho.gemini as gemini

    monkeypatch.setattr(cli, "fetch_sources", _never_fetch)
    monkeypatch.setattr(gemini, "build_judge", lambda provider=None, meter=None: (_ for _ in ()).throw(
        ImportError("No module named 'google'")
    ))

    out = tmp_path / "s.json"
    code = cli.main([str(FIXTURE), "--split-only", "--save-split", str(out), "--skip-freeze-check"])

    assert code == 2
    assert f"sayswho.cli {FIXTURE} --split-only" in capsys.readouterr().out, (
        "the command it offers has to be the one that was run, not --judge"
    )
    assert not out.exists(), "a run that stopped here wrote no split for anybody to label"


def test_a_fetch_only_run_asks_the_provider_nothing(monkeypatch):
    """Without --judge there is no judge to check, and checking one anyway would put a network call and a
    key requirement in front of the half of this tool that needs neither."""
    from sayswho import preflight

    monkeypatch.setattr(
        preflight, "check_judge",
        lambda *a, **kw: (_ for _ in ()).throw(AssertionError("preflighted a run with no judge in it")),
    )

    assert cli.main([str(FIXTURE), "--skip-freeze-check"]) == 0
