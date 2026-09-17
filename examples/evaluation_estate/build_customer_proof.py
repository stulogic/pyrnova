"""PYRNOVA INTERNAL EVALUATION — the multinational evaluation estate (one Lens, five national domains).

WHAT THIS IS. One INTERNAL evaluation Lens, populated from accepted historical/replay evidence already in
this repository, so the real customer product can be inspected under realistic data load. It is NOT a real
customer, asserts NO commercial relationship, and contains NO live production intelligence. Every record is
lawful replay/fixture-derived evidence and says so in its own provenance — the Evidence Inspector shows the
real fixture source, and live-source status stays whatever the national domain honestly reports.

WHY ONE LENS. A customer buys one intelligence surface, not five national demos. The per-country evaluation
lenses (``eval-au``/``eval-nz``/``eval-uk``/``eval-ca``/``eval-us``) still exist and still prove their own
national semantics; this estate reuses their EXACT projection functions with a different lens identity, so
there is one projection path per country and no second implementation, no country UI fork, and no demo-only
product logic. Provisioned by the ordinary operator command:

    pyrnova domains provision-eval --replay-dir examples/evaluation_estate

SELECTION. Cases are chosen for semantic breadth, not volume: every national mechanism family the accepted
fixtures support, both attractive and unattractive dispositions, cancellation and reissue, post-award,
route/access/prime changes, evidence-rich and legitimately evidence-thin cases, and honest unknowns. Cases
whose backing source is not rights-approved are NOT listed here at all — they remain blocked by the national
builders' own fail-closed gate and are reported as blocked, never silently materialized.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

from pyrnova.customers import (
    WATCH_AGENCY, WATCH_PROGRAM, CustomerProfile, WatchlistEntry, add_watch, get_customer,
    upsert_customer,
)
from pyrnova.decision_memory import Disposition, record_disposition

HERE = Path(__file__).resolve().parent
EXAMPLES = HERE.parent

# ---------------------------------------------------------------- the evaluation Lens identity
# An INTERNAL Pyrnova evaluation lens. Deliberately NOT a plausible external company name: nothing here
# may read as a real customer.
LENS_ID = "eval-multinational"
LENS_NAME = "Pyrnova Internal Evaluation"
LENS_REF = "co_pyrnova_internal_evaluation"
# Onboarded before the earliest selected case became knowable, so the lens was "already monitoring".
ONBOARDED = "2018-01-01T00:00:00+00:00"
# The estate's point-in-time cutoff: after every selected case became knowable, and before today.
ESTATE_AS_OF = "2026-09-01"

# The lens's own intelligence configuration. This is OUR evaluation tenant's configuration — an operator
# choice about what this lens monitors, not an assertion about any third party.
CAPABILITIES = [
    "C4ISR", "radar and sensors", "directed energy", "engineering and technical services",
    "land vehicles", "naval sustainment", "air mobility sustainment", "digital and ICT",
    "counter-UAS", "ground-based air defence",
]
SECTORS = ["defence", "national security", "government digital"]
GEOGRAPHY = ["US", "CA", "GB", "AU", "NZ"]


# ---------------------------------------------------------------- case selection, per national domain
# Case ids are the accepted corpora's own ids. A case absent here is simply not part of the estate; a case
# present but rights-blocked is still refused by the national builder and reported as blocked.
SELECTION = {
    # Australia — every accepted AU case: open progression, limited/panel route change, FMS/GtG movement,
    # and a cancellation.
    "au_replay": [
        "au-open-progression",
        "au-limited-route-change",
        "au-fms-case-movement",
        "au-gtg-cancellation",
    ],
    # New Zealand — strong early warning, a thin/closed route, a re-scope, a short-lead panel case, a
    # non-Defence (civil) case, and a cancellation.
    "nz_replay": [
        "nz-mod-early-warning",
        "nz-mod-thin-prime-closed",
        "nz-mod-rescope",
        "nz-mod-short-dlt",
        "nz-treasury-civil-blocked",
        "nz-mod-cancellation",
    ],
    # United Kingdom — all eight rights-approved consequential-change archetypes (the SSRO/QDC case is
    # rights-blocked by the UK builder and must stay blocked).
    "uk_replay": [
        "uk-nmh-precursor",
        "uk-fss-industrial",
        "uk-warrior-closed",
        "uk-ajax-postaward",
        "uk-fdis-framework",
        "uk-skynet-prime",
        "uk-mace-directaward",
        "uk-tempest-gcap",
    ],
    # Canada — all five mechanism families (competitive/open, directed/OEM, FMS/GtG, strategic-source,
    # digital/ICT), the full timing spread (exact / bounded / contaminated), French-original evidence, and
    # the cancellation → reissue pair.
    "ca_replay": [
        "ca-gbad-open",
        "ca-lvm-contaminated",
        "ca-tapv-bounded",
        "ca-himars-fms",
        "ca-nss-strategic",
        "ca-taccom-digital",
        "ca-victoria-bilingual",
        "ca-msvs-cancelled",
        "ca-msvs-reissued",
    ],
    # United States — evidence-rich procurement chains, an incumbent-held recompete, a closed/passed
    # window, an honestly-unknown contract value, and a deliberately thin/ambiguous monitoring case.
    "us_replay": [
        "m8-fit-navy-radar-2024",
        "m8-fit-radar-recompete-defend-2024",
        "m8-fit-directed-energy-open-2024",
        "m8-fit-directed-energy-closed-2023",
        "m7-unknown-value-directed-energy-2024",
        "m6-defer-fragment-ambiguous-gsa-2024",
    ],
}

# Agencies / programmes this lens monitors. Watchlist entries give the lens an explicit, auditable
# monitoring configuration (and exercise the watchlist surface) — they assert nothing about any third party.
WATCHES = [
    (WATCH_AGENCY, "Department of the Navy", "US Navy"),
    (WATCH_AGENCY, "Department of the Air Force", "US Air Force"),
    (WATCH_AGENCY, "General Services Administration", "GSA"),
    (WATCH_PROGRAM, "radar sustainment", "Radar sustainment (multinational)"),
    (WATCH_PROGRAM, "directed energy", "Directed energy (multinational)"),
]


# ---------------------------------------------------------------- Decision Memory (internal review)
# Recorded reactions from the INTERNAL evaluation review of delivered intelligence. Decision Memory is
# explicitly customer feedback, never a Pyrnova assessment — here the reviewer is us, and the note says so.
# Keyed by national case id; resolved to the real opportunity id at seed time.
_REVIEW_NOTE = "Internal Pyrnova evaluation review — not a customer reaction."
DISPOSITIONS = {
    "uk-ajax-postaward": dict(novelty="NEW_TO_CUSTOMER", relevance="RELEVANT", pursuit="INVESTIGATE",
                              timing="EARLY_ENOUGH", value="ACTIONABLE", reason="GOOD_LEAD",
                              outcome="UNRESOLVED"),
    "uk-warrior-closed": dict(novelty="ALREADY_KNOWN", relevance="RELEVANT", pursuit="PASS",
                              timing="EARLY_ENOUGH", value="INFORMATIVE_ONLY", reason="NOT_ADDRESSABLE",
                              outcome="CANCELLED"),
    "uk-skynet-prime": dict(novelty="NEW_TO_CUSTOMER", relevance="RELEVANT", pursuit="WATCH",
                            timing="EARLY_ENOUGH", value="ACTIONABLE", reason="GOOD_LEAD",
                            outcome="UNRESOLVED"),
    "ca-msvs-cancelled": dict(novelty="NEW_TO_CUSTOMER", relevance="RELEVANT", pursuit="PASS",
                              timing="EARLY_ENOUGH", value="INFORMATIVE_ONLY", reason="NOT_ADDRESSABLE",
                              outcome="CANCELLED"),
    "ca-msvs-reissued": dict(novelty="NEW_TO_CUSTOMER", relevance="RELEVANT", pursuit="PURSUE",
                             timing="EARLY_ENOUGH", value="ACTIONABLE", reason="GOOD_LEAD",
                             outcome="PURSUED"),
    "ca-victoria-bilingual": dict(novelty="NEW_TO_CUSTOMER", relevance="RELEVANT", pursuit="WATCH",
                                  timing="EARLY_ENOUGH", value="INFORMATIVE_ONLY", reason="OTHER",
                                  outcome="UNRESOLVED"),
    "nz-mod-cancellation": dict(novelty="NEW_TO_CUSTOMER", relevance="RELEVANT", pursuit="PASS",
                                timing="EARLY_ENOUGH", value="INFORMATIVE_ONLY",
                                reason="NOT_ADDRESSABLE", outcome="CANCELLED"),
    "nz-mod-thin-prime-closed": dict(novelty="NEW_TO_CUSTOMER", relevance="NOT_RELEVANT", pursuit="PASS",
                                     timing="TOO_LATE", value="NO_VALUE", reason="NOT_ADDRESSABLE",
                                     outcome="DECLINED"),
    "au-gtg-cancellation": dict(novelty="NEW_TO_CUSTOMER", relevance="RELEVANT", pursuit="PASS",
                                timing="EARLY_ENOUGH", value="INFORMATIVE_ONLY",
                                reason="NOT_ADDRESSABLE", outcome="CANCELLED"),
    "au-limited-route-change": dict(novelty="NEW_TO_CUSTOMER", relevance="RELEVANT", pursuit="INVESTIGATE",
                                    timing="EARLY_ENOUGH", value="ACTIONABLE", reason="GOOD_LEAD",
                                    outcome="UNRESOLVED"),
    "m8-fit-radar-recompete-defend-2024": dict(novelty="NEW_TO_CUSTOMER", relevance="RELEVANT",
                                               pursuit="PURSUE", timing="EARLY_ENOUGH", value="ACTIONABLE",
                                               reason="GOOD_LEAD", outcome="PURSUED"),
    "m8-fit-directed-energy-closed-2023": dict(novelty="ALREADY_KNOWN", relevance="RELEVANT",
                                               pursuit="PASS", timing="TOO_LATE",
                                               value="INFORMATIVE_ONLY", reason="TIMING",
                                               outcome="NO_BID"),
    "m6-defer-fragment-ambiguous-gsa-2024": dict(novelty="NEW_TO_CUSTOMER", relevance="UNKNOWN",
                                                 pursuit="WATCH", timing="UNKNOWN",
                                                 value="INFORMATIVE_ONLY", reason="LOW_CONFIDENCE",
                                                 outcome="UNRESOLVED"),
}


# Country label used to prefix a programme title. The programme name itself is never invented: it is read
# from the accepted corpus's own ``note`` field (the text before its first colon), so a title is always a
# quotation of the fixture. A corpus without notes (AU) keeps the national builder's default title.
_COUNTRY_LABEL = {"ca_replay": "Canada", "uk_replay": "United Kingdom", "nz_replay": "New Zealand",
                  "au_replay": "Australia"}
_TITLE_MAX = 80


def _leading_clause(note: str) -> str:
    """The note's leading clause — the programme name or case subject, as the corpus itself states it."""
    clause = note.split(":", 1)[0].strip()
    if len(clause) > _TITLE_MAX:                 # no early colon: fall back to the first sentence
        clause = note.split(". ", 1)[0].strip().rstrip(".")
    return clause


