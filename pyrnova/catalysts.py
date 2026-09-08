"""Capital catalysts and commercial consequences (M7).

Turns an evidence-backed capital chain into explicit, evidence-linked commercial consequences:

    EVENTS / RELATIONSHIPS -> CAPITAL CATALYST -> COMMERCIAL CONSEQUENCE
    -> SCREENING / FALSIFICATION -> STRIKE / WATCH / REJECT

This module is a conservative, deterministic reasoning layer. It never fabricates a commercial
consequence from topic similarity: every mechanism, participant role, capability, and value is grounded
in explicit structured evidence (procurement language, funding type, regulatory obligation, award
identity, capability codes/phrases, historical amounts). Zero consequences is a common, valid result.

It is pure with respect to scoring: it produces its own catalyst/consequence/mechanism confidences and
a *recommended* screened disposition, but it never creates a candidate or changes ``scoring_v1``.
"""

from __future__ import annotations

import hashlib

from .capabilities import extract_capabilities
from .models import (
    CapitalCatalyst,
    CommercialConsequence,
    ConsequenceFalsifier,
    Participant,
    to_record,
)
from .precursors import PRECURSOR_STAGES, stable_signal_id
from .value import estimate_value

CATALYST_ENGINE_VERSION = "commercial_consequence_v1"

_STAGE_SET = set(PRECURSOR_STAGES)
_STAGE_ORDER = {stage: i for i, stage in enumerate(PRECURSOR_STAGES)}

CATALYST_TYPES = {
    "BUDGET_APPROPRIATION", "PROGRAM_ESTABLISHMENT", "PROCUREMENT_LIFECYCLE",
    "REGULATORY_MANDATE", "CAPACITY_BUILDOUT", "SUPPLY_DISRUPTION",
}

MECHANISM_FAMILIES = {
    "DIRECT_PROCUREMENT", "FUNDED_DOWNSTREAM_DEMAND", "FORCED_COMPLIANCE_SPEND",
    "CAPITAL_EXPANSION", "SUPPLY_DISPLACEMENT", "TECHNOLOGY_MIGRATION",
    "INDUSTRIAL_CAPACITY_BUILDOUT",
}

DIRECTNESS = {"DIRECT", "DOWNSTREAM", "SECOND_ORDER"}
_DIRECTNESS_FACTOR = {"DIRECT": 1.0, "DOWNSTREAM": 0.8, "SECOND_ORDER": 0.5}

ROLES = {
    "FUNDING_AUTHORITY", "PROGRAM_OWNER", "BUYER", "PRIME_RECIPIENT", "BENEFICIARY",
    "SUPPLIER", "SUBCONTRACTOR", "AFFECTED_ENTITY", "REGULATED_ENTITY",
}

FALSIFIER_CODES = {
    "no_identifiable_buyer", "no_executable_procurement_path",
    "funding_restricted_from_commercial_use", "incumbent_lock_in",
    "internal_self_performance", "already_awarded", "expired_timing",
    "capability_mismatch", "no_downstream_commercial_mechanism", "saturated_supply",
    "geographic_restriction", "regulatory_exemption", "funding_not_appropriated",
    "program_cancelled", "speculative_second_order",
}

_PROCUREMENT_KINDS = {"solicitation", "presolicitation", "rfi", "sources_sought"}
_CONTRA_KINDS = {"cancellation", "closure", "recall", "shortage", "sanction", "rescission"}


# --------------------------------------------------------------------------- helpers

def _evidence_id(record: dict) -> str:
    stage = record.get("stage")
    if stage in _STAGE_SET:
        return stable_signal_id(record["source_id"], record["source_ref"], stage)
    return record["source_ref"]


def _catalyst_id(component_keys: list[str]) -> str:
    basis = "|".join([CATALYST_ENGINE_VERSION, *sorted(component_keys)]).encode("utf-8")
    return "cat_" + hashlib.sha256(basis).hexdigest()[:20]


