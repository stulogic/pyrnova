"""M18 — archived, authoritative ADVERSE-EVENT observations as first-class OBSERVED catalysts.

M15–M17 proved threat/exposure/propagation semantics, but every direct-threat catalyst was *modeled*
(a structured, dated hypothetical attached to a real exposure). M18's primary gap is empirical: the
adverse event itself must be REAL — an authoritative record we archived, with a source-native identifier,
a publication date, and provenance — not a hand-authored change.

This module normalizes archived source bytes into first-class **OBSERVED** catalysts that flow into the
existing :func:`pyrnova.threat.assess_threats` engine (no parallel threat architecture). The first
adverse-event family is the **Federal Register** (BIS/Commerce export-control & Entity List rules): real,
dated, RIN-bearing regulatory actions archived once at
``examples/real_evidence/federal_register_bis_export_controls.json`` and replayed offline.

Catalyst authority (Workstream H) is a durable, first-class distinction:

* ``OBSERVED``  — grounded in an archived authoritative source record (has a source-native id + date).
* ``MODELED``   — a structured hypothetical (the M16/M17 convention). This is the default when a catalyst
  record declares no ``catalyst_class``, so no earlier fixture is silently relabelled OBSERVED.
* ``SYNTHETIC`` / ``PROBE`` — deliberately fabricated test/probe inputs.

Discipline preserved: an OBSERVED adverse event is NOT itself an exposure. A BIS Entity-List revision does
not threaten Company X unless X has an *evidenced* exposure to the controlled activity AND (for
propagation) an *evidenced* relationship edge. Normalization keeps the raw record reachable and discards
nothing potentially useful. Self-contained: no imports from scoring/fit/replay/threat.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Optional

FEDERAL_REGISTER_SOURCE_ID = "federal_register"

# Durable catalyst-authority vocabulary (Workstream H).
CATALYST_CLASSES = ("OBSERVED", "MODELED", "SYNTHETIC", "PROBE")


def catalyst_class(record: Optional[dict]) -> str:
    """The catalyst authority of a catalyst record. Absent an explicit class the record is MODELED —
    old modeled fixtures are therefore never silently promoted to OBSERVED."""
    value = (record or {}).get("catalyst_class")
    return value if value in CATALYST_CLASSES else "MODELED"


def _agency_names(agencies: Any) -> list[str]:
    out = []
    for a in agencies or ():
        if isinstance(a, dict) and a.get("name"):
            out.append(a["name"])
    return out


def _event_type(title: str, action: str) -> str:
    """Coarse, deterministic adverse-event type from the source record's own text."""
    t = (title or "").lower()
    if "entity list" in t:
        return "ENTITY_LIST_REVISION"
    if "removal" in t:
        return "EXPORT_CONTROL_RELIEF"
    return "EXPORT_CONTROL_ACTION"


def parse_federal_register_adverse(
    raw: bytes | str, *, source_id: str = FEDERAL_REGISTER_SOURCE_ID,
) -> dict:
    """Parse archived Federal Register bytes into OBSERVED adverse-event records.

    Accepts either the raw ``/documents.json`` payload (``{"results": [...]}``) or the committed evidence
    wrapper (``{"provenance": {...}, "results": [...]}``). Never raises; returns empty structures on bad
    input. Each event retains the source-native identifier (FR document number), event type, agency,
    publication/knowability date, regulation ids (RIN), docket ids, source url, an archive hash of the raw
    bytes, and a pointer back to the raw record — nothing potentially useful is dropped.
    """
    try:
        payload = json.loads(raw) if isinstance(raw, (bytes, str, bytearray)) else raw
    except (TypeError, ValueError, json.JSONDecodeError):
        payload = {}
    if not isinstance(payload, dict):
        payload = {}
    results = payload.get("results")
    if not isinstance(results, list):
        results = []
    raw_bytes = raw.encode("utf-8") if isinstance(raw, str) else (raw if isinstance(raw, (bytes, bytearray)) else b"")
    archive_hash = hashlib.sha256(bytes(raw_bytes)).hexdigest() if raw_bytes else None

    events: list[dict] = []
    for row in results:
        if not isinstance(row, dict):
            continue
        doc = row.get("document_number")
        if not doc:
            continue
        agencies = _agency_names(row.get("agencies"))
        pub = row.get("publication_date")
        events.append({
            "event_id": str(doc),
            "catalyst_class": "OBSERVED",
            "source_id": source_id,
            "family": "regulatory_adverse_event",
            "event_type": _event_type(row.get("title") or "", row.get("action") or ""),
            "title": row.get("title"),
            "abstract": row.get("abstract"),
            "action": row.get("action"),
            "doc_type": row.get("type"),
            "agency": agencies[-1] if agencies else None,
            "agencies": agencies,
            "publication_date": pub,
            "available_at": pub,  # a published rule is knowable at publication
            "regulation_ids": list(row.get("regulation_id_numbers") or []),
            "docket_ids": list(row.get("docket_ids") or []),
            "source_url": row.get("html_url"),
            "source_ref": f"fr:doc:{doc}",
            "evidence_id": f"fr:doc:{doc}",
            "archive_hash": archive_hash,
            "raw": row,
        })
    events.sort(key=lambda e: (e.get("publication_date") or "", e["event_id"]), reverse=True)
    return {"source_id": source_id, "family": "regulatory_adverse_event",
            "archive_hash": archive_hash, "events": events}


