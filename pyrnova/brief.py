"""Customer-facing output (COMMUNICATE): Signal Brief (outbound, ~3 items) and Capture Radar Report.

Markdown is sufficient initially (PDF is a trivial later render). Each item separates confidence from
attractiveness and always shows evidence, incumbent/history, timing, contra-evidence and next action.
"""

from __future__ import annotations

from datetime import date

from .models import Opportunity
from .pipeline import Report


def _pct(x: float) -> str:
    return f"{round((x or 0) * 100)}%"


def _money(x) -> str:
    return f"${x:,.0f}" if isinstance(x, (int, float)) else "unknown"


def _history_md(opp: Opportunity) -> list[str]:
    rows = opp.meta.get("historical_awards") or []
    if not rows:
        return ["- **Historical award / competitor context:** none linked"]
    rendered = []
    for row in rows:
        recipient = row.get("recipient_name") or "unknown recipient"
        rendered.append(
            f"{recipient} · {_money(row.get('amount'))} · ends {row.get('end_date') or 'unknown'}"
        )
    return ["- **Historical award / competitor context:** " + "; ".join(rendered)]


def _precursor_md(opp: Opportunity) -> list[str]:
    rows = opp.meta.get("upstream_precursors") or []
    if not rows:
        return ["- **Upstream precursor:** none linked"]
    rendered = []
    for row in rows:
        label = row.get("title") or row.get("document_number") or "Federal Register document"
        if row.get("url"):
            label = f"[{label}]({row['url']})"
        rendered.append(f"{label} ({row.get('role', 'supporting')})")
    return [
        "- **Upstream precursor/context:** " + "; ".join(rendered)
        + ". Agency/topic overlap does not by itself prove a program relationship or procurement intent."
    ]


def _chain(opp: Opportunity) -> str:
    precursors = [e for e in opp.events if e.kind == "regulatory_precursor"]
    primary = [e for e in opp.events if e.kind == "notice_posted"]
    context = [e for e in opp.events if e.kind == "award"]
    parts = [f"{e.kind} ({e.source_id})" for e in precursors + primary]
    if context:
        parts.append(f"historical award context ({context[0].source_id})")
    return " → ".join(parts) if parts else "primary signal only"


def _item_md(n: int, opp: Opportunity) -> str:
    ev_links = []
    for ev in opp.evidence:
        if ev.source_url:
            ev_links.append(f"[{ev.source_ref or ev.source_id}]({ev.source_url})")
        else:
            ev_links.append(f"`{ev.source_id}:{ev.content_sha256[:12]}`")
    review_status = opp.meta.get("review_status", "pending_human")
    flag = " · ⚠️ PENDING HUMAN REVIEW" if review_status == "pending_human" else ""
    posture = opp.meta.get("posture")
    tag = {"defend": "🛡️ DEFEND", "capture": "🎯 CAPTURE"}.get(posture, "")
    tag = f" · {tag}" if tag else ""
    lines = [
        f"### SIGNAL {n:02d} — {opp.title}{tag}{flag}",
        "",
        f"- **Assessment:** STRIKE · human-review gate: {review_status.replace('_', ' ')}",
        f"- **Opportunity hypothesis:** {opp.meta.get('opportunity_hypothesis') or opp.title}",
        f"- **What we found:** {opp.catalyst.summary}",
        f"- **Why it matters:** {opp.recommended_action.split(';')[0].strip().capitalize()}.",
        f"- **Customer fit:** relevance **{_pct(opp.relevance_score)}**"
        + (f" — {', '.join(opp.relevance_reasons)}" if opp.relevance_reasons else ""),
        f"- **Agency / program:** {opp.agency or 'n/a'}"
        + (f" · NAICS {opp.naics}" if opp.naics else "")
        + (f" · PSC {opp.psc}" if opp.psc else ""),
        f"- **Incumbent / history:** {opp.incumbent or 'unknown'}",
        f"- **Timing:** expected action ~ **{opp.expected_action_at or 'unknown'}**"
        + (f" ({opp.catalyst.horizon_days} days out)" if opp.catalyst.horizon_days is not None else ""),
        f"- **Value (est.):** {_money(opp.value_usd)}",
        f"- **Evidence:** {', '.join(ev_links) if ev_links else 'archived (content-addressed)'}",
        f"- **Evidence roles:** supporting/primary **{sum(1 for r in opp.evidence_roles.values() if r != 'contra')}** · "
        f"contradictory **{sum(1 for r in opp.evidence_roles.values() if r == 'contra')}**",
        "- **Evidence strength:** " + (
            "; ".join(
                f"{a.strength_class}={a.strength}/5 ({a.polarity})"
                for a in opp.evidence_assessments
            ) or "not assessed"
        ),
        f"- **Catalyst chain:** {_chain(opp)}",
        f"- **Reasons NOT to pursue (falsification):** {opp.falsification}",
        f"- **Recommended next action:** {opp.recommended_action}",
        f"- **Confidence (in the intelligence):** {_pct(opp.confidence)}  ·  "
        f"**Attractiveness (opportunity):** {_pct(opp.attractiveness)}  *(kept separate)*",
        "",
    ]
    lines[8:8] = _history_md(opp) + _precursor_md(opp)
    return "\n".join(lines)


