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
