"""National → shared-tenant bridge: project a national opportunity into the SHARED customer product.

SHARE MECHANISM. KEEP NATIONAL TRUTH NATIONAL. The per-tenant customer machinery
(:mod:`pyrnova.customer_material_changes` fan-out, the Material Changes read model, the customer SPA,
the Integrated Decision object, Decision Memory and the brief download) is the shared kernel's and is
NOT re-implemented per country. This module is the *seam* that lets a :class:`NationalOpportunity`
enter that machinery as an ordinary record in the global ``opportunities`` stream — so an Australian
acquisition reaches the SAME tenant-isolated customer product the US uses.

National acquisition truth is NOT flattened into the US ontology: it travels as a self-contained
``meta["national"]`` block (national domain, acquisition route + its meaning, lifecycle stage, access
class, Industrial Position, Important Miss, national value in its own currency, cited DLT calibration).
The read model passes that block through untouched; only records that carry it render national meaning,
so no US record is affected and no US semantic assumption (USD value, "incumbent", US agency) is
imported into AU — those national-inapplicable fields stay ``None``.

Fail-closed guarantees enforced here:

* **AS-OF integrity** — evidence dated after ``as_of`` is refused (no point-in-time leakage).
* **Source rights** — every backing source must be known to the national domain and not PROHIBITED,
  and at least FIXTURE_ONLY (lawful replay) — UNKNOWN/DECLARED => DENY. The registry rights gate is
  applied again at persistence time by the shared fan-out (:func:`authorize_derived_projection`), so a
  source without an approved derived-use rights profile can never be materialized for a customer.
* **Deterministic identity** — the opportunity id and evidence ids are derived from source-linked
  content, never wall-clock or random, so the same national truth yields the same record (idempotent
  fan-out, byte-reproducible proofs).
* **Tenant safety** — the record is scoped by ``customer_id`` only; nothing cross-tenant is embedded.
"""

from __future__ import annotations

import hashlib
import json
from typing import Optional, Sequence

from .base import NationalDomain, SourceActivation
from .pipeline import NationalEvidence, NationalOpportunity, _assert_asof

# National change categories that DOWNGRADE/CLOSE, or flag for REVIEW, a customer opportunity rather than
# present it as a fresh live pursuit. These are country-NEUTRAL string sets (no per-country branching): a
# domain supplies its own kinds (AU/NZ via ``important_miss``; UK via the richer consequential-change state
# model) and the same disposition mapping applies. A cancelled/closed change is material (the customer must
# not miss it) but is not an actionable opportunity, so it maps to a shared ``state`` the read model treats
# as MONITORING. A narrowed / access-changed / prime-changed / window-changed / post-award-risk change stays
# open but flagged for review. Award is NOT terminal: post-award risk keeps the opportunity monitored, never
# silently closed. Everything else (created/expanded/progression/capability-insertion) is a live candidate.
_DOWNGRADE_KINDS = {"CANCELLATION", "CONSOLIDATION", "OPPORTUNITY_CLOSED"}
_REVIEW_KINDS = {
    "RE_SCOPE", "ROUTE_CHANGE",
    "OPPORTUNITY_NARROWED", "ACCESS_CHANGED", "PRIME_POSITION_CHANGED", "DECISION_WINDOW_CHANGED",
    "POST_AWARD_RISK_INCREASED",
}


def _stable_id(prefix: str, payload: dict) -> str:
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()
    return f"{prefix}_" + hashlib.sha256(blob).hexdigest()[:20]


def _national_state(important_miss_kind: Optional[str],
                    consequential_change_kind: Optional[str] = None) -> str:
    """Shared opportunity ``state`` derived from a national change kind (country-neutral downgrade).

    The consequential-change state (UK) takes precedence when present; otherwise the Important-Miss kind
    (AU/NZ) is used. The mapping is identical for both — one shared disposition rule, no country fork.
    """
    kind = (consequential_change_kind or important_miss_kind or "").upper()
    if kind in _DOWNGRADE_KINDS:
        return "cancelled"      # -> MONITORING in the shared read model (downgraded / closed)
    if kind in _REVIEW_KINDS:
        return "reviewing"      # -> OPPORTUNITY, flagged for review (materially moved / post-award risk)
    return "candidate"          # -> OPPORTUNITY (live)


def _assert_source_rights(domain: NationalDomain, source_id: str) -> None:
    """National-layer fail-closed rights check. UNKNOWN/DECLARED => DENY; PROHIBITED hard-locks.

    Lawful replay/fixture evidence (FIXTURE_ONLY) and live-approved sources (ACTIVE) may back a derived
    customer projection; the registry derived-use rights gate is applied again at persistence time.
    """
    src = domain.source(source_id)
    if src is None:
        raise PermissionError(f"[{domain.code}] source {source_id!r} is not a known national source "
                              "(UNKNOWN => DENY)")
    if src.activation is SourceActivation.PROHIBITED:
        domain.assert_ingestible(source_id)  # raises ProhibitedSourceIngestion
    if src.activation not in (SourceActivation.ACTIVE, SourceActivation.FIXTURE_ONLY):
        raise PermissionError(f"[{domain.code}] source {source_id!r} activation {src.activation.value} "
                              "does not permit evidence use (UNKNOWN => DENY)")


