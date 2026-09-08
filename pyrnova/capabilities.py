"""CAPABILITIES — deterministic extraction of the SPECIFIC capability class(es) an opportunity requires.

Answers: "what specific capability does this opportunity require?" — derived from a source-native
record (NAICS, PSC, title/description text), with provenance back to the structured fields and any
supplied evidence id. Distinct from `match.CapabilityProfile`, which describes a *customer's* declared
capability profile; this module extracts the capability *demanded by an opportunity itself*.

Hard rule: broad, non-actionable labels ("technology", "consulting", "services", "manufacturing",
"support", "solutions", "management", "software" alone) are never acceptable as a capability class.
A record whose only signal is such a broad word yields no capability class at all — an empty list is
the deterministic and correct answer when nothing specific is supportable.

Self-contained: no imports from chains/replay/catalysts.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass(frozen=True)
class CapabilityClass:
    """A specific capability class an opportunity requires, with provenance."""

    label: str                       # normalized snake_case specific label
    display: str                     # human-readable label
    confidence: float                # 0..1
    evidence_ids: tuple[str, ...]
    source_fields: dict
    basis: str                       # short human rationale


# ---------------------------------------------------------------------------
# Controlled vocabulary
# ---------------------------------------------------------------------------

# Broad/generic terms that are NEVER acceptable as a standalone capability label or the sole basis
# for one. A phrase match consisting only of these words (or containing one as its entire text) is
# rejected.
BROAD_STOPWORDS: frozenset[str] = frozenset({
    "technology",
    "consulting",
    "services",
    "service",
    "manufacturing",
    "support",
    "solutions",
    "solution",
    "management",
    "software",
    "products",
    "systems",
    "engineering",
    "professional",
})

# NAICS code prefix -> (label, display). Longest matching prefix wins.
NAICS_CAPABILITIES: dict[str, tuple[str, str]] = {
    "334511": ("radar_component_manufacturing", "Radar / search, detection, navigation, guidance, and nautical system manufacturing"),
    "334220": ("radio_tv_broadcast_communications_equipment", "Radio and television broadcasting and wireless communications equipment manufacturing"),
    "334419": ("electronic_component_manufacturing", "Other electronic component manufacturing"),
    "333242": ("semiconductor_process_equipment", "Semiconductor machinery manufacturing"),
    "334413": ("semiconductor_device_manufacturing", "Semiconductor and related device manufacturing"),
    "562910": ("environmental_remediation", "Environmental remediation services"),
    "541620": ("environmental_consulting", "Environmental consulting services"),
    "541512": ("cloud_computer_systems_design", "Computer systems design services (cloud/IT)"),
    "541519": ("it_security_services", "Other computer related services (IT security)"),
    "238210": ("electrical_construction", "Electrical contractors and other wiring installation contractors"),
    "336611": ("shipbuilding", "Ship building and repairing"),
    "336413": ("aerospace_vehicle_component_manufacturing", "Other aircraft parts and auxiliary equipment manufacturing"),
    "336411": ("aircraft_manufacturing", "Aircraft manufacturing"),
    "335911": ("battery_manufacturing", "Storage battery manufacturing"),
    "221118": ("electric_power_generation", "Other electric power generation"),
    "237130": ("power_electric_line_construction", "Power and communication line and related structures construction"),
    "541715": ("directed_energy_research", "Research and development in physical, engineering, and life sciences"),
    "488190": ("air_traffic_support_services", "Other support activities for air transportation"),
    "928110": ("national_security_operations", "National security operations"),
}

# PSC code prefix -> (label, display). Longest matching prefix wins. Kept specific, never broad.
PSC_CAPABILITIES: dict[str, tuple[str, str]] = {
    "5840": ("radar_equipment", "Radar equipment, complete"),
    "5841": ("radar_navigation_equipment", "Radio and navigation equipment (radar-related)"),
    "5895": ("electronic_countermeasures_equipment", "Electronic countermeasures equipment"),
    "F003": ("environmental_remediation", "Environmental remediation"),
    "F004": ("environmental_restoration", "Environmental restoration services"),
    "D310": ("cloud_security_assessment", "IT and telecom - cyber security and data backup"),
    "D302": ("it_systems_development", "IT systems development services"),
    "Z2AA": ("electrical_construction", "Construction of electrical work"),
    "5961": ("semiconductor_devices", "Semiconductor devices and associated hardware"),
    "6140": ("battery_manufacturing", "Batteries, secondary type"),
    "1810": ("space_vehicle_hardware", "Space vehicle propulsion units and components"),
    "1905": ("shipbuilding", "Ships, small craft, pontoons, and floating docks"),
    "AC13": ("directed_energy_research", "Defense R&D - directed energy"),
}

# Specific keyword phrases (2+ words, or a single clearly-specific term) -> (label, display, weight).
# weight: "phrase" (multi-word, 0.7) or "keyword" (single specific word, 0.55).
PHRASE_CAPABILITIES: list[tuple[str, str, str, str]] = [
    ("environmental remediation", "environmental_remediation", "Environmental remediation services", "phrase"),
    ("environmental restoration", "environmental_remediation", "Environmental remediation services", "phrase"),
    ("cloud security", "cloud_security_assessment", "Cloud security assessment", "phrase"),
    ("cloud security assessment", "cloud_security_assessment", "Cloud security assessment", "phrase"),
    ("air traffic control", "air_traffic_control_systems", "Air traffic control systems", "phrase"),
    ("directed energy", "directed_energy_research", "Directed energy research", "phrase"),
    ("battery manufacturing", "battery_manufacturing", "Battery manufacturing", "phrase"),
    ("electrical construction", "electrical_construction", "Electrical construction", "phrase"),
    ("semiconductor process", "semiconductor_process_equipment", "Semiconductor process equipment", "phrase"),
    ("radar component", "radar_component_manufacturing", "Radar component manufacturing", "phrase"),
    ("shipbuilding repair", "shipbuilding", "Shipbuilding and repair", "phrase"),
    ("wireless communications equipment", "radio_tv_broadcast_communications_equipment",
     "Wireless communications equipment", "phrase"),
    ("radar", "radar_component_manufacturing", "Radar component manufacturing", "keyword"),
    ("semiconductor", "semiconductor_process_equipment", "Semiconductor process equipment", "keyword"),
    ("shipbuilding", "shipbuilding", "Shipbuilding", "keyword"),
    # M9 real defense-services capability classes (specific specialties, not broad "engineering").
    ("hardware in the loop", "hardware_in_the_loop_simulation", "Hardware-in-the-loop simulation", "phrase"),
    ("hardware-in-the-loop", "hardware_in_the_loop_simulation", "Hardware-in-the-loop simulation", "phrase"),
    ("hwil", "hardware_in_the_loop_simulation", "Hardware-in-the-loop simulation", "keyword"),
    ("missile defense", "missile_defense_engineering", "Missile defense systems engineering", "phrase"),
    ("modeling and simulation", "modeling_and_simulation", "Modeling and simulation", "phrase"),
    ("modeling & simulation", "modeling_and_simulation", "Modeling and simulation", "phrase"),
    ("test and evaluation", "test_and_evaluation_services", "Test and evaluation services", "phrase"),
    ("systems engineering and technical assistance", "systems_engineering_technical_assistance",
     "Systems engineering and technical assistance (SETA)", "phrase"),
    ("system engineering and technical assistance", "systems_engineering_technical_assistance",
     "Systems engineering and technical assistance (SETA)", "phrase"),
    ("specialty engineering", "specialty_engineering", "Specialty engineering", "phrase"),
]

_CONF_NAICS = 0.9
_CONF_PSC = 0.9
_CONF_PHRASE = 0.7
_CONF_KEYWORD = 0.55


def _snake(text: str) -> str:
    text = re.sub(r"[^a-z0-9]+", "_", text.strip().lower())
    return text.strip("_")


def _display(label: str) -> str:
    words = label.replace("_", " ").split()
    if not words:
        return label
    return " ".join([words[0].capitalize()] + words[1:])


def _is_broad_only(text: str) -> bool:
    """True if the normalized text carries no signal beyond BROAD_STOPWORDS."""
    tokens = [t for t in re.split(r"[^a-z0-9]+", text.lower()) if t]
    if not tokens:
        return True
    return all(t in BROAD_STOPWORDS for t in tokens)


def _naics_lookup(naics: str) -> tuple[str, str] | None:
    naics = re.sub(r"\D", "", naics or "")
    if not naics:
        return None
    best: tuple[str, str] | None = None
    best_len = -1
    for prefix, val in NAICS_CAPABILITIES.items():
        if naics.startswith(prefix) and len(prefix) > best_len:
            best = val
            best_len = len(prefix)
    return best


def _psc_lookup(psc: str) -> tuple[str, str] | None:
    psc = (psc or "").strip().upper()
    if not psc:
        return None
    best: tuple[str, str] | None = None
    best_len = -1
    for prefix, val in PSC_CAPABILITIES.items():
        if psc.startswith(prefix) and len(prefix) > best_len:
            best = val
            best_len = len(prefix)
    return best


def _phrase_matches(text: str) -> list[tuple[str, str, float]]:
    """Return list of (label, display, confidence) for phrase/keyword matches in text."""
    if not text:
        return []
    hay = text.lower()
    results: list[tuple[str, str, float]] = []
    seen_labels: set[str] = set()
    for phrase, label, display, kind in PHRASE_CAPABILITIES:
        if phrase in hay:
            if _is_broad_only(phrase):
                continue
            if label in seen_labels:
                continue
            conf = _CONF_PHRASE if kind == "phrase" else _CONF_KEYWORD
            results.append((label, display, conf))
            seen_labels.add(label)
    return results


def extract_capabilities(record: dict, *, evidence_id: str | None = None) -> list[CapabilityClass]:
    """Derive specific capability class(es) required by an opportunity from a source-native record.

    Reads (tolerating absent keys): naics, psc, title, summary/description, record_kind,
    capability_terms (an optional list of free-text terms).

    Priority: NAICS > PSC > phrase/keyword text match. A structured-code match outranks a phrase
    match and carries higher confidence. Results are deduplicated by label (highest confidence kept,
    provenance merged) and returned sorted by (-confidence, label). Broad-only signal yields [].
    """
    record = record or {}
    evidence_ids: tuple[str, ...] = (evidence_id,) if evidence_id else ()

    text_parts = [
        str(record.get("title") or ""),
        str(record.get("summary") or record.get("description") or ""),
    ]
    terms = record.get("capability_terms") or []
    if isinstance(terms, (list, tuple)):
        text_parts.extend(str(t) for t in terms)
    free_text = " ".join(p for p in text_parts if p).strip()

    # Collect raw candidates: label -> dict(confidence, source_fields, basis)
    candidates: dict[str, dict] = {}

    def _add(label: str, display: str, confidence: float, source_fields: dict, basis: str) -> None:
        existing = candidates.get(label)
        if existing is None or confidence > existing["confidence"]:
            merged_fields = dict(existing["source_fields"]) if existing else {}
            merged_fields.update(source_fields)
            candidates[label] = {
                "display": display,
                "confidence": confidence,
                "source_fields": merged_fields,
                "basis": basis if existing is None or confidence > existing["confidence"] else existing["basis"],
            }
        else:
            existing["source_fields"].update(source_fields)

    naics = record.get("naics")
    if naics:
        hit = _naics_lookup(str(naics))
        if hit:
            label, display = hit
            _add(label, display, _CONF_NAICS, {"naics": str(naics)}, f"NAICS {naics} maps to {display.lower()}")

    psc = record.get("psc")
    if psc:
        hit = _psc_lookup(str(psc))
        if hit:
            label, display = hit
            _add(label, display, _CONF_PSC, {"psc": str(psc)}, f"PSC {psc} maps to {display.lower()}")

    for label, display, conf in _phrase_matches(free_text):
        # find which phrase matched for source_fields provenance
        matched_phrase = None
        for phrase, plabel, pdisplay, _kind in PHRASE_CAPABILITIES:
            if plabel == label and phrase in free_text.lower():
                matched_phrase = phrase
                break
        _add(label, display, conf, {"phrase": matched_phrase or label},
             f"text phrase '{matched_phrase}' maps to {display.lower()}")

    results: list[CapabilityClass] = []
    for label, info in candidates.items():
        results.append(CapabilityClass(
            label=label,
            display=info["display"],
            confidence=round(info["confidence"], 3),
            evidence_ids=evidence_ids,
            source_fields=info["source_fields"],
            basis=info["basis"],
        ))

    results.sort(key=lambda c: (-c.confidence, c.label))
    return results
