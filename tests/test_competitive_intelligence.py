"""B2.4 — Incumbent + Competitive Intelligence: hypotheses with evidence and uncertainty."""

from pyrnova.competitive_intelligence import build_competitive_intelligence
from pyrnova.customer_intelligence import PUBLIC_EVIDENCE, PYRNOVA_DERIVED


CURRENT = {
    "award_id": "W911-CURR", "agency": "Army", "value_usd": 50_000_000.0, "obligated_usd": 30_000_000.0,
    "period_start": "2021-01-01", "period_end": "2026-03-01", "available_at": "2021-01-01",
}
RELATED = [
    {"source_ref": "A-1", "recipient": "Acme", "available_at": "2020-01-01"},   # incumbent's own prior
    {"source_ref": "A-2", "recipient": "Rival Systems", "available_at": "2019-06-01"},
]


def test_incumbent_and_current_contract_are_public_evidence():
    ci = build_competitive_intelligence(
        incumbent={"name": "Acme", "evidence_ref": "W911-CURR"}, current_contract=CURRENT,
        related_awards=RELATED, as_of="2025-09-01")
    assert ci.by_dimension("incumbent")[0].provenance_class == PUBLIC_EVIDENCE
    assert ci.by_dimension("obligated_value")[0].value["obligated_usd"] == 30_000_000.0
    assert ci.by_dimension("incumbent_tenure")[0].value > 0


def test_expiring_contract_is_a_derived_vulnerability():
    ci = build_competitive_intelligence(incumbent={"name": "Acme"}, current_contract=CURRENT, as_of="2025-09-01")
    vulns = ci.by_dimension("incumbent_vulnerability")
    assert any(v.key == "expiring_contract" for v in vulns)  # 2026-03 is < 1yr from 2025-09


def test_competitor_hypothesis_requires_evidence_not_similarity():
    ci = build_competitive_intelligence(incumbent={"name": "Acme"}, related_awards=RELATED)
    hyps = {f.value for f in ci.competitor_hypotheses()}
    assert "Rival Systems" in hyps          # bid a related procurement -> evidenced hypothesis
    assert "Acme" not in hyps               # the incumbent is not its own competitor
    for f in ci.competitor_hypotheses():
        assert f.provenance_class == PYRNOVA_DERIVED and f.uncertainty and f.evidence_ids


def test_no_evidence_is_unknown():
    ci = build_competitive_intelligence()
    assert ci.is_unknown is True
    assert ci.competitor_hypotheses() == []


def test_contradictions_are_kept_visible():
    cc = dict(CURRENT, contradictions=["award protested and re-opened"])
    ci = build_competitive_intelligence(incumbent={"name": "Acme"}, current_contract=cc, as_of="2025-09-01")
    contra = [f for f in ci.by_dimension("incumbent_vulnerability") if f.contradicts]
    assert contra and "protested" in contra[0].contradicts[0]
