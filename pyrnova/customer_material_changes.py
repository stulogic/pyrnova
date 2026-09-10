"""Customer-scoped Material Change store + deterministic fan-out (M22-C).

M22-A proved Pyrnova can *present* intelligence customer-specifically; M22-B persisted *who the customer
is and what they did*. Both still computed the customer's Material Changes on-the-fly from the SHARED
global intelligence streams at read time — customer isolation held at the relevance/overlay layer but not
at the storage boundary. M22-C closes that seam: it materializes a durable, per-customer Material Change
record so a relevant global change becomes customer-scoped stored state, and ordinary reads serve that
state instead of re-projecting shared streams.

Doctrine honored (see ``docs/specs/M22C_CUSTOMER_MATERIAL_CHANGE_STREAMS.md``, D-057, extending D-055/D-056):

* **Global truth stays global; customer-scoped state stays customer-scoped.** Global intelligence
  (``threats`` / ``propagated_threats`` / ``opportunities`` / ``outcomes``) is never duplicated as an
  independent customer-owned truth system and is never mutated by a customer. A customer Material Change
  stores *references* to the underlying global intelligence plus the customer-specific facts that global
  truth does not carry (relevance basis for THIS customer, when it became relevant, when it was delivered,
  a compact assessment snapshot, and delivered outcome state). The prose projection is reconstructed at
  read time from the referenced global record — never stored as authoritative truth (§3).
* **Stable, deterministic identity (§4).** A customer Material Change is keyed by
  ``(customer_id, material_change_id)`` where ``material_change_id`` IS the source intelligence id. It does
  not change on refresh, projection rebuild, lifecycle change, or a revisit. Two customers relevant to the
  same global intelligence share the ``material_change_id`` linkage but keep independent customer-scoped
  rows (relevance basis, first-seen, versions). This preserves the M22-B review-action linkage unchanged.
* **First-seen semantics are explicit and never collapsed (§8).** ``intelligence_observed_at`` (global
  knowability), ``first_relevant_at`` (when it became relevant to THIS customer, temporally correct), and
  ``delivered_at`` (when Pyrnova first materialized it into the customer's feed) are distinct. When the
  customer *reviewed* it is the separate M22-B review lifecycle, joined at read time.
* **Append/version update semantics (§11/§12).** When the underlying global intelligence evolves, a new
  version is appended (``content_version`` + 1) — never a duplicate card, never an in-place rewrite of a
  prior assessment. First-seen fields are carried forward immutably. A later global outcome attaches as a
  new version whose earlier assessment snapshots remain intact, so a future observer can still see what
  Pyrnova originally said, what the customer did, and what subsequently happened.
* **Deterministic, idempotent, replayable fan-out (§5).** Re-running fan-out with unchanged inputs writes
  nothing (content-hash dedupe). Nothing is written for a customer to whom a change is not relevant.
* **Temporal correctness (§7).** Fan-out respects global knowability (``_visible``), the customer profile
  ``effective_from``, and watchlist ``valid_from``/``valid_to`` via the M22-B point-in-time
  :func:`~pyrnova.customers.build_context`. ``first_relevant_at`` never precedes the moment BOTH the
  intelligence was knowable AND the matching customer configuration was in effect.
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import asdict, dataclass, field
from typing import Iterable, Optional

from . import customers as cust
from .customers import (
    WATCH_AGENCY,
    WATCH_CONTRACT,
    WATCH_ENTITY,
    WATCH_PROGRAM,
    _now,
    _parse_dt,
    _stable_id,
    build_context,
    get_customer,
    list_customers,
)
from .material_changes import build_material_changes

log = logging.getLogger("pyrnova.customer_material_changes")

# --- customer-scoped streams (never global intelligence) ---------------------------------------
STREAM_CUSTOMER_MATERIAL_CHANGES = "customer_material_changes"
STREAM_FANOUT_RUNS = "fanout_runs"  # observability (§17): one structured record per fan-out run

SOURCE_KINDS = ("threat", "propagated_threat", "opportunity")

# Version change classification (§11/§12): what a new version records relative to the prior one.
CHANGE_INITIAL = "initial"
CHANGE_ASSESSMENT = "assessment"  # materiality/confidence/mechanism/relevance evolved
CHANGE_OUTCOME = "outcome"        # ONLY the linked outcome state became known/changed


# ------------------------------------------------------------------ the customer-scoped record

@dataclass
class CustomerMaterialChange:
    """One durable, append-only VERSION of a customer-scoped Material Change.

    ``material_change_id`` is the source intelligence id (the stable linkage to global truth and the key
    M22-B review actions already use). ``record_id`` is this version's storage identity. First-seen fields
    (``intelligence_observed_at`` / ``first_relevant_at`` / ``delivered_at``) are set on v1 and carried
    forward immutably. ``assessment_snapshot`` and ``outcome_state`` capture WHAT Pyrnova presented at this
    version — enough to reconstruct "what did we show Customer X at time T, and why" without storing prose
    or duplicating evidence bodies. ``source_refs`` are references, never copies (§3, §19).
    """

    customer_id: str
    material_change_id: str
    source_kind: str
    content_version: int
    content_hash: str
    disposition: str
    relevance_basis: str
    relevance_reasons: list = field(default_factory=list)
    assessment_snapshot: dict = field(default_factory=dict)
    outcome_state: str = "UNKNOWN"
    outcome_ref: Optional[str] = None
    intelligence_observed_at: Optional[str] = None
    first_relevant_at: Optional[str] = None
    delivered_at: str = ""
    last_updated_at: str = ""
    source_refs: dict = field(default_factory=dict)
    change_kind: str = CHANGE_INITIAL
    valid_from: str = ""
    ingest_run_id: Optional[str] = None
    schema_version: str = "cmc_v1"

    def __post_init__(self) -> None:
        if not str(self.customer_id).strip():
            raise ValueError("customer_id is required")
        if not str(self.material_change_id).strip():
            raise ValueError("material_change_id is required")
        if self.source_kind not in SOURCE_KINDS:
            raise ValueError(f"source_kind must be one of {SOURCE_KINDS}")
        if int(self.content_version) < 1:
            raise ValueError("content_version is 1-based")
        if not self.delivered_at:
            self.delivered_at = _now()
        if not self.valid_from:
            self.valid_from = self.delivered_at
        if not self.last_updated_at:
            self.last_updated_at = self.valid_from
        _parse_dt(self.valid_from)

    @property
    def record_id(self) -> str:
        return _stable_id("cmc", {"c": self.customer_id, "m": self.material_change_id,
                                  "v": int(self.content_version)})

    def to_record(self) -> dict:
        d = asdict(self)
        d["record_id"] = self.record_id
        return d


# ------------------------------------------------------------------ content hashing / snapshots

def _assessment_snapshot(projection: dict) -> dict:
    """The compact, assessment-defining fields Pyrnova asserted (NOT prose, NOT evidence bodies)."""
    a = projection.get("assessment") or {}
    return {
        "disposition": projection.get("disposition"),
        "materiality": a.get("materiality"),
        "confidence": a.get("confidence"),
        "mechanism": a.get("mechanism"),
        "lifecycle_state": projection.get("lifecycle_state"),
    }


def _content_hash(projection: dict) -> str:
    """Deterministic hash of the material fields that define a version.

    Includes the assessment snapshot, the customer relevance basis, and the outcome state. A change to any
    of these produces a new version; identical inputs hash identically so re-running fan-out is a no-op.
    """
    payload = {
        "snapshot": _assessment_snapshot(projection),
        "relevance_basis": (projection.get("relevance") or {}).get("basis"),
        "outcome_state": projection.get("outcome_state", "UNKNOWN"),
    }
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()
    return hashlib.sha256(blob).hexdigest()[:24]


def _source_refs(projection: dict) -> dict:
    """References into global truth — never a copy of it (§3, §19)."""
    refs = projection.get("refs") or {}
    prov = projection.get("provenance") or {}
    return {
        "subject_ref": refs.get("subject_ref"),
        "program": refs.get("program"),
        "catalyst_id": refs.get("catalyst_id"),
        "root_change_id": refs.get("root_change_id"),
        "evidence_ids": list(refs.get("evidence_ids") or []),
        "source_ref": prov.get("source_ref"),
        "archive_hash": prov.get("archive_hash"),
    }


def _classify_change(prior: dict, projection: dict) -> str:
    """Decide whether a new version reflects an assessment change or only an outcome change (§12)."""
    prior_snap = prior.get("assessment_snapshot") or {}
    prior_basis = prior.get("relevance_basis")
    new_snap = _assessment_snapshot(projection)
    new_basis = (projection.get("relevance") or {}).get("basis")
    if prior_snap == new_snap and prior_basis == new_basis:
        return CHANGE_OUTCOME  # assessment held; only the linked outcome moved
    return CHANGE_ASSESSMENT


# ------------------------------------------------------------------ temporal: became-relevant time

def _became_relevant_at(projection: dict, *, profile, watch_rows: list[dict],
                        observed_at: Optional[str]) -> Optional[str]:
    """Earliest time the change could have been relevant to THIS customer (temporally correct, §7/§8).

    A change becomes relevant only once BOTH the intelligence is knowable AND a matching customer
    configuration channel is in effect. So ``first_relevant_at = max(intelligence_observed_at,
    earliest matching-config effective_from)``. Profile-borne channels (DIRECT_SUBJECT, CAPABILITY_MATCH,
    agency-of-interest carried on the profile) use ``profile.effective_from``; watch-borne channels use the
    matching watch's ``valid_from``. When several channels match, the earliest wins (it became relevant as
    soon as any qualifying channel was active). The value is never earlier than ``observed_at``.
    """
    reasons = (projection.get("relevance") or {}).get("reasons") or []
    bases = {r.get("basis") for r in reasons}
    refs = projection.get("refs") or {}
    subject = str(refs.get("subject_ref") or "").strip().lower()
    program = str(refs.get("program") or "").strip().lower()
    agency = str((projection.get("observed") or {}).get("agency") or "").strip().lower()

    candidates: list[str] = []
    profile_eff = getattr(profile, "effective_from", None)

    # Profile-borne relevance channels.
    if bases & {"DIRECT_SUBJECT", "CAPABILITY_MATCH"} and profile_eff:
        candidates.append(profile_eff)
    if "AGENCY_INTEREST" in bases and profile_eff:
        prof_agencies = {str(a).strip().lower() for a in (getattr(profile, "agencies", None) or [])}
        if agency and agency in prof_agencies:
            candidates.append(profile_eff)

    # Watch-borne relevance channels: the matching watch's valid_from.
    def _watch_vf(pred) -> None:
        vfs = [w.get("valid_from") for w in watch_rows if pred(w) and w.get("valid_from")]
        if vfs:
            candidates.append(min(vfs))

    if "WATCHED_ENTITY" in bases:
        # The subject may be watched directly, or a watched entity may lie on the propagation path. We do
        # not always have the path refs on the projection, so fall back to the earliest active ENTITY watch
        # (never earlier than when the customer actually held a watch — temporally safe).
        matched = [w for w in watch_rows
                   if w.get("object_type") == WATCH_ENTITY
                   and str(w.get("ref") or "").strip().lower() == subject and w.get("valid_from")]
        if matched:
            candidates.append(min(w["valid_from"] for w in matched))
        else:
            _watch_vf(lambda w: w.get("object_type") == WATCH_ENTITY)
    if "WATCHED_PROGRAM" in bases:
        matched = [w for w in watch_rows
                   if w.get("object_type") in (WATCH_PROGRAM, WATCH_CONTRACT)
                   and str(w.get("ref") or "").strip().lower() == program and w.get("valid_from")]
        if matched:
            candidates.append(min(w["valid_from"] for w in matched))
        else:
            _watch_vf(lambda w: w.get("object_type") in (WATCH_PROGRAM, WATCH_CONTRACT))
    if "AGENCY_INTEREST" in bases:
        _watch_vf(lambda w: w.get("object_type") == WATCH_AGENCY
                  and str(w.get("ref") or "").strip().lower() == agency)

    config_eff = min(candidates) if candidates else profile_eff
    times = [t for t in (observed_at, config_eff) if t]
    if not times:
        return None
    return max(times, key=lambda t: _parse_dt(t))


# ------------------------------------------------------------------ store reads

def _latest_versions(cmc_store, customer_id: str, *, as_of: Optional[str] = None) -> dict[str, dict]:
    """Latest customer Material Change version per ``material_change_id`` for one customer.

    Storage-level isolation: rows for other customers are never returned. ``as_of`` selects the latest
    version whose ``valid_from`` is at or before the cutoff (point-in-time reconstruction, §12/§10).
    """
    cutoff = _parse_dt(as_of) if as_of is not None else None
    latest: dict[str, dict] = {}
    for r in cmc_store.read(STREAM_CUSTOMER_MATERIAL_CHANGES):
        if r.get("customer_id") != customer_id:
            continue
        if cutoff is not None:
            vf = r.get("valid_from")
            if vf and _parse_dt(vf) > cutoff:
                continue
        mid = r.get("material_change_id")
        if not mid:
            continue
        cur = latest.get(mid)
        if cur is None or int(r.get("content_version", 0)) >= int(cur.get("content_version", 0)):
            latest[mid] = r
    return latest


def version_history(cmc_store, customer_id: str, material_change_id: str) -> list[dict]:
    """All stored versions of one customer Material Change, oldest first (append/version audit, §12)."""
    rows = [r for r in cmc_store.read(STREAM_CUSTOMER_MATERIAL_CHANGES)
            if r.get("customer_id") == customer_id and r.get("material_change_id") == material_change_id]
    rows.sort(key=lambda r: (int(r.get("content_version", 0)), r.get("_ts") or ""))
    return rows


# ------------------------------------------------------------------ fan-out / ingestion (§5)

def _read_latest_global(store, name: str) -> list[dict]:
    """Latest record per id from a global stream, empty-safe."""
    latest: dict[str, dict] = {}
    try:
        for r in store.read(name):
            rid = r.get("id")
            if rid:
                latest[str(rid)] = r
    except Exception:  # noqa: BLE001 — degrade gracefully if the collection is absent
        return []
    return list(latest.values())


def fan_out(
    *,
    mc_store,
    customer_store,
    cmc_store,
    customer_ids: Optional[Iterable[str]] = None,
    as_of: Optional[str] = None,
    run_id: Optional[str] = None,
    now: Optional[str] = None,
) -> dict:
    """Fan new/updated global intelligence into customer-scoped Material Change state (§5).

    Deterministic, idempotent, replayable, temporally correct, per-customer failure-isolated. For each
    customer, builds its point-in-time relevance context (M22-B) and projects the SAME relevant changes the
    read model would, then upserts a customer-scoped record per relevant change:

    * no existing record  → append v1 (``delivered_at`` = now, ``first_relevant_at`` computed);
    * unchanged content   → suppressed as a duplicate (nothing written);
    * changed content     → append a new version, carrying first-seen fields forward immutably.

    Nothing is written for a customer to whom a change is not relevant. A malformed customer or one failed
    relevance evaluation is recorded and skipped; it never corrupts global or other-customer state (§18).
    Returns a structured observability report (also appended to ``fanout_runs`` and logged, §17).
    """
    now = now or _now()
    run_id = run_id or _stable_id("fanrun", {"at": now})

    threats = _read_latest_global(mc_store, "threats")
    propagated = _read_latest_global(mc_store, "propagated_threats")
    all_opportunities = _read_latest_global(mc_store, "opportunities")

    global_item_count = len(threats) + len(propagated) + len(all_opportunities)
    customer_list = (list(customer_ids) if customer_ids is not None
                     else [c["id"] for c in list_customers(customer_store)])

    per_customer: list[dict] = []
    failures: list[dict] = []
    totals = {"inserted": 0, "updated": 0, "duplicates_suppressed": 0,
              "relevant": 0, "suppressed_irrelevant": 0}

    for cid in customer_list:
        c_stats = {"customer_id": cid, "evaluated": 0, "relevant": 0, "suppressed_irrelevant": 0,
                   "inserted": 0, "updated": 0, "duplicates_suppressed": 0}
        try:
            profile = get_customer(customer_store, cid, as_of=as_of)
            if profile is None:
                raise ValueError(f"customer not found: {cid}")
            ctx = build_context(customer_store, cid, as_of=as_of)
            watch_rows = cust._active_watches(customer_store, cid, as_of=as_of)
        except Exception as exc:  # noqa: BLE001 — fail this customer only; continue safely (§18)
            failures.append({"customer_id": cid, "stage": "context", "error": str(exc)})
            per_customer.append(c_stats)
            continue

        opps = [o for o in all_opportunities if o.get("customer_id") == cid]
        # The read model is the single source of the relevant/visible/projected set — fan-out persists
        # exactly what a read would present, so the persisted path and the on-the-fly path never diverge.
        try:
            projected = build_material_changes(
                threats=threats, propagated_threats=propagated, opportunities=opps,
                context=ctx, as_of=as_of)
        except Exception as exc:  # noqa: BLE001 — a bad projection fails this customer only (§18)
            failures.append({"customer_id": cid, "stage": "project", "error": str(exc)})
            per_customer.append(c_stats)
            continue

        c_stats["evaluated"] = global_item_count
        c_stats["suppressed_irrelevant"] = max(0, global_item_count - len(projected))
        existing = _latest_versions(cmc_store, cid)

        for projection in projected:
            try:
                mid = projection["id"]
                c_stats["relevant"] += 1
                chash = _content_hash(projection)
                prior = existing.get(mid)
                observed_at = projection.get("available_at") or (projection.get("observed") or {}).get("observed_at")
                snapshot = _assessment_snapshot(projection)
                relevance = projection.get("relevance") or {}

                if prior is None:
                    row = CustomerMaterialChange(
                        customer_id=cid, material_change_id=mid,
                        source_kind=projection.get("kind", "threat"),
                        content_version=1, content_hash=chash,
                        disposition=projection.get("disposition"),
                        relevance_basis=relevance.get("basis"),
                        relevance_reasons=relevance.get("reasons") or [],
                        assessment_snapshot=snapshot,
                        outcome_state=projection.get("outcome_state", "UNKNOWN"),
                        intelligence_observed_at=observed_at,
                        first_relevant_at=_became_relevant_at(
                            projection, profile=profile, watch_rows=watch_rows, observed_at=observed_at),
                        delivered_at=now, last_updated_at=now, valid_from=now,
                        source_refs=_source_refs(projection),
                        change_kind=CHANGE_INITIAL, ingest_run_id=run_id)
                    cmc_store.append(STREAM_CUSTOMER_MATERIAL_CHANGES, row.to_record())
                    existing[mid] = row.to_record()
                    c_stats["inserted"] += 1
                elif prior.get("content_hash") == chash:
                    c_stats["duplicates_suppressed"] += 1
                else:
                    row = CustomerMaterialChange(
                        customer_id=cid, material_change_id=mid,
                        source_kind=prior.get("source_kind", projection.get("kind", "threat")),
                        content_version=int(prior.get("content_version", 1)) + 1, content_hash=chash,
                        disposition=projection.get("disposition"),
                        relevance_basis=relevance.get("basis"),
                        relevance_reasons=relevance.get("reasons") or [],
                        assessment_snapshot=snapshot,
                        outcome_state=projection.get("outcome_state", "UNKNOWN"),
                        # First-seen fields are immutable: carry them forward from the original delivery.
                        intelligence_observed_at=prior.get("intelligence_observed_at"),
                        first_relevant_at=prior.get("first_relevant_at"),
                        delivered_at=prior.get("delivered_at"),
                        last_updated_at=now, valid_from=now,
                        source_refs=_source_refs(projection),
                        change_kind=_classify_change(prior, projection), ingest_run_id=run_id)
                    cmc_store.append(STREAM_CUSTOMER_MATERIAL_CHANGES, row.to_record())
                    existing[mid] = row.to_record()
                    c_stats["updated"] += 1
            except Exception as exc:  # noqa: BLE001 — one bad item fails that item only (§18)
                failures.append({"customer_id": cid,
                                 "material_change_id": projection.get("id"),
                                 "stage": "upsert", "error": str(exc)})

        for k in ("inserted", "updated", "duplicates_suppressed", "relevant", "suppressed_irrelevant"):
            totals[k] += c_stats[k]
        per_customer.append(c_stats)

    report = {
        "run_id": run_id,
        "at": now,
        "as_of": as_of,
        "global_items_evaluated": global_item_count,
        "customers": len(customer_list),
        "inserted": totals["inserted"],
        "updated": totals["updated"],
        "duplicates_suppressed": totals["duplicates_suppressed"],
        "relevant": totals["relevant"],
        "suppressed_irrelevant": totals["suppressed_irrelevant"],
        "failures": failures,
        "failure_count": len(failures),
        "per_customer": per_customer,
    }
    try:
        cmc_store.append(STREAM_FANOUT_RUNS, report)
    except Exception:  # noqa: BLE001 — observability write must never break the fan-out itself
        pass
    log.info("fan_out run=%s customers=%d evaluated=%d inserted=%d updated=%d dup=%d failures=%d",
             run_id, len(customer_list), global_item_count, totals["inserted"], totals["updated"],
             totals["duplicates_suppressed"], len(failures))
    return report


def rebuild_customer(*, mc_store, customer_store, cmc_store, customer_id: str,
                     as_of: Optional[str] = None, now: Optional[str] = None) -> dict:
    """Rebuild one customer's derived Material Change state (§10).

    Re-runs fan-out for a single customer. Because fan-out is content-hash idempotent, a rebuild over
    unchanged global truth appends nothing. Customer *actions* (the M22-B review/lifecycle stream) are a
    SEPARATE stream keyed by the stable ``material_change_id`` and are never touched here, so rebuilding
    derived projections never erases customer history.
    """
    return fan_out(mc_store=mc_store, customer_store=customer_store, cmc_store=cmc_store,
                   customer_ids=[customer_id], as_of=as_of, now=now)


__all__ = [
    "CustomerMaterialChange",
    "STREAM_CUSTOMER_MATERIAL_CHANGES", "STREAM_FANOUT_RUNS", "SOURCE_KINDS",
    "CHANGE_INITIAL", "CHANGE_ASSESSMENT", "CHANGE_OUTCOME",
    "fan_out", "rebuild_customer", "version_history",
    "_latest_versions", "_content_hash", "_became_relevant_at",
]
