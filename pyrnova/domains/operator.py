"""Operator controls for national domains — inspect status, provision an evaluation lens, see fan-out.

CLI/operator capability (no admin UI). Every reader is fail-closed and crosses the TWO independent
governance layers so an operator sees the whole truth for a national source:

* the **national domain** activation posture (``pyrnova/domains``): is the source ACTIVE / FIXTURE_ONLY /
  DECLARED / PROHIBITED for this nation's *acquisition*? (UNKNOWN => DENY).
* the **source-rights registry** (``pyrnova/sources``): does a reviewed rights profile permit live
  transport, derived use, and customer display?

A source is only *live-activatable* when BOTH layers approve it; anything else is honestly reported as
blocked, with the reason, so an operator never mistakes "a fixture adapter exists" for "we may go live".
"""

from __future__ import annotations

from typing import Optional

from .base import NationalDomain, SourceActivation
from . import get_domain


def _registry_rights(source_id: str) -> dict:
    """Registry rights posture for a source (fail-closed). Reports transport / derived / display."""
    try:
        from ..sources.registry import get_spec
        from ..sources.rights import authorize_request, authorize_derived_projection, source_policy
    except Exception as exc:  # noqa: BLE001
        return {"registered": False, "note": f"registry unavailable: {exc}"}
    try:
        spec = get_spec(source_id)
    except KeyError:
        return {"registered": False, "note": "no reviewed rights profile (UNKNOWN => DENY)"}
    policy = spec.policy
    # Live transport: probe the request gate (raises when denied).
    live_ok, live_reason = True, "permitted"
    try:
        host = (policy.allowed_hosts[0] if policy and policy.allowed_hosts else spec.base_url)
        url = spec.base_url if "://" in spec.base_url else f"https://{host}"
        decision = authorize_request(source_id, "GET", url)
        live_ok, live_reason = decision.allowed, (decision.reason_code or "permitted")
    except Exception as exc:  # noqa: BLE001 — fail closed: any denial means not live
        live_ok, live_reason = False, str(getattr(exc, "reason_code", "") or exc)
    # Derived-use (a customer projection built from lawful replay/historical evidence).
    d = authorize_derived_projection({"id": f"{source_id}:probe",
                                      "evidence": {"sources": [source_id]}})
    return {
        "registered": True,
        "state": str(getattr(policy, "state", "unknown")),
        "rights_class": str(getattr(policy, "rights_class", "unknown")),
        "live_transport": {"allowed": bool(live_ok), "reason": live_reason},
        "derived_use": {"allowed": bool(d.allowed), "reason": d.reason_code or d.reason},
        "customer_display": getattr(policy, "customer_display", "unknown"),
        "policy_version": getattr(policy, "policy_version", "unknown"),
    }


def domain_source_status(code: str) -> dict:
    """Full national source status for one domain, crossing activation posture × registry rights."""
    domain = get_domain(code)
    sources = []
    for s in domain.sources:
        rights = _registry_rights(s.id)
        live_activatable = bool(s.activation is SourceActivation.ACTIVE
                                and rights.get("registered")
                                and rights.get("live_transport", {}).get("allowed"))
        blocked_reason = None
        if not live_activatable:
            if s.activation is SourceActivation.PROHIBITED:
                blocked_reason = "PROHIBITED: hard-locked; never an ingestion source"
            elif s.activation is not SourceActivation.ACTIVE:
                blocked_reason = (f"national activation {s.activation.value} (UNKNOWN => DENY); "
                                  "live production ingestion requires rights approval")
            elif not rights.get("registered"):
                blocked_reason = "no reviewed source-rights profile (UNKNOWN => DENY)"
            else:
                blocked_reason = f"registry denies live transport: {rights.get('live_transport', {}).get('reason')}"
        sources.append({
            "id": s.id, "name": s.name, "role": s.role,
            "national_activation": s.activation.value,
            "national_ingestible": s.ingestible,
            "registry_rights": rights,
            "live_activatable": live_activatable,
            "replay_derived_permitted": bool(rights.get("registered")
                                             and rights.get("derived_use", {}).get("allowed")
                                             and s.activation in (SourceActivation.ACTIVE,
                                                                  SourceActivation.FIXTURE_ONLY)),
            "blocked_live_activation": blocked_reason,
            "note": s.note,
        })
    return {
        "domain": domain.code, "name": domain.name,
        "validated": domain.validated, "build_authority": domain.build_authority,
        "operational": bool(domain.validated and domain.build_authority),
        "important_miss_taxonomy": list(domain.important_miss),
        "sources": sources,
    }


def lens_national_state(console, customer_id: str, *, as_of: Optional[str] = None) -> dict:
    """Operator view of a customer lens's NATIONAL opportunity/Important-Miss state via the shared product.

    Reads the shared customer product (no second read model). For each opportunity carrying national
    truth, surfaces route/lifecycle/access/Industrial Position/Important Miss and the shared disposition,
    so an operator can inspect fan-out and opportunity/decision state without a country fork.
    """
    opps = console.customer_opportunities(customer_id, as_of=as_of)
    rows = []
    important_miss: dict[str, int] = {}
    consequential: dict[str, int] = {}      # UK consequential-change rollup (empty for AU/NZ)
    for item in opps.get("opportunities", []):
        dec = console.opportunity_decision(customer_id, item["id"], as_of=as_of)
        nat = dec.get("decision_chain", {}).get("national_acquisition")
        if not nat:
            continue
        kind = nat.get("important_miss_kind") or "—"
        important_miss[kind] = important_miss.get(kind, 0) + 1
        cck = nat.get("consequential_change_kind")
        if cck:
            consequential[cck] = consequential.get(cck, 0) + 1
        rows.append({
            "opportunity_id": item["id"], "title": item.get("title"),
            "domain": nat.get("domain"), "route": nat.get("route"),
            "lifecycle_stage": nat.get("lifecycle_stage"),
            "access_class": nat.get("access_class"),
            "industrial_position": nat.get("industrial_position"),
            "important_miss_kind": nat.get("important_miss_kind"),
            "consequential_change_kind": cck,
            "sscr_qdc": nat.get("sscr_qdc"),
            "post_award": nat.get("post_award"),
            "shared_state": item.get("lifecycle_state"),
            "source_rights": item.get("source_rights", {}).get("display"),
        })
    return {"customer_id": customer_id, "as_of": as_of, "count": len(rows),
            "important_miss": dict(sorted(important_miss.items())),
            "consequential_change": dict(sorted(consequential.items())), "opportunities": rows}


__all__ = ["domain_source_status", "lens_national_state"]
