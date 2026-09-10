"""Persisted customer intelligence, tenancy boundary, and Material Change lifecycle (M22-B).

M22-A proved Pyrnova can *present* intelligence customer-specifically from a deterministic read model,
but its customer configuration lived in committed demo fixtures. M22-B moves the customer-facing product
off that demo seam: it persists the minimum durable customer model, watchlists, and per-customer Material
Change review/lifecycle state, and reconstructs a point-in-time :class:`CustomerContext` from that
persisted state so ordinary reads no longer depend on demo-only configuration.

Doctrine honored (see ``docs/specs/M22B_PERSISTED_CUSTOMER_LIFECYCLE.md``, D-056, and the M22-A doctrine
it extends):

* **Global vs customer-private boundary.** Customer configuration, watchlists, relevance inputs, and
  review/lifecycle state are *customer-private*. They are written ONLY to customer-scoped streams and are
  never written back into Pyrnova's global intelligence streams (``threats`` / ``propagated_threats`` /
  ``exposures`` / ``relationships``). A customer-private fact can never silently become global truth.
* **System assessment ≠ customer review state.** A customer dismissing or resolving a Material Change
  records a *customer review state* in a separate append-only stream; it never rewrites Pyrnova's
  historical system assessment. This is not a second intelligence verdict system.
* **Tenancy isolation.** Every record is keyed by ``customer_id``; a customer may only act on a Material
  Change that is actually relevant/visible to it, and never on another customer's changes.
* **Temporal truth for configuration.** A watchlist entry carries ``valid_from`` and a customer profile
  version carries ``effective_from``; point-in-time reconstruction uses only configuration knowable at the
  cutoff, so a watch added today does not imply the customer was monitoring the entity months ago.
* **Auditability.** Configuration and review state are append-only and timestamped; history is
  reconstructable (previous state → new state → time → customer → actor), never destructively overwritten.
* **No arbitrary canonicalization.** A free-text watchlist ref is preserved honestly as *unresolved*; it
  never silently becomes a canonical Pyrnova entity.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Iterable, Optional

from .material_changes import CustomerContext

# --- stream names (customer-private; never global intelligence) --------------------------------
STREAM_CUSTOMERS = "customers"
STREAM_WATCHLIST = "customer_watchlist"
STREAM_REVIEW_ACTIONS = "customer_review_actions"

# Global intelligence streams that customer-private writes must NEVER touch (used by the boundary test
# and documented here as the authoritative list).
GLOBAL_INTELLIGENCE_STREAMS = (
    "threats", "propagated_threats", "exposures", "relationships",
    "beneficiary_opportunities", "threat_rejections", "threat_outcomes",
)

# --- watchlist object types -> relevance channel ----------------------------------------------
WATCH_ENTITY = "ENTITY"
WATCH_PROGRAM = "PROGRAM"
WATCH_CONTRACT = "CONTRACT"   # a specific award/contract; matched as a program identifier
WATCH_AGENCY = "AGENCY"
WATCH_OBJECT_TYPES = (WATCH_ENTITY, WATCH_PROGRAM, WATCH_CONTRACT, WATCH_AGENCY)

# --- Material Change customer review lifecycle -------------------------------------------------
# CUSTOMER review state — orthogonal to the SYSTEM lifecycle_state carried on the threat record.
STATE_NEW = "NEW"
STATE_REVIEWED = "REVIEWED"
STATE_MONITORING = "MONITORING"
STATE_INVESTIGATING = "INVESTIGATING"
STATE_DISMISSED = "DISMISSED"
STATE_RESOLVED = "RESOLVED"
REVIEW_STATES = (
    STATE_NEW, STATE_REVIEWED, STATE_MONITORING, STATE_INVESTIGATING, STATE_DISMISSED, STATE_RESOLVED,
)

# Action -> resulting customer review state. Actions are the audit trail; state is the fold over them.
ACTION_TO_STATE = {
    "MARK_REVIEWED": STATE_REVIEWED,
    "MONITOR": STATE_MONITORING,
    "RECORD_INVESTIGATION": STATE_INVESTIGATING,
    "RECORD_ACTION": STATE_INVESTIGATING,
    "DISMISS": STATE_DISMISSED,
    "REJECT": STATE_DISMISSED,
    "RESOLVE": STATE_RESOLVED,
    "REOPEN": STATE_NEW,
}
REVIEW_ACTIONS = tuple(ACTION_TO_STATE)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_dt(value: str) -> datetime:
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _stable_id(prefix: str, payload: dict, length: int = 20) -> str:
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return f"{prefix}_" + hashlib.sha256(blob).hexdigest()[:length]


_SLUG_RE = re.compile(r"[^a-z0-9]+")


def _slug(value: str) -> str:
    return _SLUG_RE.sub("-", str(value).strip().lower()).strip("-")


# A ref "looks canonical" if it is one of Pyrnova's structured identifier shapes: an internal entity ref
# (``co_*``), a UEI-bearing entity ref (``co_uei_*``), or a source-native program/contract identifier
# (PIID-like: uppercase alnum, length >= 6). This is a conservative honesty check, NOT entity resolution.
_CANONICAL_ENTITY_RE = re.compile(r"^co_[a-z0-9_]+$", re.IGNORECASE)
_PIID_RE = re.compile(r"^[A-Z0-9][A-Z0-9._-]{5,}$")


def _looks_canonical(object_type: str, ref: str) -> bool:
    ref = str(ref or "").strip()
    if not ref:
        return False
    if object_type == WATCH_ENTITY:
        return bool(_CANONICAL_ENTITY_RE.match(ref))
    if object_type in (WATCH_PROGRAM, WATCH_CONTRACT):
        return bool(_PIID_RE.match(ref))
    if object_type == WATCH_AGENCY:
        return True  # agency-of-interest is a monitoring channel, matched by name; always "resolved"
    return False


# ------------------------------------------------------------------ customer profile

@dataclass
class CustomerProfile:
    """The minimum durable per-customer intelligence configuration Phase 1 needs.

    Reuses M22-A's structured relevance inputs (``entity_refs`` / ``capabilities`` / ``agencies`` /
    ``sectors``) and adds durable identity, provenance, and temporal semantics. Watchlists live in a
    SEPARATE stream (:class:`WatchlistEntry`) so they carry independent provenance, resolution status,
    and ``valid_from`` temporal semantics. This is not a CRM, a tenant schema, or billing.
    """

    customer_id: str
    name: str
    entity_refs: list[str] = field(default_factory=list)
    capabilities: list[str] = field(default_factory=list)
    agencies: list[str] = field(default_factory=list)
    sectors: list[str] = field(default_factory=list)
    geography: list[str] = field(default_factory=list)
    provenance: str = "operator"
    effective_from: Optional[str] = None
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)

    def __post_init__(self) -> None:
        if not str(self.customer_id).strip():
            raise ValueError("customer_id is required")
        if not str(self.name).strip():
            raise ValueError("customer name is required")
        if self.effective_from is None:
            self.effective_from = self.created_at
        _parse_dt(self.effective_from)  # validate

    def to_record(self) -> dict:
        return asdict(self)


def _record_to_profile(rec: dict) -> CustomerProfile:
    allowed = set(CustomerProfile.__dataclass_fields__)
    return CustomerProfile(**{k: v for k, v in rec.items() if k in allowed})


def upsert_customer(store, profile: CustomerProfile) -> dict:
    """Append a customer profile *version* (append-only; the latest effective version wins).

    Never destructively overwrites: an update appends a new version with a new ``updated_at``, so profile
    history is auditable and point-in-time reconstructable via :func:`build_context`.
    """
    profile.updated_at = _now()
    row = profile.to_record()
    store.append(STREAM_CUSTOMERS, row)
    return row


def get_customer(store, customer_id: str, *, as_of: Optional[str] = None) -> Optional[CustomerProfile]:
    """Return the customer profile version effective as of ``as_of`` (latest if ``as_of`` is None)."""
    versions = [r for r in store.read(STREAM_CUSTOMERS) if r.get("customer_id") == customer_id]
    if as_of is not None:
        cutoff = _parse_dt(as_of)
        versions = [r for r in versions if _parse_dt(r.get("effective_from") or r.get("_ts")) <= cutoff]
    if not versions:
        return None
    versions.sort(key=lambda r: (r.get("effective_from") or r.get("_ts") or "", r.get("_ts") or ""))
    return _record_to_profile(versions[-1])


def list_customers(store) -> list[dict]:
    """List current customers (latest version per id), id + name, deterministic order."""
    latest: dict[str, dict] = {}
    order: dict[str, tuple] = {}
    for r in store.read(STREAM_CUSTOMERS):
        cid = r.get("customer_id")
        if not cid:
            continue
        key = (r.get("effective_from") or r.get("_ts") or "", r.get("_ts") or "")
        if cid not in order or key >= order[cid]:
            latest[cid], order[cid] = r, key
    return [{"id": cid, "name": latest[cid].get("name", cid)} for cid in sorted(latest)]


# ------------------------------------------------------------------ watchlist

@dataclass
class WatchlistEntry:
    """One persisted watched object for a customer (entity, program, contract, or agency).

    ``resolved`` records honestly whether ``ref`` matches a canonical Pyrnova identifier shape; a
    free-text ref is preserved as unresolved and never silently canonicalized. ``valid_from`` /
    ``valid_to`` give the watch temporal semantics so historical replay does not leak a watch backward.
    """

    customer_id: str
    object_type: str
    ref: str
    label: str = ""
    valid_from: Optional[str] = None
    valid_to: Optional[str] = None
    provenance: str = "operator"
    added_at: str = field(default_factory=_now)
    resolved: Optional[bool] = None
    resolution_note: str = ""

    def __post_init__(self) -> None:
        if not str(self.customer_id).strip():
            raise ValueError("customer_id is required")
        self.object_type = str(self.object_type or "").strip().upper()
        if self.object_type not in WATCH_OBJECT_TYPES:
            raise ValueError(f"object_type must be one of {WATCH_OBJECT_TYPES}")
        if not str(self.ref).strip():
            raise ValueError("watchlist ref is required (arbitrary empty refs are rejected)")
        self.ref = str(self.ref).strip()
        if self.valid_from is None:
            self.valid_from = self.added_at
        _parse_dt(self.valid_from)
        if self.valid_to is not None:
            _parse_dt(self.valid_to)
        if self.resolved is None:
            self.resolved = _looks_canonical(self.object_type, self.ref)
            if not self.resolved and not self.resolution_note:
                self.resolution_note = (
                    "ref does not match a canonical Pyrnova identifier; matched literally, "
                    "not treated as a resolved canonical entity"
                )

    @property
    def id(self) -> str:
        return _stable_id("watch", {"c": self.customer_id, "t": self.object_type,
                                    "r": self.ref.lower(), "vf": self.valid_from})

    def to_record(self) -> dict:
        d = asdict(self)
        d["id"] = self.id
        return d


def add_watch(store, entry: WatchlistEntry) -> dict:
    """Append a watchlist entry (append-only; idempotent per (customer, type, ref, valid_from))."""
    row = entry.to_record()
    existing = {r.get("id") for r in store.read(STREAM_WATCHLIST)}
    if row["id"] not in existing:
        store.append(STREAM_WATCHLIST, row)
    return row


def retire_watch(store, customer_id: str, watch_id: str, *, at: Optional[str] = None) -> dict:
    """Retire a watch by appending a ``valid_to`` closure record (append-only; no destructive delete).

    Preserves history: the original add stays; a closure marks the watch inactive from ``at`` onward so
    point-in-time replay before ``at`` still sees the watch. Rejects a watch owned by another customer.
    """
    at = at or _now()
    _parse_dt(at)
    entries = [r for r in store.read(STREAM_WATCHLIST) if r.get("id") == watch_id]
    if not entries:
        raise ValueError(f"watch not found: {watch_id}")
    owner = entries[-1].get("customer_id")
    if owner != customer_id:
        raise ValueError("cross-customer access rejected: watch belongs to a different customer")
    closure = dict(entries[-1])
    closure["valid_to"] = at
    closure["retired_at"] = at
    store.append(STREAM_WATCHLIST, closure)
    return closure


def _active_watches(store, customer_id: str, *, as_of: Optional[str] = None) -> list[dict]:
    """Watchlist entries for a customer that are temporally valid as of ``as_of`` (latest per id).

    A watch is valid when ``valid_from <= as_of`` and (``valid_to`` is unset or ``as_of < valid_to``).
    Latest record per watch id wins, so a retirement closure supersedes the original add.
    """
    latest: dict[str, dict] = {}
    for r in store.read(STREAM_WATCHLIST):
        if r.get("customer_id") != customer_id:
            continue
        wid = r.get("id")
        if wid:
            latest[wid] = r  # append-only; last write wins (closure supersedes add)
    cutoff = _parse_dt(as_of) if as_of is not None else None
    out = []
    for r in latest.values():
        if cutoff is not None:
            vf = r.get("valid_from")
            if vf and _parse_dt(vf) > cutoff:
                continue  # watch not yet in effect at the cutoff — no retrospective leakage
            vt = r.get("valid_to")
            if vt and _parse_dt(vt) <= cutoff:
                continue  # watch retired at/before the cutoff
        else:
            if r.get("valid_to"):
                continue  # currently retired
        out.append(r)
    return out


def list_watches(store, customer_id: str, *, as_of: Optional[str] = None) -> list[dict]:
    """Public read of a customer's active watches (deterministic order)."""
    return sorted(_active_watches(store, customer_id, as_of=as_of),
                  key=lambda r: (r.get("object_type", ""), r.get("ref", "")))


