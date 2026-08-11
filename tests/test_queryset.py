"""Binding tests.

Every capture in the repo so far carries `query_id: UNASSIGNED`, which is fine for auditing one answer and
not fine for publishing a rate. These pin the difference.
"""

from __future__ import annotations

import json

import pytest

from sayswho.queryset import (
    CAPTURE_UNBOUND,
    QUERY_NOT_FROZEN,
    QUERY_UNKNOWN,
    UNASSIGNED,
    binding,
    frozen_query_ids,
)
from sayswho.records import Capture, Citation

TOML = """
[stratum]
id = "professional_research"
id_prefix = "PR"
label = "Professional research"
status = "ready"

[[query]]
id = "PR-01"
domain = "competitive"
text = "A real question."
cost_of_error = "Something concrete."

[[query]]
id = "PR-02"
domain = "regulatory"
text = "Another real question."
cost_of_error = "Something else concrete."
"""


@pytest.fixture
def frozen_set(tmp_path):
    """A queries directory with PR-01 frozen and PR-02 present but not frozen."""
    queries = tmp_path / "queries"
    queries.mkdir()
    (queries / "professional.toml").write_text(TOML)
    manifest = tmp_path / "FREEZE.json"
    manifest.write_text(json.dumps({
        "version": 1,
        "unfreezes": [],
        "frozen": {
            "professional.toml": {
                "frozen_at": "2026-08-11T00:00:00+00:00",
                "file_sha256": "unused-by-these-tests",
                "stratum_id": "professional_research",
                "query_count": 1,
                "query_hashes": {"PR-01": "deadbeef"},
            }
        },
    }))
    return queries, manifest


def capture(query_id):
    return Capture(
        query_id=query_id,
        product="chatgpt",
        model_id="test",
        generated_at="2026-08-11T00:00:00+00:00",
        captured_at="2026-08-11T00:00:01+00:00",
        answer_text="A claim [1].",
        citations=[Citation(marker="[1]", url="https://a.example/1")],
    )


def test_an_unassigned_capture_cannot_publish_a_rate(frozen_set):
    result = binding(capture(UNASSIGNED), *frozen_set)
    assert not result.ok
    assert result.code == CAPTURE_UNBOUND
    assert "Per-claim verdicts stand" in result.detail


def test_an_empty_query_id_is_the_same_refusal(frozen_set):
    assert binding(capture(""), *frozen_set).code == CAPTURE_UNBOUND


def test_a_frozen_query_binds(frozen_set):
    assert binding(capture("PR-01"), *frozen_set).ok


def test_a_query_on_disk_but_not_in_the_manifest_is_refused(frozen_set):
    """A query added after the freeze. `freeze_queries.py check` catches this too; this catches it at the
    point where a number would be printed."""
    result = binding(capture("PR-02"), *frozen_set)
    assert result.code == QUERY_NOT_FROZEN
    assert "added after the freeze" in result.detail


def test_an_id_that_exists_nowhere_is_a_different_refusal(frozen_set):
    result = binding(capture("PR-99"), *frozen_set)
    assert result.code == QUERY_UNKNOWN


def test_frozen_ids_are_the_intersection_of_disk_and_manifest(frozen_set):
    assert frozen_query_ids(*frozen_set) == {"PR-01"}


def test_a_manifest_entry_whose_file_vanished_binds_nothing(tmp_path):
    manifest = tmp_path / "FREEZE.json"
    manifest.write_text(json.dumps({
        "frozen": {"gone.toml": {"query_hashes": {"PR-01": "x"}}}, "unfreezes": [], "version": 1,
    }))
    queries = tmp_path / "queries"
    queries.mkdir()
    assert frozen_query_ids(queries, manifest) == set()


def test_the_repos_own_consumer_stratum_is_frozen():
    """A real check against the real manifest: day 1 froze 24 consumer queries."""
    ids = frozen_query_ids()
    assert len([i for i in ids if i.startswith("CO-")]) == 24


def test_the_professional_stratum_is_still_empty():
    """It stays empty until real queries arrive. If this test ever fails because it found some, good."""
    assert not [i for i in frozen_query_ids() if i.startswith("PR-")]
