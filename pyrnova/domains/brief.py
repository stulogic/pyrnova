"""National decision brief — renders a SHARED IntegratedDecision without flattening national meaning.

There is NO per-country frontend fork and NO per-country brief engine: this single renderer reads the
shared decision object (:meth:`IntegratedDecision.to_record`) and presents the national truth that
travels on it (route meaning, lifecycle stage, access, Industrial Position, Important Miss, the
Decision-Lead-Time derived by the shared engine, and referenced evidence provenance). It states clearly
what is SOURCE FACT vs PYRNOVA DERIVED and preserves UNKNOWN.
"""

from __future__ import annotations

from typing import Any

from .base import NationalDomain


def _dash(v: Any) -> str:
    return "—" if v in (None, "", [], {}) else str(v)


def render_national_brief(domain: NationalDomain, decision: Any, *, customer_name: str | None = None) -> str:
    """Render a decision-grade brief for one national IntegratedDecision. ``decision`` is an
    IntegratedDecision (its ``.to_record()`` / properties are read; nothing is recomputed)."""
    rec = decision.to_record()
    mcs = rec.get("material_changes") or []
    mc = mcs[0] if mcs else {}
    dlt = rec.get("decision_lead_time") or getattr(decision, "decision_lead_time", None) or {}
    unc = decision.uncertainty

    lines: list[str] = []
    who = customer_name or "customer"
    lines.append(f"# Pyrnova Decision Brief — {domain.name} ({domain.code})")
    lines.append(f"_Opportunity {rec.get('opportunity_ref')} · as-of {_dash(rec.get('as_of'))} · "
                 "human review required before action_")
    lines.append("")
    lines.append(f"National domain: **{domain.name}**. National acquisition truth is preserved; the "
                 "intelligence machinery is shared.")
    lines.append("")

    # --- Material Change (national) — SOURCE-anchored + PYRNOVA DERIVED classification --------------
    lines.append("## What materially changed")
    lines.append(f"- Lifecycle stage: **{_dash(mc.get('lifecycle_stage'))}** "
                 f"(one of the {domain.name} acquisition lifecycle states)")
    lines.append(f"- Acquisition route: **{_dash(mc.get('route'))}** — {_dash(mc.get('route_meaning'))}")
    lines.append(f"- Industrial Position: **{_dash(mc.get('industrial_position'))}**")
    if mc.get("important_miss_kind"):
        lines.append(f"- Important Miss category addressed: **{mc['important_miss_kind']}**")
    # Consequential-change state + SSCR/QDC evidenced field (UK). Rendered only when present so other
    # national briefs are unchanged. SSCR/QDC is the EVIDENCED value (UNKNOWN unless proven) — never derived.
    if mc.get("consequential_change_kind"):
        lines.append(f"- Consequential change (PYRNOVA DERIVED): **{mc['consequential_change_kind']}**")
        lines.append(f"- SSCR/QDC status (SOURCE-EVIDENCED, not derived): **{mc.get('sscr_qdc') or 'UNKNOWN'}**")
        if mc.get("lifecycle_stage") in ("PERFORMANCE", "POST_AWARD_CHANGE"):
            lines.append("- Post-award intelligence: award is **not** a terminal state — monitoring continues.")
    lines.append(f"- Observed at (SOURCE FACT): {_dash(mc.get('observed_at'))}")
    lines.append("")

    # --- Access (national) — Material Change != Opportunity != Access != decision ------------------
    lines.append("## Your access position")
    lines.append(f"- Access (PYRNOVA DERIVED): **{_dash(unc.get('access_verdict'))}**")
    lines.append("- Note: a Material Change is not itself an Opportunity, and an access position is not "
                 "itself a pursuit decision.")
    lines.append("")

    # --- Decision Lead Time (shared engine) --------------------------------------------------------
    lines.append("## Decision lead time (shared engine, national anchors)")
    if dlt.get("external_lead_time_established"):
        lines.append(f"- External decision lead time: **{dlt.get('external_decision_lead_time_days')} days** "
                     "(from source availability to the national benchmark)")
    else:
        lines.append("- External decision lead time: **not established** (no benchmark) — UNKNOWN preserved")
    lines.append(f"- Internal pipeline latency: {_dash(dlt.get('internal_pipeline_latency_days'))} days")
    if domain.dlt_calibration is not None:
        c = domain.dlt_calibration
        lines.append(f"- National calibration (cited): median {c.median_dlt_to_market_days}d, "
                     f"P25 {c.p25_days}d — {c.source_reference}")
    lines.append("")

    # --- Evidence + uncertainty --------------------------------------------------------------------
    lines.append("## Evidence & uncertainty")
    ev = list(mc.get("evidence_ids") or []) or decision.referenced_evidence_ids
    lines.append(f"- Referenced evidence (provenance, not copied content): {_dash(', '.join(ev))}")
    open_unknowns = unc.get("open_unknowns") or []
    lines.append(f"- Open unknowns: {_dash(', '.join(map(str, open_unknowns)))}")
    lines.append("")
    lines.append(f"_Prepared for {who}. Evidence is {domain.name} source material; assessments and access "
                 "are PYRNOVA DERIVED._")
    return "\n".join(lines) + "\n"