# ------------------------------------------------------------------ point-in-time context assembly

def build_context(store, customer_id: str, *, as_of: Optional[str] = None) -> CustomerContext:
    """Assemble a deterministic :class:`CustomerContext` from PERSISTED customer state, point-in-time.

    Merges the customer profile version effective at ``as_of`` with the watchlist entries valid at
    ``as_of``. This is the M22-B replacement for reading a demo JSON context: ordinary Material Changes
    reads run against persisted customer state, and historical replay reconstructs exactly what the
    customer was configured to monitor at the cutoff (no retrospective watchlist leakage).
    """
    profile = get_customer(store, customer_id, as_of=as_of)
    if profile is None:
        raise ValueError(f"customer not found: {customer_id}")

    watched_entities: list[str] = []
    watched_programs: list[str] = []
    agencies: list[str] = list(profile.agencies)
    for w in _active_watches(store, customer_id, as_of=as_of):
        otype, ref = w.get("object_type"), w.get("ref")
        if otype == WATCH_ENTITY:
            watched_entities.append(ref)
        elif otype in (WATCH_PROGRAM, WATCH_CONTRACT):
            watched_programs.append(ref)
        elif otype == WATCH_AGENCY:
            agencies.append(ref)

    return CustomerContext(
        customer_id=profile.customer_id,
        name=profile.name,
        entity_refs=list(profile.entity_refs),
        watched_entity_refs=sorted(set(watched_entities)),
        watched_programs=sorted(set(watched_programs)),
        agencies=sorted(set(agencies)),
        capabilities=list(profile.capabilities),
        sectors=list(profile.sectors),
    )