def render_signal_brief(report: Report, *, customer_name: str | None = None, limit: int = 3) -> str:
    name = customer_name or report.profile_name
    items = report.strikes[:limit]
    extra = max(0, len(report.strikes) - len(items))
    header = [
        f"# Pyrnova Signal Brief — {name}",
        f"_Generated {date.today().isoformat()} · as-of data {report.as_of.isoformat()} · "
        f"human review required before action_",
        "",
        "Three developments affecting your capture pipeline that you may not be tracking yet. "
        "Each is evidence-backed and matched to your stated capabilities.",
        "",
    ]
    body = [_item_md(i + 1, opp) for i, opp in enumerate(items)]
    footer = []
    if extra or report.stats.get("defend"):
        defend_n = report.stats.get("defend", 0)
        portfolio = (
            f" That set also includes **{defend_n} of your own contracts** approaching recompete "
            "(we track your portfolio as well as the market)."
            if defend_n
            else ""
        )
        footer = [
            "---",
            f"**Pyrnova identified {extra} additional relevant item(s)** for {name}.{portfolio} We "
            "investigate, rank, monitor and re-price them under a paid engagement (Intelligence Sprint "
            "/ Capture Radar).",
            "",
        ]
    return "\n".join(header + body + footer) or f"# Pyrnova Signal Brief — {name}\n\n_No items._\n"


def render_capture_radar_report(report: Report) -> str:
    s = report.stats
    header = [
        f"# Pyrnova Capture Radar — {report.profile_name}",
        f"_as-of {report.as_of.isoformat()} · {s.get('strikes', 0)} STRIKE(s) from "
        f"{s.get('candidates', 0)} candidate(s)_",
        "",
        f"- Recompete/expiry STRIKEs: **{s.get('recompete', 0)}**",
        f"- Pre-solicitation STRIKEs: **{s.get('presolicitation', 0)}**",
        f"- WATCH candidates: **{s.get('watch', 0)}** · duplicates suppressed: "
        f"**{s.get('duplicate_candidates', 0)}**",
        f"- 🛡️ Defend (your recompetes): **{s.get('defend', 0)}**  ·  🎯 Capture (displace incumbent): "
        f"**{s.get('capture', 0)}**",
        f"- Avg lead time: **{s.get('avg_lead_time_days', 'n/a')} days**",
        "",
        "> Confidence (our certainty in the intelligence) is reported separately from attractiveness "
        "(how good the opportunity is) throughout. All items require human review before action.",
        "",
        "## STRIKEs",
        "",
    ]
    body = [_item_md(i + 1, opp) for i, opp in enumerate(report.strikes)]
    if not report.strikes:
        body = ["_No STRIKEs above the relevance threshold for this profile/window._\n"]
    return "\n".join(header + body)