def national_value_block(amount: Optional[float], currency: str = "AUD") -> Optional[dict]:
    """National contract value in its OWN currency — never coerced into the US ``value_usd`` field."""
    if amount is None:
        return None
    return {"amount": amount, "currency": currency}


def build_national_opportunity_record(
    domain: NationalDomain,
    opportunity: NationalOpportunity,
    *,
    evidence: Sequence[NationalEvidence],
    subject_ref: str,
    subject_name: str,
    title: str,
    as_of: Optional[str] = None,
    value: Optional[dict] = None,
    expected_action_at: Optional[str] = None,
    confidence: Optional[float] = None,
    buyer: Optional[str] = None,
) -> dict:
    """Project one :class:`NationalOpportunity` into a shared ``opportunities`` global-stream record.

    The record is an ordinary customer opportunity as far as the shared machinery is concerned; national
    acquisition truth rides on ``meta["national"]`` and is passed through the read model untouched. The
    result is deterministic given its inputs and carries only ``customer_id``-scoped facts.
    """
    mc = opportunity.material_change
    access = opportunity.access
    if mc.domain_code != domain.code:
        raise ValueError(f"material change domain {mc.domain_code!r} != {domain.code!r}")

    ev_records = []
    for ev in evidence:
        _assert_asof(ev.available_at, as_of)
        _assert_source_rights(domain, ev.source_id)
        ev_records.append({
            "id": ev.evidence_id,
            "source_id": ev.source_id,
            "source_ref": ev.payload.get("source_ref") or ev.evidence_id,
            "source_url": ev.payload.get("source_url"),
            "archive_uri": ev.payload.get("archive_uri"),
            "first_seen_at": ev.available_at,
            "language": ev.language,
        })

    evidence_sources = sorted({ev.source_id for ev in evidence})
    national = {
        "domain": domain.code,
        "domain_name": domain.name,
        "route": mc.route,
        "route_meaning": domain.routes.get(mc.route),
        "lifecycle_stage": mc.lifecycle_stage,
        "access_class": access.verdict,
        "industrial_position": access.industrial_position,
        "important_miss_kind": mc.important_miss_kind,
        # UK consequential-change state + SSCR/QDC evidenced field ride through untouched (None/"UNKNOWN"
        # for domains that do not use them, so no US/AU/NZ record changes).
        "consequential_change_kind": mc.consequential_change_kind,
        "sscr_qdc": mc.sscr_qdc,
        # Post-award marker: award is NOT terminal. A change at a post-award lifecycle stage remains
        # monitored; the flag lets the read model / brief show post-award intelligence explicitly.
        "post_award": mc.lifecycle_stage in ("PERFORMANCE", "POST_AWARD_CHANGE"),
        "value_local": value,
        "national_material_change_id": mc.material_change_id,
        "dlt_calibration_ref": (domain.dlt_calibration.source_reference
                                if domain.dlt_calibration is not None else None),
    }

    opp_id = _stable_id("opp", {"domain": domain.code, "mc": mc.material_change_id,
                                "subject": subject_ref, "customer": opportunity.customer_id})
    return {
        "id": opp_id,
        "customer_id": opportunity.customer_id,
        "state": _national_state(mc.important_miss_kind, mc.consequential_change_kind),
        "title": title,
        # Top-level program key (= the national material-change id) so the shared decision view relates
        # this opportunity to its own Material Change on the customer feed (country-neutral linkage).
        "program_key": mc.material_change_id,
        # National-inapplicable US fields stay None (no US assumption imported):
        "agency": buyer,           # a national buyer name if supplied; NOT a US agency taxonomy
        "value_usd": None,         # AU value is carried in meta.national.value_local, in AUD
        "incumbent": None,         # AU uses the national access position, not the US "incumbent" concept
        "confidence": confidence,
        "expected_action_at": expected_action_at,
        "catalyst": {"kind": (mc.consequential_change_kind or mc.important_miss_kind
                              or "NATIONAL_MATERIAL_CHANGE")},
        "evidence": ev_records,
        "meta": {
            "subject_ref": subject_ref,
            "subject_name": subject_name,
            "program_key": mc.material_change_id,
            "source_ref": (ev_records[0]["source_ref"] if ev_records else None),
            "source_as_of": mc.observed_at,
            "evidence_sources": evidence_sources,
            "national": national,
        },
    }


__all__ = [
    "build_national_opportunity_record",
    "national_value_block",
    "_national_state",
    "_assert_source_rights",
]
