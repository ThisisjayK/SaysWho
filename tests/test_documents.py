"""A gate for prose.

Every number in this repo is guarded by something. `SCOPE.md` was guarded by nothing, and on day 5 three of
its claims turned out to be false: it said the extension was written in TypeScript, which it never was; it
said every competitor outputs a confidence score, which is false for two of the four; and a commit message
said §7 contained a section that did not exist. All three were found by a person asking, not by anything
structural. `FINDINGS.md` items 12 and 13.

The two prose checks that already existed are lexical: a banned-vocabulary scan and an em dash check. Neither
can tell whether a sentence about a file is true of that file. This one can, for the subset of claims that are
mechanically checkable, which is the subset that goes stale: a path, a module name, a command, a count.

**What this deliberately does not do.** It cannot check an argument, and it does not try. "A confidence score
on a source that could not be fetched is a fabricated number" is not checkable here and should not be. The
line is between a claim about this repo and a claim about the world; the first is in scope and the second
belongs to a reader.

`tests/test_extension_manifest.py` is the same mechanism pointed at code, and predates this file by three
days. Pointing it at documentation is the whole idea.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent

#: Documents this gate reads. `email-to-professor.md` and `reply-to-professor.md` are gitignored
#: correspondence and `CLAUDE.md` is instructions to a tool, so neither is a published claim about the repo.
DOCUMENTS = sorted(
    p for p in REPO.glob("*.md")
    if p.name not in {"email-to-professor.md", "reply-to-professor.md", "CLAUDE.md"}
) + sorted((REPO / "recipes").glob("*.md")) + [REPO / "extension" / "README.md"]

#: Paths a document may name that do not exist on disk, with the reason each is legitimate. Anything not
#: here has to exist. Keeping this list short is the point: every entry is a claim that a reader cannot
#: verify by looking, so each one needs a reason.
EXPECTED_ABSENT = {
    # Written at runtime, gitignored, and empty on a fresh clone. DATA_CONTRACT.md §9.
    "captures/": "written by the local server, gitignored",
    "reports/": "written by the local server, gitignored",
    "captures/raw/": "raw API responses, gitignored",
    ".cache/": "the fetch cache, gitignored",
    ".cache/fetch": "the fetch cache, gitignored",
    ".cache/break": "the break-attempt cache, gitignored",
    "runs/break": "an output directory the user chooses",
    "pages/": "stored pages, gitignored",
    "email-to-professor.md": "gitignored correspondence, deliberately not in the repo",
    "reply-to-professor.md": "gitignored correspondence, deliberately not in the repo",
    ".venv/bin/python": "a virtualenv the reader creates",
}

#: A repo-relative path inside backticks: at least one slash, and a file extension or a trailing slash.
#: Deliberately conservative. A pattern that matched every backticked token would flag `--judge` and
#: `SOURCE_OK`, and a gate that cries wolf gets deleted.
PATH_PATTERN = re.compile(
    r"`([A-Za-z0-9_.][A-Za-z0-9_./-]*(?:/[A-Za-z0-9_.-]+)+(?:\.[a-z]{2,5}|/))`"
)

#: A dotted module path inside backticks, like `sayswho.apicapture` or `tools/run_stratum.py`.
MODULE_PATTERN = re.compile(r"`(sayswho\.[a-z_]+(?:\.[a-z_]+)*)`")


def documents_with_text():
    for path in DOCUMENTS:
        if path.exists():
            yield path, path.read_text()


def strip_code_fences(text: str) -> str:
    """Fenced blocks are commands and examples, not claims about what exists.

    A shell example may legitimately name an output file that does not exist yet, and flagging those would
    make this gate wrong more often than the prose it guards.
    """
    return re.sub(r"```.*?```", "", text, flags=re.S)


# ---------------------------------------------------------------- paths


@pytest.mark.parametrize("path", DOCUMENTS, ids=lambda p: str(p.relative_to(REPO)))
def test_every_file_a_document_names_exists(path):
    """The check that would have caught the TypeScript claim's neighbours, and any renamed module."""
    if not path.exists():
        pytest.skip(f"{path} is not in this repo")

    prose = strip_code_fences(path.read_text())
    missing = []
    for match in PATH_PATTERN.finditer(prose):
        named = match.group(1)
        if named in EXPECTED_ABSENT or named.rstrip("/") + "/" in EXPECTED_ABSENT:
            continue
        if named.startswith(("http", "www.")) or "://" in named:
            continue
        # Relative to the repo root or to the document's own directory. `extension/README.md` names
        # `src/adapters.js`, which is correct from where that file sits and nonsense from the root.
        candidates = (REPO / named.rstrip("/"), path.parent / named.rstrip("/"))
        if not any(c.exists() for c in candidates):
            missing.append(named)

    assert not missing, (
        f"{path.relative_to(REPO)} names files that do not exist: {sorted(set(missing))}. "
        "Either the document is wrong or the file moved. If it is written at runtime, add it to "
        "EXPECTED_ABSENT with a reason."
    )


