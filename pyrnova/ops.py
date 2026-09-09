"""Read/write application service for the local Pyrnova Operator Console.

This layer deliberately consumes the engine's append-only JSONL contracts. It does not
run sources, score opportunities, or change automated dispositions.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import fields
from datetime import date, datetime
from pathlib import Path
from typing import Any

from .brief import render_signal_brief
from .models import Catalyst, Evidence, EvidenceAssessment, Event, Opportunity, Relationship, to_record
from .pipeline import Report
from .review import adjudicate, apply_review
from .scoreboard import record as record_metric, totals
from .sources.registry import active_sources
from .state import StateStore

POSTURES = {"PRIME", "SUPPORT", "TEAM", "DEFEND"}
OUTCOMES = {"UNKNOWN", "CONTACTED", "QUALIFIED", "WON", "LOST", "NO_ACTION"}


def _now() -> str:
    return datetime.utcnow().isoformat()


def _latest(records, key: str = "id") -> dict[str, dict]:
    result: dict[str, dict] = {}
    for item in records:
        value = item.get(key)
        if value:
            result[str(value)] = item
    return result


def _dataclass(cls, value: dict | None):
    value = value or {}
    allowed = {item.name for item in fields(cls)}
    return cls(**{key: val for key, val in value.items() if key in allowed})


def opportunity_from_record(record: dict) -> Opportunity:
    """Rehydrate a persisted opportunity for existing engine presentation functions."""
    data = dict(record)
    data.pop("_ts", None)
    data.pop("run_id", None)
    data["catalyst"] = _dataclass(Catalyst, data.get("catalyst"))
    data["evidence"] = [_dataclass(Evidence, item) for item in data.get("evidence", [])]
    data["events"] = [_dataclass(Event, item) for item in data.get("events", [])]
    data["relationships"] = [_dataclass(Relationship, item) for item in data.get("relationships", [])]
    data["evidence_assessments"] = [
        _dataclass(EvidenceAssessment, item) for item in data.get("evidence_assessments", [])
    ]
    return _dataclass(Opportunity, data)


class OperatorConsole:
    def __init__(self, store: StateStore, profiles_dir: Path, out_dir: Path,
                 source_state_dir: Path | None = None):
        self.store = store
        self.profiles_dir = Path(profiles_dir)
        self.out_dir = Path(out_dir)
        # M12: optional durable source-state directory for the Operations Panel source view.
        self.source_state_dir = Path(source_state_dir) if source_state_dir else None

    def source_operations(self) -> dict:
        """M12 Operations Panel view: durable per-source health + operator controls (read-only).

        Returns an empty, well-formed report when no durable source-state directory is configured, so
        the panel degrades gracefully rather than erroring."""
        if not self.source_state_dir:
            return {"configured": False, "source_count": 0, "sources": []}
        from .scheduler import SourceScheduler
        from .sources.source_state import SourceStateStore

        report = SourceScheduler(SourceStateStore(self.source_state_dir)).health_report()
        report["configured"] = True
        return report

    def targets(self) -> list[dict]:
        rows = []
        if not self.profiles_dir.exists():
            return rows
        for path in sorted(self.profiles_dir.glob("*.json")):
            try:
                profile = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            rows.append({"id": profile.get("name", path.stem), "name": profile.get("name", path.stem)})
        return rows

    def snapshot(self, target: str | None = None) -> dict:
        opportunities = list(_latest(self.store.read("opportunities")).values())
        actions = _latest(self.store.read("operator_actions"), "opportunity_id")
        outcomes = _latest(self.store.read("outcomes"), "opportunity_id")
        consequences = _latest(self.store.read("commercial_consequences"), "program_key")
        human_reviews = {
            key: value
            for key, value in _latest(self.store.read("reviews"), "opportunity_id").items()
            if value.get("human_decision")
        }
        if target:
            opportunities = [item for item in opportunities if item.get("customer_id") == target]

        queue = []
        for item in opportunities:
            op_id = str(item["id"])
            action = actions.get(op_id, {})
            review = human_reviews.get(op_id)
            evidence = item.get("evidence") or []
            program_key = (item.get("meta") or {}).get("program_key")
            consequence = consequences.get(str(program_key)) if program_key else None
            posture = action.get("posture") or (
                "DEFEND" if (item.get("meta") or {}).get("posture") == "defend" else "SUPPORT"
            )
            queue.append(
                {
                    "id": op_id,
                    "run_id": item.get("run_id"),
                    "target": item.get("customer_id"),
                    "title": item.get("title") or "Untitled candidate",
                    "agency": item.get("agency"),
                    "state": item.get("state", "candidate"),
                    "system_disposition": (item.get("meta") or {}).get("system_disposition", "WATCH"),
                    "human_decision": review.get("human_decision") if review else None,
                    "posture": posture,
                    "relevance": item.get("relevance_score", 0),
                    "confidence": item.get("confidence", 0),
                    "attractiveness": item.get("attractiveness", 0),
                    "value_usd": item.get("value_usd"),
                    "expected_action_at": item.get("expected_action_at"),
                    "falsification": action.get("falsification", item.get("falsification", "")),
                    "notes": action.get("notes", ""),
                    "evidence": [
                        {
                            "id": ev.get("id"),
                            "source": ev.get("source_id"),
                            "ref": ev.get("source_ref"),
                            "url": ev.get("source_url"),
                        }
                        for ev in evidence
                    ],
                    "outcome": outcomes.get(op_id),
                    "data_origin": (item.get("meta") or {}).get("data_origin", "engine"),
                    "source_as_of": (item.get("meta") or {}).get("source_as_of"),
                    "source_status": (item.get("meta") or {}).get("source_status"),
                    "score_status": (item.get("meta") or {}).get("score_status", "available"),
                    "m7_consequence": {
                        "mechanism": consequence.get("mechanism"),
                        "directness": consequence.get("directness"),
                        "confidence": consequence.get("confidence"),
                        "screened_disposition": consequence.get("screened_disposition"),
                        "spend_category": consequence.get("likely_spend_category"),
                    } if consequence else None,
                    "updated_at": item.get("_ts"),
                }
            )
        queue.sort(key=lambda item: (-float(item["relevance"] or 0), item["title"]))

        observations = {}
        for observation in self.store.read("observations"):
            source_id = observation.get("source_id")
            if source_id:
                observations[source_id] = observation
        source_health = []
        for spec in active_sources():
            observed = observations.get(spec.id)
            source_health.append(
                {
                    "id": spec.id,
                    "name": spec.name,
                    "status": "observed" if observed else "not_observed",
                    "last_observed_at": (observed or {}).get("fetched_at") or (observed or {}).get("_ts"),
                }
            )

        runs: dict[str, dict] = {}
        for item in opportunities:
            run_id = item.get("run_id") or "legacy"
            run = runs.setdefault(run_id, {"id": run_id, "candidates": 0, "last_activity": None})
            run["candidates"] += 1
            run["last_activity"] = max(filter(None, [run["last_activity"], item.get("_ts")]), default=None)

        return {
            "generated_at": _now(),
            "target": target,
            "targets": self.targets(),
            "runs": sorted(runs.values(), key=lambda item: item["last_activity"] or "", reverse=True),
            "source_health": source_health,
            "source_operations": self.source_operations(),
            "queue": queue,
            "scoreboard": totals(self.store),
        }

    def adjudicate(
        self,
        opportunity_id: str,
        *,
        decision: str,
        reviewer: str,
        reason: str = "",
        posture: str = "SUPPORT",
        notes: str = "",
        falsification: str = "",
    ) -> dict:
        decision = decision.strip().upper()
        posture = posture.strip().upper()
        if posture not in POSTURES:
            raise ValueError(f"posture must be one of {sorted(POSTURES)}")
        record = self.store.latest("opportunities", opportunity_id)
        if not record:
            raise ValueError(f"opportunity not found: {opportunity_id}")
        opportunity = opportunity_from_record(record)
        review = adjudicate(opportunity, decision=decision, reviewer=reviewer, reason=reason)
        apply_review(opportunity, review)
        self.store.append("reviews", to_record(review))
        updated = dict(record)
        updated.pop("_ts", None)
        updated["state"] = opportunity.state
        updated["meta"] = opportunity.meta
        updated["falsification"] = falsification
        self.store.append("opportunities", updated)
        self.store.append(
            "operator_actions",
            {
                "id": uuid.uuid4().hex,
                "opportunity_id": opportunity_id,
                "posture": posture,
                "notes": notes,
                "falsification": falsification,
                "review_id": review.id,
            },
        )
        record_metric(
            self.store,
            {"ACCEPT": "review_accepts", "WATCH": "review_watches", "REJECT": "review_rejects"}[decision],
            opportunity_id=opportunity_id,
            reviewer=reviewer,
        )
        return {"opportunity_id": opportunity_id, "state": opportunity.state, "review": to_record(review)}

    def record_outcome(self, opportunity_id: str, *, status: str, notes: str = "", value_usd=None) -> dict:
        if not self.store.latest("opportunities", opportunity_id):
            raise ValueError(f"opportunity not found: {opportunity_id}")
        status = status.strip().upper()
        if status not in OUTCOMES:
            raise ValueError(f"status must be one of {sorted(OUTCOMES)}")
        row = {
            "id": uuid.uuid4().hex,
            "opportunity_id": opportunity_id,
            "status": status,
            "notes": notes,
            "value_usd": value_usd,
            "recorded_at": _now(),
        }
        self.store.append("outcomes", row)
        return row

    def export_signal_brief(self, target: str) -> dict:
        if not target or not target.strip():
            raise ValueError("target is required")
        records = [
            item for item in _latest(self.store.read("opportunities")).values()
            if item.get("customer_id") == target and item.get("state") == "strike"
        ]
        opportunities = [opportunity_from_record(item) for item in records]
        opportunities.sort(key=lambda item: (-item.relevance_score, -item.attractiveness))
        report = Report(
            profile_name=target,
            as_of=date.today(),
            run_id="operator-export",
            strikes=opportunities,
            stats={"strikes": len(opportunities), "candidates": len(records)},
        )
        markdown = render_signal_brief(report, customer_name=target)
        self.out_dir.mkdir(parents=True, exist_ok=True)
        slug = "".join(char for char in target.lower() if char.isalnum() or char in "-_") or "target"
        path = self.out_dir / f"signal_brief_{slug}.md"
        path.write_text(markdown, encoding="utf-8")
        record_metric(self.store, "signal_briefs_produced", profile=target, origin="operator_console")
        return {"path": str(path), "markdown": markdown, "items": len(opportunities)}
