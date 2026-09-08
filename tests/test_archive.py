import json

import pytest

from pyrnova.archive import LocalEvidenceArchive, sha256_hex


def test_put_is_content_addressed_and_dedups(tmp_path):
    arc = LocalEvidenceArchive(tmp_path / "archive")
    content = json.dumps({"hello": "world"}).encode()
    ev1 = arc.put(content, source_id="usaspending", retention_tier="A", source_ref="X")
    ev2 = arc.put(content, source_id="usaspending", retention_tier="A", source_ref="X")
    assert ev1.content_sha256 == sha256_hex(content) == ev2.content_sha256
    # Same bytes -> single stored object (dedup), but two observation records (Tier A history).
    stored = list((tmp_path / "archive" / "usaspending").rglob(ev1.content_sha256))
    assert len(stored) == 1
    obs = list((tmp_path / "archive").rglob("*.observations.jsonl"))
    assert len(obs) == 1
    lines = obs[0].read_text().strip().splitlines()
    assert len(lines) == 2


def test_roundtrip_get(tmp_path):
    arc = LocalEvidenceArchive(tmp_path / "archive")
    content = b'{"a":1}'
    ev = arc.put(content, source_id="sam_opportunities", retention_tier="A")
    assert arc.get(ev.content_sha256, "sam_opportunities") == content


def test_invalid_tier_rejected(tmp_path):
    arc = LocalEvidenceArchive(tmp_path / "archive")
    with pytest.raises(ValueError):
        arc.put(b"{}", source_id="usaspending", retention_tier="Z")
