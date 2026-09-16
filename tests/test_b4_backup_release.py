"""B4.8 — off-host backup/restore release readiness (no redesign of the accepted backup/restore).

Closes only production/release readiness after the B4.4 durability changes:
* the release state paths are captured (var/state + db/schema.sql) and the manifest records the release SHA
  linking the backup to a deployable code release;
* a backup taken while state is being actively written is self-consistent (every stored artifact matches
  its recorded sha) and the manifest is complete, never a silent partial;
* restored state is cleanly readable by the hardened StateStore.
"""

from __future__ import annotations

import threading
import pytest

from pyrnova import backup
from pyrnova.backup import create_backup, sha256_file
from pyrnova.state import StateStore


def _seed_state(root):
    """Write a couple of durable streams under <root>/var/state (the backup source layout)."""
    store = StateStore(root / "var" / "state")
    for i in range(30):
        store.append("opportunities", {"id": f"opp-{i}", "customer_id": "torch"})
        store.append("customers", {"id": f"cust-{i}", "customer_id": "torch"})
    (root / "db").mkdir(parents=True, exist_ok=True)
    (root / "db" / "schema.sql").write_text("-- schema identity\n")
    return store


def test_backup_records_release_sha_and_captures_state(tmp_path):
    root = tmp_path / "srv"
    _seed_state(root)
    dest = tmp_path / "backup"
    m = create_backup(root, dest, source_commit="abc123def")
    assert m.status == "complete"
    assert m.source_commit == "abc123def"  # backup <-> deployable release SHA linkage
    paths = {e.path for e in m.files}
    assert "state/opportunities.jsonl" in paths and "state/customers.jsonl" in paths
    # Manifest is self-consistent: every stored artifact matches its recorded sha.
    for e in m.files:
        assert sha256_file(dest / e.path) == e.sha256


def test_backup_honours_state_dir_outside_source_root(tmp_path):
    """Production layout: durable state lives at PYRNOVA_STATE_DIR (e.g. /srv/pyrnova/var/state),
    OUTSIDE the release working directory (/srv/pyrnova/current). Deriving the state path from the
    repo root would silently capture nothing. An explicit state_dir/archive_dir must be honoured so
    the backup captures the real live state regardless of where the release is checked out."""
    release_root = tmp_path / "srv" / "current"        # the repo (source_root) — no var/state here
    (release_root / "db").mkdir(parents=True, exist_ok=True)
    (release_root / "db" / "schema.sql").write_text("-- schema identity\n")
    live_state = tmp_path / "srv" / "var" / "state"     # durable state, a sibling of the release
    live_archive = tmp_path / "srv" / "var" / "archive"
    store = StateStore(live_state)
    for i in range(5):
        store.append("opportunities", {"id": f"opp-{i}", "customer_id": "torch"})

    # Repo-root default finds no var/state under the release dir: the backup silently captures only
    # db/schema.sql and ZERO durable state streams — a "complete" backup with none of the customer data.
    wrong = create_backup(release_root, tmp_path / "bk_wrong", source_commit="sha")
    wrong_paths = {e.path for e in wrong.files}
    assert not any(p.startswith("state/") for p in wrong_paths), wrong_paths

    # Config-resolved dirs capture the real state.
    m = create_backup(release_root, tmp_path / "bk_right", source_commit="sha",
                      state_dir=live_state, archive_dir=live_archive)
    assert m.status == "complete"
    paths = {e.path for e in m.files}
    assert "state/opportunities.jsonl" in paths and "schema.sql" in paths


def test_backup_during_active_writes_is_self_consistent(tmp_path):
    root = tmp_path / "srv"
    store = _seed_state(root)
    stop = threading.Event()

    def writer():
        i = 0
        while not stop.is_set():
            store.append("opportunities", {"id": f"live-{i}", "customer_id": "torch"})
            i += 1

    t = threading.Thread(target=writer)
    t.start()
    try:
        for k in range(8):
            dest = tmp_path / f"bk{k}"
            m = create_backup(root, dest, source_commit="sha")
            assert m.status == "complete"
            # The manifest sha always matches the bytes actually stored (no torn/partial artifact reported).
            for e in m.files:
                assert sha256_file(dest / e.path) == e.sha256
    finally:
        stop.set()
        t.join()


def test_restored_state_is_cleanly_readable_after_hardening(tmp_path):
    root = tmp_path / "srv"
    _seed_state(root)
    dest = tmp_path / "backup"
    create_backup(root, dest, source_commit="sha")
    # Read the captured stream back through the hardened StateStore (torn-tail safe, fail-closed on corruption).
    restored = StateStore(dest)  # dest/state/opportunities.jsonl matches the store layout
    opps = list(restored.read("state/opportunities"))
    assert len(opps) >= 30 and all(o["customer_id"] == "torch" for o in opps)
