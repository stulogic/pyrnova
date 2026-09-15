"""Customer Usefulness Ledger / Decision Memory (PRELAUNCH-CONVERGENCE-001 · B1.4).

The smallest canonical customer disposition/outcome layer for Phase 1 — NOT a CRM, pipeline,
task system, or account-management suite.

For each *delivered* intelligence object a customer may record a durable, append-only disposition:
NOVELTY, RELEVANCE, PURSUIT DECISION, TIMING, VALUE, IMPORTANT MISS, a bounded REASON (+ optional
note), and an EVENTUAL OUTCOME. Every field is an explicit vocabulary with `UNKNOWN` for
genuinely-not-provided — unknown never silently becomes a real value.

Invariants (mirroring the M22-B customer-private architecture in :mod:`pyrnova.customers`):

* **Customer-private + isolated.** Dispositions live in a customer-scoped stream and are NEVER written
  into Pyrnova's global intelligence streams. A customer may only read/write its own dispositions.
* **Customer feedback ≠ Pyrnova assessment.** A disposition carries `origin = "CUSTOMER_FEEDBACK"` and
  references (not copies) Pyrnova's assessment; recording a disposition never mutates any Pyrnova
  judgment stream. Later customer reaction never overwrites earlier Pyrnova belief.
* **Append-only / auditable / temporal.** Each disposition is a new immutable version; the latest
  effective version (by `recorded_at`, bounded by an optional `as_of`) is the current one, and history
  is preserved. Prior customer reactions are also retained, not overwritten.
* **Decision Memory linkage.** A disposition references `signal_ref`, `evidence_refs`,
  `pyrnova_assessment_ref`, and `outcome_ref`, so the chain
  SIGNAL → EVIDENCE → CONSEQUENCE → DECISION → ACTION → OUTCOME → LEARNING can be reconstructed later.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .customers import _now, _parse_dt, _stable_id  # reuse the M22-B primitives

STREAM_DISPOSITIONS = "customer_dispositions"  # customer-private; never a global intelligence stream

UNKNOWN = "UNKNOWN"

NOVELTY = ("NEW_TO_CUSTOMER", "ALREADY_KNOWN", UNKNOWN)
RELEVANCE = ("RELEVANT", "NOT_RELEVANT", UNKNOWN)
PURSUIT = ("PURSUE", "WATCH", "PASS", "INVESTIGATE", UNKNOWN)
TIMING = ("EARLY_ENOUGH", "TOO_LATE", UNKNOWN)
VALUE = ("ACTIONABLE", "INFORMATIVE_ONLY", "NO_VALUE", UNKNOWN)
IMPORTANT_MISS = ("YES", "NO", UNKNOWN)
OUTCOME = (
    "PURSUED", "DECLINED", "BID", "NO_BID", "AWARD", "LOSS", "CANCELLED", "UNRESOLVED", "OTHER", UNKNOWN,
)
# Bounded structured reasons; an optional free-text note carries specifics safely (length-capped).
REASON = (
    "DUPLICATE_OF_KNOWN", "WRONG_AGENCY", "WRONG_CAPABILITY", "TOO_SMALL", "OUT_OF_SCOPE",
    "NOT_ADDRESSABLE", "LOW_CONFIDENCE", "TIMING", "GOOD_LEAD", "OTHER", UNKNOWN,
)
_NOTE_MAX = 500


def _check(value: str, allowed: tuple, label: str) -> str:
    v = UNKNOWN if value in (None, "") else str(value)
    if v not in allowed:
        raise ValueError(f"{label} must be one of {allowed}, got {value!r}")
    return v


@dataclass
class Disposition:
    """A customer's usefulness disposition on one delivered intelligence object (append-only version)."""

    customer_id: str
    intelligence_ref: str            # the delivered intelligence object (e.g. material_change id)
    novelty: str = UNKNOWN
    relevance: str = UNKNOWN
    pursuit: str = UNKNOWN
    timing: str = UNKNOWN
    value: str = UNKNOWN
    important_miss: str = UNKNOWN     # YES/NO/UNKNOWN — a miss the customer expected but did not receive
    reason: str = UNKNOWN
    note: Optional[str] = None
    outcome: str = UNKNOWN
    # Decision Memory linkage (references, never copies of Pyrnova judgment):
    signal_ref: Optional[str] = None
    evidence_refs: tuple = ()
    pyrnova_assessment_ref: Optional[str] = None
    outcome_ref: Optional[str] = None
    recorded_at: str = field(default_factory=_now)

    def __post_init__(self):
        if not str(self.customer_id).strip():
            raise ValueError("customer_id is required")
        if not str(self.intelligence_ref).strip():
            raise ValueError("intelligence_ref is required")
        self.novelty = _check(self.novelty, NOVELTY, "novelty")
        self.relevance = _check(self.relevance, RELEVANCE, "relevance")
        self.pursuit = _check(self.pursuit, PURSUIT, "pursuit")
        self.timing = _check(self.timing, TIMING, "timing")
        self.value = _check(self.value, VALUE, "value")
        self.important_miss = _check(self.important_miss, IMPORTANT_MISS, "important_miss")
        self.reason = _check(self.reason, REASON, "reason")
        self.outcome = _check(self.outcome, OUTCOME, "outcome")
        if self.note is not None:
            note = str(self.note).strip()
            self.note = note[:_NOTE_MAX] or None
        self.evidence_refs = tuple(self.evidence_refs or ())

    @property
    def disposition_id(self) -> str:
        # Stable per (customer, intelligence object); versions differ by recorded_at.
        return _stable_id("disp", {"c": self.customer_id, "i": self.intelligence_ref})

    def to_record(self) -> dict:
        return {
            "id": self.disposition_id,
            "origin": "CUSTOMER_FEEDBACK",   # explicitly NOT a Pyrnova assessment
            "customer_id": self.customer_id,
            "intelligence_ref": self.intelligence_ref,
            "novelty": self.novelty,
            "relevance": self.relevance,
            "pursuit": self.pursuit,
            "timing": self.timing,
            "value": self.value,
            "important_miss": self.important_miss,
            "reason": self.reason,
            "note": self.note,
            "outcome": self.outcome,
            "signal_ref": self.signal_ref,
            "evidence_refs": list(self.evidence_refs),
            "pyrnova_assessment_ref": self.pyrnova_assessment_ref,
            "outcome_ref": self.outcome_ref,
            "recorded_at": self.recorded_at,
        }


