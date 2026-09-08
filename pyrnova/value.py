"""Evidence-backed value-estimation foundation (M7).

This is NOT a total-addressable-market model. It classifies how well a commercial
value is known and preserves method/inputs/confidence/provenance/range so a caller
never presents an unsupported precise dollar amount.

Self-contained: no imports from chains/replay/catalysts/capabilities.
"""

from __future__ import annotations

import re
import statistics
from dataclasses import dataclass, field


_MULTIPLIERS = {
    "k": 1_000,
    "thousand": 1_000,
    "m": 1_000_000,
    "mm": 1_000_000,
    "million": 1_000_000,
    "b": 1_000_000_000,
    "bn": 1_000_000_000,
    "billion": 1_000_000_000,
}

_AMOUNT_RE = re.compile(
    r"^\$?\s*(?P<num>[0-9][0-9,]*\.?[0-9]*)\s*(?P<suffix>[a-zA-Z]+)?$"
)


def parse_amount(value) -> float | None:
    """Safely parse a dollar-ish value into a float. Never raises; None if unparseable."""
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
    text = str(value).strip()
    if not text:
        return None
    text = text.replace(",", "")
    match = _AMOUNT_RE.match(text)
    if not match:
        return None
    num_str = match.group("num")
    if not num_str or num_str in {".", ""}:
        return None
    try:
        num = float(num_str)
    except ValueError:
        return None
    suffix = (match.group("suffix") or "").strip().casefold()
    if suffix:
        multiplier = _MULTIPLIERS.get(suffix)
        if multiplier is None:
            return None
        num *= multiplier
    return num


@dataclass(frozen=True)
class ValueEstimate:
    status: str  # "KNOWN" | "ESTIMATED" | "BOUNDED" | "UNKNOWN"
    amount_usd: float | None
    low_usd: float | None
    high_usd: float | None
    method: str
    inputs: dict
    confidence: float
    provenance: tuple[str, ...]


def _round(value: float | None) -> float | None:
    if value is None:
        return None
    return round(value)


def estimate_value(
    *,
    explicit_amount=None,
    appropriation_amount=None,
    program_amount=None,
    comparable_awards=(),
    project_fraction=None,
    evidence_ids=(),
) -> ValueEstimate:
    provenance = tuple(evidence_ids)

    explicit = parse_amount(explicit_amount)
    if explicit is not None:
        return ValueEstimate(
            status="KNOWN",
            amount_usd=_round(explicit),
            low_usd=_round(explicit),
            high_usd=_round(explicit),
            method="explicit_procurement_amount",
            inputs={"explicit_amount": explicit},
            confidence=0.95,
            provenance=provenance,
        )

    parsed_comparables = [
        amt for amt in (parse_amount(v) for v in comparable_awards) if amt is not None
    ]
    if parsed_comparables:
        median = statistics.median(parsed_comparables)
        confidence = 0.6 if len(parsed_comparables) > 1 else 0.4
        return ValueEstimate(
            status="ESTIMATED",
            amount_usd=_round(median),
            low_usd=_round(min(parsed_comparables)),
            high_usd=_round(max(parsed_comparables)),
            method="comparable_awards_median",
            inputs={"comparable_awards": parsed_comparables},
            confidence=confidence,
            provenance=provenance,
        )

    base_amount = parse_amount(appropriation_amount)
    base_field = "appropriation_amount"
    if base_amount is None:
        base_amount = parse_amount(program_amount)
        base_field = "program_amount"

    if base_amount is not None and project_fraction is not None:
        low_frac, high_frac = project_fraction
        low = base_amount * low_frac
        high = base_amount * high_frac
        return ValueEstimate(
            status="BOUNDED",
            amount_usd=None,
            low_usd=_round(low),
            high_usd=_round(high),
            method="appropriation_fraction_range",
            inputs={
                base_field: base_amount,
                "project_fraction": tuple(project_fraction),
            },
            confidence=0.45,
            provenance=provenance,
        )

    if base_amount is not None:
        return ValueEstimate(
            status="BOUNDED",
            amount_usd=None,
            low_usd=None,
            high_usd=_round(base_amount),
            method="program_ceiling_upper_bound",
            inputs={base_field: base_amount},
            confidence=0.3,
            provenance=provenance,
        )

    return ValueEstimate(
        status="UNKNOWN",
        amount_usd=None,
        low_usd=None,
        high_usd=None,
        method="unknown",
        inputs={},
        confidence=0.0,
        provenance=provenance,
    )