def regulation_target_ref(event: dict) -> str:
    """A deterministic exposure/catalyst join key for a regulatory adverse event.

    Prefers the Regulation Identifier Number (RIN); falls back to the FR document number. An exposed
    company's declared REGULATION exposure must carry the SAME ``target_ref`` for the threat engine to
    link them (a broad rule never threatens a company with no evidenced exposure to it)."""
    rins = event.get("regulation_ids") or []
    if rins:
        return f"EAR:{rins[0]}"
    return f"fr:reg:{event.get('event_id')}"


def to_regulatory_catalyst(
    event: dict,
    *,
    target_ref: Optional[str] = None,
    evidence_strength: int = 4,
    eligibility_gated: bool = False,
    compliance_cost_usd: Optional[float] = None,
    horizon: str = "MEDIUM_TERM",
) -> dict:
    """Turn one OBSERVED adverse event into a catalyst record the threat engine consumes.

    Emits a ``regulatory_mandate`` catalyst (see ``pyrnova.threat._assess_regulatory``) carrying the
    OBSERVED authority, the source-native evidence id, publication date (knowability), and a deterministic
    ``target_ref``. It does NOT create an exposure — a company is only threatened if it separately declares
    a REGULATION exposure with the same ``target_ref``.
    """
    tref = target_ref or regulation_target_ref(event)
    return {
        "catalyst_kind": "regulatory_mandate",
        "catalyst_class": event.get("catalyst_class", "OBSERVED"),
        "catalyst_id": f"cat_fr_{event.get('event_id')}",
        "family": "regulatory_adverse_event",
        "target_ref": tref,
        "available_at": event.get("available_at"),
        "source_id": event.get("source_id"),
        "source_ref": event.get("source_ref"),
        "evidence_id": event.get("evidence_id"),
        "evidence_strength": int(evidence_strength),
        "eligibility_gated": bool(eligibility_gated),
        "compliance_cost_usd": compliance_cost_usd,
        "horizon": horizon,
        "summary": event.get("title"),
        "event_type": event.get("event_type"),
    }


USASPENDING_SOURCE_ID = "usaspending"

# Coarse, deterministic contract-modification event type from the source-native action fields.
def _contract_event_type(action_type: Optional[str], action_desc: Optional[str], fao: float) -> str:
    desc = (action_desc or "").upper()
    at = (action_type or "").upper()
    if "TERMINAT" in desc or at in ("F", "G", "H", "J", "K", "L", "M") and "TERMINAT" in desc:
        return "CONTRACT_TERMINATION"
    if fao < 0:
        return "CONTRACT_DEOBLIGATION"
    return "CONTRACT_MODIFICATION"


def contract_target_ref(event: dict) -> str:
    """Deterministic exposure/catalyst join key for a contract-modification adverse event.

    The key is the globally-unique contract PIID. An exposed company's PROGRAM/INCUMBENT exposure must
    carry the SAME ``target_ref`` (its own award's PIID) for the threat engine to link them — a
    deterministic native-id join, never a name/industry/geography resemblance. This is exactly the
    *deterministic observed exposure* anchor M18 lacked (M19 Workstream A)."""
    return str(event.get("piid") or event.get("event_id") or "")