# ------------------------------------------------------------------ Material Change review lifecycle

@dataclass
class ReviewAction:
    """One customer review/lifecycle action on a Material Change (append-only audit record).

    This is CUSTOMER review state, kept strictly separate from Pyrnova's system assessment. It records
    the transition (``from_state`` → ``to_state``), the actor (a placeholder id compatible with later
    auth), an optional structured reason/note, and an optional ``outcome_ref`` linking a resolution to an
    existing Pyrnova outcome — preserving the intelligence → saw → reviewed → acted → outcome lineage.
    """

    customer_id: str
    material_change_id: str
    action_type: str
    from_state: str
    to_state: str
    actor: str = "operator"
    reason: str = ""
    note: str = ""
    outcome_ref: Optional[str] = None
    at: str = field(default_factory=_now)

    def __post_init__(self) -> None:
        if not str(self.customer_id).strip():
            raise ValueError("customer_id is required")
        if not str(self.material_change_id).strip():
            raise ValueError("material_change_id is required")
        self.action_type = str(self.action_type or "").strip().upper()
        if self.action_type not in ACTION_TO_STATE:
            raise ValueError(f"action_type must be one of {REVIEW_ACTIONS}")
        _parse_dt(self.at)

    @property
    def id(self) -> str:
        return _stable_id("rev", {"c": self.customer_id, "m": self.material_change_id,
                                  "a": self.action_type, "at": self.at, "actor": self.actor})

    def to_record(self) -> dict:
        d = asdict(self)
        d["id"] = self.id
        return d


