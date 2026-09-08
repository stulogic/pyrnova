"""Commercial + intelligence scoreboard (authority §F). Append-only metric events."""

from __future__ import annotations

from .state import StateStore

# Metric names tracked from Day 1 (see EXECUTION_AUTHORITY_30D.md Part II §F).
INTELLIGENCE_METRICS = {
    "candidate_opportunities",
    "strikes_published",
    "customer_relevant_strikes",
    "evidence_items",
    "predictions_logged",
    "lead_time_days",
    "duplicate_opportunities",
    "review_accepts",
    "review_watches",
    "review_rejects",
}
COMMERCIAL_METRICS = {
    "targeted_accounts",
    "signal_briefs_produced",
    "decision_makers_contacted",
    "replies",
    "meetings",
    "paid_sprints",
    "radar_customers",
    "cash_collected_usd",
    "enterprise_conversations",
}


def record(store: StateStore, metric: str, value: float = 1.0, **context) -> None:
    store.append("scoreboard", {"metric": metric, "value": value, "context": context})


def totals(store: StateStore) -> dict[str, float]:
    out: dict[str, float] = {}
    for ev in store.read("scoreboard"):
        out[ev["metric"]] = out.get(ev["metric"], 0.0) + float(ev.get("value", 0))
    return out