def _consequence_id(catalyst_id: str, mechanism: str, anchor_ref: str) -> str:
    basis = f"{catalyst_id}|{mechanism}|{anchor_ref}".encode("utf-8")
    return "cons_" + hashlib.sha256(basis).hexdigest()[:20]


def _earliest(records: list[dict]) -> str | None:
    times = [r["available_at"] for r in records if r.get("available_at")]
    return min(times) if times else None


def _staged(records: list[dict]) -> list[dict]:
    return [r for r in records if r.get("stage") in _STAGE_SET and r.get("program_key")]


def _is_contradiction(record: dict) -> bool:
    return bool(record.get("contradicts")) or record.get("record_kind") in _CONTRA_KINDS


# --------------------------------------------------------------------------- catalyst grouping

def _program_components(records: list[dict], relationships) -> list[list[str]]:
    """Union program_keys connected by any accepted relationship into one catalyst chain, so a chain
    spanning program keys (native-id or accepted inferred crosswalk) yields ONE catalyst, never one
    per key. Deterministic; isolated program keys form singleton components."""
    keys = sorted({r["program_key"] for r in _staged(records)})
    parent = {k: k for k in keys}

    def find(k):
        while parent[k] != k:
            parent[k] = parent[parent[k]]
            k = parent[k]
        return k

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[max(ra, rb)] = min(ra, rb)

    signal_key = {}
    for record in _staged(records):
        signal_key[stable_signal_id(record["source_id"], record["source_ref"], record["stage"])] = record["program_key"]
    for rel in relationships:
        a, b = signal_key.get(rel.subject_id), signal_key.get(rel.object_id)
        if a in parent and b in parent:
            union(a, b)

    components: dict[str, list[str]] = {}
    for k in keys:
        components.setdefault(find(k), []).append(k)
    return [sorted(v) for v in sorted(components.values(), key=lambda v: min(v))]


# --------------------------------------------------------------------------- participant roles

def _agency_key(name: str | None) -> str | None:
    return " ".join((name or "").split()).casefold() or None


def resolve_participants(records: list[dict]) -> list[Participant]:
    """Distinct economic roles established only from authoritative structured fields.

    FUNDING_AUTHORITY / PROGRAM_OWNER / BUYER / PRIME_RECIPIENT / BENEFICIARY / REGULATED_ENTITY are
    resolved from stage + source + entity identity. SUPPLIER / SUBCONTRACTOR are NOT inferred without
    explicit evidence (a supplier/subcontract record field)."""
    participants: dict[tuple, Participant] = {}

    def add(role, name, entity_ref, record, basis):
        key = (role, entity_ref or _agency_key(name))
        if not key[1] or key in participants:
            return
        participants[key] = Participant(role=role, entity_ref=entity_ref, name=name,
                                        evidence_ids=[_evidence_id(record)], basis=basis)

    for record in records:
        stage, kind, agency = record.get("stage"), record.get("record_kind"), record.get("agency")
        if stage in ("AUTHORIZATION", "FUNDING") or kind in ("appropriation", "authorization"):
            authority = "U.S. Congress" if kind == "authorization" or stage == "AUTHORIZATION" else agency
            add("FUNDING_AUTHORITY", authority, None, record, "appropriation/authorization record")
            if agency:
                add("PROGRAM_OWNER", agency, _agency_key(agency), record, "owning agency of funded program")
        if stage in ("PROGRAM", "MARKET_ENGAGEMENT") and agency:
            add("PROGRAM_OWNER", agency, _agency_key(agency), record, "agency owns the program/market engagement")
        if stage in ("PROCUREMENT", "AWARD") and agency:
            add("BUYER", agency, _agency_key(agency), record, "agency executes the procurement/award")
        uei = record.get("recipient_uei")
        if uei and stage == "AWARD":
            add("PRIME_RECIPIENT", record.get("recipient") or f"UEI {uei}", f"entity:uei:{str(uei).strip().upper()}",
                record, "award names the prime recipient UEI")
        if uei and (kind in ("grant_award", "grant_nofo") or (stage == "FUNDING" and record.get("source_id") == "grants_gov")):
            add("BENEFICIARY", record.get("recipient") or f"UEI {uei}", f"entity:uei:{str(uei).strip().upper()}",
                record, "grant names the funded beneficiary")
        regulated = record.get("regulated_entity")
        if regulated:
            add("REGULATED_ENTITY", regulated, None, record, "regulatory record names a regulated party")
        # Explicit supplier evidence only — never inferred.
        for supplier in record.get("suppliers") or ():
            add("SUPPLIER", supplier, None, record, "record explicitly names a supplier")
    return list(participants.values())


