"""Append-only local state (predictions, reviews, observations, scoreboard).

This is the Day-1 proprietary accumulation in the local dev path. In production the same records go to
Postgres (db/schema.sql); the interface is intentionally tiny so the Postgres adapter drops in later.
Append-only + timestamped = the point-in-time history the moat depends on.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Iterator


class StateStore:
    def __init__(self, root: Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, stream: str) -> Path:
        return self.root / f"{stream}.jsonl"

    def append(self, stream: str, record: dict) -> None:
        record = {"_ts": datetime.utcnow().isoformat(), **record}
        with self._path(stream).open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")

    def read(self, stream: str) -> Iterator[dict]:
        p = self._path(stream)
        if not p.exists():
            return iter(())
        with p.open("r", encoding="utf-8") as fh:
            return iter([json.loads(line) for line in fh if line.strip()])

    def count(self, stream: str) -> int:
        return sum(1 for _ in self.read(stream))

    def latest(self, stream: str, record_id: str) -> dict | None:
        found = None
        for record in self.read(stream):
            if record.get("id") == record_id:
                found = record
        return found
