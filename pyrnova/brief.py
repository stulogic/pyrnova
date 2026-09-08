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
    return f"${x:,.0f}" if isinstance(x, (int, float)) else "n/a"


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
        f"- **What we found:** {opp.catalyst.summary}",
        f"- **Why it matters:** {opp.recommended_action.split(';')[0].strip().capitalize()}.",
        f"- **Customer fit:** relevance **{_pct(opp.relevance_score)}**"
        + (f" — {', '.join(opp.relevance_reasons)}" if opp.relevance_reasons else ""),
        f"- **Agency / program:** {opp.agency or 'n/a'}"
        + (f" · NAICS {opp.naics}" if opp.naics else "")
        + (f" · PSC {opp.psc}" if opp.psc else ""),
        f"- **Incumbent / history:** {opp.incumbent or 'n/a'}",
        f"- **Timing:** expected action ~ **{opp.expected_action_at or 'n/a'}**"
        + (f" ({opp.catalyst.horizon_days} days out)" if opp.catalyst.horizon_days is not None else ""),
        f"- **Value (est.):** {_money(opp.value_usd)}",
        f"- **Evidence:** {', '.join(ev_links) if ev_links else 'archived (content-addressed)'}",
        f"- **Reasons NOT to pursue (falsification):** {opp.falsification}",
        f"- **Recommended next action:** {opp.recommended_action}",
        f"- **Confidence (in the intelligence):** {_pct(opp.confidence)}  ·  "
        f"**Attractiveness (opportunity):** {_pct(opp.attractiveness)}  *(kept separate)*",
        "",
    ]
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
    if extra:
        footer = [
            "---",
            f"**Pyrnova identified {extra} additional relevant item(s)** for {name}. We investigate, "
            "rank, monitor and re-price them under a paid engagement (Intelligence Sprint / Capture "
            "Radar).",
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
