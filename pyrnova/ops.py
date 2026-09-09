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
        from .live_ops import operating_cost_report
        from .scheduler import SourceScheduler
        from .sources.source_state import SourceStateStore

        scheduler = SourceScheduler(SourceStateStore(self.source_state_dir))
        report = scheduler.health_report()  # M12/M13: per-source mode, budget, cache hits, calls
        report["configured"] = True         # avoided, circuit state, poll cadence + next_poll_at, due
        # M13: the operating-cost / call-telemetry view — "what does source operation cost in calls?"
        report["operating_cost"] = operating_cost_report(scheduler)
        # M14: the broader source mesh — group the health rows by economic-domain family, and surface
        # recently demonstrated cross-source chains (thin read; the panel is not redesigned).
        report["families"] = self._family_view(report.get("sources", []))
        report["cross_source_chains"] = self.recent_cross_source_chains()
        return report

    def _family_view(self, source_rows: list[dict]) -> list[dict]:
        """Roll up per-source health rows into an economic-domain family view (M14 source mesh)."""
        from .sources.registry import REGISTRY

        health_by_id = {r.get("source_id"): r for r in source_rows}
        families: dict[str, dict] = {}
        for spec in REGISTRY.values():
            fam = families.setdefault(spec.family, {
                "family": spec.family, "sources": [], "operational": 0, "calls_made": 0,
                "calls_avoided": 0,
            })
            row = health_by_id.get(spec.id, {})
            fam["sources"].append(spec.id)
            if spec.status == "operational":
                fam["operational"] += 1
            fam["calls_made"] += row.get("calls_made") or 0
            fam["calls_avoided"] += row.get("calls_avoided") or 0
        return [families[f] for f in sorted(families)]

    def recent_cross_source_chains(self, limit: int = 10) -> list[dict]:
        """Recent demonstrated cross-source chains (empty-safe; append-only JSONL)."""
        try:
            rows = list(self.store.read("cross_source_chains"))
        except Exception:  # noqa: BLE001 — the panel degrades gracefully if the collection is absent
            return []
        return rows[-limit:][::-1]

    def threat_operations(self, subject_ref: str | None = None) -> dict:
        """M15 Operations Panel view: active threats, exposures, and zero-threat rejections (read-only).

        Reads the append-only ``threats`` / ``threat_rejections`` / ``exposures`` streams and rolls them
        up so an operator can see WHY a threat exists (mechanism, severity, confidence, horizon, affected
        exposure, evidence, dual opportunity). Degrades to a well-formed empty report when nothing has
        been persisted. Preserves the existing panel; nothing here changes scoring or fit."""
        from .threat import SEVERITY_LEVELS, company_threat_surface
        from .models import Threat

        def _read(name):
            try:
                return list(self.store.read(name))
            except Exception:  # noqa: BLE001 — panel degrades gracefully if the collection is absent
                return []

        threat_rows = list(_latest(_read("threats")).values())
        rejections = _read("threat_rejections")
        exposures = list(_latest(_read("exposures")).values())
        if subject_ref:
            threat_rows = [t for t in threat_rows if t.get("subject_ref") == subject_ref]
            rejections = [r for r in rejections if r.get("subject_ref") == subject_ref]
            exposures = [e for e in exposures if e.get("subject_ref") == subject_ref]

        active = [t for t in threat_rows if t.get("status") in ("WATCH", "ACTIVE", "MITIGATED")]

        def dist(items, key):
            out: dict[str, int] = {}
            for it in items:
                out[it.get(key)] = out.get(it.get(key), 0) + 1
            return dict(sorted((k, v) for k, v in out.items() if k is not None))

        # Per-company threat surface, reusing the shared entity layer / threat helper.
        surfaces = []
        for ref in sorted({t.get("subject_ref") for t in active if t.get("subject_ref")}):
            objs = [Threat(**{k: v for k, v in t.items()
                             if k in Threat.__dataclass_fields__}) for t in active
                    if t.get("subject_ref") == ref]
            surfaces.append(company_threat_surface(ref, objs))

        return {
            "configured": bool(threat_rows or rejections or exposures),
            "active_threat_count": len(active),
            "zero_threat_rejections": len(rejections),
            "by_mechanism": dist(active, "mechanism"),
            "by_severity": dist(active, "severity"),
            "by_confidence": dist(active, "confidence"),
            "by_horizon": dist(active, "horizon"),
            "rejection_reasons": dist(rejections, "reason_code"),
            "dual_sided_count": sum(1 for t in active if t.get("dual_opportunity_ref")),
            "exposure_count": len(exposures),
            "exposure_confirmed": sum(1 for e in exposures if e.get("link_class") == "CONFIRMED"),
            "company_threat_surfaces": surfaces,
            "threats": sorted(
                [{"id": t.get("id"), "subject": t.get("subject_name"), "mechanism": t.get("mechanism"),
                  "severity": t.get("severity"), "confidence": t.get("confidence"),
                  "horizon": t.get("horizon"), "affected_value_category": t.get("affected_value_category"),
                  "economic_effect": t.get("economic_effect"), "evidence_ids": t.get("evidence_ids"),
                  "dual_opportunity_ref": t.get("dual_opportunity_ref")} for t in active],
                key=lambda t: (-SEVERITY_LEVELS.index(t["severity"]) if t["severity"] in SEVERITY_LEVELS
                               else 0, t["mechanism"]),
            ),
        }

    def threat_propagation_view(self) -> dict:
        """M16 Operations Panel view: direct vs propagated threats, propagation paths, and beneficiary
        opportunities (read-only, empty-safe). Reads the append-only ``propagated_threats`` and
        ``beneficiary_opportunities`` streams the propagation engine persists."""
        def _read(name):
            try:
                return list(self.store.read(name))
            except Exception:  # noqa: BLE001 — degrade gracefully if the collection is absent
                return []

        direct = list(_latest(_read("threats")).values())
        propagated = list(_latest(_read("propagated_threats")).values())
        beneficiaries = list(_latest(_read("beneficiary_opportunities")).values())
        depths = [(p.get("meta") or {}).get("propagation_depth", 0) for p in propagated]
        return {
            "configured": bool(propagated or beneficiaries),
            "direct_threat_count": len(direct),
            "propagated_threat_count": len(propagated),
            "beneficiary_opportunity_count": len(beneficiaries),
            "max_propagation_depth": max(depths) if depths else 0,
            "propagated_threats": [
                {"id": p.get("id"), "subject": p.get("subject_name"), "mechanism": p.get("mechanism"),
                 "severity": p.get("severity"), "confidence": p.get("confidence"),
                 "root_threat_id": (p.get("meta") or {}).get("root_threat_id"),
                 "depth": (p.get("meta") or {}).get("propagation_depth"),
                 "path": (p.get("meta") or {}).get("propagation_path"),
                 "evidence_ids": p.get("evidence_ids")}
                for p in propagated],
            "beneficiary_opportunities": beneficiaries,
        }

    def company_threat_network_view(self, company_ref: str) -> dict:
        """M17 Operations Panel view (Workstream M): "For Company X, what DIRECT and INDIRECT threats
        currently affect it, and through which relationships?"

        Composes the persisted ``threats`` / ``propagated_threats`` / ``beneficiary_opportunities`` /
        ``threat_outcomes`` streams (read-only, empty-safe) around one company ref:

        * ``direct_threats`` — threats whose subject is the company (with its ``company_threat_surface``),
        * ``inbound_propagated`` — threats that reached the company THROUGH a relationship edge (each with
          its root catalyst, full propagation path, degraded confidence/severity, evidence, and current
          outcome status where knowable),
        * ``outbound_network`` — threats rooted AT this company that propagated to dependents (its network
          footprint).

        Builds on ``company_threat_surface``; it does not replace it, and it is not the full Company
        Opportunity Surface (deliberately out of M17 scope)."""
        from .threat import company_threat_surface, resolve_threat_outcome
        from .models import Threat

        def _read(name):
            try:
                return list(self.store.read(name))
            except Exception:  # noqa: BLE001 — degrade gracefully if the collection is absent
                return []

        threats = list(_latest(_read("threats")).values())
        propagated = list(_latest(_read("propagated_threats")).values())
        beneficiaries = _read("beneficiary_opportunities")
        outcome_obs = _read("threat_outcomes")
        by_threat: dict[str, list[dict]] = {}
        for obs in outcome_obs:
            tid = obs.get("threat_id")
            if tid:
                by_threat.setdefault(tid, []).append(obs)
        now = _now()

        def outcome_status(threat_id: str) -> dict:
            obs = by_threat.get(threat_id)
            if not obs:
                return {"label": "UNKNOWN", "resolved": False}
            res = resolve_threat_outcome(obs, as_of=now)
            return {"label": res.get("label"), "resolved": res.get("resolved")}

        active = [t for t in threats
                  if t.get("subject_ref") == company_ref and t.get("status") in ("WATCH", "ACTIVE", "MITIGATED")]
        surface_objs = [Threat(**{k: v for k, v in t.items() if k in Threat.__dataclass_fields__})
                        for t in active]
        surface = company_threat_surface(company_ref, surface_objs) if surface_objs else None

        inbound = [p for p in propagated if p.get("subject_ref") == company_ref]
        my_root_ids = {t.get("id") for t in threats if t.get("subject_ref") == company_ref}
        outbound = [p for p in propagated if (p.get("meta") or {}).get("root_threat_id") in my_root_ids]

        def hop_view(p):
            meta = p.get("meta") or {}
            return {
                "id": p.get("id"), "subject": p.get("subject_name"), "mechanism": p.get("mechanism"),
                "severity": p.get("severity"), "confidence": p.get("confidence"),
                "horizon": p.get("horizon"), "catalyst_id": p.get("catalyst_id"),
                "root_threat_id": meta.get("root_threat_id"), "depth": meta.get("propagation_depth"),
                "catalyst_class": meta.get("catalyst_class", "MODELED"),
                "relationship_path": meta.get("propagation_path"), "evidence_ids": p.get("evidence_ids"),
                "outcome": outcome_status(p.get("id")),
            }

        return {
            "company_ref": company_ref,
            "configured": bool(active or inbound or outbound),
            "direct_threat_count": len(active),
            "inbound_propagated_count": len(inbound),
            "outbound_propagated_count": len(outbound),
            "company_threat_surface": surface,
            "direct_threats": [
                {"id": t.get("id"), "mechanism": t.get("mechanism"), "severity": t.get("severity"),
                 "confidence": t.get("confidence"), "horizon": t.get("horizon"),
                 "catalyst_class": (t.get("meta") or {}).get("catalyst_class", "MODELED"),
                 "economic_effect": t.get("economic_effect"), "evidence_ids": t.get("evidence_ids"),
                 "outcome": outcome_status(t.get("id"))}
                for t in active],
            "inbound_propagated": [hop_view(p) for p in inbound],
            "outbound_network": [hop_view(p) for p in outbound],
            "beneficiary_opportunities": [b for b in beneficiaries
                                          if b.get("subject_ref") == company_ref],
        }

    @staticmethod
    def selectivity_view(result: dict) -> dict:
        """M16 Operations Panel view: format one selectivity-harness funnel for the operator (the funnel
        + rates + note). Pure pass-through of ``selectivity.run_selectivity`` output; no store access."""
        result = result or {}
        return {
            "stream": result.get("stream"),
            "monitored_companies": result.get("monitored_companies"),
            "funnel": result.get("funnel"),
            "threat_emission_rate": result.get("threat_emission_rate"),
            "weak_rejection_rate": result.get("weak_rejection_rate"),
            "per_company": result.get("per_company"),
            "note": result.get("note"),
        }

    @staticmethod
    def adverse_catalyst_view(parsed_events: dict, independence: dict | None = None) -> dict:
        """M18 Operations Panel view (Workstream Q, thin): surface archived OBSERVED adverse catalysts
        (source-native id, type, agency, date) alongside optional relationship-independence/diversity
        counts. Pure pass-through of ``adverse_events.parse_*`` + ``relationships.independence_metrics``
        output; no store access, empty-safe. Does not redesign the panel or add a second console."""
        parsed_events = parsed_events or {}
        events = parsed_events.get("events", [])
        return {
            "source_id": parsed_events.get("source_id"),
            "family": parsed_events.get("family"),
            "observed_catalyst_count": sum(1 for e in events if e.get("catalyst_class") == "OBSERVED"),
            "catalysts": [
                {"event_id": e.get("event_id"), "event_type": e.get("event_type"),
                 "agency": e.get("agency"), "published": e.get("publication_date"),
                 "catalyst_class": e.get("catalyst_class"), "source_url": e.get("source_url")}
                for e in events[:25]],
            "relationship_independence": independence or {},
        }

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
