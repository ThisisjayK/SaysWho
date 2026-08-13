"""Binding twenty-four captures at once, which is twenty-four chances to be off by one.

A misbound capture is a rate computed over the wrong question, and it is silent: every hash still verifies,
every gate still passes, and the number is about a question nobody asked in that session. Nothing downstream
can catch it, because the binding is the only thing that ever knew.

So this mode is built to be refused rather than trusted. It writes nothing without `--confirm`, it prints the
query beside the first sentence of the answer it is about to bind, and it fails rather than guessing whenever
the counts do not line up. These tests are mostly about the refusals.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

import bind_capture  # noqa: E402

from sayswho.records import Capture, Citation  # noqa: E402


def capture_file(path: Path, answer: str, captured_at: str, product="claude", query_id="UNASSIGNED"):
    record = Capture(
        query_id=query_id, product=product, model_id="test",
        generated_at=captured_at, captured_at=captured_at,
        answer_text=answer,
        citations=[Citation(marker="[1]", url="https://example.org/1")],
    )
    path.write_text(json.dumps(record.to_dict(), indent=2), encoding="utf-8")
    return path


def consumer_ids(frozen):
    from sayswho.queryset import stratum_of

    return sorted(q for q in frozen if stratum_of(q) == "consumer")


def args_for(captures, **kw):
    class A:
        pass

    a = A()
    a.captures = captures
    a.stratum = kw.get("stratum", "consumer")
    a.confirm = kw.get("confirm", False)
    a.allow_partial = kw.get("allow_partial", False)
    a.rebind = kw.get("rebind", False)
    return a


# ---------------------------------------------------------------- the dry run is the default


def test_nothing_is_written_without_confirm(tmp_path, capsys):
    from sayswho.queryset import frozen_query_ids

    frozen = frozen_query_ids()
    ids = consumer_ids(frozen)
    paths = [
        capture_file(tmp_path / f"c{n}.json", f"Answer number {n}. Second sentence.",
                     f"2026-08-12T10:{n:02d}:00+00:00")
        for n in range(3)
    ]

    code = bind_capture.bind_in_order(args_for(paths, allow_partial=True), frozen)
    printed = capsys.readouterr().out

    assert code == 0
    assert "Nothing was written" in printed
    for path in paths:
        assert Capture.from_json(path).query_id == "UNASSIGNED"
    assert ids[0] in printed, "the pairing has to name the query it proposes"


def test_the_pairing_shows_the_query_beside_the_answer_it_would_bind(tmp_path, capsys):
    """The eyeball check, and the only thing standing between an off-by-one and a published rate over the
    wrong question. A person reading a question about visas next to an answer about security deposits sees it
    in a second; no hash in this project can."""
    from sayswho.queryset import frozen_query_ids, query_text

    frozen = frozen_query_ids()
    ids = consumer_ids(frozen)
    path = capture_file(tmp_path / "c0.json", "Ibuprofen and lisinopril interact. More text follows.",
                        "2026-08-12T10:00:00+00:00")

    bind_capture.bind_in_order(args_for([path], allow_partial=True), frozen)
    printed = capsys.readouterr().out

    assert "answer opens: Ibuprofen and lisinopril interact." in printed
    assert " ".join(query_text(ids[0]).split())[:40] in printed


# ---------------------------------------------------------------- order comes from the record


def test_captures_are_paired_in_capture_time_order_not_filename_order(tmp_path, capsys):
    """A filename is whatever the browser wrote. `captured_at` is in the record and is what the extension
    stamped at the moment of capture."""
    from sayswho.queryset import frozen_query_ids

    frozen = frozen_query_ids()
    ids = consumer_ids(frozen)
    # Named so that alphabetical order is the reverse of capture order.
    late = capture_file(tmp_path / "aaa.json", "Second answer.", "2026-08-12T11:00:00+00:00")
    early = capture_file(tmp_path / "zzz.json", "First answer.", "2026-08-12T10:00:00+00:00")

    bind_capture.bind_in_order(args_for([late, early], allow_partial=True, confirm=True), frozen)
    capsys.readouterr()

    assert Capture.from_json(early).query_id == ids[0]
    assert Capture.from_json(late).query_id == ids[1]


def test_confirm_writes_every_binding(tmp_path, capsys):
    from sayswho.queryset import frozen_query_ids

    frozen = frozen_query_ids()
    ids = consumer_ids(frozen)
    paths = [
        capture_file(tmp_path / f"c{n}.json", f"Answer {n}.", f"2026-08-12T10:{n:02d}:00+00:00")
        for n in range(4)
    ]

    assert bind_capture.bind_in_order(args_for(paths, allow_partial=True, confirm=True), frozen) == 0
    for n, path in enumerate(paths):
        assert Capture.from_json(path).query_id == ids[n]


# ---------------------------------------------------------------- the refusals


def test_more_captures_than_queries_is_refused(tmp_path, capsys):
    """More captures than questions means at least one question was asked twice, and order cannot say which
    one. Guessing here would bind two answers to two different questions and be undetectable."""
    from sayswho.queryset import frozen_query_ids

    frozen = frozen_query_ids()
    n_ids = len(consumer_ids(frozen))
    paths = [
        capture_file(tmp_path / f"c{n}.json", f"Answer {n}.", f"2026-08-12T10:{n:02d}:00+00:00")
        for n in range(n_ids + 1)
    ]

    assert bind_capture.bind_in_order(args_for(paths, confirm=True), frozen) == 1
    assert all(Capture.from_json(p).query_id == "UNASSIGNED" for p in paths)


def test_fewer_captures_than_queries_needs_allow_partial(tmp_path, capsys):
    """A run that stopped early is normal. A run that stopped early and said nothing is not."""
    from sayswho.queryset import frozen_query_ids

    frozen = frozen_query_ids()
    path = capture_file(tmp_path / "c0.json", "Answer.", "2026-08-12T10:00:00+00:00")

    assert bind_capture.bind_in_order(args_for([path], confirm=True), frozen) == 1
    assert Capture.from_json(path).query_id == "UNASSIGNED"

    assert bind_capture.bind_in_order(args_for([path], confirm=True, allow_partial=True), frozen) == 0


def test_the_unbound_ids_are_named_rather_than_left_implicit(tmp_path, capsys):
    from sayswho.queryset import frozen_query_ids

    frozen = frozen_query_ids()
    ids = consumer_ids(frozen)
    path = capture_file(tmp_path / "c0.json", "Answer.", "2026-08-12T10:00:00+00:00")

    bind_capture.bind_in_order(args_for([path], allow_partial=True), frozen)
    printed = capsys.readouterr().out
    assert "not bound, because no capture reached them" in printed
    assert ids[-1] in printed


def test_an_unreadable_capture_stops_everything(tmp_path, capsys):
    """Including one whose answer was edited after capture, which `Capture.from_dict` rejects on the hash. A
    run with one hole in it is not a run to bind halfway through."""
    from sayswho.queryset import frozen_query_ids

    frozen = frozen_query_ids()
    good = capture_file(tmp_path / "c0.json", "Answer.", "2026-08-12T10:00:00+00:00")
    bad = tmp_path / "c1.json"
    payload = json.loads(good.read_text())
    payload["answer_text"] = "edited after capture"
    bad.write_text(json.dumps(payload))

    assert bind_capture.bind_in_order(args_for([good, bad], confirm=True, allow_partial=True), frozen) == 1
    assert Capture.from_json(good).query_id == "UNASSIGNED", "nothing is written when any file is bad"


def test_a_stratum_with_no_frozen_queries_is_refused(tmp_path):
    from sayswho.queryset import frozen_query_ids

    frozen = frozen_query_ids()
    path = capture_file(tmp_path / "c0.json", "Answer.", "2026-08-12T10:00:00+00:00")
    assert bind_capture.bind_in_order(args_for([path], stratum="professional_research"), frozen) == 1


def test_in_order_without_a_stratum_is_refused(tmp_path):
    from sayswho.queryset import frozen_query_ids

    path = capture_file(tmp_path / "c0.json", "Answer.", "2026-08-12T10:00:00+00:00")
    assert bind_capture.bind_in_order(args_for([path], stratum=None), frozen_query_ids()) == 1


# ---------------------------------------------------------------- one implementation of the write


def test_both_modes_write_through_the_same_function(tmp_path):
    """`bind_one` verifies the answer hash and records a rebind rather than overwriting it. Two callers
    writing the binding themselves would have meant two places deciding what a rebind does."""
    from sayswho.queryset import frozen_query_ids

    ids = consumer_ids(frozen_query_ids())
    path = capture_file(tmp_path / "c0.json", "Answer.", "2026-08-12T10:00:00+00:00")

    ok, _ = bind_capture.bind_one(path, ids[0])
    assert ok and Capture.from_json(path).query_id == ids[0]

    refused, message = bind_capture.bind_one(path, ids[1])
    assert not refused and "already bound" in message

    ok, _ = bind_capture.bind_one(path, ids[1], rebind=True)
    assert ok
    assert json.loads(path.read_text())["_rebound_from"] == [ids[0]]


def test_first_sentence_stops_at_the_sentence():
    assert bind_capture.first_sentence("One. Two.") == "One."
    assert bind_capture.first_sentence("No terminator here") == "No terminator here"
    assert bind_capture.first_sentence("x" * 200).endswith("...")
