"""Application services and replaceable local repositories for Operator Console v0.1."""

from __future__ import annotations

import json
import threading
import uuid
from dataclasses import asdict
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Callable, Iterable

from .acquisition import SourceStatus, fetch_live_rows, fixture_rows
from .archive import build_archive
from .brief import render_signal_brief
from .config import Config, load_config
from .match import CapabilityProfile
from .models import Catalyst, Evidence, Opportunity, to_record
from .pipeline import Report, run
from .state import StateStore

QUALITY_VALUES = {"STRONG", "POSSIBLE", "NOISE"}
PURSUIT_VALUES = {"PRIME", "SUPPORT", "TEAM", "DEFEND", "UNKNOWN"}
DECISION_VALUES = {"APPROVE", "REJECT", "HOLD"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")
    temp.replace(path)


class ProfileStore:
    """Read-only profile adapter; a database-backed implementation can replace it later."""

    def __init__(self, root: Path):
        self.root = Path(root)

    def list(self) -> list[dict]:
        profiles = []
        for path in sorted(self.root.glob("*.json")):
            data = json.loads(path.read_text(encoding="utf-8"))
            profiles.append({"id": path.stem, "path": str(path), **data})
        return profiles

    def get(self, profile_id: str) -> tuple[CapabilityProfile, dict]:
        if not profile_id or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_" for c in profile_id):
            raise ValueError("invalid profile id")
        path = self.root / f"{profile_id}.json"
        if not path.exists():
            raise KeyError(profile_id)
        raw = json.loads(path.read_text(encoding="utf-8"))
        return CapabilityProfile.from_dict(raw), {"id": profile_id, "path": str(path), **raw}


class RunStore:
    """File-backed run snapshot repository with one immutable machine record per run."""

    def __init__(self, root: Path):
        self.root = Path(root)
        self._lock = threading.Lock()

    def save(self, record: dict) -> None:
        with self._lock:
            _write_json(self.root / f"{record['id']}.json", record)

    def get(self, run_id: str) -> dict:
        path = self.root / f"{run_id}.json"
        if not path.exists():
            raise KeyError(run_id)
        return json.loads(path.read_text(encoding="utf-8"))

    def list(self) -> list[dict]:
        records = [json.loads(path.read_text(encoding="utf-8")) for path in self.root.glob("*.json")]
        records.sort(key=lambda r: r.get("created_at", ""), reverse=True)
        return [
            {
                "id": record["id"],
                "status": record.get("status"),
                "created_at": record.get("created_at"),
                "completed_at": record.get("completed_at"),
                "profile_name": record.get("profile", {}).get("name"),
                "options": record.get("options", {}),
                "source_status": record.get("source_status", []),
                "summary": record.get("summary", {}),
                "outputs": record.get("outputs", {}),
                "error": record.get("error"),
            }
            for record in records
        ]


class ReviewStore:
    """Append-only human adjudication repository; latest state is a derived view."""

    def __init__(self, state_store: StateStore):
        self.state_store = state_store
        self._lock = threading.Lock()

    def append(self, review: dict) -> dict:
        quality = str(review.get("quality", "")).upper()
        pursuit = str(review.get("pursuit_posture", "")).upper()
        decision = str(review.get("decision", "")).upper()
        if quality not in QUALITY_VALUES or pursuit not in PURSUIT_VALUES or decision not in DECISION_VALUES:
            raise ValueError("invalid adjudication value")
        revised = review.get("revised_attractiveness")
        if revised not in (None, ""):
            revised = float(revised)
            if not 0 <= revised <= 1:
                raise ValueError("revised attractiveness must be between 0 and 1")
        record = {
            "id": uuid.uuid4().hex,
            "candidate_id": str(review["candidate_id"]),
            "run_id": str(review["run_id"]),
            "target": str(review["target"]),
            "machine_scores": dict(review["machine_scores"]),
            "quality": quality,
            "pursuit_posture": pursuit,
            "analyst_note": str(review.get("analyst_note", "")).strip(),
            "falsification": str(review.get("falsification", "")).strip(),
            "revised_attractiveness": revised if revised != "" else None,
            "decision": decision,
            "reviewer": str(review.get("reviewer") or "operator").strip(),
            "created_at": _now(),
        }
        with self._lock:
            self.state_store.append("human_reviews", record)
        return record

    def history(self, *, run_id: str | None = None, candidate_id: str | None = None) -> list[dict]:
        records = list(self.state_store.read("human_reviews"))
        if run_id:
            records = [r for r in records if r.get("run_id") == run_id]
        if candidate_id:
            records = [r for r in records if r.get("candidate_id") == candidate_id]
        return records

    def latest_for_run(self, run_id: str) -> dict[str, dict]:
        latest: dict[str, dict] = {}
        for record in self.history(run_id=run_id):
            latest[record["candidate_id"]] = record
        return latest


def _candidate_record(opp: Opportunity) -> dict:
    record = to_record(opp)
    record["candidate_id"] = opp.id
    record["source"] = opp.meta.get("source") or (opp.evidence[0].source_id if opp.evidence else None)
    record["opportunity_type"] = opp.catalyst.kind
    record["machine_state"] = (
        "SUGGESTED_STRIKE" if opp.meta.get("review_status") == "pending_human" else "MACHINE_REJECTED"
    )
    return record


def _opportunity_from_record(record: dict, review: dict) -> Opportunity:
    catalyst_data = record["catalyst"]
    catalyst = Catalyst(**catalyst_data)
    evidence = [Evidence(**item) for item in record.get("evidence", [])]
    fields = {
        key: record.get(key)
        for key in Opportunity.__dataclass_fields__
        if key not in {"catalyst", "evidence"}
    }
    fields["id"] = record["candidate_id"]
    fields["state"] = "strike"
    fields["falsification"] = review.get("falsification") or record.get("falsification", "")
    if review.get("revised_attractiveness") is not None:
        fields["attractiveness"] = review["revised_attractiveness"]
    fields["meta"] = {**record.get("meta", {}), "review_status": "human_confirmed"}
    return Opportunity(catalyst=catalyst, evidence=evidence, **fields)


class OperatorService:
    """Use-case boundary between transport/UI and the existing intelligence kernel."""

    def __init__(
        self,
        *,
        config: Config,
        profiles: ProfileStore,
        runs: RunStore,
        reviews: ReviewStore,
        fixtures_dir: Path,
    ):
        self.config = config
        self.profiles = profiles
        self.runs = runs
        self.reviews = reviews
        self.fixtures_dir = Path(fixtures_dir)

    @classmethod
    def default(cls, repo_root: Path) -> "OperatorService":
        config = load_config()
        state = StateStore(config.state_dir)
        return cls(
            config=config,
            profiles=ProfileStore(repo_root / "examples" / "profiles"),
            runs=RunStore(config.state_dir / "operator_runs"),
            reviews=ReviewStore(state),
            fixtures_dir=repo_root / "tests" / "fixtures",
        )

    def create_run(self, options: dict, *, run_id: str | None = None) -> dict:
        run_id = run_id or uuid.uuid4().hex
        profile, profile_raw = self.profiles.get(str(options["profile_id"]))
        as_of = date.fromisoformat(options.get("as_of") or date.today().isoformat())
        mode = "fixtures" if options.get("mode") == "fixtures" else "live"
        window_days = int(options.get("window_days", 540))
        lookback_days = int(options.get("lookback_days", 30))
        threshold = float(options.get("threshold", 0.3))
        min_amount = float(options.get("min_amount", 0))
        created_at = _now()
        base = {
            "id": run_id,
            "status": "running",
            "created_at": created_at,
            "completed_at": None,
            "profile": profile_raw,
            "options": {
                "mode": mode,
                "as_of": as_of.isoformat(),
                "window_days": window_days,
                "lookback_days": lookback_days,
                "threshold": threshold,
                "min_amount": min_amount,
            },
            "source_status": [],
            "summary": {},
            "candidates": [],
            "outputs": {},
        }
        self.runs.save(base)
        try:
            if mode == "fixtures":
                awards, notices = fixture_rows(self.fixtures_dir)
                observed = _now()
                statuses = [
                    SourceStatus("usaspending", "fixture", len(awards), observed),
                    SourceStatus("sam", "fixture", len(notices), observed),
                ]
            else:
                awards, notices, statuses = fetch_live_rows(
                    self.config, profile, as_of, sam_lookback_days=lookback_days
                )
            report = run(
                profile=profile,
                award_rows=awards,
                notice_rows=notices,
                archive=build_archive(self.config),
                store=StateStore(self.config.state_dir),
                as_of=as_of,
                window_days=window_days,
                relevance_threshold=threshold,
                min_amount=min_amount,
            )
            candidates = [_candidate_record(o) for o in report.strikes + report.rejected]
            candidates.sort(
                key=lambda c: (
                    c["machine_state"] != "SUGGESTED_STRIKE",
                    -float(c.get("relevance_score") or 0),
                    -float(c.get("attractiveness") or 0),
                )
            )
            radar_path = self.config.out_dir / f"operator_run_{run_id}_capture_radar.md"
            self.config.out_dir.mkdir(parents=True, exist_ok=True)
            from .brief import render_capture_radar_report

            radar_path.write_text(render_capture_radar_report(report), encoding="utf-8")
            result = {
                **base,
                "status": "complete",
                "completed_at": _now(),
                "source_status": [s.to_dict() for s in statuses],
                "summary": {
                    **report.stats,
                    "awards_retrieved": len(awards),
                    "sam_notices_retrieved": len(notices),
                    "candidate_recompete": sum(
                        1 for candidate in candidates if candidate["opportunity_type"] == "recompete_expiry"
                    ),
                    "candidate_presolicitation": sum(
                        1 for candidate in candidates if candidate["opportunity_type"] != "recompete_expiry"
                    ),
                    "run_id": run_id,
                },
                "candidates": candidates,
                "outputs": {"capture_radar": str(radar_path), "signal_brief": None},
            }
        except Exception as exc:
            result = {**base, "status": "failed", "completed_at": _now(), "error": str(exc)}
        self.runs.save(result)
        return result

    def get_run(self, run_id: str) -> dict:
        record = self.runs.get(run_id)
        latest = self.reviews.latest_for_run(run_id)
        record["latest_reviews"] = latest
        record["review_history"] = self.reviews.history(run_id=run_id)
        return record

    def save_review(self, run_id: str, payload: dict) -> dict:
        run_record = self.runs.get(run_id)
        candidate = next((c for c in run_record["candidates"] if c["candidate_id"] == payload.get("candidate_id")), None)
        if not candidate:
            raise KeyError(payload.get("candidate_id"))
        return self.reviews.append(
            {
                **payload,
                "run_id": run_id,
                "target": run_record["profile"]["name"],
                "machine_scores": {
                    "relevance": candidate.get("relevance_score"),
                    "confidence": candidate.get("confidence"),
                    "attractiveness": candidate.get("attractiveness"),
                    "machine_state": candidate.get("machine_state"),
                },
            }
        )

    def generate_brief(self, run_id: str, candidate_ids: Iterable[str]) -> dict:
        run_record = self.runs.get(run_id)
        selected = list(dict.fromkeys(str(i) for i in candidate_ids))
        if not selected:
            raise ValueError("select at least one approved STRIKE")
        latest = self.reviews.latest_for_run(run_id)
        by_id = {c["candidate_id"]: c for c in run_record["candidates"]}
        invalid = [cid for cid in selected if cid not in latest or latest[cid].get("decision") != "APPROVE"]
        if invalid:
            raise ValueError("brief items must have a latest APPROVE adjudication")
        opportunities = [_opportunity_from_record(by_id[cid], latest[cid]) for cid in selected]
        as_of = date.fromisoformat(run_record["options"]["as_of"])
        report = Report(
            profile_name=run_record["profile"]["name"],
            as_of=as_of,
            strikes=opportunities,
            stats={
                "strikes": len(opportunities),
                "candidates": len(run_record["candidates"]),
                "defend": sum(1 for o in opportunities if o.meta.get("posture") == "defend"),
            },
        )
        self.config.out_dir.mkdir(parents=True, exist_ok=True)
        path = self.config.out_dir / f"signal_brief_{run_id}.md"
        path.write_text(render_signal_brief(report, limit=len(opportunities)), encoding="utf-8")
        return {"path": str(path), "candidate_ids": selected, "generated_at": _now()}