def _fixture_titles(replay_dir: str) -> dict:
    """Human-readable titles taken from the accepted corpus itself — never invented.

    Preference order, both drawn from the fixture: the note's leading clause (the programme name, where
    the corpus names one), else the case's own national route + lifecycle stage. Nothing is added that the
    accepted case does not already say.
    """
    corpus_path = EXAMPLES / replay_dir / "corpus.json"
    if not corpus_path.exists():
        return {}
    label = _COUNTRY_LABEL.get(replay_dir)
    titles = {}
    for case in json.loads(corpus_path.read_text(encoding="utf-8"))["cases"]:
        subject = _leading_clause((case.get("note") or "").strip())
        if not subject or len(subject) > _TITLE_MAX:
            route, stage = case.get("route"), case.get("lifecycle_stage")
            subject = f"{route} route — {stage}" if route and stage else ""
        if subject:
            titles[case["case_id"]] = f"{label} — {subject}" if label else subject
    return titles


def _national_builder(replay_dir: str):
    """Load a national proof builder by file path (evaluation identities live in examples/, not runtime)."""
    path = EXAMPLES / replay_dir / "build_customer_proof.py"
    spec = importlib.util.spec_from_file_location(f"pyrnova_eval_proof_{replay_dir}", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def seed_customer(store) -> dict:
    """Provision the internal multinational evaluation lens (idempotent) with its watchlist."""
    created = 0
    if get_customer(store, LENS_ID) is None:
        upsert_customer(store, CustomerProfile(
            customer_id=LENS_ID, name=LENS_NAME, entity_refs=[LENS_REF],
            capabilities=CAPABILITIES, sectors=SECTORS, geography=GEOGRAPHY,
            provenance="internal_evaluation", effective_from=ONBOARDED,
            created_at=ONBOARDED, updated_at=ONBOARDED))
        created = 1
    watches = 0
    for object_type, ref, label in WATCHES:
        add_watch(store, WatchlistEntry(customer_id=LENS_ID, object_type=object_type, ref=ref,
                                        label=label, valid_from=ONBOARDED))
        watches += 1
    return {"customer_id": LENS_ID, "created": created, "watches": watches}


def build_opportunity_records() -> dict:
    """Project every selected national case into shared opportunity records for the ONE evaluation lens.

    Each country's own accepted projection function is reused verbatim with this lens's identity, so the
    rights gate, AS-OF gate, and every national semantic behave exactly as they do for that country's own
    evaluation lens. Returns ``{"records", "blocked", "withheld_evidence", "by_country"}``.
    """
    records: list[dict] = []
    blocked: list[dict] = []
    withheld: list[dict] = []
    by_country: dict[str, int] = {}
    for replay_dir, case_ids in SELECTION.items():
        module = _national_builder(replay_dir)
        kwargs = dict(customer_id=LENS_ID, subject_ref=LENS_REF, subject_name=LENS_NAME,
                      case_ids=case_ids)
        titles = _fixture_titles(replay_dir)
        if titles:
            kwargs["titles"] = titles
        built = module.build_opportunity_records(**kwargs)
        missing = set(case_ids) - {
            r["meta"]["national"]["national_material_change_id"].split(":", 1)[-1] for r in built["records"]
        } - {b["case_id"] for b in built["blocked"]}
        if missing:
            raise ValueError(f"{replay_dir}: selected case(s) not found in the accepted corpus: "
                             f"{sorted(missing)}")
        records.extend(built["records"])
        blocked.extend(built["blocked"])
        withheld.extend(built.get("withheld_evidence", []))
        for rec in built["records"]:
            code = rec["meta"]["national"]["domain"]
            by_country[code] = by_country.get(code, 0) + 1
    return {"records": records, "blocked": blocked, "withheld_evidence": withheld,
            "by_country": by_country}


def _record_dispositions(store, records: list[dict]) -> int:
    """Record the internal evaluation review's Decision Memory against the materialized opportunities."""
    by_case = {rec["meta"]["national"]["national_material_change_id"].split(":", 1)[-1]: rec
               for rec in records}
    recorded = 0
    for case_id, fields in DISPOSITIONS.items():
        rec = by_case.get(case_id)
        if rec is None:      # the case was not selected or was rights-blocked: record nothing.
            continue
        record_disposition(store, Disposition(
            customer_id=LENS_ID, intelligence_ref=rec["id"], note=_REVIEW_NOTE,
            evidence_refs=tuple(e["id"] for e in rec.get("evidence", [])),
            recorded_at=ESTATE_AS_OF + "T00:00:00+00:00", **fields))
        recorded += 1
    return recorded


def seed(store) -> dict:
    """Provision the evaluation Lens, project every selected case, and record the internal review."""
    cust = seed_customer(store)
    built = build_opportunity_records()
    for rec in built["records"]:
        store.append("opportunities", rec)
    dispositions = _record_dispositions(store, built["records"])
    return {"customer": cust, "materialized": len(built["records"]),
            "by_country": built["by_country"], "blocked": built["blocked"],
            "withheld_evidence": built["withheld_evidence"], "dispositions": dispositions,
            "as_of": ESTATE_AS_OF, "lens": LENS_ID,
            "provenance": "INTERNAL EVALUATION — lawful accepted replay/fixture evidence; not a real "
                          "customer and not live production intelligence"}


def main() -> int:
    from pyrnova.config import load_config
    from pyrnova.state import StateStore

    store = StateStore(load_config().state_dir)
    print(json.dumps(seed(store), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
