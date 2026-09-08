"""Raw USAspending award bytes -> evidence-backed company FACT records.

This module is the raw-source -> facts step: it turns archived USAspending
``spending_by_award`` JSON bytes into structured, temporally-provenanced
records about a company's contract history. It does not build profiles,
run capability extraction, or interpret vehicles beyond what is explicitly
named in the award text.

Self-contained: no imports from chains/replay/catalysts/fit/company/capabilities.
"""

from __future__ import annotations

import json
from typing import Any, Optional


def detect_vehicles(text: str) -> list[str]:
    """Detect explicit contract vehicles named in ``text``.

    Only recognizes explicit substrings (case-insensitive). Never infers a
    vehicle that is not named in the text.
    """
    if not text:
        return []
    upper = text.upper()
    found: set[str] = set()

    if "OASIS SB" in upper or "OASIS SMALL BUSINESS" in upper:
        found.add("GSA OASIS SB")
    elif "OASIS" in upper:
        found.add("GSA OASIS")

    # "GSA schedule" only applies to a bare GSA mention, not when GSA is part
    # of an explicit "GSA OASIS[...]" phrase (already captured above).
    stripped = (
        upper.replace("GSA OASIS SMALL BUSINESS", "")
        .replace("GSA OASIS SB", "")
        .replace("GSA OASIS", "")
    )
    if "GSA" in stripped:
        found.add("GSA schedule")

    if "SEWP" in upper:
        found.add("NASA SEWP")

    if "IDIQ" in upper:
        found.add("IDIQ")

    return sorted(found)