# --------------------------------------------------------------------------- mechanism classification

def _spend_category(record: dict) -> str | None:
    return record.get("spend_category") or record.get("psc") or record.get("naics")


def classify_mechanisms(records: list[dict]) -> list[dict]:
    """Return distinct, evidence-anchored candidate mechanisms for one catalyst's records.

    Deterministic and rule-backed: mechanism comes from stage + record_kind + source + explicit
    structured flags, never from topical similarity. Each candidate names its anchor record and
    evidence so the classification is auditable.
    """
    staged = _staged(records)
    kinds = {r.get("record_kind") for r in staged}
    candidates: list[dict] = []

    def add(mechanism, directness, confidence, rationale, anchor, extra_evidence=()):
        evidence = [_evidence_id(anchor), *[_evidence_id(r) for r in extra_evidence]]
        candidates.append({
            "mechanism": mechanism, "directness": directness, "confidence": round(confidence, 3),
            "rationale": rationale, "anchor": anchor, "evidence_ids": list(dict.fromkeys(evidence)),
            "spend_category": _spend_category(anchor),
        })

    # 1) DIRECT PROCUREMENT — explicit procurement/award record with a named buyer.
    procurement = [r for r in staged if r.get("stage") == "PROCUREMENT" and r.get("record_kind") in _PROCUREMENT_KINDS]
    award = [r for r in staged if r.get("stage") == "AWARD" and r.get("record_kind") == "award"]
    if procurement or award:
        anchor = next((r for r in procurement if r.get("record_kind") == "solicitation"), None) \
            or (award[0] if award else procurement[0])
        explicit = anchor.get("record_kind") in ("solicitation", "award")
        add("DIRECT_PROCUREMENT", "DIRECT", 0.9 if explicit else 0.7,
            "explicit procurement/award record with a named buying agency", anchor,
            extra_evidence=[r for r in (procurement + award) if r is not anchor])

    # 2) FUNDED DOWNSTREAM DEMAND — grant/subsidy creates downstream private demand (distinct money path).
    grants = [r for r in staged if r.get("record_kind") in ("grant_nofo", "grant_award")
              or (r.get("stage") == "FUNDING" and r.get("source_id") == "grants_gov")]
    if grants:
        add("FUNDED_DOWNSTREAM_DEMAND", "DOWNSTREAM", 0.75,
            "grant/NOFO funding creates downstream demand from the funded recipient", grants[0])

    # 3) FORCED COMPLIANCE SPEND — a regulatory obligation compels expenditure.
    regs = [r for r in staged if r.get("source_id") == "federal_register"
            or r.get("record_kind") in ("rule", "proposed_rule", "regulatory_precursor")]
    obligating = [r for r in regs if r.get("obligation")]
    if obligating:
        add("FORCED_COMPLIANCE_SPEND", "DOWNSTREAM", 0.7,
            "regulatory obligation compels regulated entities to spend to comply", obligating[0])

    # 4) CAPITAL EXPANSION — capex/facility project creates supplier/service demand.
    capex = [r for r in staged if r.get("record_kind") in ("capex", "facility_expansion")
             or (r.get("source_id") == "sec_edgar" and r.get("capex_disclosed"))]
    if capex:
        directness = "DOWNSTREAM" if capex[0].get("explicit_supplier_need") else "SECOND_ORDER"
        add("CAPITAL_EXPANSION", directness, 0.6,
            "disclosed capital expansion creates supplier/service demand", capex[0])

    # 5) SUPPLY DISPLACEMENT — failure/closure/recall/shortage/sanction creates replacement demand.
    disruptions = [r for r in staged if _is_contradiction(r)]
    if disruptions:
        add("SUPPLY_DISPLACEMENT", "SECOND_ORDER", 0.5,
            "disruption (closure/recall/shortage/sanction) may create replacement demand", disruptions[0])

    # 6) TECHNOLOGY MIGRATION — deprecation/standard change forces migration/implementation.
    migration = [r for r in staged if r.get("record_kind") in ("deprecation", "standard_change", "migration_mandate")]
    if migration:
        add("TECHNOLOGY_MIGRATION", "DOWNSTREAM", 0.65,
            "mandated deprecation/standard change forces migration spend", migration[0])

    # 7) INDUSTRIAL CAPACITY BUILDOUT — policy/program drives capacity expansion and supplier demand.
    capacity = [r for r in staged if r.get("record_kind") in ("program_designation", "capacity_program")
                or r.get("industrial_policy")]
    if capacity:
        add("INDUSTRIAL_CAPACITY_BUILDOUT", "DOWNSTREAM" if capacity[0].get("explicit_supplier_need") else "SECOND_ORDER",
            0.6, "industrial-policy program drives capacity expansion and supplier demand", capacity[0])

    return _subsume(candidates)