def _actions_for(store, customer_id: str, material_change_id: str, *,
                 as_of: Optional[str] = None) -> list[dict]:
    rows = [r for r in store.read(STREAM_REVIEW_ACTIONS)
            if r.get("customer_id") == customer_id and r.get("material_change_id") == material_change_id]
    if as_of is not None:
        cutoff = _parse_dt(as_of)
        rows = [r for r in rows if _parse_dt(r.get("at") or r.get("_ts")) <= cutoff]
    rows.sort(key=lambda r: (r.get("at") or r.get("_ts") or "", r.get("_ts") or ""))
    return rows


def current_review_state(store, customer_id: str, material_change_id: str, *,
                         as_of: Optional[str] = None) -> str:
    """Fold the append-only action log to the current customer review state (NEW by default)."""
    actions = _actions_for(store, customer_id, material_change_id, as_of=as_of)
    return actions[-1]["to_state"] if actions else STATE_NEW


def review_history(store, customer_id: str, material_change_id: str, *,
                   as_of: Optional[str] = None) -> list[dict]:
    """Full ordered review history for one Material Change (point-in-time reconstructable)."""
    return _actions_for(store, customer_id, material_change_id, as_of=as_of)


def record_review_action(
    store,
    *,
    customer_id: str,
    material_change_id: str,
    action_type: str,
    actor: str = "operator",
    reason: str = "",
    note: str = "",
    outcome_ref: Optional[str] = None,
    at: Optional[str] = None,
    visible_change_ids: Optional[Iterable[str]] = None,
) -> dict:
    """Record one customer review action (append-only), returning the action and resulting state.

    Tenancy: if ``visible_change_ids`` is supplied (the ids of the changes actually relevant/visible to
    this customer), the ``material_change_id`` MUST be in it — a customer can never act on another
    customer's Material Change. The action is appended with the computed ``from_state`` → ``to_state``
    transition; the append-only log is the audit trail and never destructively overwrites prior state.
    """
    if visible_change_ids is not None and material_change_id not in set(visible_change_ids):
        raise ValueError(
            "cross-customer access rejected: material change is not visible to this customer")
    at = at or _now()
    from_state = current_review_state(store, customer_id, material_change_id)
    action = ReviewAction(
        customer_id=customer_id, material_change_id=material_change_id,
        action_type=action_type, from_state=from_state,
        to_state=ACTION_TO_STATE[str(action_type).strip().upper()],
        actor=actor, reason=reason, note=note, outcome_ref=outcome_ref, at=at)
    row = action.to_record()
    store.append(STREAM_REVIEW_ACTIONS, row)
    return {"action": row, "from_state": from_state, "to_state": row["to_state"]}