def parse_amount(value: Any) -> Optional[float]:
    """Safely parse an amount to float. Never raises; returns None on failure."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
    if isinstance(value, str):
        cleaned = value.strip().replace(",", "").replace("$", "")
        if not cleaned:
            return None
        try:
            return float(cleaned)
        except ValueError:
            return None
    return None


def parse_usaspending_awards(
    raw: bytes,
    *,
    company_name: str,
    source_id: str = "usaspending",
) -> dict:
    """Parse archived USAspending ``spending_by_award`` response bytes into facts.

    Returns a dict with keys: company_name, source_id, recipient_names, awards,
    contract_history, capability_records, scale, vehicles, buyer_agencies,
    award_count. See module docstring / caller contract for field semantics.
    """
    try:
        payload = json.loads(raw)
    except (TypeError, ValueError, json.JSONDecodeError):
        payload = {}

    results = payload.get("results") or []
    if not isinstance(results, list):
        results = []

    recipient_names: set[str] = set()
    # dedupe by Award ID, keeping the row with the highest Award Amount
    best_by_award_ref: dict[str, dict] = {}
    best_amount_by_award_ref: dict[str, float] = {}

    for row in results:
        if not isinstance(row, dict):
            continue

        award_ref = row.get("Award ID")
        if not award_ref:
            # a row missing Award ID is skipped
            continue

        recipient_name = row.get("Recipient Name")
        if recipient_name:
            recipient_names.add(recipient_name)

        amount = parse_amount(row.get("Award Amount"))
        compare_amount = amount if amount is not None else float("-inf")

        prior_amount = best_amount_by_award_ref.get(award_ref)
        if prior_amount is not None and compare_amount <= prior_amount:
            continue

        best_by_award_ref[award_ref] = row
        best_amount_by_award_ref[award_ref] = compare_amount

    awards: list[dict] = []
    for award_ref, row in best_by_award_ref.items():
        generated_internal_id = row.get("generated_internal_id")
        source_url = (
            f"https://www.usaspending.gov/award/{generated_internal_id}"
            if generated_internal_id
            else None
        )
        agency = row.get("Awarding Agency")
        sub_agency = row.get("Awarding Sub Agency")
        buyer_agency = sub_agency or agency
        amount_usd = parse_amount(row.get("Award Amount"))
        start_date = row.get("Start Date")
        end_date = row.get("End Date")
        award_type = row.get("Contract Award Type")
        description = row.get("Description")
        naics = row.get("NAICS Code")
        psc = row.get("PSC Code")

        awards.append(
            {
                "award_ref": award_ref,
                "generated_internal_id": generated_internal_id,
                "source_url": source_url,
                "agency": agency,
                "sub_agency": sub_agency,
                "buyer_agency": buyer_agency,
                "amount_usd": amount_usd,
                "start_date": start_date,
                "end_date": end_date,
                "award_type": award_type,
                "description": description,
                "naics": naics,
                "psc": psc,
                "role": "prime",
                "available_at": start_date,
                "observed_at": None,
            }
        )

    # deterministic ordering: sort by -amount then award_ref
    def _sort_key(a: dict) -> tuple:
        amount = a["amount_usd"] if a["amount_usd"] is not None else float("-inf")
        return (-amount, a["award_ref"])

    awards.sort(key=_sort_key)

    contract_history: list[dict] = []
    capability_records: list[dict] = []
    vehicles: set[str] = set()
    buyer_agencies: set[str] = set()
    max_amount: Optional[float] = None

    for award in awards:
        contract_history.append(
            {
                "agency": award["buyer_agency"],
                "naics": award["naics"],
                "psc": award["psc"],
                "value_usd": award["amount_usd"],
                "role": "prime",
                "award_ref": award["award_ref"],
                "program_key": None,
                "description": award["description"],
                "available_at": award["start_date"],
            }
        )

        description = award["description"]
        if description:
            capability_records.append(
                {
                    "source_id": source_id,
                    "source_ref": award["award_ref"],
                    "available_at": award["start_date"],
                    "description": description,
                    "naics": award["naics"],
                    "psc": award["psc"],
                }
            )
            vehicles.update(detect_vehicles(description))

        if award["buyer_agency"]:
            buyer_agencies.add(award["buyer_agency"])

        if award["amount_usd"] is not None:
            if max_amount is None or award["amount_usd"] > max_amount:
                max_amount = award["amount_usd"]

    return {
        "company_name": company_name,
        "source_id": source_id,
        "recipient_names": sorted(recipient_names),
        "awards": awards,
        "contract_history": contract_history,
        "capability_records": capability_records,
        "scale": {"max_contract_usd": max_amount},
        "vehicles": sorted(vehicles),
        "buyer_agencies": sorted(buyer_agencies),
        "award_count": len(awards),
    }


# ---------------------------------------------------------------------------
# Point-in-time profile construction (M9 temporal gate)
# ---------------------------------------------------------------------------
# profile_as_of builds a CompanyProfile from parsed award facts using ONLY evidence
# knowable at a historical cutoff. Point-in-time filtering (available_at <= cutoff for
# both capability evidence and contract history) is delegated to company.build_profile,
# so future awards / facility facts / capability statements cannot leak backward.

def load_parsed(path: str, *, company_name: str) -> dict:
    """Parse an archived USAspending fixture on disk into fact records."""
    from pathlib import Path

    return parse_usaspending_awards(Path(path).read_bytes(), company_name=company_name)


def profile_as_of(company_name: str, parsed: dict, cutoff: Optional[str], *,
                  aliases=(), geography=(), certifications=(), clearances=(),
                  partners=(), exclusions=(), meta_extra: Optional[dict] = None):
    """Build a CompanyProfile for ``company_name`` as of ``cutoff`` from parsed award facts.

    Only USAspending-grounded contract/capability evidence dated at or before the cutoff is used.
    Non-award facts (HQ geography, certifications, clearances) are official/primary-source inputs the
    caller supplies explicitly — never inferred here."""
    from .company import build_profile

    # Scale is a temporal fact too: derive the max known contract value from awards knowable at the
    # cutoff, never the all-time maximum (a future mega-award must not inflate an earlier profile).
    def _knowable(award):
        at = award.get("available_at")
        return at and (cutoff is None or at <= cutoff)

    known_awards = [a for a in parsed.get("awards", []) if _knowable(a)]
    max_known = max((a["amount_usd"] for a in known_awards if a.get("amount_usd")), default=None)
    scale = {"max_contract_usd": max_known} if max_known is not None else {}
    naics = sorted({a["naics"] for a in known_awards if a.get("naics")})
    psc = sorted({a["psc"] for a in known_awards if a.get("psc")})
    # Vehicles and buyer agencies are temporal facts too — derive them only from awards knowable at
    # the cutoff, never all-time.
    known_vehicles = sorted({v for a in known_awards for v in detect_vehicles(a.get("description") or "")})
    known_buyers = sorted({a["buyer_agency"] for a in known_awards if a.get("buyer_agency")})
    meta = {"contract_vehicles": known_vehicles,
            "buyer_agencies": known_buyers,
            "grounding_source": parsed.get("source_id", "usaspending")}
    meta.update(meta_extra or {})
    profile = build_profile(
        company_name,
        parsed.get("capability_records", []),
        aliases=list(aliases),
        naics=naics,
        psc=psc,
        certifications=list(certifications),
        clearances=list(clearances),
        geography=list(geography),
        scale=scale,
        contract_history=parsed.get("contract_history", []),
        partners=list(partners),
        exclusions=list(exclusions),
        as_of=cutoff,
    )
    profile.meta.update(meta)
    return profile


def first_supportable_capability_date(parsed: dict, label: str) -> Optional[str]:
    """Earliest available_at at which ``label`` becomes supportable from award evidence, else None.

    Answers "when did we first have evidence of capability X?" without future knowledge."""
    from .capabilities import extract_capabilities

    dates = []
    for record in parsed.get("capability_records", []):
        labels = {c.label for c in extract_capabilities(record)}
        if label in labels and record.get("available_at"):
            dates.append(record["available_at"])
    return min(dates) if dates else None