def _subsume(candidates: list[dict]) -> list[dict]:
    """Drop mechanisms that are the same money already captured by a stronger, more direct mechanism.

    A DIRECT_PROCUREMENT subsumes a FUNDED_DOWNSTREAM_DEMAND anchored on the *same* program's
    appropriation (the appropriation funds that procurement — not distinct downstream demand). Grant-
    anchored downstream demand and genuine capacity buildout survive because they are separate money
    paths with their own evidence.
    """
    has_direct = any(c["mechanism"] == "DIRECT_PROCUREMENT" for c in candidates)
    kept = []
    for c in candidates:
        if (has_direct and c["mechanism"] == "FUNDED_DOWNSTREAM_DEMAND"
                and c["anchor"].get("record_kind") == "appropriation"):
            continue
        kept.append(c)
    # Deterministic order: most direct/strongest first.
    kept.sort(key=lambda c: (_DIRECTNESS_ORDER[c["directness"]], -c["confidence"], c["mechanism"]))
    return kept


_DIRECTNESS_ORDER = {"DIRECT": 0, "DOWNSTREAM": 1, "SECOND_ORDER": 2}


# --------------------------------------------------------------------------- catalyst build

def _catalyst_type(records: list[dict]) -> str:
    staged = _staged(records)
    kinds = {r.get("record_kind") for r in staged}
    stages = {r.get("stage") for r in staged}
    if any(_is_contradiction(r) for r in staged):
        return "SUPPLY_DISRUPTION"
    if any(r.get("obligation") for r in staged) or "rule" in kinds or "proposed_rule" in kinds:
        return "REGULATORY_MANDATE"
    if kinds & {"program_designation", "capacity_program"} or any(r.get("industrial_policy") for r in staged):
        return "CAPACITY_BUILDOUT"
    if stages & {"PROCUREMENT", "AWARD"}:
        return "PROCUREMENT_LIFECYCLE"
    if stages & {"FUNDING", "AUTHORIZATION"} or kinds & {"appropriation", "authorization"}:
        return "BUDGET_APPROPRIATION"
    return "PROGRAM_ESTABLISHMENT"


