"""Phase 1 unattended Live Operations soak harness.

The harness composes the accepted scheduler, archive, pipeline, customer fan-out, and append-only
StateStore. It owns only operational execution/evidence: it does not change intelligence semantics,
source rights, scoring, customer configuration, or replay.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import signal
import subprocess
import time
from dataclasses import dataclass
from functools import partial
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Optional

from .archive import LocalEvidenceArchive
from .config import load_config
from .customer_material_changes import fan_out
from .customers import get_customer, list_watches
from .live_ops import LiveRunner, http_fetcher, source_record_count, source_response_rows
from .match import CapabilityProfile
from .pipeline import run as run_pipeline
from .scheduler import CACHE_HIT, ERROR, LIVE_FETCH, SourceScheduler
from .sources.registry import get_spec
from .sources.source_state import SourceStateStore
from .state import StateStore

MISS_CLASSES = frozenset({
    "coverage", "identity", "relationship", "materiality", "consequence", "timing", "delivery",
})
SUPPORTED_SOURCE_PARSERS = frozenset({"usaspending", "sam_opportunities", "federal_register"})
REQUIRED_OPERATIONAL_SOURCES = frozenset({"usaspending", "sam_opportunities"})
SOAK_DESIGNATION = "SOAK TEST LENS — NON-CUSTOMER / NON-COMMERCIAL"
SOAK_LEGAL_NAME = "IRONMOUNTAIN SOLUTIONS, LLC"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _stable_id(prefix: str, value: Any) -> str:
    canonical = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return f"{prefix}_{hashlib.sha256(canonical.encode()).hexdigest()[:20]}"


def _atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def _append_jsonl(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(value, sort_keys=True, default=str) + "\n")


def record_important_miss(
    store: StateStore,
    *,
    miss_class: str,
    source_id: str,
    source_ref: str,
    detected_at: str,
    reviewer: str,
    material_change_id: Optional[str] = None,
    acquisition_ref: Optional[str] = None,
    assessment_ref: Optional[str] = None,
    customer_id: Optional[str] = None,
    relevance_state: str = "UNKNOWN",
    emitted: bool = False,
    actionable: bool = True,
    material: bool = True,
    reasonably_detectable: bool = True,
    notes: str = "",
) -> dict:
    """Append one idempotent, structured Important Miss investigation record."""
    classification = str(miss_class).strip().lower()
    if classification not in MISS_CLASSES:
        raise ValueError(f"miss_class must be one of {sorted(MISS_CLASSES)}")
    required = {"source_id": source_id, "source_ref": source_ref,
                "detected_at": detected_at, "reviewer": reviewer}
    missing = [name for name, value in required.items() if not str(value or "").strip()]
    if missing:
        raise ValueError(f"missing required Important Miss fields: {', '.join(missing)}")
    basis = {
        "miss_class": classification, "source_id": source_id, "source_ref": source_ref,
        "customer_id": customer_id, "material_change_id": material_change_id,
    }
    record = {
        "id": _stable_id("miss", basis), "kind": "important_miss", "miss_class": classification,
        "source_id": source_id, "source_ref": source_ref, "acquisition_ref": acquisition_ref,
        "assessment_ref": assessment_ref, "customer_id": customer_id,
        "material_change_id": material_change_id, "relevance_state": relevance_state,
        "emitted": bool(emitted), "actionable": bool(actionable), "material": bool(material),
        "reasonably_detectable": bool(reasonably_detectable), "detected_at": detected_at,
        "reviewer": reviewer, "notes": notes,
    }
    if store.latest("important_misses", record["id"]) is None:
        store.append("important_misses", record)
    return record


@dataclass(frozen=True)
class SoakPlan:
    raw: dict
    path: Path

    @property
    def evidence_dir(self) -> Path:
        return (self.path.parent / self.raw["evidence_dir"]).resolve()

    @property
    def manifest_hash(self) -> str:
        return hashlib.sha256(
            json.dumps(self.raw, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()


def load_plan(path: str | Path) -> SoakPlan:
    plan_path = Path(path).resolve()
    raw = json.loads(plan_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("soak plan must be a JSON object")
    return SoakPlan(raw=raw, path=plan_path)


def _has_placeholder(value: Any) -> bool:
    if isinstance(value, str):
        return value.startswith("SET_")
    if isinstance(value, list):
        return any(_has_placeholder(item) for item in value)
    if isinstance(value, dict):
        return any(_has_placeholder(item) for item in value.values())
    return False


def _repo_commit(repo: Path) -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo, check=True, capture_output=True, text=True
    ).stdout.strip()


def _repo_tracked_changes(repo: Path) -> str:
    return subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=no"], cwd=repo,
        check=True, capture_output=True, text=True,
    ).stdout.strip()


def preflight(plan: SoakPlan, *, repo: Path) -> dict:
    """Validate immutable acceptance inputs without starting or mutating the soak."""
    errors: list[str] = []
    warnings: list[str] = []
    raw = plan.raw
    required = (
        "soak_id", "canonical_commit", "environment", "duration_calendar_days",
        "required_business_days", "evidence_dir", "state_dir", "source_state_dir",
        "archive_dir", "customers", "sources", "health_thresholds",
        "allowed_observation", "allowed_intervention", "invalidating_intervention",
        "soak_test_lens", "designation",
    )
    for field in required:
        if field not in raw:
            errors.append(f"missing plan field: {field}")
    if _has_placeholder(raw):
        errors.append("plan contains unresolved SET_ placeholders")
    if raw.get("duration_calendar_days") != 7:
        errors.append("duration_calendar_days must be exactly 7")
    if raw.get("required_business_days") != 5:
        errors.append("required_business_days must be exactly 5")
    current_commit = _repo_commit(repo)
    if raw.get("canonical_commit") != current_commit:
        errors.append(f"canonical_commit does not match current HEAD ({current_commit})")
    if _repo_tracked_changes(repo):
        errors.append("canonical repository has uncommitted tracked changes")

    state_dir = (plan.path.parent / str(raw.get("state_dir", ""))).resolve()
    customer_store = StateStore(state_dir) if state_dir.is_dir() else None
    if customer_store is None:
        errors.append(f"state_dir does not exist: {state_dir}")
    customers = raw.get("customers") if isinstance(raw.get("customers"), list) else []
    if not customers:
        errors.append("at least one persisted customer Lens is required")
    monitored = 0
    for customer in customers:
        cid = str((customer or {}).get("customer_id") or "")
        profile_value = str((customer or {}).get("profile") or "")
        profile_path = (plan.path.parent / profile_value).resolve()
        persisted_profile = get_customer(customer_store, cid) if customer_store is not None and cid else None
        if persisted_profile is None:
            errors.append(f"persisted customer Lens not found: {cid or '<missing>'}")
        elif len(list_watches(customer_store, cid)) < int((customer or {}).get("monitored_objects") or 0):
            errors.append(f"declared monitored_objects exceed active persisted watches for {cid}")
        if persisted_profile is not None and SOAK_DESIGNATION not in persisted_profile.provenance:
            errors.append(f"persisted Lens lacks explicit non-commercial soak designation: {cid}")
        if not profile_value or not profile_path.is_file():
            errors.append(f"capability profile not found for customer {cid or '<missing>'}")
        else:
            try:
                profile_raw = json.loads(profile_path.read_text(encoding="utf-8"))
                if profile_raw.get("designation") != SOAK_DESIGNATION:
                    errors.append(f"capability profile lacks explicit non-commercial soak designation: {cid}")
                CapabilityProfile.from_dict(profile_raw)
            except (ValueError, TypeError, AttributeError) as exc:
                errors.append(f"invalid capability profile for {cid}: {exc}")
        monitored += int((customer or {}).get("monitored_objects") or 0)
    if monitored < 1:
        errors.append("monitored_objects must be declared and non-zero")
    if monitored > 75:
        errors.append("monitored_objects exceeds the authorized Phase 1 test envelope of 75")

    cfg = load_config()
    sources = raw.get("sources") if isinstance(raw.get("sources"), list) else []
    source_ids = {str((source or {}).get("source_id") or "") for source in sources}
    missing_sources = sorted(REQUIRED_OPERATIONAL_SOURCES - source_ids)
    if missing_sources:
        errors.append("soak-critical source set missing: " + ", ".join(missing_sources))
    for source in sources:
        sid = str((source or {}).get("source_id") or "")
        if sid not in SUPPORTED_SOURCE_PARSERS:
            errors.append(f"unsupported soak source: {sid or '<missing>'}")
            continue
        spec = get_spec(sid)
        if not spec.active or spec.status != "operational" or spec.reliability not in {
            "live_proven", "archive_operational"
        }:
            errors.append(f"source is not operational on authorized real evidence: {sid}")
        if spec.auth == "api_key" and sid == "sam_opportunities" and not cfg.has_sam:
            errors.append("SAM_API_KEY is unavailable")
        if float((source or {}).get("interval_seconds") or 0) <= 0:
            errors.append(f"positive interval_seconds required for {sid}")
        if int((source or {}).get("max_calls_per_epoch") or 0) <= 0:
            errors.append(f"positive max_calls_per_epoch required for {sid}")
        request = (source or {}).get("request")
        if not isinstance(request, dict) or not request.get("url"):
            errors.append(f"explicit request required for {sid}")

    if raw.get("soak_test_lens") != SOAK_LEGAL_NAME:
        errors.append(f"soak_test_lens must remain {SOAK_LEGAL_NAME}")
    if raw.get("designation") != SOAK_DESIGNATION:
        errors.append("plan must explicitly designate a non-customer, non-commercial soak test Lens")
    if "customer_1" in raw:
        errors.append("customer_1 must not label this non-commercial soak test Lens")
    if not raw.get("restart_rule"):
        errors.append("restart_rule is required")
    if not raw.get("failure_thresholds"):
        errors.append("failure_thresholds are required")
    return {
        "ok": not errors, "checked_at": _now(), "current_commit": current_commit,
        "manifest_hash": plan.manifest_hash, "errors": errors, "warnings": warnings,
        "customer_count": len(customers), "monitored_objects": monitored,
        "source_ids": sorted(source_ids),
    }


def _expand(value: Any, *, cfg, today: date) -> Any:
    tokens = {
        "{{today_iso}}": today.isoformat(),
        "{{today_mmddyyyy}}": today.strftime("%m/%d/%Y"),
        "{{date_minus_30_mmddyyyy}}": (today - timedelta(days=30)).strftime("%m/%d/%Y"),
        "${SAM_API_KEY}": cfg.sam_api_key,
    }
    if isinstance(value, str):
        return tokens.get(value, value)
    if isinstance(value, list):
        return [_expand(v, cfg=cfg, today=today) for v in value]
    if isinstance(value, dict):
        return {k: _expand(v, cfg=cfg, today=today) for k, v in value.items()}
    return value


def _parse_source(source_id: str, raw: bytes) -> tuple[list[dict], list[dict], list[dict]]:
    rows = source_response_rows(source_id, raw)
    if source_id == "usaspending":
        return rows, [], []
    if source_id == "sam_opportunities":
        return [], rows, []
    if source_id == "federal_register":
        return [], [], rows
    raise ValueError(f"unsupported source parser: {source_id}")


class SoakHarness:
    def __init__(self, plan: SoakPlan, *, repo: Path):
        self.plan = plan
        self.repo = repo.resolve()
        self.cfg = load_config()
        self.evidence_dir = plan.evidence_dir
        raw = plan.raw
        resolve = lambda name: (plan.path.parent / raw[name]).resolve()
        self.state_dir = resolve("state_dir")
        self.source_state_dir = resolve("source_state_dir")
        self.archive_dir = resolve("archive_dir")
        self.state: Optional[StateStore] = None
        self.source_state: Optional[SourceStateStore] = None
        self.archive: Optional[LocalEvidenceArchive] = None

    def _ensure_runtime(self) -> None:
        if self.state is None:
            self.state = StateStore(self.state_dir)
            self.source_state = SourceStateStore(self.source_state_dir)
            self.archive = LocalEvidenceArchive(self.archive_dir)

    def start(self) -> dict:
        report = preflight(self.plan, repo=self.repo)
        if not report["ok"]:
            raise RuntimeError("soak preflight failed: " + "; ".join(report["errors"]))
        self._ensure_runtime()
        started_at = _now()
        start_dt = datetime.fromisoformat(started_at)
        business = start_dt
        count = 0
        while count < 5:
            if business.weekday() < 5:
                count += 1
            if count < 5:
                business += timedelta(days=1)
        manifest = {
            "status": "SOAK_IN_PROGRESS", "started_at": started_at,
            "expected_earliest_completion_at": (start_dt + timedelta(days=7)).isoformat(),
            "fifth_business_day": business.date().isoformat(), "plan": self.plan.raw,
            "plan_hash": self.plan.manifest_hash,
        }
        manifest_path = self.evidence_dir / "manifest.json"
        if manifest_path.exists():
            existing = json.loads(manifest_path.read_text(encoding="utf-8"))
            if existing.get("plan_hash") != self.plan.manifest_hash:
                raise RuntimeError("existing soak manifest differs; start a new evidence directory")
            return existing
        _atomic_json(manifest_path, manifest)
        _append_jsonl(self.evidence_dir / "events.jsonl", {
            "id": _stable_id("event", {"kind": "start", "at": started_at}),
            "kind": "SOAK_STARTED", "at": started_at, "plan_hash": self.plan.manifest_hash,
        })
        return manifest

    def run_cycle(self, *, fetcher: Callable[[dict], bytes] = http_fetcher,
                  now: Optional[datetime] = None, pre_soak: bool = False) -> dict:
        manifest_path = self.evidence_dir / "manifest.json"
        if pre_soak:
            report = preflight(self.plan, repo=self.repo)
            if not report["ok"]:
                raise RuntimeError("foreground preflight failed: " + "; ".join(report["errors"]))
            if manifest_path.exists():
                raise RuntimeError("official soak already started; foreground validation cannot move its clock")
        elif not manifest_path.exists():
            raise RuntimeError("soak has not been started")
        self._ensure_runtime()
        assert self.state is not None and self.source_state is not None and self.archive is not None
        at = now or datetime.now(timezone.utc)
        phase = "PRE_SOAK_FOREGROUND" if pre_soak else "SOAK"
        cycle_id = _stable_id("cycle", {"plan": self.plan.manifest_hash, "at": at.isoformat(), "phase": phase})
        scheduler = SourceScheduler(
            self.source_state, archive=self.archive, default_mode="OFFLINE",
            budget_epoch=at.date().isoformat(),
        )
        rows_by_customer = {
            str(c["customer_id"]): {"awards": [], "notices": [], "precursors": []}
            for c in self.plan.raw["customers"]
        }
        source_results: list[dict] = []
        source_successes: list[str] = []
        for source in self.plan.raw["sources"]:
            sid = source["source_id"]
            scheduler.set_poll_interval(sid, float(source["interval_seconds"]))
            request = _expand(source["request"], cfg=self.cfg, today=at.date())
            source_doc = self.source_state.load(sid)
            pending = source_doc.get("pending_processing") or {}
            if pending.get("content_sha256"):
                content_sha256 = pending["content_sha256"]
                source_results.append({
                    "source_id": sid, "action": "resume_pending", "mode": "LIVE_SAFE",
                    "content_sha256": content_sha256, "from_archive": True,
                    "reason": "resuming archived acquisition not yet checkpointed downstream",
                })
            elif not scheduler.due(sid, now=at.timestamp()):
                scheduler.state.record_operation(
                    sid, action="skipped_not_due", at=at.isoformat()
                )
                source_results.append({
                    "source_id": sid, "action": "skipped_not_due", "mode": "LIVE_SAFE",
                    "content_sha256": None, "from_archive": False,
                    "reason": f"not due until {scheduler.next_poll_at(sid)}",
                })
                continue
            else:
                runner = LiveRunner(
                    scheduler, sid, mode="LIVE_SAFE", fetcher=fetcher,
                    max_calls=int(source["max_calls_per_epoch"]),
                    record_counter=partial(source_record_count, sid),
                )
                entry = runner.run(request, checkpoint=None, now=at.timestamp())
                source_results.append(entry.as_dict())
                content_sha256 = entry.content_sha256
                if entry.action not in {LIVE_FETCH, CACHE_HIT} or not content_sha256:
                    continue
                # The pending marker is written before parsing. A crash now resumes these exact archived
                # bytes without a second external call and without waiting for ordinary source cadence.
                source_doc = self.source_state.load(sid)
                source_doc["pending_processing"] = {
                    "content_sha256": content_sha256, "acquired_at": at.isoformat(),
                    "request_fingerprint": entry.request_fingerprint,
                }
                self.source_state.save(sid, source_doc)
            try:
                raw = self.archive.get(content_sha256, sid)
                if hashlib.sha256(raw).hexdigest() != content_sha256:
                    raise ValueError("source artifact hash mismatch")
                awards, notices, precursors = _parse_source(sid, raw)
                parsed_count = len(awards) + len(notices) + len(precursors)
                result_row = source_results[-1]
                if result_row.get("action") == "resume_pending":
                    result_row["records_returned"] = parsed_count
                if result_row.get("counting_error") or result_row.get("records_returned") != parsed_count:
                    raise ValueError("source record telemetry unavailable or disagrees with parsed artifact")
                targets = source.get("customer_ids") or list(rows_by_customer)
                for cid in targets:
                    if cid in rows_by_customer:
                        rows_by_customer[cid]["awards"].extend(awards)
                        rows_by_customer[cid]["notices"].extend(notices)
                        rows_by_customer[cid]["precursors"].extend(precursors)
                source_successes.append(sid)
            except Exception as exc:  # preserve raw evidence; fail the cycle visibly
                source_results[-1]["processing_error"] = str(exc)
                self.source_state.record_operation(
                    sid, action="processing_error", at=at.isoformat(), error=str(exc)
                )

        pipeline_results: list[dict] = []
        if source_successes:
            for customer in self.plan.raw["customers"]:
                cid = customer["customer_id"]
                profile_path = (self.plan.path.parent / customer["profile"]).resolve()
                profile = CapabilityProfile.from_dict(json.loads(profile_path.read_text(encoding="utf-8")))
                source_rows = rows_by_customer[cid]
                try:
                    report = run_pipeline(
                        profile=profile, customer_id=cid, award_rows=source_rows["awards"],
                        notice_rows=source_rows["notices"], precursor_rows=source_rows["precursors"],
                        archive=self.archive, store=self.state, as_of=at.date(),
                    )
                    pipeline_results.append({"customer_id": cid, **report.stats})
                except Exception as exc:
                    pipeline_results.append({"customer_id": cid, "error": str(exc)})

            customer_ids = [str(c["customer_id"]) for c in self.plan.raw["customers"]]
            fanout = fan_out(
                mc_store=self.state, customer_store=self.state, cmc_store=self.state,
                customer_ids=customer_ids, run_id=cycle_id, now=at.isoformat(),
            )
        else:
            fanout = {"run_id": cycle_id, "skipped": True, "reason": "no source batch due or recoverable",
                      "failure_count": 0}
        clean_pipeline = all("error" not in result for result in pipeline_results)
        clean_sources = all("processing_error" not in result for result in source_results)
        if clean_pipeline and clean_sources and fanout.get("failure_count", 0) == 0:
            for sid in source_successes:
                source_doc = self.source_state.load(sid)
                source_doc["checkpoint"] = cycle_id
                source_doc.pop("pending_processing", None)
                self.source_state.save(sid, source_doc)
        cycle = {
            "id": cycle_id, "at": at.isoformat(), "phase": phase, "commit": _repo_commit(self.repo),
            "plan_hash": self.plan.manifest_hash, "sources": source_results,
            "pipelines": pipeline_results, "fanout": fanout,
            "source_health": scheduler.health_report(),
            "important_miss_count": self.state.count("important_misses"),
            "operator_intervention": False,
            "ok": clean_pipeline and clean_sources and fanout.get("failure_count", 0) == 0
                  and not any(r.get("action") == ERROR for r in source_results),
        }
        prefix = "foreground_" if pre_soak else ""
        _append_jsonl(self.evidence_dir / f"{prefix}cycles.jsonl", cycle)
        _atomic_json(self.evidence_dir / f"{prefix}status.json", cycle)
        return cycle

    def run_foreground(self, *, fetcher: Callable[[dict], bytes] = http_fetcher,
                       now: Optional[datetime] = None) -> dict:
        """Prove a real cycle and unchanged fan-out without starting the acceptance clock."""
        cycle = self.run_cycle(fetcher=fetcher, now=now, pre_soak=True)
        assert self.state is not None
        real_acquisitions = bool(cycle["sources"]) and all(
            source.get("action") == LIVE_FETCH for source in cycle["sources"]
        )
        if cycle["ok"] and real_acquisitions:
            repeat = fan_out(
                mc_store=self.state, customer_store=self.state, cmc_store=self.state,
                customer_ids=[str(c["customer_id"]) for c in self.plan.raw["customers"]],
                run_id=cycle["id"] + "_idempotency", now=_now(),
            )
        else:
            # A verification retry must not silently repair the outputs of a failed first cycle.
            repeat = {"skipped": True, "reason": "foreground cycle failed or lacked real acquisitions"}
        result = {
            "at": _now(), "phase": "PRE_SOAK_FOREGROUND", "cycle": cycle,
            "idempotency": repeat,
            "real_acquisitions": real_acquisitions,
            "ok": cycle["ok"] and real_acquisitions and repeat.get("failure_count", 0) == 0
                  and repeat.get("inserted", 0) == 0 and repeat.get("updated", 0) == 0,
        }
        _atomic_json(self.evidence_dir / "foreground_validation.json", result)
        return result

    def verify_retained_foreground(self, foreground_path: Path) -> dict:
        """Re-verify checkpointed real evidence without ingestion, repair, or provider calls.

        The original failed telemetry remains historical truth. This creates a distinct gate snapshot
        using corrected counters only while the same acquisitions are current and not due for polling.
        """
        report = preflight(self.plan, repo=self.repo)
        if not report["ok"]:
            raise RuntimeError("retained preflight failed: " + "; ".join(report["errors"]))
        foreground_path = foreground_path.resolve()
        if foreground_path.parent == self.evidence_dir:
            raise RuntimeError("retained gate requires a new evidence directory; preserve original evidence")
        if (self.evidence_dir / "manifest.json").exists():
            raise RuntimeError("official soak already started")
        original_bytes = foreground_path.read_bytes()
        original = json.loads(original_bytes)
        prior = original["cycle"]
        self._ensure_runtime()
        scheduler = SourceScheduler(self.source_state, archive=self.archive, default_mode="OFFLINE")
        at = datetime.now(timezone.utc)
        errors = []
        if not prior.get("ok") or not original.get("real_acquisitions"):
            errors.append("retained foreground did not complete real acquisition and downstream processing")
        repeat = original.get("idempotency") or {}
        if (repeat.get("skipped") or repeat.get("failure_count", 0)
                or repeat.get("inserted", 0) or repeat.get("updated", 0)):
            errors.append("retained unchanged fan-out verification failed")
        if prior.get("operator_intervention") or prior.get("fanout", {}).get("failure_count", 0):
            errors.append("retained cycle has intervention or fan-out failure")
        expected_customers = {c["customer_id"] for c in self.plan.raw["customers"]}
        pipelines = prior.get("pipelines", [])
        if ({pipeline.get("customer_id") for pipeline in pipelines} != expected_customers
                or any("error" in pipeline for pipeline in pipelines)):
            errors.append("retained pipeline failed or Lens coverage differs")
        if any(row.get("processing_error") or row.get("error") for row in prior.get("sources", [])):
            errors.append("retained acquisition or processing failed")
        if datetime.fromisoformat(prior["at"]) > at:
            errors.append("retained cycle timestamp is in the future")
        for events_path in (foreground_path.parent / "events.jsonl", self.evidence_dir / "events.jsonl"):
            if events_path.exists():
                for line in events_path.read_text().splitlines():
                    event = json.loads(line)
                    if event.get("invalidates_soak"):
                        errors.append("invalidating intervention recorded in evidence")
        ledger = []
        verification = []
        for source in self.plan.raw["sources"]:
            sid = source["source_id"]
            doc = self.source_state.load(sid)
            prior_rows = [row for row in prior["sources"] if row["source_id"] == sid]
            try:
                if len(prior_rows) != 1 or prior_rows[0].get("action") != LIVE_FETCH:
                    raise ValueError("retained source must have exactly one real acquisition")
                row = prior_rows[0]
                sha = row["content_sha256"]
                indexed = (doc.get("requests") or {}).get(row["request_fingerprint"]) or {}
                if indexed.get("content_sha256") != sha or doc.get("checkpoint") != prior["id"]:
                    raise ValueError("retained acquisition is not the current indexed downstream checkpoint")
                if doc.get("pending_processing"):
                    raise ValueError("unprocessed acquisition is pending")
                operation = doc.get("operation") or {}
                if datetime.fromisoformat(operation["last_successful_acquisition_at"]) > at:
                    raise ValueError("source acquisition timestamp is in the future")
                if scheduler.due(sid, now=at.timestamp()):
                    raise ValueError("source is due; retained gate cannot substitute for scheduled acquisition")
                if float((doc.get("schedule") or {}).get("interval_seconds") or 0) != float(source["interval_seconds"]):
                    raise ValueError("retained cadence differs from pinned plan")
                health = scheduler.health([sid])[0]
                if health["operational_state"] != "HEALTHY" or health["freshness_state"] != "CURRENT":
                    raise ValueError("retained source is not HEALTHY/CURRENT")
                raw = self.archive.get(sha, sid)
                actual_sha = hashlib.sha256(raw).hexdigest()
                if actual_sha != sha:
                    raise ValueError("retained artifact hash mismatch")
                actual_count = sum(map(len, _parse_source(sid, raw)))
                recorded_count = source_record_count(sid, raw)
                if recorded_count != actual_count:
                    raise ValueError("retained parser/counter disagreement")
                ledger.append({
                    "source_id": sid, "action": "retained_verification", "mode": "OFFLINE",
                    "content_sha256": sha, "from_archive": True, "requests_sent": 0,
                    "records_returned": recorded_count, "prior_cycle_id": prior["id"],
                    "prior_records_returned": row.get("records_returned"),
                })
                verification.append({
                    "source_id": sid, "artifact": str(self.archive._path(sid, sha)),
                    "content_sha256": sha, "hash_verified": True, "actual_count": actual_count,
                    "recorded_count": recorded_count, "agreement": "PASS",
                })
            except (ValueError, KeyError, OSError, TypeError) as exc:
                errors.append(f"{sid}: {exc}")
        cycle = {
            "id": _stable_id("cycle", {"plan": self.plan.manifest_hash, "at": at.isoformat(),
                                       "phase": "RETAINED_START_GATE"}),
            "at": at.isoformat(), "phase": "RETAINED_START_GATE", "commit": report["current_commit"],
            "plan_hash": self.plan.manifest_hash, "sources": ledger,
            "source_health": scheduler.health_report(), "operator_intervention": False,
            "ok": not errors,
        }
        result = {
            "at": at.isoformat(), "phase": "RETAINED_START_GATE", "cycle": cycle,
            "retained_foreground_path": str(foreground_path),
            "retained_foreground_sha256": hashlib.sha256(original_bytes).hexdigest(),
            "artifact_verification": verification, "errors": errors,
            "real_acquisitions": False, "current_retained_evidence": not errors,
            "additional_provider_calls": 0, "manual_repairs": 0, "ok": not errors,
        }
        _append_jsonl(self.evidence_dir / "foreground_cycles.jsonl", cycle)
        _atomic_json(self.evidence_dir / "foreground_status.json", cycle)
        _atomic_json(self.evidence_dir / "foreground_validation.json", result)
        return result

    def record_intervention(self, *, kind: str, actor: str, reason: str,
                            invalidates_soak: bool) -> dict:
        event = {
            "id": _stable_id("event", {"kind": kind, "actor": actor, "at": _now()}),
            "kind": "INTERVENTION", "intervention_kind": kind, "actor": actor,
            "reason": reason, "at": _now(), "invalidates_soak": bool(invalidates_soak),
        }
        _append_jsonl(self.evidence_dir / "events.jsonl", event)
        return event

    def serve(self, *, check_interval_seconds: float = 60.0) -> None:
        if check_interval_seconds <= 0 or check_interval_seconds > 60:
            raise ValueError("check_interval_seconds must be within 1..60")
        gate_path = self.evidence_dir / "foreground_validation.json"
        if not gate_path.is_file():
            raise RuntimeError("service requires a passed foreground/start gate")
        gate = json.loads(gate_path.read_text())
        if (not gate.get("ok") or gate.get("cycle", {}).get("commit") != _repo_commit(self.repo)
                or gate.get("cycle", {}).get("plan_hash") != self.plan.manifest_hash):
            raise RuntimeError("service start gate failed or differs from pinned runtime/plan")
        self.start()
        stopping = False

        def stop(_signum, _frame):
            nonlocal stopping
            stopping = True

        signal.signal(signal.SIGTERM, stop)
        signal.signal(signal.SIGINT, stop)
        while not stopping:
            self.run_cycle()
            deadline = time.monotonic() + check_interval_seconds
            while not stopping and time.monotonic() < deadline:
                time.sleep(min(1.0, deadline - time.monotonic()))


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m pyrnova.live_ops_acceptance")
    parser.add_argument(
        "action", choices=("preflight", "foreground", "start", "run-once", "serve", "record-miss", "list-misses")
    )
    parser.add_argument("--plan")
    parser.add_argument("--repo", default=".")
    parser.add_argument("--retained-foreground", help="Original checkpointed foreground evidence, preserved read-only")
    parser.add_argument("--check-interval-seconds", type=float, default=60.0)
    parser.add_argument("--state-dir", default="var/state")
    parser.add_argument("--miss-class", choices=sorted(MISS_CLASSES))
    parser.add_argument("--source-id")
    parser.add_argument("--source-ref")
    parser.add_argument("--detected-at")
    parser.add_argument("--reviewer")
    parser.add_argument("--customer-id")
    parser.add_argument("--material-change-id")
    parser.add_argument("--acquisition-ref")
    parser.add_argument("--assessment-ref")
    parser.add_argument("--relevance-state", default="UNKNOWN")
    parser.add_argument("--emitted", action="store_true")
    parser.add_argument("--notes", default="")
    args = parser.parse_args(argv)
    if args.action in {"record-miss", "list-misses"}:
        store = StateStore(Path(args.state_dir))
        if args.action == "list-misses":
            print(json.dumps(list(store.read("important_misses")), indent=2, sort_keys=True))
            return 0
        missing = [name for name in ("miss_class", "source_id", "source_ref", "reviewer")
                   if not getattr(args, name)]
        if missing:
            parser.error("record-miss requires " + ", ".join("--" + n.replace("_", "-") for n in missing))
        record = record_important_miss(
            store, miss_class=args.miss_class, source_id=args.source_id, source_ref=args.source_ref,
            detected_at=args.detected_at or _now(), reviewer=args.reviewer,
            customer_id=args.customer_id, material_change_id=args.material_change_id,
            acquisition_ref=args.acquisition_ref, assessment_ref=args.assessment_ref,
            relevance_state=args.relevance_state, emitted=args.emitted, notes=args.notes,
        )
        print(json.dumps(record, indent=2, sort_keys=True))
        return 0
    if not args.plan:
        parser.error("--plan is required for soak actions")
    plan = load_plan(args.plan)
    repo = Path(args.repo)
    if args.action == "preflight":
        report = preflight(plan, repo=repo)
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report["ok"] else 2
    harness = SoakHarness(plan, repo=repo)
    if args.action == "foreground":
        result = (harness.verify_retained_foreground(Path(args.retained_foreground))
                  if args.retained_foreground else harness.run_foreground())
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result["ok"] else 2
    if args.action == "start":
        print(json.dumps(harness.start(), indent=2, sort_keys=True))
    elif args.action == "run-once":
        harness.start()
        print(json.dumps(harness.run_cycle(), indent=2, sort_keys=True))
    else:
        harness.serve(check_interval_seconds=args.check_interval_seconds)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
