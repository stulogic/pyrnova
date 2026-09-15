"""B4.4 — JSONL concurrency / durability hardening (single-node, append-only).

Proves the durable state model is production-safe for the intended single-node concurrency model:
concurrent process/thread appends never corrupt or interleave records; a partial/torn trailing write is
detected and recovered (fail-closed, no silent truncation); a malformed COMPLETE record fails closed; the
store recovers correctly on restart; and a backup snapshot coordinates safely with active writes.
"""

from __future__ import annotations

import json
import multiprocessing as mp
import threading
from pathlib import Path

import pytest

from pyrnova.state import StateCorruptionError, StateStore


def _proc_worker(root: str, worker_id: int, n: int) -> None:
    store = StateStore(Path(root))
    for i in range(n):
        store.append("stream", {"id": f"{worker_id}-{i}", "worker": worker_id, "seq": i})


def test_concurrent_process_appends_are_all_durable_and_intact(tmp_path):
    workers, per = 6, 40
    ctx = mp.get_context("spawn")
    procs = [ctx.Process(target=_proc_worker, args=(str(tmp_path), w, per)) for w in range(workers)]
    for p in procs:
        p.start()
    for p in procs:
        p.join()
        assert p.exitcode == 0
    # Every append landed exactly once, every line is a complete valid record (no interleaving / torn lines).
    raw = (tmp_path / "stream.jsonl").read_text().splitlines()
    assert len(raw) == workers * per
    ids = set()
    for line in raw:
        rec = json.loads(line)  # would raise if a line were torn/interleaved
        ids.add(rec["id"])
    assert ids == {f"{w}-{i}" for w in range(workers) for i in range(per)}


def test_concurrent_thread_appends_are_intact(tmp_path):
    store = StateStore(tmp_path)
    threads, per = 8, 50

    def work(tid):
        for i in range(per):
            store.append("s", {"id": f"{tid}-{i}"})

    ts = [threading.Thread(target=work, args=(t,)) for t in range(threads)]
    for t in ts:
        t.start()
    for t in ts:
        t.join()
    recs = list(store.read("s"))
    assert len(recs) == threads * per
    assert {r["id"] for r in recs} == {f"{t}-{i}" for t in range(threads) for i in range(per)}


def test_partial_trailing_write_is_recovered(tmp_path):
    store = StateStore(tmp_path)
    store.append("s", {"id": "committed-1"})
    store.append("s", {"id": "committed-2"})
    # Simulate a writer that crashed mid-append: a trailing line with no terminating newline.
    with (tmp_path / "s.jsonl").open("a", encoding="utf-8") as fh:
        fh.write('{"id": "torn", "half')  # no closing / no newline
    recs = list(store.read("s"))
    assert [r["id"] for r in recs] == ["committed-1", "committed-2"]  # torn tail dropped, committed intact
    assert store.count("s") == 2


def test_malformed_complete_record_fails_closed(tmp_path):
    store = StateStore(tmp_path)
    store.append("s", {"id": "ok"})
    with (tmp_path / "s.jsonl").open("a", encoding="utf-8") as fh:
        fh.write("{not valid json}\n")  # a COMPLETE (newline-terminated) but malformed record
    with pytest.raises(StateCorruptionError):
        list(store.read("s"))


def test_restart_recovery(tmp_path):
    StateStore(tmp_path).append("s", {"id": "a"})
    StateStore(tmp_path).append("s", {"id": "b"})
    # A fresh store on the same root sees all durably-committed records.
    assert {r["id"] for r in StateStore(tmp_path).read("s")} == {"a", "b"}


def test_snapshot_during_active_writes_is_consistent(tmp_path):
    store = StateStore(tmp_path)
    for i in range(20):
        store.append("s", {"id": f"pre-{i}"})
    stop = threading.Event()

    def writer():
        i = 0
        while not stop.is_set():
            store.append("s", {"id": f"live-{i}"})
            i += 1

    t = threading.Thread(target=writer)
    t.start()
    try:
        dest = tmp_path / "snap" / "s.jsonl"
        for _ in range(20):
            n = store.snapshot("s", dest)
            # Every snapshot is internally consistent: only complete, parseable records, no torn tail.
            lines = dest.read_text().splitlines()
            assert len(lines) == n
            for line in lines:
                json.loads(line)
    finally:
        stop.set()
        t.join()


def test_snapshot_excludes_torn_tail(tmp_path):
    store = StateStore(tmp_path)
    store.append("s", {"id": "1"})
    with (tmp_path / "s.jsonl").open("a", encoding="utf-8") as fh:
        fh.write('{"id": "torn"')  # torn tail
    dest = tmp_path / "s_snap.jsonl"
    n = store.snapshot("s", dest)
    assert n == 1
    assert [json.loads(l)["id"] for l in dest.read_text().splitlines()] == ["1"]