def build_catalyst(component_keys: list[str], records: list[dict], resolution) -> CapitalCatalyst | None:
    program_records = [r for r in _staged(records) if r["program_key"] in set(component_keys)]
    if not program_records:
        return None
    contradiction = any(_is_contradiction(r) for r in program_records)
    stages_present = [s for s in PRECURSOR_STAGES if s in {r["stage"] for r in program_records}]
    participants = resolve_participants(program_records)
    owner = next((p.name for p in participants if p.role == "PROGRAM_OWNER"), None) \
        or next((p.name for p in participants if p.role == "FUNDING_AUTHORITY"), None)

    chain_value = float((resolution.confidence or {}).get("value") or 0.0)
    confidence = max(chain_value, 0.6)  # a single strong staged record still establishes a real change
    if contradiction:
        confidence = min(confidence, 0.3)
    confidence = round(min(0.95, confidence), 3)

    rel_ids = [r.id for r in resolution.relationships
               if r.meta.get("program_key") in set(component_keys) or True]  # keep all chain edges as support
    earliest = _earliest(program_records)
    catalyst = CapitalCatalyst(
        program_key=min(component_keys),
        catalyst_type=_catalyst_type(program_records),
        summary=_catalyst_summary(program_records),
        controlling_institution=owner,
        triggering_evidence_ids=[_evidence_id(r) for r in program_records],
        supporting_relationship_ids=rel_ids,
        participants=[to_record(p) for p in participants],
        geography=next((r.get("place_of_performance") or r.get("geography") for r in program_records
                        if r.get("place_of_performance") or r.get("geography")), None),
        effective_date=next((r.get("effective_date") for r in program_records if r.get("effective_date")), None),
        stages_present=stages_present,
        confidence=confidence,
        first_observed_at=earliest,
        available_at=earliest,
        status="contradicted" if contradiction else "active",
        contradictions=[_evidence_id(r) for r in program_records if _is_contradiction(r)],
        meta={"program_keys": sorted(component_keys), "engine_version": CATALYST_ENGINE_VERSION,
              "record_count": len(program_records)},
    )
    catalyst.id = _catalyst_id(component_keys)
    return catalyst


def _catalyst_summary(records: list[dict]) -> str:
    owner = next((r.get("agency") for r in records if r.get("agency")), "an agency")
    lead = min(records, key=lambda r: (_STAGE_ORDER.get(r.get("stage"), 99), r.get("available_at") or ""))
    return f"{owner}: {lead.get('summary') or lead.get('record_kind') or 'capital program'}"


# --------------------------------------------------------------------------- consequence generation

def _timing(anchor: dict, records: list[dict]) -> dict:
    award = next((r for r in records if r.get("stage") == "AWARD"), None)
    return {
        "first_supportable_at": anchor.get("available_at"),
        "expected_at": (award or anchor).get("available_at"),
        "basis": f"mechanism supportable from {anchor.get('record_kind')} at {anchor.get('available_at')}",
    }


def _falsifiers(candidate: dict, records: list[dict], participants: list[Participant],
                capabilities: list, as_of: str | None) -> list[ConsequenceFalsifier]:
    anchor = candidate["anchor"]
    directness = candidate["directness"]
    out: list[ConsequenceFalsifier] = []
    roles = {p.role for p in participants}

    if any(_is_contradiction(r) for r in records):
        out.append(ConsequenceFalsifier("program_cancelled",
                   "a later same-program record records cancellation/rescission", fatal=True))
    if directness == "DIRECT" and not (roles & {"BUYER", "PRIME_RECIPIENT"}):
        out.append(ConsequenceFalsifier("no_identifiable_buyer",
                   "a direct procurement consequence requires a resolved buyer or prime recipient", fatal=True))
    if anchor.get("commercial_use") == "restricted":
        out.append(ConsequenceFalsifier("funding_restricted_from_commercial_use",
                   "funding is explicitly restricted from commercial procurement", fatal=True))
    if anchor.get("internal_self_performance"):
        out.append(ConsequenceFalsifier("internal_self_performance",
                   "the work is performed internally by the government/entity", fatal=True))
    if anchor.get("funding_not_appropriated"):
        out.append(ConsequenceFalsifier("funding_not_appropriated",
                   "authority exists but no funds have been appropriated", fatal=True))
    if candidate["mechanism"] == "DIRECT_PROCUREMENT" and anchor.get("already_awarded_closed"):
        out.append(ConsequenceFalsifier("already_awarded", "the requirement is already awarded and closed", fatal=False))
    if anchor.get("incumbent_locked"):
        out.append(ConsequenceFalsifier("incumbent_lock_in", "a locked incumbent leaves no capturable path", fatal=False))
    if directness == "SECOND_ORDER" and not anchor.get("second_order_corroborated"):
        out.append(ConsequenceFalsifier("speculative_second_order",
                   "second-order effect is plausible but uncorroborated; stays internal/WATCH", fatal=False))
    if directness == "DIRECT" and not capabilities:
        out.append(ConsequenceFalsifier("capability_mismatch",
                   "no specific capability class could be resolved for a direct procurement", fatal=False))
    return out


