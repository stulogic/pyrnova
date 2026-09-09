"""Archived USAspending sub-award bytes -> subaward records, partner edges, sub-role history (M10).

Turns an archived ``spending_by_award`` (spending_level=subawards) response into:
  - sub-award records where the target company is the SUBRECIPIENT (deduped),
  - authoritative partner edges (a prime the company *repeatedly* subcontracts under), and
  - sub-role ``contract_history`` rows (role="sub") plus capability records from sub descriptions.

TEAM doctrine (M10): a partner edge is *authoritative* only on repetition — ≥2 sub-awards under the
same prime, or sub-awards spanning ≥2 distinct years. A single occurrence is weak and is retained for
observability but does NOT populate ``profile.partners`` (so it cannot fire TEAM). This prevents a
one-off pairing from manufacturing a teaming relationship.

Self-contained: no imports from fit/replay/scoring/company.
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from typing import Any, Optional

SUBAWARD_SOURCE_ID = "usaspending_subawards"

_SUFFIXES = {"inc", "incorporated", "llc", "corp", "corporation", "co", "company", "ltd", "limited"}


def _canon(name: str) -> str:
    text = re.sub(r"[^a-z0-9\s]+", " ", (name or "").lower())
    tokens = [t for t in text.split() if t]
    while tokens and tokens[-1] in _SUFFIXES:
        tokens.pop()
    return " ".join(tokens)


def _amount(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        cleaned = value.strip().replace(",", "").replace("$", "")
        try:
            return float(cleaned) if cleaned else None
        except ValueError:
            return None
    return None


def _code(value: Any) -> Optional[str]:
    if isinstance(value, dict):
        return value.get("code")
    return value


def parse_subawards(raw: bytes, *, company_name: str, source_id: str = SUBAWARD_SOURCE_ID,
                    repeat_min: int = 2) -> dict:
    """Parse archived sub-award bytes into records/partners/history where ``company_name`` is the sub.

    Never raises; returns empty structures on bad input. A partner edge is authoritative when the
    company has ``>= repeat_min`` sub-awards under a prime OR sub-awards spanning >= 2 distinct years.
    """
    try:
        payload = json.loads(raw)
    except (TypeError, ValueError, json.JSONDecodeError):
        payload = {}
    results = payload.get("results") if isinstance(payload, dict) else None
    if not isinstance(results, list):
        results = []

    target = _canon(company_name)
    seen: set = set()
    subawards: list[dict] = []
    for row in results:
        if not isinstance(row, dict):
            continue
        if _canon(row.get("Sub-Awardee Name") or "") != target:
            continue  # keep only rows where our company is the subrecipient
        sub_id = row.get("Sub-Award ID")
        prime = row.get("Prime Recipient Name")
        date = row.get("Sub-Award Date")
        key = (sub_id, prime, date)
        if key in seen:
            continue
        seen.add(key)
        subawards.append({
            "sub_award_id": sub_id,
            "prime": prime,
            "subrecipient": row.get("Sub-Awardee Name"),
            "amount_usd": _amount(row.get("Sub-Award Amount")),
            "available_at": date,
            "agency": row.get("Awarding Sub Agency") or row.get("Awarding Agency"),
            "naics": _code(row.get("NAICS")),
            "psc": _code(row.get("PSC")),
            "description": row.get("Sub-Award Description"),
            "prime_award_id": row.get("Prime Award ID"),
            "source_id": source_id,
            "source_ref": sub_id,
        })

    subawards.sort(key=lambda s: (-(s["amount_usd"] or 0.0), str(s["sub_award_id"])))

    # Partner edges by prime.
    by_prime: dict[str, list[dict]] = defaultdict(list)
    for s in subawards:
        if s["prime"]:
            by_prime[s["prime"]].append(s)

    partners: list[dict] = []
    for prime, rows in sorted(by_prime.items()):
        years = sorted({(r["available_at"] or "")[:4] for r in rows if r["available_at"]})
        authoritative = len(rows) >= repeat_min or len(years) >= 2
        first = min((r["available_at"] for r in rows if r["available_at"]), default=None)
        partners.append({
            "name": prime,
            "relationship": "prime_of_subcontract",
            "sub_award_count": len(rows),
            "total_subaward_usd": round(sum(r["amount_usd"] or 0.0 for r in rows), 2),
            "years": years,
            "authoritative": authoritative,
            "first_observed_at": first,
            "source_id": source_id,
        })

    # Sub-role contract history + capability records (point-in-time filtered downstream).
    contract_history = [{
        "agency": s["agency"], "naics": s["naics"], "psc": s["psc"], "value_usd": s["amount_usd"],
        "role": "sub", "award_ref": s["sub_award_id"], "program_key": None, "prime": s["prime"],
        "description": s["description"], "available_at": s["available_at"],
    } for s in subawards]

    capability_records = [{
        "source_id": source_id, "source_ref": s["sub_award_id"], "available_at": s["available_at"],
        "description": s["description"], "naics": s["naics"], "psc": s["psc"],
    } for s in subawards if s["description"]]

    return {
        "company_name": company_name,
        "source_id": source_id,
        "subawards": subawards,
        "partners": partners,
        "contract_history": contract_history,
        "capability_records": capability_records,
    }