def review_overlay(store, customer_id: str, *, as_of: Optional[str] = None) -> dict[str, dict]:
    """Current review state + last action per Material Change for a customer (for the read overlay)."""
    by_change: dict[str, list[dict]] = {}
    for r in store.read(STREAM_REVIEW_ACTIONS):
        if r.get("customer_id") != customer_id:
            continue
        if as_of is not None and _parse_dt(r.get("at") or r.get("_ts")) > _parse_dt(as_of):
            continue
        by_change.setdefault(r.get("material_change_id"), []).append(r)
    overlay: dict[str, dict] = {}
    for mid, actions in by_change.items():
        actions.sort(key=lambda r: (r.get("at") or r.get("_ts") or "", r.get("_ts") or ""))
        last = actions[-1]
        overlay[mid] = {
            "state": last["to_state"],
            "action_count": len(actions),
            "last_action": {
                "action_type": last.get("action_type"), "actor": last.get("actor"),
                "at": last.get("at"), "reason": last.get("reason"), "note": last.get("note"),
                "outcome_ref": last.get("outcome_ref"),
            },
        }
    return overlay


__all__ = [
    "CustomerProfile", "WatchlistEntry", "ReviewAction", "CustomerContext",
    "STREAM_CUSTOMERS", "STREAM_WATCHLIST", "STREAM_REVIEW_ACTIONS",
    "GLOBAL_INTELLIGENCE_STREAMS",
    "WATCH_OBJECT_TYPES", "WATCH_ENTITY", "WATCH_PROGRAM", "WATCH_CONTRACT", "WATCH_AGENCY",
    "REVIEW_STATES", "REVIEW_ACTIONS", "ACTION_TO_STATE",
    "STATE_NEW", "STATE_REVIEWED", "STATE_MONITORING", "STATE_INVESTIGATING",
    "STATE_DISMISSED", "STATE_RESOLVED",
    "upsert_customer", "get_customer", "list_customers",
    "add_watch", "retire_watch", "list_watches",
    "build_context", "record_review_action", "current_review_state", "review_history",
    "review_overlay",
]