def _screen(candidate: dict, falsifiers: list[ConsequenceFalsifier], participants: list[Participant],
            capabilities: list) -> tuple[str, str]:
    fatal = [f for f in falsifiers if f.fatal]
    if fatal:
        return "REJECT", "fatal falsifier(s): " + ", ".join(f.code for f in fatal)
    roles = {p.role for p in participants}
    if candidate["directness"] == "DIRECT" and (roles & {"BUYER", "PRIME_RECIPIENT"}) and capabilities:
        return "STRIKE", "direct procurement with a resolved buyer and specific capability"
    if candidate["directness"] == "SECOND_ORDER":
        return "WATCH", "second-order consequence held internal pending corroboration"
    return "WATCH", "supported but one step removed from executable spend; monitor for a procurement path"


def _consequence_confidence(candidate: dict, falsifiers: list[ConsequenceFalsifier],
                            capabilities: list, value: dict) -> float:
    base = candidate["confidence"] * _DIRECTNESS_FACTOR[candidate["directness"]]
    base -= 0.15 * sum(1 for f in falsifiers if not f.fatal)
    if any(f.fatal for f in falsifiers):
        base = min(base, 0.15)
    if capabilities:
        base = min(0.95, base + 0.03 * min(len(capabilities), 2))
    return round(max(0.0, base), 3)


def generate_consequences(catalyst: CapitalCatalyst, records: list[dict], resolution,
                          *, as_of: str | None = None) -> list[CommercialConsequence]:
    """Zero or more economically distinct, separately evidenced commercial consequences for a catalyst.

    Zero is a common valid result (no evidenced commercial route). Consequences are never promoted to
    STRIKE automatically — each carries a *recommended* screened disposition after falsification, which
    the corpus checks for consistency with the frozen ``scoring_v1`` disposition.
    """
    keys = set(catalyst.meta.get("program_keys") or [catalyst.program_key])
    program_records = [r for r in _staged(records) if r["program_key"] in keys]
    consequences: list[CommercialConsequence] = []
    for candidate in classify_mechanisms(program_records):
        anchor = candidate["anchor"]
        evidence_records = [r for r in program_records if _evidence_id(r) in set(candidate["evidence_ids"])]
        participants = resolve_participants(program_records)
        capabilities = extract_capabilities(anchor, evidence_id=_evidence_id(anchor))
        cap_dicts = [to_record(c) for c in capabilities]
        value = estimate_value(
            explicit_amount=anchor.get("amount_usd"),
            appropriation_amount=next((r.get("amount_usd") for r in program_records
                                       if r.get("record_kind") == "appropriation"), None),
            program_amount=anchor.get("program_amount"),
            comparable_awards=anchor.get("comparable_awards") or (),
            project_fraction=tuple(anchor["project_fraction"]) if anchor.get("project_fraction") else None,
            evidence_ids=tuple(candidate["evidence_ids"]),
        )
        falsifiers = _falsifiers(candidate, program_records, participants, capabilities, as_of)
        disposition, basis = _screen(candidate, falsifiers, participants, capabilities)
        confidence = _consequence_confidence(candidate, falsifiers, cap_dicts, value.__dict__)
        # Participants economically relevant to this mechanism.
        relevant = _relevant_participants(candidate["mechanism"], participants)
        consequence = CommercialConsequence(
            catalyst_id=catalyst.id,
            program_key=catalyst.program_key,
            mechanism=candidate["mechanism"],
            directness=candidate["directness"],
            mechanism_confidence=candidate["confidence"],
            mechanism_rationale=candidate["rationale"],
            participants=[to_record(p) for p in relevant],
            capability_classes=cap_dicts,
            likely_spend_category=candidate["spend_category"],
            timing=_timing(anchor, program_records),
            geography=anchor.get("place_of_performance") or anchor.get("geography") or catalyst.geography,
            value=_value_record(value),
            evidence_ids=candidate["evidence_ids"],
            assumptions=_assumptions(candidate, participants),
            falsifiers=[to_record(f) for f in falsifiers],
            confidence=confidence,
            screened_disposition=disposition,
            screening_basis=basis,
            first_supportable_at=anchor.get("available_at"),
            meta={"engine_version": CATALYST_ENGINE_VERSION},
        )
        consequence.id = _consequence_id(catalyst.id, candidate["mechanism"], anchor["source_ref"])
        consequences.append(consequence)
    return consequences


