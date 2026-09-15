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
                 source_state_dir: Path | None = None,
                 mc_store: StateStore | None = None,
                 contexts_dir: Path | None = None,
                 customer_store: StateStore | None = None,
                 cmc_store: StateStore | None = None,
                 access_check=None,
                 delivery_store=None):
        self.store = store
        self.profiles_dir = Path(profiles_dir)
        self.out_dir = Path(out_dir)
        # M12: optional durable source-state directory for the Operations Panel source view.
        self.source_state_dir = Path(source_state_dir) if source_state_dir else None
        # M22-A: optional separate store for Material Changes intelligence (threats/propagated threats)
        # and the directory of customer intelligence contexts. Defaults keep the existing panel intact.
        self.mc_store = mc_store or store
        self.contexts_dir = Path(contexts_dir) if contexts_dir else None
        # M22-B: persisted customer intelligence + watchlists + Material Change review/lifecycle state.
        # Defaults to the main store. When a customer is persisted here it drives the read path; the
        # demo ``contexts_dir`` JSON remains a fallback so a fresh checkout stays populated (D-056).
        self.customer_store = customer_store or store
        # M22-C: optional customer-scoped persisted Material Change store. When set AND populated for a
        # customer, the read path serves that customer-scoped state (the production-shaped path). Left as
        # None, the read path recomputes on the fly exactly as M22-A/B did (fully backward compatible).
        self.cmc_store = cmc_store
        # M22-C: the authorization seam (§15). A callable ``access_check(customer_id) -> bool`` decides
        # whether the current actor may read/act on a customer. Authentication is deferred (D-048); this
        # is the single chokepoint a later AUTHENTICATED ACTOR -> AUTHORIZED CUSTOMER layer attaches to,
        # so no intelligence-model rewrite is needed to add auth. ``None`` means permissive (dev default).
        self.access_check = access_check
        # B3.11: optional tenant-safe customer brief delivery store (CustomerDeliveryStore). None disables
        # the delivery surface (it then reports as not configured rather than fabricating a send).
        self.delivery_store = delivery_store

    def _require_access(self, customer_id: str) -> None:
        """Enforce the customer-authorization boundary (§6/§15). Rejects a mismatched/unauthorized id."""
        if self.access_check is not None and not self.access_check(customer_id):
            raise PermissionError(f"actor is not authorized for customer: {customer_id}")

    # --- M22-A: Material Changes (customer-facing "what materially changed?") ---------------------

    def customers(self) -> list[dict]:
        """List available customers (id + name), empty-safe.

        M22-B: persisted customers drive the product. Any demo ``contexts_dir`` customer not yet
        persisted is still listed (M22-A compatibility) so a fresh checkout is populated."""
        from . import customers as cust
        rows = {r["id"]: r for r in cust.list_customers(self.customer_store)}
        if self.contexts_dir and self.contexts_dir.exists():
            for path in sorted(self.contexts_dir.glob("*.json")):
                try:
                    data = json.loads(path.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError):
                    continue
                cid = data.get("customer_id") or path.stem
                rows.setdefault(cid, {"id": cid, "name": data.get("name", cid)})
        return [rows[k] for k in sorted(rows)]

    def customer_identity(self, customer_id: str) -> dict | None:
        """The public identity ({id, name}) of one customer, or None — for the ``/api/me`` org display.

        Reads only id + name (never another customer's private state); used to show the authenticated
        organization instead of a tenant-selection dropdown (§36)."""
        for row in self.customers():
            if row["id"] == customer_id:
                return row
        return None

    def _load_context(self, customer_id: str, *, as_of: str | None = None):
        """Build the customer's deterministic relevance context, point-in-time.

        Prefers PERSISTED customer state (profile + temporally-valid watchlists); falls back to the demo
        ``contexts_dir`` JSON only when the customer is not persisted (M22-A compatibility)."""
        from . import customers as cust
        from .material_changes import CustomerContext

        if cust.get_customer(self.customer_store, customer_id) is not None:
            return cust.build_context(self.customer_store, customer_id, as_of=as_of)
        if self.contexts_dir:
            for path in sorted(self.contexts_dir.glob("*.json")):
                try:
                    data = json.loads(path.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError):
                    continue
                if (data.get("customer_id") or path.stem) == customer_id:
                    return CustomerContext.from_dict(data)
        raise ValueError(f"customer not found: {customer_id}")

    def material_changes(self, customer_id: str, *, as_of: str | None = None,
                         disposition: str | None = None) -> dict:
        """Material Changes read view for one customer (deterministic, point-in-time, isolated).

        Projects existing ``threats`` / ``propagated_threats`` / ``opportunities`` into customer-relevant
        Material Change records and overlays the customer's persisted review/lifecycle state (M22-B).
        Reads only; changes no dispositions, mutates no system assessment, runs no LLM reasoning."""
        from . import customers as cust
        from .material_changes import build_material_changes

        self._require_access(customer_id)
        context = self._load_context(customer_id, as_of=as_of)

        def _read(store, name):
            try:
                return list(_latest(store.read(name)).values())
            except Exception:  # noqa: BLE001 — degrade gracefully if a collection is absent
                return []

        threats = _read(self.mc_store, "threats")
        propagated = _read(self.mc_store, "propagated_threats")
        # All global intelligence streams are read from the SAME store (one canonical pattern — engineering
        # doctrine §2/§3, and consistent with the M22-C fan-out, which reads opportunities from mc_store).
        # ``mc_store`` is the demo fixture store on a fresh checkout and the persisted store in production
        # (where it equals ``self.store``), so this is a no-op in production and correct in the demo.
        opportunities = [o for o in _read(self.mc_store, "opportunities")
                         if o.get("customer_id") == customer_id]

        changes = build_material_changes(
            threats=threats, propagated_threats=propagated, opportunities=opportunities,
            context=context, as_of=as_of, disposition=disposition)

        # M22-B: overlay the customer's persisted review/lifecycle state. This is CUSTOMER state, kept
        # separate from the SYSTEM assessment/lifecycle already on each change (never flattened together).
        overlay = cust.review_overlay(self.customer_store, customer_id, as_of=as_of)
        # M22-C: overlay the customer-scoped PERSISTED Material Change state (first-seen semantics, delivered
        # outcome, content version). This state is storage-isolated per customer; the global intelligence
        # projection above is reconstructed from shared global truth and is never duplicated per customer.
        versions = {}
        if self.cmc_store is not None:
            from .customer_material_changes import _latest_versions
            versions = _latest_versions(self.cmc_store, customer_id, as_of=as_of)
        by_disposition: dict[str, int] = {}
        by_review_state: dict[str, int] = {}
        materialized = 0
        for change in changes:
            state = overlay.get(change["id"], {}).get("state", cust.STATE_NEW)
            change["review"] = overlay.get(change["id"], {"state": state, "action_count": 0,
                                                          "last_action": None})
            change["review"]["state"] = state
            # M22-D §5: investigation navigation. A Material Change links to the affected company, the
            # affected program, and any related entities on its propagation path — the user need never
            # copy an identifier into search. Built from refs already on the projection (canonical objects).
            refs = change.get("refs") or {}
            subject_ref = refs.get("subject_ref")
            related: list[dict] = []
            for hop in ((change.get("propagation") or {}).get("path") or []):
                for r in (hop.get("from_ref"), hop.get("to_ref")):
                    if r and r != subject_ref and r not in [x["ref"] for x in related]:
                        related.append({"ref": r})
            change["investigation"] = {
                "company": {"ref": subject_ref,
                            "name": (change.get("observed") or {}).get("affected_entity")}
                            if subject_ref else None,
                "program": {"key": refs.get("program")} if refs.get("program") else None,
                "related_entities": related,
            }
            v = versions.get(change["id"])
            if v is not None:
                materialized += 1
                change["first_seen"] = {
                    # §8: three distinct times, never collapsed into one created_at. "Reviewed" is the
                    # separate M22-B lifecycle carried in ``review`` above.
                    "intelligence_observed_at": v.get("intelligence_observed_at"),
                    "first_relevant_at": v.get("first_relevant_at"),
                    "delivered_at": v.get("delivered_at"),
                    "content_version": v.get("content_version"),
                    "last_updated_at": v.get("last_updated_at"),
                    "change_kind": v.get("change_kind"),
                    # The outcome state Pyrnova had DELIVERED to the customer at the last fan-out (may lag
                    # current global truth; the top-level ``outcome_state`` reflects current global truth).
                    "delivered_outcome_state": v.get("outcome_state"),
                    "status": "MATERIALIZED",
                }
            elif self.cmc_store is not None:
                # Relevant now, but fan-out has not yet materialized it into the customer-scoped feed.
                change["first_seen"] = {"status": "PENDING_FANOUT", "delivered_at": None}
            by_disposition[change["disposition"]] = by_disposition.get(change["disposition"], 0) + 1
            by_review_state[state] = by_review_state.get(state, 0) + 1
        payload = {
            "customer": {"id": context.customer_id, "name": context.name},
            "as_of": as_of,
            "disposition_filter": (disposition or "").strip().upper() or None,
            "generated_at": _now(),
            "count": len(changes),
            "by_disposition": dict(sorted(by_disposition.items())),
            "by_review_state": dict(sorted(by_review_state.items())),
            "materialized": materialized if self.cmc_store is not None else None,
            "material_changes": changes,
        }
        from .sources.rights import gate_customer_display
        gated_changes = [gate_customer_display(change) for change in changes]
        payload["material_changes"] = gated_changes
        payload["source_rights"] = {
            "display": "PARTIAL" if any(c.get("source_rights", {}).get("display") == "BLOCKED" for c in gated_changes) else "ALLOWED",
            "items": [c.get("source_rights") for c in gated_changes],
        }
        return payload

    # --- M22-D: deterministic search + company/program investigation pages ------------------------

    def _build_estate(self, *, as_of: str | None = None):
        """Build the point-in-time investigation estate from the GLOBAL intelligence streams (§10/§13).

        Reuses the same threat/opportunity streams the Material Changes read model consumes, so search and
        the investigation pages reference exactly the canonical objects the feed does — never a second,
        divergent entity model."""
        from .investigation import build_estate

        def _read(store, name):
            try:
                return list(_latest(store.read(name)).values())
            except Exception:  # noqa: BLE001 — degrade gracefully if a collection is absent
                return []

        return build_estate(
            threats=_read(self.mc_store, "threats"),
            propagated_threats=_read(self.mc_store, "propagated_threats"),
            # Opportunities from the SAME store as threats (one canonical pattern; see the feed read path).
            opportunities=_read(self.mc_store, "opportunities"),
            relationships=_read(self.store, "relationships"),
            as_of=as_of,
        )

    def search(self, query: str, *, as_of: str | None = None, limit: int = 25) -> dict:
        """Resolve a query against the Pyrnova estate (deterministic; no runtime LLM — §6/§9)."""
        from .investigation import search as _search
        estate = self._build_estate(as_of=as_of)
        result = _search(estate, query or "", limit=limit)
        result["as_of"] = as_of
        result["generated_at"] = _now()
        return result

    def _entity_customer_context(self, estate, *, entity_ref: str | None = None,
                                 program_key: str | None = None, customer_id: str | None = None) -> dict | None:
        """Customer-specific overlay for an investigation page (§12), kept strictly separate from global truth.

        Authorization is enforced first. Returns whether the customer watches/owns the object and which of
        THAT customer's Material Changes touch it — never another customer's private state, never folded
        into the global page."""
        if not customer_id:
            return None
        self._require_access(customer_id)
        from . import customers as cust
        context = self._load_context(customer_id, as_of=None)
        norm = context._norm
        watched = False
        relation = None
        if entity_ref:
            if norm(context.entity_refs) and entity_ref.strip().lower() in norm(context.entity_refs):
                watched, relation = True, "DIRECT_SUBJECT"
            elif entity_ref.strip().lower() in norm(context.watched_entity_refs):
                watched, relation = True, "WATCHED_ENTITY"
        if program_key and program_key.strip().lower() in norm(context.watched_programs):
            watched, relation = True, "WATCHED_PROGRAM"
        # Which of this customer's own Material Changes reference the object (customer-isolated read).
        feed = self.material_changes(customer_id)["material_changes"]
        related = []
        for c in feed:
            refs = c.get("refs") or {}
            if (entity_ref and refs.get("subject_ref") == entity_ref) or \
               (program_key and refs.get("program") == program_key):
                related.append({"id": c["id"], "disposition": c.get("disposition"),
                                "review_state": (c.get("review") or {}).get("state")})
        return {"customer_id": customer_id, "watched": watched, "relation": relation,
                "related_material_change_ids": [r["id"] for r in related],
                "related_material_changes": related}

    def company_intelligence(self, ref: str, *, as_of: str | None = None,
                             customer: str | None = None) -> dict:
        """Company investigation page (global). Optional isolated customer overlay when authorized (§3/§12)."""
        from .investigation import company_intelligence as _company
        estate = self._build_estate(as_of=as_of)
        overlay = self._entity_customer_context(estate, entity_ref=ref, customer_id=customer)
        try:
            page = _company(estate, ref, as_of=as_of, customer_context=overlay)
        except KeyError:
            raise ValueError(f"entity not found in the Pyrnova estate: {ref}")
        page["generated_at"] = _now()
        from .sources.rights import gate_customer_display
        decisions = []
        for key in ("relationships", "material_history", "evidence"):
            if isinstance(page.get(key), list):
                page[key] = [gate_customer_display(item) for item in page[key]]
                decisions.extend(item.get("source_rights") for item in page[key])
        ci = page.get("current_intelligence") or {}
        if isinstance(ci.get("material_events"), list):
            ci["material_events"] = [gate_customer_display(item) for item in ci["material_events"]]
            decisions.extend(item.get("source_rights") for item in ci["material_events"])
        page["source_rights"] = {"display": "PARTIAL" if any(d and d.get("display") == "BLOCKED" for d in decisions) else "ALLOWED", "items": decisions}
        return page

    def program_intelligence(self, program_key: str, *, as_of: str | None = None,
                             customer: str | None = None) -> dict:
        """Program investigation page (global). Optional isolated customer overlay when authorized (§4/§12)."""
        from .investigation import program_intelligence as _program
        estate = self._build_estate(as_of=as_of)
        overlay = self._entity_customer_context(estate, program_key=program_key, customer_id=customer)
        try:
            page = _program(estate, program_key, as_of=as_of, customer_context=overlay)
        except KeyError:
            raise ValueError(f"program not found in the Pyrnova estate: {program_key}")
        page["generated_at"] = _now()
        from .sources.rights import gate_customer_display
        decisions = []
        mc = page.get("material_changes") or {}
        if isinstance(mc.get("material_events"), list):
            mc["material_events"] = [gate_customer_display(item) for item in mc["material_events"]]
            decisions.extend(item.get("source_rights") for item in mc["material_events"])
        for key in ("relationships", "material_history", "evidence"):
            if isinstance(page.get(key), list):
                page[key] = [gate_customer_display(item) for item in page[key]]
                decisions.extend(item.get("source_rights") for item in page[key])
        page["source_rights"] = {"display": "PARTIAL" if any(d and d.get("display") == "BLOCKED" for d in decisions) else "ALLOWED", "items": decisions}
        return page

    # --- M22-B: persisted customer CRUD + Material Change review/lifecycle -------------------------

    def create_customer(self, *, customer_id: str, name: str, entity_refs=None, capabilities=None,
                        agencies=None, sectors=None, geography=None, provenance: str = "operator",
                        effective_from: str | None = None) -> dict:
        """Create/replace a persisted customer profile version (append-only, auditable)."""
        from . import customers as cust
        profile = cust.CustomerProfile(
            customer_id=customer_id, name=name, entity_refs=list(entity_refs or []),
            capabilities=list(capabilities or []), agencies=list(agencies or []),
            sectors=list(sectors or []), geography=list(geography or []),
            provenance=provenance, effective_from=effective_from)
        return cust.upsert_customer(self.customer_store, profile)

    def get_customer_profile(self, customer_id: str, *, as_of: str | None = None) -> dict:
        from . import customers as cust
        profile = cust.get_customer(self.customer_store, customer_id, as_of=as_of)
        if profile is None:
            raise ValueError(f"customer not found: {customer_id}")
        out = profile.to_record()
        out["watchlist"] = cust.list_watches(self.customer_store, customer_id, as_of=as_of)
        return out

    def add_customer_watch(self, customer_id: str, *, object_type: str, ref: str, label: str = "",
                           valid_from: str | None = None, provenance: str = "operator") -> dict:
        """Add a persisted watchlist entry for a customer (validates the object type + ref)."""
        from . import customers as cust
        if cust.get_customer(self.customer_store, customer_id) is None:
            raise ValueError(f"customer not found: {customer_id}")
        entry = cust.WatchlistEntry(customer_id=customer_id, object_type=object_type, ref=ref,
                                    label=label, valid_from=valid_from, provenance=provenance)
        return cust.add_watch(self.customer_store, entry)

    def retire_customer_watch(self, customer_id: str, watch_id: str) -> dict:
        from . import customers as cust
        return cust.retire_watch(self.customer_store, customer_id, watch_id)

    def list_customer_watches(self, customer_id: str, *, as_of: str | None = None) -> list[dict]:
        from . import customers as cust
        return cust.list_watches(self.customer_store, customer_id, as_of=as_of)

    def record_customer_review(self, customer_id: str, material_change_id: str, *, action_type: str,
                               actor: str = "operator", reason: str = "", note: str = "",
                               outcome_ref: str | None = None) -> dict:
        """Record a customer review/lifecycle action on one Material Change (tenancy-checked).

        Rejects cross-customer access: the change must be relevant/visible to this customer. Appends an
        audit record; never mutates the authoritative system assessment."""
        from . import customers as cust
        self._require_access(customer_id)
        # Compute the customer's currently visible change ids and enforce the tenancy boundary.
        visible = {c["id"] for c in self.material_changes(customer_id)["material_changes"]}
        return cust.record_review_action(
            self.customer_store, customer_id=customer_id, material_change_id=material_change_id,
            action_type=action_type, actor=actor, reason=reason, note=note, outcome_ref=outcome_ref,
            visible_change_ids=visible)

    def customer_review_history(self, customer_id: str, material_change_id: str, *,
                               as_of: str | None = None) -> dict:
        from . import customers as cust
        history = cust.review_history(self.customer_store, customer_id, material_change_id, as_of=as_of)
        return {
            "customer_id": customer_id,
            "material_change_id": material_change_id,
            "current_state": cust.current_review_state(self.customer_store, customer_id,
                                                       material_change_id, as_of=as_of),
            "history": history,
        }

    # --- M22-C: customer-scoped Material Change fan-out / rebuild / version history ----------------

    def fan_out(self, *, customer_ids=None, as_of: str | None = None) -> dict:
        """Materialize relevant global intelligence into customer-scoped Material Change state (§5/§9).

        This is the ordinary continuous-operations path: no demo script is required. Requires a
        ``cmc_store``. Returns the structured fan-out observability report (§17)."""
        if self.cmc_store is None:
            raise ValueError("fan-out requires a customer-scoped Material Change store (cmc_store)")
        from .customer_material_changes import fan_out as _fan_out
        return _fan_out(mc_store=self.mc_store, customer_store=self.customer_store,
                        cmc_store=self.cmc_store, customer_ids=customer_ids, as_of=as_of)

    def rebuild_customer_material_changes(self, customer_id: str, *, as_of: str | None = None) -> dict:
        """Rebuild one customer's derived Material Change state (§10); customer actions survive untouched."""
        if self.cmc_store is None:
            raise ValueError("rebuild requires a customer-scoped Material Change store (cmc_store)")
        self._require_access(customer_id)
        from .customer_material_changes import rebuild_customer
        return rebuild_customer(mc_store=self.mc_store, customer_store=self.customer_store,
                                cmc_store=self.cmc_store, customer_id=customer_id, as_of=as_of)

    def customer_material_change_versions(self, customer_id: str, material_change_id: str) -> dict:
        """Full stored version history for one customer Material Change (original assessment → outcome, §12)."""
        self._require_access(customer_id)
        if self.cmc_store is None:
            return {"customer_id": customer_id, "material_change_id": material_change_id, "versions": []}
        from .customer_material_changes import version_history
        payload = {"customer_id": customer_id, "material_change_id": material_change_id,
                   "versions": version_history(self.cmc_store, customer_id, material_change_id)}
        from .sources.rights import gate_customer_display
        versions = [gate_customer_display(v) for v in payload["versions"]]
        payload["versions"] = versions
        payload["source_rights"] = {"display": "PARTIAL" if any(v.get("source_rights", {}).get("display") == "BLOCKED" for v in versions) else "ALLOWED",
                                     "items": [v.get("source_rights") for v in versions]}
        return payload

    # --- B3: customer product surface — opportunities, decision view, evidence, disposition, brief ---
    #
    # These surfaces expose the ALREADY-PERSISTED, accepted opportunity intelligence (Bundle-1 catalyst /
    # confidence / attractiveness / incumbent / recommended action / falsification / evidence) and COMPOSE
    # the Bundle-2 Integrated Decision contract (B2.10) by reference. They fabricate no verdict and invent
    # no composite score: where a Bundle-2 component is not derivable from persisted state it is UNKNOWN.
    # Every projection is tenant-scoped and rights-gated (fail closed).

    def _read_opportunities(self, customer_id: str, *, as_of: str | None = None) -> list[dict]:
        """This customer's persisted opportunities, point-in-time (no future evidence leaks in at as_of)."""
        try:
            rows = list(_latest(self.mc_store.read("opportunities")).values())
        except Exception:  # noqa: BLE001 — degrade gracefully if the collection is absent
            rows = []
        rows = [o for o in rows if o.get("customer_id") == customer_id]
        if as_of:
            cutoff = str(as_of)
            kept = []
            for o in rows:
                seen = [e.get("first_seen_at") for e in (o.get("evidence") or []) if e.get("first_seen_at")]
                # Known at the cutoff only if some evidence was first seen at/before it (or no evidence times).
                if not seen or min(seen) <= cutoff:
                    kept.append(o)
            rows = kept
        return rows

    def _find_opportunity(self, customer_id: str, opportunity_id: str, *, as_of: str | None = None) -> dict:
        for o in self._read_opportunities(customer_id, as_of=as_of):
            if o.get("id") == opportunity_id:
                return o
        raise ValueError(f"opportunity not found for customer: {opportunity_id}")

    @staticmethod
    def _opp_source_ids(o: dict) -> list[str]:
        return sorted({e.get("source_id") for e in (o.get("evidence") or []) if e.get("source_id")})

    def _display_rights(self, o: dict) -> dict:
        """Source-policy display decision for an opportunity, via the canonical DERIVED-projection gate.

        The opportunity's narrative (title/why-now/recommended action) is Pyrnova-DERIVED, not copied
        source expression, so it is gated on the underlying source POLICY (is customer display permitted?)
        exactly as the Material Changes feed's derived records are — not on the copied-prose heuristic that
        governs verbatim source text. Fails closed to BLOCKED if a source policy denies customer display.
        The raw source facts remain separately inspectable and gated via the Evidence Inspector (B3.6)."""
        from .sources.rights import gate_customer_display
        evidence_map = {e.get("id"): {"source_id": e.get("source_id"), "source_url": e.get("source_url")}
                        for e in (o.get("evidence") or []) if e.get("id")}
        stub = {"id": o.get("id"), "kind": "opportunity",
                "observed": {"agency": o.get("agency")},
                "assessment": {"is_assessment": True},
                "evidence": evidence_map}
        return gate_customer_display(stub, source_ids=self._opp_source_ids(o))["source_rights"]

    def _opportunity_summary(self, o: dict, *, disposition: dict | None = None,
                             pursuit: dict | None = None) -> dict:
        """Rights-gated prioritisation projection of one opportunity (native signals, no new score)."""
        ev = o.get("evidence") or []
        seen = [e.get("first_seen_at") for e in ev if e.get("first_seen_at")]
        cat = o.get("catalyst") or {}
        summary = {
            "id": o.get("id"),
            "title": o.get("title"),
            "agency": o.get("agency"),
            "lifecycle_state": o.get("state"),
            "incumbent": o.get("incumbent"),
            "value_usd": o.get("value_usd"),
            "expected_action_at": o.get("expected_action_at"),
            "why_now": {"kind": cat.get("kind"), "summary": cat.get("summary"),
                        "horizon_days": cat.get("horizon_days"),
                        "detected_by": cat.get("detected_by")},
            "recommended_action": o.get("recommended_action"),
            # Native persisted signals surfaced as-is (labeled) — NOT combined into a fabricated composite.
            "signal": {"attractiveness": o.get("attractiveness"), "confidence": o.get("confidence"),
                       "relevance_score": o.get("relevance_score")},
            "evidence_count": len(ev),
            "evidence_freshness": min(seen) if seen else None,
            # Customer's own disposition (Decision Memory) — distinct from Pyrnova judgment; None if none.
            "customer_disposition": disposition,
            # B4.1 — compact recomputed pursuit verdict (UNKNOWN where evidence is insufficient).
            "pursuit": pursuit or {"verdict": "UNKNOWN"},
            "provenance": "PYRNOVA_DERIVED",
        }
        rights = self._display_rights(o)
        if rights.get("display") == "BLOCKED":
            # Fail closed: retain only stable identifiers + the rights decision.
            return {"id": o.get("id"), "source_rights": rights}
        summary["source_rights"] = rights
        return summary

    def customer_opportunities(self, customer_id: str, *, as_of: str | None = None) -> dict:
        """B3.3 — this customer's opportunity list, prioritisation-ready and tenant-isolated."""
        self._require_access(customer_id)
        from . import decision_memory as dm
        from .customers import get_customer
        from .opportunity_recompute import recompute_decision_components
        rows = self._read_opportunities(customer_id, as_of=as_of)
        disp_by_ref = {d.get("intelligence_ref"): d
                       for d in dm.list_dispositions(self.customer_store, customer_id, as_of=as_of)}
        cp = get_customer(self.customer_store, customer_id) if self.customer_store is not None else None
        items = []
        for o in rows:
            comp = recompute_decision_components(o, customer_profile=cp, as_of=as_of)
            pv = comp.pursuit_verdict
            pursuit = {"verdict": pv.disposition, "confidence": pv.confidence} if pv else {"verdict": "UNKNOWN"}
            items.append(self._opportunity_summary(o, disposition=disp_by_ref.get(o.get("id")), pursuit=pursuit))
        # Deterministic priority order: nearest expected action first, then higher attractiveness.
        items.sort(key=lambda s: (s.get("expected_action_at") or "9999",
                                  -(s.get("signal", {}).get("attractiveness") or 0.0)))
        blocked = any(i.get("source_rights", {}).get("display") == "BLOCKED" for i in items)
        return {
            "customer_id": customer_id, "as_of": as_of, "generated_at": _now(),
            "count": len(items), "opportunities": items,
            "source_rights": {"display": "PARTIAL" if blocked else "ALLOWED",
                              "items": [i.get("source_rights") for i in items]},
        }

    def _mc_touches_opportunity(self, change: dict, o: dict) -> bool:
        refs = change.get("refs") or {}
        subj = (change.get("observed") or {}).get("affected_entity")
        incumbent = (o.get("incumbent") or "").strip().lower()
        if incumbent and subj and incumbent == str(subj).strip().lower():
            return True
        prog = o.get("program_key")
        return bool(prog and refs.get("program") == prog)

    def opportunity_decision(self, customer_id: str, opportunity_id: str, *,
                             as_of: str | None = None) -> dict:
        """B3.4 — the core decision surface for one opportunity, coherently along the canonical chain.

        Surfaces the persisted opportunity's native decision intelligence and COMPOSES the B2.10 Integrated
        Decision contract by reference. Pursuit is presented as the opportunity's persisted recommended
        action + native signals + reversal (falsification); no PURSUE/WATCH/PASS verdict is fabricated when
        the underlying Bundle-2 pursuit inputs are not present in persisted state (they remain UNKNOWN)."""
        self._require_access(customer_id)
        from . import decision_memory as dm
        from .customers import get_customer
        from .decision_object import assemble_decision
        from .opportunity_recompute import recompute_decision_components
        from .sources.rights import gate_customer_display

        o = self._find_opportunity(customer_id, opportunity_id, as_of=as_of)
        cat = o.get("catalyst") or {}
        feed = self.material_changes(customer_id, as_of=as_of)["material_changes"]
        related_mc = [c for c in feed if self._mc_touches_opportunity(c, o)]
        disposition = dm.latest_disposition(self.customer_store, customer_id, opportunity_id, as_of=as_of)

        # B4.1 — deterministically recompute the Bundle-2 verdicts for THIS opportunity from its persisted,
        # accepted evidence (no second engine, no fabrication): each component stays None (UNKNOWN) where
        # the evidence is genuinely insufficient. See pyrnova/opportunity_recompute.py.
        cp = get_customer(self.customer_store, customer_id) if self.customer_store is not None else None
        comp = recompute_decision_components(o, customer_profile=cp, as_of=as_of)

        # Compose the B2.10 Integrated Decision contract by reference, now populated with the recomputed
        # Bundle-2 components where evidence supports them (the object still degrades gracefully to UNKNOWN).
        integrated = assemble_decision(
            opportunity_ref=o.get("id"), program_key=o.get("program_key"),
            material_changes=related_mc, buyer_intelligence=comp.buyer_intelligence,
            competitive_intelligence=comp.competitive_intelligence, vehicle_access=comp.vehicle_access,
            fit_reasoning=comp.fit_reasoning, pursuit_verdict=comp.pursuit_verdict, as_of=as_of).to_record()

        # Per-opportunity decision views derived from the recomputed components (UNKNOWN-safe).
        buyer_view = {"agency": o.get("agency"), "status": "UNKNOWN"}
        if comp.buyer_intelligence is not None:
            buyer_view = {"agency": o.get("agency"), "status": "EVIDENCED",
                          "buyer_intelligence": comp.buyer_intelligence.to_record()}
        competitive_view = {"incumbent": o.get("incumbent"), "relationships": o.get("relationships") or [],
                            "customer_is_incumbent": comp.customer_is_incumbent}
        if comp.competitive_intelligence is not None:
            competitive_view["competitive_intelligence"] = comp.competitive_intelligence.to_record()
        access_view = comp.vehicle_access.to_record() if comp.vehicle_access is not None else {"status": "UNKNOWN"}
        fit_view = {"relevance_score": o.get("relevance_score"),
                    "relevance_reasons": o.get("relevance_reasons") or [],
                    "status": "EVIDENCED" if (comp.fit_reasoning is not None or o.get("relevance_reasons"))
                    else "UNKNOWN"}
        if comp.fit_reasoning is not None:
            fit_view["fit_reasoning"] = comp.fit_reasoning.to_record()
        pursuit_view = {
            "recommended_action": o.get("recommended_action"),
            "native_signal": {"attractiveness": o.get("attractiveness"), "confidence": o.get("confidence")},
            "verdict": "UNKNOWN",
            "reversal_conditions": [o.get("falsification")] if o.get("falsification") else [],
        }
        if comp.pursuit_verdict is not None:
            pv = comp.pursuit_verdict
            pursuit_view.update({"verdict": pv.disposition, "confidence": pv.confidence, "why": pv.why,
                                 "why_not": pv.why_not, "next_actions": pv.next_actions,
                                 "pursuit_verdict": pv.to_record()})
            if pv.reversal_conditions:
                pursuit_view["reversal_conditions"] = pv.reversal_conditions
        unknown_components = [n for n, v in (("buyer_intelligence", comp.buyer_intelligence),
                                             ("competitive_intelligence", comp.competitive_intelligence),
                                             ("vehicle_access", comp.vehicle_access),
                                             ("fit_reasoning", comp.fit_reasoning),
                                             ("pursuit_verdict", comp.pursuit_verdict)) if v is None]

        gated_evidence = [gate_customer_display(e, source_ids=[e.get("source_id")] if e.get("source_id") else None)
                          for e in (o.get("evidence") or [])]
        decision_chain = {
            "opportunity": {"id": o.get("id"), "title": o.get("title"), "agency": o.get("agency"),
                            "lifecycle_state": o.get("state"), "value_usd": o.get("value_usd")},
            "why_now": {"kind": cat.get("kind"), "summary": cat.get("summary"),
                        "horizon_days": cat.get("horizon_days"), "detected_by": cat.get("detected_by"),
                        "expected_action_at": o.get("expected_action_at")},
            "buyer": buyer_view,                       # B2.3 recomputed from persisted evidence (else UNKNOWN)
            "incumbent_competitive": competitive_view,  # B2.4 recomputed from persisted evidence (else UNKNOWN)
            "access": access_view,                      # B2.5 recomputed from persisted evidence (else UNKNOWN)
            "customer_fit": fit_view,                   # B2.6 recomputed from persisted evidence (else UNKNOWN)
            "pursuit": pursuit_view,                    # B2.7 recomputed from persisted evidence (else UNKNOWN)
            "material_changes": [gate_customer_display(c) for c in related_mc],
            "next_action": o.get("recommended_action"),
            "evidence": gated_evidence,
            "temporal": {"as_of": as_of, "expected_action_at": o.get("expected_action_at"),
                         "evidence_first_seen": sorted(
                             [e.get("first_seen_at") for e in (o.get("evidence") or [])
                              if e.get("first_seen_at")])},
            "uncertainty": {"falsification": o.get("falsification"),
                            "confidence": o.get("confidence"),
                            "unknown_components": unknown_components},
            "customer_disposition": disposition,  # Decision Memory (customer judgment), distinct from above
        }
        opp_rights = self._display_rights(o)
        rights_items = [opp_rights] + [e.get("source_rights") for e in gated_evidence]
        rights_items += [c.get("source_rights") for c in decision_chain["material_changes"]]
        blocked = any(r and r.get("display") == "BLOCKED" for r in rights_items)
        if opp_rights.get("display") == "BLOCKED":
            # A source policy denies customer display of this opportunity's basis — fail closed. The
            # recomputed integrated decision carries derived narrative, so it is minimized here too.
            decision_chain = {"opportunity": {"id": o.get("id")}, "source_rights": opp_rights,
                              "customer_disposition": disposition}
            integrated = {"opportunity_ref": o.get("id"), "source_rights": opp_rights}
        return {
            "customer_id": customer_id, "opportunity_id": opportunity_id, "as_of": as_of,
            "generated_at": _now(), "decision_chain": decision_chain,
            "integrated_decision": integrated,
            "source_rights": {"display": "PARTIAL" if blocked else "ALLOWED", "items": rights_items},
        }

    def opportunity_evidence(self, customer_id: str, opportunity_id: str, evidence_id: str, *,
                             as_of: str | None = None) -> dict:
        """B3.6 — inspect one evidence item behind an opportunity, rights-gated (fail closed)."""
        self._require_access(customer_id)
        from .sources.rights import gate_customer_display
        o = self._find_opportunity(customer_id, opportunity_id, as_of=as_of)
        for e in (o.get("evidence") or []):
            if e.get("id") == evidence_id:
                gated = gate_customer_display(e, source_ids=[e.get("source_id")] if e.get("source_id") else None)
                gated["doctrine"] = {"source_fact": e.get("source_id"),
                                     "provenance": {"source_ref": e.get("source_ref"),
                                                    "source_url": e.get("source_url"),
                                                    "content_sha256": e.get("content_sha256"),
                                                    "archive_uri": e.get("archive_uri")},
                                     "observed_at": e.get("first_seen_at") or e.get("published_at"),
                                     "retention_tier": e.get("retention_tier")}
                return gated
        raise ValueError(f"evidence not found on opportunity: {evidence_id}")

    def customer_lens(self, customer_id: str, *, as_of: str | None = None) -> dict:
        """B3.1 — the customer home: what changed, which opportunities matter, and what is uncertain."""
        self._require_access(customer_id)
        identity = self.customer_identity(customer_id) or {"id": customer_id, "name": customer_id}
        changes = self.material_changes(customer_id, as_of=as_of)
        opps = self.customer_opportunities(customer_id, as_of=as_of)
        top = opps["opportunities"][:5]
        uncertain = [{"id": o.get("id"), "title": o.get("title"),
                      "confidence": (o.get("signal") or {}).get("confidence")}
                     for o in opps["opportunities"]
                     if ((o.get("signal") or {}).get("confidence") or 1.0) < 0.6]
        blocked = (changes.get("source_rights", {}).get("display") == "PARTIAL"
                   or opps.get("source_rights", {}).get("display") == "PARTIAL")
        return {
            "customer": identity, "as_of": as_of, "generated_at": _now(),
            "material_changes": {"count": changes.get("count", 0),
                                 "by_disposition": changes.get("by_disposition", {}),
                                 "items": changes.get("material_changes", [])[:5]},
            "opportunities": {"count": opps.get("count", 0), "top": top},
            "uncertainty": {"low_confidence_opportunities": uncertain},
            "source_rights": {"display": "PARTIAL" if blocked else "ALLOWED"},
        }

    def record_opportunity_disposition(self, customer_id: str, opportunity_id: str, *,
                                       relevance: str = "UNKNOWN", novelty: str = "UNKNOWN",
                                       pursuit: str = "UNKNOWN", timing: str = "UNKNOWN",
                                       value: str = "UNKNOWN", important_miss: str = "UNKNOWN",
                                       reason: str = "UNKNOWN", note: str | None = None,
                                       outcome: str = "UNKNOWN") -> dict:
        """B3.8 — record the customer's own disposition on an opportunity into Decision Memory.

        This is CUSTOMER judgment (origin CUSTOMER_FEEDBACK), kept strictly distinct from Pyrnova's
        assessment, and tenant-isolated. The opportunity must be visible to this customer."""
        self._require_access(customer_id)
        from . import decision_memory as dm
        self._find_opportunity(customer_id, opportunity_id)  # tenancy + existence check (raises otherwise)
        disp = dm.Disposition(customer_id=customer_id, intelligence_ref=opportunity_id,
                              relevance=relevance, novelty=novelty, pursuit=pursuit, timing=timing,
                              value=value, important_miss=important_miss, reason=reason, note=note,
                              outcome=outcome)
        return dm.record_disposition(self.customer_store, disp)

    def build_customer_brief(self, customer_id: str, opportunity_id: str, *,
                             as_of: str | None = None) -> dict:
        """B3.10 — a bounded, deterministic, rights-aware decision brief for one opportunity.

        Returns the brief text plus its content hash and rights disposition (for authenticated download and
        for the delivery contract). Restricted source expression is never rendered (fail closed)."""
        import hashlib
        view = self.opportunity_decision(customer_id, opportunity_id, as_of=as_of)
        dc = view["decision_chain"]
        opp = dc["opportunity"]
        rights_display = view["source_rights"]["display"]
        lines = [
            f"PYRNOVA DECISION BRIEF — {opp.get('title') or opp.get('id')}",
            # No generation timestamp in the hashed body: the brief is DETERMINISTIC for a given
            # (customer, opportunity, as-of, underlying data) so its content hash is audit-stable and the
            # delivery contract can dedupe reissues.
            f"Customer: {customer_id}    As-of: {as_of or 'current'}",
            "",
            f"OPPORTUNITY   {opp.get('id')}  ({opp.get('lifecycle_state')})",
            f"Agency:       {opp.get('agency')}",
            f"Est. value:   {opp.get('value_usd')}",
            "",
            f"WHY NOW       {dc['why_now'].get('kind')}: {dc['why_now'].get('summary')}",
            f"Expected action by: {dc['why_now'].get('expected_action_at')}",
            "",
            f"INCUMBENT     {dc['incumbent_competitive'].get('incumbent')}",
            f"CUSTOMER FIT  relevance_score={dc['customer_fit'].get('relevance_score')} "
            f"({dc['customer_fit'].get('status')})",
            "",
            "PURSUIT",
            f"  Recommended: {dc['pursuit'].get('recommended_action')}",
            f"  Native signal: attractiveness={dc['pursuit']['native_signal'].get('attractiveness')} "
            f"confidence={dc['pursuit']['native_signal'].get('confidence')}",
            (f"  Verdict: {dc['pursuit'].get('verdict')} (confidence {dc['pursuit'].get('confidence')})"
             if dc['pursuit'].get('confidence')
             else f"  Verdict: {dc['pursuit'].get('verdict')} (insufficient persisted evidence for a verdict)"),
            "",
            f"MATERIAL CHANGES: {len(dc['material_changes'])} affecting this opportunity",
            "",
            "UNCERTAINTY",
            f"  {dc['uncertainty'].get('falsification')}",
            "",
            f"EVIDENCE: {len(dc['evidence'])} item(s); source-rights display = {rights_display}",
        ]
        body = "\n".join(str(x) for x in lines)
        content_sha256 = hashlib.sha256(body.encode("utf-8")).hexdigest()
        return {
            "customer_id": customer_id, "opportunity_id": opportunity_id, "as_of": as_of,
            "subject": f"Pyrnova brief: {opp.get('title') or opp.get('id')}"[:200],
            "artifact_ref": f"brief:{opportunity_id}:{as_of or 'current'}",
            "body": body, "content_sha256": content_sha256,
            "rights_display": rights_display,
            "filename": f"pyrnova-brief-{opportunity_id}.txt",
        }

    # --- B3.11: customer brief delivery (wires the tenant-safe delivery contract) --------------------

    _DELIVERY_RECIPIENTS_STREAM = "delivery_recipients"

    def authorize_delivery_recipient(self, customer_id: str, email: str, *,
                                     provenance: str = "operator") -> dict:
        """Operator-provisioned: authorize an email to receive this tenant's briefs (append-only)."""
        email = (email or "").strip().lower()
        if not email or "@" not in email:
            raise ValueError("a valid recipient email is required")
        row = {"customer_id": customer_id, "email": email, "provenance": provenance,
               "authorized_at": _now()}
        self.customer_store.append(self._DELIVERY_RECIPIENTS_STREAM, row)
        return row

    def _authorized_recipients(self, customer_id: str) -> list[str]:
        try:
            rows = self.customer_store.read(self._DELIVERY_RECIPIENTS_STREAM)
        except Exception:  # noqa: BLE001
            return []
        return sorted({r.get("email") for r in rows
                       if r.get("customer_id") == customer_id and r.get("email")})

    def deliver_customer_brief(self, customer_id: str, opportunity_id: str, *, recipients,
                               sender: str | None = None, transport=None,
                               as_of: str | None = None, max_attempts: int | None = None) -> dict:
        """B3.11 / B4.3 — deliver a bounded decision brief through the tenant-safe delivery contract.

        Recipients must be operator-authorized for this tenant. When no transport is injected, the
        production transport is resolved from configuration (B4.3): a real SMTP transport when SMTP is
        configured, else an explicit DisabledTransport (the delivery is recorded FAILED, never fabricated
        as delivered, and REAL EXTERNAL DELIVERY VERIFICATION stays an explicit dependency)."""
        self._require_access(customer_id)
        if self.delivery_store is None:
            raise ValueError("customer delivery is not configured (no delivery store)")
        from .config import build_customer_delivery_transport, load_customer_delivery_config
        from .customer_delivery import deliver_customer_brief as _deliver
        cfg = load_customer_delivery_config()
        if transport is None:
            transport = build_customer_delivery_transport(cfg)
        brief = self.build_customer_brief(customer_id, opportunity_id, as_of=as_of)
        return _deliver(
            self.delivery_store, customer_id=customer_id, artifact_ref=brief["artifact_ref"],
            subject=brief["subject"], body=brief["body"], recipients=recipients,
            authorized_recipients=self._authorized_recipients(customer_id),
            sender=sender or cfg.sender, transport=transport, rights_display=brief["rights_display"],
            content_sha256=brief["content_sha256"],
            max_attempts=max_attempts if max_attempts is not None else cfg.max_attempts)

    def list_customer_deliveries(self, customer_id: str) -> dict:
        """B3.11 — this tenant's delivery audit (tenant-isolated)."""
        self._require_access(customer_id)
        rows = self.delivery_store.list_deliveries(customer_id) if self.delivery_store else []
        return {"customer_id": customer_id, "deliveries": rows, "count": len(rows)}

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
                "exposure_join_class": meta.get("exposure_join_class", "candidate"),
                "adverse_event_family": meta.get("adverse_event_family"),
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
                 "exposure_join_class": (t.get("meta") or {}).get("exposure_join_class", "candidate"),
                 "adverse_event_family": (t.get("meta") or {}).get("adverse_event_family"),
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
                 "agency": e.get("agency"),
                 # Federal Register carries publication_date; a contract modification carries action_date.
                 "published": e.get("publication_date") or e.get("action_date") or e.get("available_at"),
                 "catalyst_class": e.get("catalyst_class"),
                 # Deterministic native ids present for the contract-modification family (PIID + UEI).
                 "piid": e.get("piid"), "recipient_uei": e.get("recipient_uei"),
                 "cik": e.get("cik"), "target_ref": e.get("target_ref"),
                 "amount_usd": e.get("amount_usd"), "summary": e.get("summary") or e.get("title"),
                 "source_url": e.get("source_url")}
                for e in events[:25]],
            "relationship_independence": independence or {},
        }

    @staticmethod
    def raw_adverse_event_view(
        parsed_events: dict, relationship_edges: list[dict] | None = None,
        propagation_result: dict | None = None, sec_status: dict | None = None,
    ) -> dict:
        """M21 Operations Panel view (thin, read-only): surface a raw-archived adverse event with its
        raw/archive provenance, deterministic exposure state, relationship path + validity, and
        direct/propagated classification. Pure pass-through of ``adverse_events.parse_*`` +
        ``relationships.ground_*`` + ``propagation.propagate_threats`` output; no store access,
        empty-safe. Functional labels only (Product Language Authority)."""
        parsed_events = parsed_events or {}
        events = parsed_events.get("events", [])
        flagship = events[0] if events else {}
        propagated = (propagation_result or {}).get("propagated_threats", []) or []
        raw_authoritative = False
        try:
            from .sources.registry import get_spec, StorageMode
            source_id = flagship.get("source_id") or flagship.get("source_ref", "").split(":", 1)[0]
            policy = get_spec(str(source_id)).policy
            raw_authoritative = bool(parsed_events.get("archive_hash")) and policy is not None and StorageMode(policy.raw_storage) is StorageMode.RAW_ALLOWED
        except (KeyError, TypeError, ValueError):
            raw_authoritative = False

        def edge_row(e):
            return {"relation": e.get("relation"), "from_ref": e.get("from_ref"),
                    "to_ref": e.get("to_ref"), "link_class": e.get("link_class"),
                    "join_method": e.get("join_method"),
                    "valid_from": e.get("valid_from"), "valid_to": e.get("valid_to"),
                    "native_ids": (e.get("provenance") or {})}

        return {
            "family": parsed_events.get("family"),
            "adverse_event": {
                "event_id": flagship.get("event_id"), "event_type": flagship.get("event_type"),
                "termination_kind": flagship.get("termination_kind"),
                "piid": flagship.get("piid"), "action_date": flagship.get("action_date"),
                "amount_withdrawn_usd": flagship.get("amount_delta_usd"),
                "summary": flagship.get("summary") or flagship.get("title"),
            },
            "raw_provenance": {
                "archive_hash": parsed_events.get("archive_hash"),
                "raw_authoritative_bytes": raw_authoritative,
                "source_ref": flagship.get("source_ref"),
            },
            "deterministic_exposure": {
                "recipient_uei": flagship.get("recipient_uei"), "piid": flagship.get("piid"),
                "join": "deterministic_native_id" if flagship.get("recipient_uei") else None,
            },
            "relationship_path": [edge_row(e) for e in (relationship_edges or [])],
            "direct_threats": max(0, 1 if flagship else 0),
            "propagated_threats": len(propagated),
            "outcome_state": (propagation_result or {}).get("outcome_state", "UNRESOLVED"),
            "sec_source_status": sec_status or {},
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