def record_disposition(store, disposition: Disposition) -> dict:
    """Append a disposition version (append-only; never overwrites a prior customer reaction)."""
    row = disposition.to_record()
    store.append(STREAM_DISPOSITIONS, row)
    return row


def _rows_for(store, customer_id: str, as_of: Optional[str]):
    cutoff = _parse_dt(as_of) if as_of else None
    for r in store.read(STREAM_DISPOSITIONS):
        if r.get("customer_id") != customer_id:   # storage-level tenancy isolation
            continue
        if cutoff is not None and _parse_dt(r.get("recorded_at")) > cutoff:
            continue
        yield r


def latest_disposition(
    store, customer_id: str, intelligence_ref: str, *, as_of: Optional[str] = None
) -> Optional[dict]:
    """Latest effective disposition for one intelligence object, isolated to ``customer_id``."""
    best, best_key = None, None
    for r in _rows_for(store, customer_id, as_of):
        if r.get("intelligence_ref") != intelligence_ref:
            continue
        key = r.get("recorded_at")
        if best_key is None or key >= best_key:
            best, best_key = r, key
    return best


def list_dispositions(store, customer_id: str, *, as_of: Optional[str] = None) -> list[dict]:
    """Current disposition per intelligence object for one customer, deterministic order."""
    latest: dict[str, dict] = {}
    for r in _rows_for(store, customer_id, as_of):
        ref = r.get("intelligence_ref")
        cur = latest.get(ref)
        if cur is None or r.get("recorded_at") >= cur.get("recorded_at"):
            latest[ref] = r
    return [latest[ref] for ref in sorted(latest)]


def disposition_history(store, customer_id: str, intelligence_ref: str) -> list[dict]:
    """Full append-only history for one intelligence object (oldest first) — nothing overwritten."""
    rows = [
        r for r in store.read(STREAM_DISPOSITIONS)
        if r.get("customer_id") == customer_id and r.get("intelligence_ref") == intelligence_ref
    ]
    return sorted(rows, key=lambda r: r.get("recorded_at") or "")