@pytest.mark.parametrize("path", DOCUMENTS, ids=lambda p: str(p.relative_to(REPO)))
def test_every_module_a_document_names_is_importable(path):
    if not path.exists():
        pytest.skip(f"{path} is not in this repo")

    import importlib

    prose = strip_code_fences(path.read_text())
    broken = []
    for match in MODULE_PATTERN.finditer(prose):
        name = match.group(1)
        try:
            importlib.import_module(name)
        except ImportError:
            broken.append(name)

    assert not broken, f"{path.relative_to(REPO)} names modules that do not import: {sorted(set(broken))}"


def test_the_expected_absent_list_stays_short():
    """Every entry is a claim a reader cannot verify by looking, so each needs a reason and the list needs a
    ceiling. If this fails, the honest fix is usually to stop naming runtime paths in prose."""
    assert len(EXPECTED_ABSENT) <= 15
    assert all(reason.strip() for reason in EXPECTED_ABSENT.values())


# ---------------------------------------------------------------- load-bearing specific claims


def test_the_stack_section_names_the_language_the_extension_is_written_in():
    """It said TypeScript for five days. There is no TypeScript in this repo and never was, and the
    no-build-step property is what makes the thirty-second install in README.md true."""
    scope = (REPO / "SCOPE.md").read_text()
    stack = scope[scope.index("**Extension (the product).**"):][:400]

    sources = list((REPO / "extension" / "src").glob("*"))
    assert not [p for p in sources if p.suffix == ".ts"], "there is no TypeScript here"
    assert "vanilla TypeScript" not in stack, "the stack section is claiming a language this repo never used"
    assert "vanilla JavaScript" in stack
    # The word may appear in the note recording the correction, which is the honest reason to keep it.


def test_the_two_dependency_claim_matches_what_the_package_imports():
    """`CLAUDE.md` and `DATA_CONTRACT.md` both promise two dependencies, both judge-only, and that every
    other layer is stdlib. A third import would make several documents false at once."""
    third_party = {"google", "anthropic"}
    allowed_importers = {"gemini.py", "model.py", "server.py"}

    offenders = {}
    for module in sorted((REPO / "sayswho").glob("*.py")):
        text = module.read_text()
        for name in third_party:
            if re.search(rf"^\s*(?:import {name}\b|from {name}[. ])", text, re.M):
                if module.name not in allowed_importers:
                    offenders.setdefault(module.name, []).append(name)

    assert not offenders, (
        f"{offenders} imports a judge-only dependency outside the judge layer. "
        "CLAUDE.md and DATA_CONTRACT.md both claim the fetch, extraction and gate layers are stdlib only."
    )


def test_the_extraction_and_fetch_layers_really_are_stdlib():
    """The claim is specific and load-bearing: it is the reason the PDF reader was hand-rolled."""
    stdlib_only = ("fetch.py", "extract.py", "reextract.py", "gates.py", "pdf.py", "apicapture.py")
    for name in stdlib_only:
        text = (REPO / "sayswho" / name).read_text()
        assert "import google" not in text and "from google" not in text, name
        assert "import anthropic" not in text and "from anthropic" not in text, name


def test_no_document_promises_a_confidence_score():
    """The hardest invariant in the project, checked in prose as well as in payloads. A document that
    described one would be describing a different tool."""
    for path, text in documents_with_text():
        for match in re.finditer(r"confidence (score|number|level|value)", text, re.I):
            # Whitespace-normalised before comparing. The first version missed "no\n   confidence score
            # anywhere" because the line wrap fell between the two words, which is the same fault as
            # comparing two character counts that were normalised differently.
            window = " ".join(text[max(0, match.start() - 220): match.end() + 220].lower().split())
            assert any(
                marker in window
                for marker in (
                    "no confidence", "never", "refus", "not", "cannot", "incumbent", "fabricated",
                    "instead", "rather than", "warns", "three of the four", "gate",
                )
            ), f"{path.name} mentions a confidence score without refusing it: {match.group(0)!r}"