def _relevant_participants(mechanism: str, participants: list[Participant]) -> list[Participant]:
    if mechanism == "DIRECT_PROCUREMENT":
        wanted = {"FUNDING_AUTHORITY", "PROGRAM_OWNER", "BUYER", "PRIME_RECIPIENT"}
    elif mechanism == "FUNDED_DOWNSTREAM_DEMAND":
        wanted = {"FUNDING_AUTHORITY", "PROGRAM_OWNER", "BENEFICIARY"}
    elif mechanism == "FORCED_COMPLIANCE_SPEND":
        wanted = {"PROGRAM_OWNER", "REGULATED_ENTITY", "AFFECTED_ENTITY"}
    else:
        wanted = {"FUNDING_AUTHORITY", "PROGRAM_OWNER", "BENEFICIARY", "AFFECTED_ENTITY", "SUPPLIER"}
    relevant = [p for p in participants if p.role in wanted]
    return relevant or participants


def _assumptions(candidate: dict, participants: list[Participant]) -> list[str]:
    out = []
    if candidate["directness"] != "DIRECT":
        out.append("commercial spend materializes downstream of the observed funding/policy event")
    if not any(p.role in ("BUYER", "PRIME_RECIPIENT") for p in participants):
        out.append("a specific buying entity emerges as the program advances")
    if candidate["mechanism"] == "INDUSTRIAL_CAPACITY_BUILDOUT":
        out.append("capacity expansion translates into procurable supplier/equipment demand")
    return out


def _value_record(value) -> dict:
    return {"status": value.status, "amount_usd": value.amount_usd, "low_usd": value.low_usd,
            "high_usd": value.high_usd, "method": value.method, "confidence": value.confidence,
            "inputs": value.inputs, "provenance": list(value.provenance)}


# --------------------------------------------------------------------------- top-level

def build_catalysts_and_consequences(records: list[dict], resolution, *, as_of: str | None = None):
    """One catalyst per connected program-chain component; each catalyst yields 0..N consequences."""
    catalysts, consequences = [], []
    for component in _program_components(records, resolution.relationships):
        catalyst = build_catalyst(component, records, resolution)
        if catalyst is None:
            continue
        catalysts.append(catalyst)
        consequences.extend(generate_consequences(catalyst, records, resolution, as_of=as_of))
    return catalysts, consequences


def persist(store, catalysts, consequences) -> None:
    for catalyst in catalysts:
        store.append("capital_catalysts", to_record(catalyst))
    for consequence in consequences:
        store.append("commercial_consequences", to_record(consequence))