def parse_usaspending_contract_modifications(
    raw: bytes | str, *, source_id: str = USASPENDING_SOURCE_ID,
) -> dict:
    """Parse archived USAspending contract-modification bytes into OBSERVED adverse-event records.

    This is M19's **second adverse-event family**, materially independent of the BIS/Federal Register
    export-control family: a real, dated, source-native contract *deobligation* (negative
    ``federal_action_obligation`` modification) on a specific PIID held by a specific recipient (UEI). It
    is the archived evidence for a **deterministic observed exposure** — the incumbent recipient is joined
    to the event by exact native identifiers (PIID + recipient UEI), not by inference.

    Accepts the committed evidence wrapper (``{"provenance": {...}, "results": [...]}``) or a bare
    ``{"results": [...]}``. Each result row carries the award identity (``piid``, ``recipient_uei``,
    ``recipient_name``) alongside the transaction fields (``modification_number``, ``action_date``,
    ``action_type``/``action_type_description``, ``federal_action_obligation``). Never raises; returns
    empty structures on bad input. Nothing potentially useful is discarded — the raw row is retained.

    Discipline: a deobligation is NOT itself a threat. Source-native semantics are preserved (a small
    routine funding pull-back is not a program cancellation); the threat engine applies a materiality gate
    and requires a matching deterministic PROGRAM exposure before any threat is emitted.
    """
    try:
        payload = json.loads(raw) if isinstance(raw, (bytes, str, bytearray)) else raw
    except (TypeError, ValueError, json.JSONDecodeError):
        payload = {}
    if not isinstance(payload, dict):
        payload = {}
    results = payload.get("results")
    if not isinstance(results, list):
        results = []
    raw_bytes = raw.encode("utf-8") if isinstance(raw, str) else (raw if isinstance(raw, (bytes, bytearray)) else b"")
    archive_hash = hashlib.sha256(bytes(raw_bytes)).hexdigest() if raw_bytes else None

    events: list[dict] = []
    for row in results:
        if not isinstance(row, dict):
            continue
        piid = row.get("piid")
        mod = row.get("modification_number")
        if not piid or mod is None:
            continue
        try:
            fao = float(row.get("federal_action_obligation"))
        except (TypeError, ValueError):
            continue
        action_date = row.get("action_date")
        events.append({
            "event_id": f"{piid}:{mod}",
            "catalyst_class": "OBSERVED",
            "source_id": source_id,
            "family": "contract_modification",
            "event_type": _contract_event_type(row.get("action_type"),
                                               row.get("action_type_description"), fao),
            "piid": str(piid),
            "modification_number": str(mod),
            "recipient_name": row.get("recipient_name"),
            "recipient_uei": (str(row.get("recipient_uei")).strip().upper()
                              if row.get("recipient_uei") else None),
            "agency": row.get("awarding_agency"),
            "action_type": row.get("action_type"),
            "action_type_description": row.get("action_type_description"),
            "federal_action_obligation": fao,
            # Magnitude of the funding change (positive for a deobligation) — what the contraction puts at
            # risk. Source-native sign is retained separately in ``federal_action_obligation``.
            "amount_delta_usd": abs(fao) if fao < 0 else 0.0,
            "action_date": action_date,
            "available_at": action_date,  # a modification is knowable at its action date
            "source_ref": f"usaspending:txn:{piid}:{mod}",
            "evidence_id": f"usaspending:txn:{piid}:{mod}",
            "generated_internal_id": row.get("generated_internal_id"),
            "archive_hash": archive_hash,
            "raw": row,
        })
    events.sort(key=lambda e: (e.get("action_date") or "", e["event_id"]), reverse=True)
    return {"source_id": source_id, "family": "contract_modification",
            "archive_hash": archive_hash, "events": events}


def to_contract_contraction_catalyst(
    event: dict,
    *,
    evidence_strength: int = 5,
    materiality_floor_usd: Optional[float] = None,
    horizon: str = "MEDIUM_TERM",
) -> dict:
    """Turn one OBSERVED contract-deobligation event into a ``funding_reduction`` catalyst the existing
    threat engine consumes (``pyrnova.threat._assess_program_change`` -> ``PROGRAM_CONTRACTION``).

    The catalyst's ``target_ref`` is the exact PIID, so it links ONLY to a subject whose deterministic
    PROGRAM/INCUMBENT exposure is that same PIID (deterministic native-id join). It carries the OBSERVED
    authority, the source-native evidence id, the action date (knowability), the deobligated magnitude,
    and an optional ``materiality_floor_usd`` (a routine sub-threshold pull-back is rejected IMMATERIAL by
    the engine — deterministic identity alone never guarantees a threat). It creates NO exposure.
    """
    piid = contract_target_ref(event)
    cat = {
        "catalyst_kind": "funding_reduction",
        "catalyst_class": event.get("catalyst_class", "OBSERVED"),
        "catalyst_id": f"cat_usasp_{event.get('event_id')}",
        "family": "contract_modification",
        "program_key": piid,
        "target_ref": piid,
        "available_at": event.get("available_at"),
        "source_id": event.get("source_id"),
        "source_ref": event.get("source_ref"),
        "evidence_id": event.get("evidence_id"),
        "evidence_strength": int(evidence_strength),
        "amount_delta_usd": event.get("amount_delta_usd"),
        "recipient_uei": event.get("recipient_uei"),
        "horizon": horizon,
        "summary": (f"{event.get('event_type', 'CONTRACT_MODIFICATION').replace('_', ' ').title()} "
                    f"on {piid} ({event.get('modification_number')})"),
        "event_type": event.get("event_type"),
    }
    if materiality_floor_usd is not None:
        cat["materiality_floor_usd"] = float(materiality_floor_usd)
    return cat


def summarize_adverse_events(parsed: dict) -> dict:
    """Compact rollup of an archived adverse-event batch (denominator-honest, empty-safe)."""
    events = parsed.get("events", [])
    by_type: dict[str, int] = {}
    by_agency: dict[str, int] = {}
    for e in events:
        by_type[e["event_type"]] = by_type.get(e["event_type"], 0) + 1
        ag = e.get("agency") or "unknown"
        by_agency[ag] = by_agency.get(ag, 0) + 1
    return {
        "source_id": parsed.get("source_id"),
        "family": parsed.get("family"),
        "events_total": len(events),
        "observed_events": sum(1 for e in events if e.get("catalyst_class") == "OBSERVED"),
        "by_event_type": dict(sorted(by_type.items())),
        "by_agency": dict(sorted(by_agency.items())),
        "archive_hash": parsed.get("archive_hash"),
    }
