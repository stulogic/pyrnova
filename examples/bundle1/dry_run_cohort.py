"""PRELAUNCH-CONVERGENCE-001 Bundle 1 · B1.1 real-cohort dry run.

Deterministic, offline observation of what the *existing* Capture Radar pipeline produces
for the MTSI and Torch capability lenses over the *shared* bundled fixture universe. No
tuning, no live source expansion, no scoring changes: this reuses `pyrnova.pipeline.run`
and the bundled `_fixture_rows()` candidate universe exactly as the CLI does.

Run:
    python -m examples.bundle1.dry_run_cohort            # prints metrics JSON
    python -m examples.bundle1.dry_run_cohort --write    # also refreshes the evidence JSON

Output is stable given the fixtures; it is committed at
`docs/evidence/bundle1/dry_run_metrics.json` as reproducible evidence.
"""
from __future__ import annotations

import argparse
import json
import tempfile
from datetime import date
from pathlib import Path

from pyrnova.archive import LocalEvidenceArchive
from pyrnova.cli import _fixture_rows, _load_profile
from pyrnova.pipeline import run
from pyrnova.state import StateStore

REPO = Path(__file__).resolve().parents[2]
LENSES = {
    "torch": REPO / "examples/profiles/torch_technologies.json",
    "mtsi": REPO / "examples/profiles/modern_technology_solutions.json",
}
AS_OF = date(2026, 9, 8)
EVIDENCE = REPO / "docs/evidence/bundle1/dry_run_metrics.json"


def _run_lens(profile_path: Path) -> dict:
    profile = _load_profile(str(profile_path))
    award_rows, notice_rows, precursor_rows, source_observations = _fixture_rows()
    with tempfile.TemporaryDirectory() as tmp:
        archive = LocalEvidenceArchive(Path(tmp) / "archive")
        store = StateStore(Path(tmp) / "state")
        report = run(
            profile=profile,
            award_rows=award_rows,
            notice_rows=notice_rows,
            precursor_rows=precursor_rows,
            source_observations=source_observations,
            archive=archive,
            store=store,
            as_of=AS_OF,
            window_days=540,
            relevance_threshold=0.3,
            reviewer=None,
            min_amount=0.0,
        )
    strikes = [
        {
            "title": o.title,
            "kind": o.catalyst.kind,
            "relevance": round(o.relevance_score, 4),
            "confidence": round(o.confidence, 4),
            "posture": o.meta.get("posture", "capture"),
        }
        for o in report.strikes
    ]
    return {
        "profile": profile.name,
        "universe": {
            "awards": len(award_rows),
            "notices": len(notice_rows),
            "precursors": len(precursor_rows),
        },
        "stats": report.stats,
        "strikes": strikes,
        "watch_titles": sorted(o.title for o in report.watch),
        "rejected_titles": sorted(o.title for o in report.rejected),
    }


def build() -> dict:
    return {
        "as_of": AS_OF.isoformat(),
        "method": "pyrnova.pipeline.run over bundled _fixture_rows(); scoring_v1; offline; no tuning",
        "lenses": {key: _run_lens(path) for key, path in LENSES.items()},
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true", help="refresh the committed evidence JSON")
    args = ap.parse_args()
    result = build()
    text = json.dumps(result, indent=2, sort_keys=True)
    print(text)
    if args.write:
        EVIDENCE.parent.mkdir(parents=True, exist_ok=True)
        EVIDENCE.write_text(text + "\n", encoding="utf-8")
        print(f"\nwrote {EVIDENCE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