def test_the_prior_art_table_is_dated():
    """Marketing pages change. A claim about a competitor with no date on it is a claim that quietly rots."""
    scope = (REPO / "SCOPE.md").read_text()
    section = scope[scope.index("## 1b."): scope.index("## 2.")]
    assert "2026-08-11" in section
    for tool in ("CiteGuardian", "CiteTrue", "GPTZero", "FactSentinel"):
        assert tool in section, f"{tool} dropped out of the prior art section"


def test_the_no_api_rates_decision_is_stated_and_enforced():
    """Both halves. The decision was recorded in prose first and was worth nothing until `rates.py` held it."""
    from sayswho.rates import UNPUBLISHABLE_SOURCES

    assert "api" in UNPUBLISHABLE_SOURCES

    scope = (REPO / "SCOPE.md").read_text()
    assert "no rate derived from an API capture is" in scope
    todo = (REPO / "TODO.md").read_text()
    assert "no API-sourced rate is published" in todo


def test_the_test_count_in_status_matches_the_suite(request):
    """STATUS.md publishes a test count. A number in a document that nothing checks is a number that drifts,
    and this file exists because of exactly that class of claim."""
    stated = re.search(r"(\d{3,}) tests", (REPO / "STATUS.md").read_text())
    assert stated, "STATUS.md should say how many tests there are"

    actual = len(request.session.items) if request.session.items else 0
    if actual < 50:
        pytest.skip("running a subset, so the total is not comparable")

    claimed = int(stated.group(1))
    assert abs(claimed - actual) <= 0, (
        f"STATUS.md says {claimed} tests, the suite collects {actual}. Update STATUS.md."
    )


# ---------------------------------------------------------------- the verified-inferred boundary, §4


def test_scope_section_four_matches_the_generated_table():
    """§4 is the heart of the attestation and it is exactly the kind of prose that rots: a field gets added
    to a payload and nobody revisits the document. It is generated from `sayswho.boundary` now, and this
    fails if the two drift apart."""
    from sayswho.boundary import render_labels, render_table

    scope = (REPO / "SCOPE.md").read_text()
    assert render_table() in scope, "SCOPE.md §4's field table is not what boundary.py renders"
    assert render_labels() in scope, "SCOPE.md §4's classification list is not what boundary.py renders"


def test_every_field_carries_one_of_the_seven_classifications():
    from sayswho.boundary import CLASSIFICATION, LABELS

    assert len(LABELS) == 7, "the attestation names seven classifications"
    for row in CLASSIFICATION:
        assert row.label in LABELS
        assert row.note.strip(), f"{row.field} has no note, so the table says what but never why"


def test_a_classification_outside_the_seven_is_refused():
    """The failure path. A row is a dataclass with a validator rather than a line in a markdown table, so an
    invented label cannot reach the document at all."""
    import pytest as _pytest

    from sayswho.boundary import Row

    with _pytest.raises(ValueError, match="not one of the seven"):
        Row("something", "probably-fine", "note")


def test_every_label_is_used_by_at_least_one_field():
    """A classification nothing is classified as is a word in a glossary, not a boundary."""
    from sayswho.boundary import CLASSIFICATION, LABELS

    used = {row.label for row in CLASSIFICATION}
    assert used == set(LABELS), f"defined but unused: {sorted(set(LABELS) - used)}"


def test_nothing_the_run_record_emits_is_unclassified(tmp_path):
    """The check a typed table cannot perform. Every top-level key of a real run record has to appear in the
    boundary, so adding a field to the payload and forgetting §4 fails here rather than in review."""
    import json
    import sys as _sys

    from sayswho.boundary import unclassified

    _sys.path.insert(0, str(REPO))
    from sayswho import cli

    out = tmp_path / "record.json"
    cli.main([str(REPO / "fixtures" / "example-capture.json"), "--json-out", str(out),
              "--skip-freeze-check"])

    missing = unclassified(json.loads(out.read_text()))
    assert not missing, f"emitted but not classified in SCOPE.md §4: {missing}"


def test_the_missing_rows_are_present_because_they_are_the_point():
    """A reader who wants one number will look for it. The absences are named rather than left blank."""
    from sayswho.boundary import CLASSIFICATION

    absent = [r.field for r in CLASSIFICATION if r.label == "missing"]
    assert any("true" in f for f in absent)
    assert any("confidence score" in f for f in absent)
