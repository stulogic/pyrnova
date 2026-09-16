"""Pyrnova CLI — run the Capture Radar kernel end to end.

    python -m pyrnova.cli capture-radar --profile examples/profiles/acme_c4isr.json --live
    python -m pyrnova.cli capture-radar --profile examples/profiles/acme_c4isr.json --fixtures
    python -m pyrnova.cli scoreboard

--live uses USAspending (no key). SAM is included live only if SAM_API_KEY is set. --fixtures runs
fully offline from bundled sample payloads.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, timedelta
from pathlib import Path

from . import scoreboard
from .archive import build_archive
from .brief import render_capture_radar_report, render_signal_brief
from .config import load_config
from .match import CapabilityProfile
from .pipeline import run
from .state import StateStore

FIXTURES = Path(__file__).resolve().parent.parent / "tests" / "fixtures"


def _load_profile(path: str) -> CapabilityProfile:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return CapabilityProfile.from_dict(data)


def _fixture_rows() -> tuple[list[dict], list[dict], list[dict], list[dict]]:
    awards = json.loads((FIXTURES / "usaspending_awards.json").read_text())["results"]
    notices = json.loads((FIXTURES / "sam_opportunities.json").read_text())["opportunitiesData"]
    precursor_path = FIXTURES / "federal_register_documents.json"
    precursors = json.loads(precursor_path.read_text()).get("results", []) if precursor_path.exists() else []
    return awards, notices, precursors, []


def _live_rows(cfg, profile: CapabilityProfile, as_of: date, window_days: int):
    from .sources.usaspending import USAspendingClient

    award_rows: list[dict] = []
    source_observations: list[dict] = []
    seen: set = set()
    # Action-date window: awards acted on in the last ~6 years may still be active/expiring soon.
    start = (as_of - timedelta(days=6 * 365)).isoformat()
    end = as_of.isoformat()
    naics = profile.naics or None
    client = USAspendingClient()
    usaspending_attempts = 0
    usaspending_failures = 0

    def _collect(**kw):
        nonlocal usaspending_attempts, usaspending_failures
        usaspending_attempts += 1
        # A single source read failing (timeout, 5xx, transport error) degrades that pass — it must not
        # crash the whole capture run. SAM and Federal Register below already degrade this way; the
        # primary source must behave consistently so partial intelligence is still produced and any
        # empty result is EXPLAINED (source degraded), never a silent/unexplained empty.
        try:
            for _raw, results in client.search_awards(
                action_date_start=start, action_date_end=end, max_pages=3, limit=100, **kw
            ):
                for r in results:
                    key = r.get("generated_internal_id") or r.get("Award ID")
                    if key and key not in seen:
                        seen.add(key)
                        award_rows.append(r)
        except Exception as exc:  # pragma: no cover - network dependent
            usaspending_failures += 1
            print(f"[warn] USAspending fetch failed ({kw!r}): {exc}", file=sys.stderr)

    # Pass 1 (anchor): the target company's own awards — incumbency + their upcoming recompetes.
    for name in profile.search_names:
        _collect(recipient_search=[name])
    # Pass 2 (market): recompete landscape in the target's NAICS they could compete for.
    if naics:
        _collect(naics_codes=naics)
    if usaspending_attempts and usaspending_failures == usaspending_attempts:
        print("[warn] USAspending DEGRADED — all award passes failed this run; awards intelligence "
              "is unavailable (this empty is source-degradation, not an absence of activity).",
              file=sys.stderr)
    # NOTE: agency-name filtering is intentionally omitted (brittle toptier/subtier naming);
    # agency relevance is handled deterministically by the capability matcher instead.

    notice_rows: list[dict] = []
    if cfg.has_sam:
        from .sources.sam import SamClient

        sam = SamClient(cfg.sam_api_key)
        posted_from = (as_of - timedelta(days=30)).strftime("%m/%d/%Y")
        posted_to = as_of.strftime("%m/%d/%Y")
        for ptype in ("r", "p", "s"):  # Sources Sought, Presolicitation, Special Notice
            try:
                observations = sam.search_observations(
                    posted_from=posted_from, posted_to=posted_to, ptype=ptype,
                    naics=(naics[0] if naics else None), limit=100, max_pages=1,
                )
                for observation in observations:
                    notice_rows.extend(observation.rows)
                    source_observations.append({
                        "source_id": "sam_opportunities",
                        "source_ref": f"search:{ptype}:{observation.request_params['offset']}",
                        "request_url": observation.request_url,
                        "request_params": observation.request_params,
                        "fetched_at": observation.fetched_at,
                        "raw_response": observation.raw_response,
                    })
            except Exception as exc:  # pragma: no cover - network dependent
                print(f"[warn] SAM {ptype} fetch failed: {exc}", file=sys.stderr)
    else:
        print("[info] SAM_API_KEY not set — running recompete-only (USAspending). "
              "Set SAM_API_KEY to include pre-solicitation intelligence.", file=sys.stderr)
    precursor_rows: list[dict] = []
    if profile.precursor_terms:
        from .sources.federal_register import FederalRegisterClient

        fr = FederalRegisterClient()
        seen_docs: set[str] = set()
        start_date = (as_of - timedelta(days=3 * 365)).isoformat()
        for term in profile.precursor_terms[:3]:
            try:
                for page in fr.search_documents(
                    term=term,
                    document_types=["NOTICE", "PROPOSED_RULE", "RULE"],
                    publication_date_start=start_date,
                    publication_date_end=as_of.isoformat(),
                    max_pages=1,
                    per_page=100,
                ):
                    for document in page.documents:
                        ref = document.get("document_number")
                        if ref and ref not in seen_docs:
                            seen_docs.add(ref)
                            row = dict(document)
                            row["_pyrnova_observation"] = {
                                "request_params": page.request_params,
                                "fetched_at": page.fetched_at,
                                "request_url": page.source_url,
                            }
                            precursor_rows.append(row)
            except Exception as exc:  # pragma: no cover - network dependent
                print(f"[warn] Federal Register fetch failed for {term!r}: {exc}", file=sys.stderr)
    return award_rows, notice_rows, precursor_rows, source_observations


def cmd_capture_radar(args) -> int:
    cfg = load_config()
    profile = _load_profile(args.profile)
    as_of = date.fromisoformat(args.as_of) if args.as_of else date.today()
    archive = build_archive(cfg)
    store = StateStore(cfg.state_dir)

    if args.fixtures:
        award_rows, notice_rows, precursor_rows, source_observations = _fixture_rows()
    else:
        award_rows, notice_rows, precursor_rows, source_observations = _live_rows(
            cfg, profile, as_of, args.window_days
        )
    if args.sam_records:
        observed = json.loads(Path(args.sam_records).read_text(encoding="utf-8"))
        notice_rows.extend(observed.get("opportunitiesData", []))

    report = run(
        profile=profile,
        award_rows=award_rows,
        notice_rows=notice_rows,
        precursor_rows=precursor_rows,
        source_observations=source_observations,
        archive=archive,
        store=store,
        as_of=as_of,
        window_days=args.window_days,
        relevance_threshold=args.threshold,
        reviewer=args.reviewer,
        min_amount=args.min_amount,
    )

    cfg.out_dir.mkdir(parents=True, exist_ok=True)
    slug = "".join(c for c in profile.name.lower() if c.isalnum() or c in "-_") or "customer"
    brief_path = cfg.out_dir / f"signal_brief_{slug}.md"
    radar_path = cfg.out_dir / f"capture_radar_{slug}.md"
    brief_path.write_text(render_signal_brief(report), encoding="utf-8")
    radar_path.write_text(render_capture_radar_report(report), encoding="utf-8")
    scoreboard.record(store, "signal_briefs_produced", 1, profile=profile.name)

    print(f"profile         : {profile.name}")
    print(f"as-of           : {as_of.isoformat()}")
    print(f"awards / notices / precursors: {len(award_rows)} / {len(notice_rows)} / {len(precursor_rows)}")
    print(f"candidates      : {report.stats['candidates']}")
    print(f"STRIKEs         : {report.stats['strikes']} "
          f"(recompete {report.stats['recompete']}, presol {report.stats['presolicitation']})")
    print(f"WATCH / deduped : {report.stats['watch']} / {report.stats['duplicate_candidates']}")
    print(f"avg lead time   : {report.stats['avg_lead_time_days']} days")
    print(f"signal brief    : {brief_path}")
    print(f"capture radar   : {radar_path}")
    if report.strikes:
        top = report.strikes[0]
        print("\nTop STRIKE:")
        print(f"  {top.title}")
        print(f"  relevance {top.relevance_score:.2f} · confidence {top.confidence:.2f} "
              f"· attractiveness {top.attractiveness:.2f}")
    return 0


def cmd_scoreboard(args) -> int:
    cfg = load_config()
    store = StateStore(cfg.state_dir)
    totals = scoreboard.totals(store)
    if not totals:
        print("scoreboard empty — run capture-radar first.")
        return 0
    width = max(len(k) for k in totals)
    for k in sorted(totals):
        print(f"{k:<{width}} : {totals[k]:g}")
    print(f"\npredictions logged (stream): {store.count('predictions')}")
    print(f"reviews recorded  (stream): {store.count('reviews')}")
    return 0


def cmd_adjudicate(args) -> int:
    from .models import Catalyst, Opportunity, to_record
    from .review import adjudicate, apply_review

    cfg = load_config()
    store = StateStore(cfg.state_dir)
    record = store.latest("opportunities", args.opportunity_id)
    if not record:
        print(f"opportunity not found: {args.opportunity_id}", file=sys.stderr)
        return 2
    catalyst = record.get("catalyst") or {}
    opp = Opportunity(
        id=record["id"],
        title=record.get("title") or "untitled",
        catalyst=Catalyst(
            kind=catalyst.get("kind") or "unknown",
            detected_by=catalyst.get("detected_by") or "unknown",
        ),
        state=record.get("state") or "candidate",
        relevance_score=float(record.get("relevance_score") or 0),
        confidence=float(record.get("confidence") or 0),
        meta=dict(record.get("meta") or {}),
    )
    review = adjudicate(
        opp, decision=args.decision, reviewer=args.reviewer, reason=args.reason or ""
    )
    apply_review(opp, review)
    store.append("reviews", to_record(review))
    updated = dict(record)
    updated["state"] = opp.state
    updated["meta"] = opp.meta
    store.append("opportunities", updated)
    scoreboard.record(
        store,
        {"ACCEPT": "review_accepts", "WATCH": "review_watches", "REJECT": "review_rejects"}[
            review.human_decision
        ],
        opportunity_id=opp.id,
        reviewer=review.reviewer,
    )
    print(f"{opp.id}: {review.human_decision} by {review.reviewer} at {review.reviewed_at}")
    return 0


def cmd_replay(args) -> int:
    from .replay import run_replay

    cfg = load_config()
    case = json.loads(Path(args.case).read_text(encoding="utf-8"))
    result = run_replay(case, store=StateStore(cfg.state_dir), scoring_version=args.scoring_version)
    if args.inspect_excluded:
        result = {"case_id": result["case_id"], "excluded_future_records": result["excluded_future_records"]}
    rendered = json.dumps(result, indent=2, sort_keys=True)
    if args.output:
        Path(args.output).write_text(rendered + "\n", encoding="utf-8")
        print(args.output)
    else:
        print(rendered)
    return 0


def cmd_metrics(args) -> int:
    from .metrics import evaluation_snapshot

    cfg = load_config()
    print(json.dumps(evaluation_snapshot(StateStore(cfg.state_dir), args.scoring_version), indent=2, sort_keys=True))
    return 0


def _persist_replay_report(cfg, store, results: list[dict], metrics: dict, kind: str) -> dict:
    from .replay import report_id

    report = {
        "id": report_id(results, kind),
        "kind": kind,
        "scoring_versions": sorted({r["scoring_version"] for r in results}),
        "result_ids": sorted(r["id"] for r in results),
        "metrics": metrics,
    }
    store.append("replay_reports", report)
    cfg.out_dir.mkdir(parents=True, exist_ok=True)
    path = cfg.out_dir / f"replay_report_{report['id']}.json"
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {**report, "output": str(path)}


def cmd_replay_corpus(args) -> int:
    from .metrics import summarize_results
    from .replay import load_corpus, run_corpus

    cfg = load_config()
    store = StateStore(cfg.state_dir)
    cases = load_corpus(Path(args.corpus))
    results = run_corpus(cases, scoring_version=args.scoring_version, mechanism=args.mechanism, store=store)
    report = _persist_replay_report(cfg, store, results, summarize_results(results), "corpus")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


def cmd_compare_scoring(args) -> int:
    from .metrics import summarize_results
    from .replay import load_corpus, run_corpus

    cfg = load_config()
    store = StateStore(cfg.state_dir)
    cases = load_corpus(Path(args.corpus))
    baseline = run_corpus(cases, scoring_version=args.baseline, mechanism=args.mechanism, store=store)
    challenger = run_corpus(cases, scoring_version=args.challenger, mechanism=args.mechanism, store=store)
    baseline_metrics, challenger_metrics = summarize_results(baseline), summarize_results(challenger)
    changed = [
        {"case_id": old["case_id"], "baseline": old["system_disposition"], "challenger": new["system_disposition"]}
        for old, new in zip(baseline, challenger)
        if old["system_disposition"] != new["system_disposition"]
    ]
    combined = baseline + challenger
    report = _persist_replay_report(
        cfg,
        store,
        combined,
        {"baseline": baseline_metrics, "challenger": challenger_metrics, "changed_dispositions": changed},
        "scoring-comparison",
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


def cmd_chain_resolve(args) -> int:
    from .replay import run_chain_replay

    cfg = load_config()
    store = StateStore(cfg.state_dir)
    case = json.loads(Path(args.case).read_text(encoding="utf-8"))
    result = run_chain_replay(case, scoring_version=args.scoring_version, store=store)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


def cmd_chain_corpus(args) -> int:
    from .replay import load_corpus, run_chain_corpus, summarize_chain_results

    cfg = load_config()
    store = StateStore(cfg.state_dir)
    cases = load_corpus(Path(args.corpus))
    results = run_chain_corpus(cases, scoring_version=args.scoring_version, store=store)
    summary = summarize_chain_results(results)
    output = {"summary": summary, "cases": results} if args.verbose else {"summary": summary}
    print(json.dumps(output, indent=2, sort_keys=True))
    return 0


def cmd_consequences(args) -> int:
    from .replay import run_consequence_replay

    cfg = load_config()
    store = StateStore(cfg.state_dir) if args.persist else None
    case = json.loads(Path(args.case).read_text(encoding="utf-8"))
    result = run_consequence_replay(case, scoring_version=args.scoring_version, store=store)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


def cmd_consequence_corpus(args) -> int:
    from .replay import load_corpus, run_consequence_corpus, summarize_consequence_results

    cfg = load_config()
    store = StateStore(cfg.state_dir) if args.persist else None
    cases = load_corpus(Path(args.corpus))
    results = run_consequence_corpus(cases, scoring_version=args.scoring_version, store=store)
    summary = summarize_consequence_results(results)
    output = {"summary": summary, "cases": results} if args.verbose else {"summary": summary}
    print(json.dumps(output, indent=2, sort_keys=True))
    return 0


def cmd_profile(args) -> int:
    from .company import to_record as company_record
    from .grounding import first_supportable_capability_date, load_parsed, profile_as_of

    parsed = load_parsed(args.evidence, company_name=args.company)
    profile = profile_as_of(args.company, parsed, args.as_of, geography=(args.geography or "").split(",") if args.geography else ())
    record = company_record(profile)
    caps = sorted({e["label"] for e in record["capabilities"]})
    out = {
        "company": profile.name, "as_of": args.as_of, "company_id": profile.company_id,
        "capabilities": caps, "contract_count": len(profile.contract_history),
        "max_contract_usd": (profile.scale or {}).get("max_contract_usd"),
        "buyer_agencies": profile.meta.get("buyer_agencies"),
        "vehicles": profile.meta.get("contract_vehicles"),
        "first_supportable": {c: first_supportable_capability_date(parsed, c) for c in caps},
    }
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0


def cmd_fit(args) -> int:
    from .replay import run_fit_replay

    cfg = load_config()
    store = StateStore(cfg.state_dir) if args.persist else None
    case = json.loads(Path(args.case).read_text(encoding="utf-8"))
    print(json.dumps(run_fit_replay(case, store=store), indent=2, sort_keys=True))
    return 0


def cmd_fit_corpus(args) -> int:
    from .replay import load_corpus, run_fit_corpus, summarize_fit_results

    cfg = load_config()
    store = StateStore(cfg.state_dir) if args.persist else None
    results = run_fit_corpus(load_corpus(Path(args.corpus)), store=store)
    summary = summarize_fit_results(results)
    output = {"summary": summary, "cases": results} if args.verbose else {"summary": summary}
    print(json.dumps(output, indent=2, sort_keys=True))
    return 0


def cmd_inferred_threshold(args) -> int:
    from .replay import evaluate_inferred_threshold, load_corpus

    report = evaluate_inferred_threshold(load_corpus(Path(args.corpus)))
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


def cmd_join_review(args) -> int:
    from .review_queue import adjudicate_join, override_rate, pending_reviews

    cfg = load_config()
    store = StateStore(cfg.state_dir)
    if args.corpus:
        # Populate the queue by resolving a corpus point-in-time (enqueues deferred inferred joins).
        from .replay import load_corpus, run_chain_corpus
        run_chain_corpus(load_corpus(Path(args.corpus)), store=store)
    if args.action == "list":
        pending = pending_reviews(store)
        print(json.dumps({"pending": pending, "override_rate": override_rate(store)},
                         indent=2, sort_keys=True))
        return 0
    if args.action == "decide":
        if not (args.relationship_id and args.decision and args.reviewer):
            print("decide requires --relationship-id, --decision, and --reviewer", file=sys.stderr)
            return 2
        review = adjudicate_join(store, args.relationship_id, decision=args.decision,
                                 reviewer=args.reviewer, reason=args.reason or "")
        print(json.dumps({"relationship_id": review.relationship_id, "decision": review.decision,
                          "reviewer": review.reviewer, "pre_review_confidence": review.pre_review_confidence,
                          "automated_recommendation": review.automated_recommendation,
                          "reviewed_at": review.reviewed_at}, indent=2, sort_keys=True))
        return 0
    print(f"unknown join-review action: {args.action}", file=sys.stderr)
    return 2


def cmd_source_contribution(args) -> int:
    from .contribution import measure_replay_source_contribution
    from .replay import load_corpus

    cases = load_corpus(Path(args.corpus))
    report = measure_replay_source_contribution(cases, scoring_version=args.scoring_version)
    if args.source:
        report = {args.source: report.get(args.source)}
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


def cmd_seed_customers(args) -> int:
    """M22-B: deterministically seed the demo customers into PERSISTED customer state.

    Loads the example seeder by file path (demo identities live in examples/, never in the runtime
    package) and writes profiles + watchlists into the configured state dir. Idempotent."""
    import importlib.util

    from .config import load_config
    from .state import StateStore

    demo_dir = Path(args.demo_dir)
    spec = importlib.util.spec_from_file_location("pyrnova_demo_seed_customers",
                                                  demo_dir / "seed_customers.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    store = StateStore(load_config().state_dir)
    print(json.dumps(module.seed(store), indent=2, sort_keys=True))
    return 0


def cmd_fanout(args) -> int:
    """M22-C: fan relevant global intelligence into customer-scoped Material Change state.

    The ordinary continuous-operations path (not a demo script): reads the configured global intelligence
    streams and the persisted customer state, then materializes/updates customer-scoped Material Changes.
    Deterministic, idempotent (content-hash deduped), point-in-time via ``--as-of``. Prints the report."""
    from .config import load_config
    from .customer_material_changes import fan_out
    from .state import StateStore

    store = StateStore(load_config().state_dir)
    customer_ids = [c.strip() for c in (args.customers or "").split(",") if c.strip()] or None
    report = fan_out(mc_store=store, customer_store=store, cmc_store=store,
                     customer_ids=customer_ids, as_of=args.as_of)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


def _state_store():
    from .config import load_config
    from .state import StateStore
    return StateStore(load_config().state_dir)


def cmd_customer_create(args) -> int:
    """M22-F: create a persisted customer WITHOUT editing any seed script (operator-assisted onboarding)."""
    from . import onboarding
    store = _state_store()
    row = onboarding.create_customer(
        store, customer_id=args.id, name=args.name,
        entity_refs=args.entity_ref or [], capabilities=args.capability or [],
        agencies=args.agency or [], sectors=args.sector or [], geography=args.geography or [])
    print(json.dumps(row, indent=2, sort_keys=True))
    return 0


def cmd_customer_show(args) -> int:
    from . import onboarding
    row = onboarding.get_customer(_state_store(), args.id, as_of=args.as_of)
    if row is None:
        print(json.dumps({"error": f"customer not found: {args.id}"}))
        return 1
    print(json.dumps(row, indent=2, sort_keys=True))
    return 0


def cmd_customer_list(args) -> int:
    from . import customers as cust
    print(json.dumps(cust.list_customers(_state_store()), indent=2, sort_keys=True))
    return 0


def cmd_watch_add(args) -> int:
    """M22-F: add a watch. With --resolve, uses M22-D deterministic resolution (never silently guesses)."""
    from . import onboarding
    store = _state_store()
    if args.resolve:
        result = onboarding.add_watch_resolved(
            store, customer_id=args.customer, query=args.ref, object_type=args.type,
            accept_probable=args.accept_probable, allow_unresolved=args.allow_unresolved,
            demo_dir=args.demo_dir, label=args.label or "")
        print(json.dumps(result, indent=2, sort_keys=True))
        # A non-committal resolution (ambiguous / needs confirmation / unresolved) is a deliberate,
        # honest non-error outcome the operator must act on — signalled with a non-zero code.
        return 0 if result.get("watch") is not None else 2
    if not args.type:
        print(json.dumps({"error": "--type is required when not using --resolve"}))
        return 1
    row = onboarding.add_watch(store, customer_id=args.customer, object_type=args.type,
                               ref=args.ref, label=args.label or "")
    print(json.dumps(row, indent=2, sort_keys=True))
    return 0


def cmd_watch_list(args) -> int:
    from . import customers as cust
    print(json.dumps(cust.list_watches(_state_store(), args.customer, as_of=args.as_of),
                     indent=2, sort_keys=True))
    return 0


def cmd_watch_retire(args) -> int:
    from . import onboarding
    row = onboarding.retire_watch(_state_store(), args.customer, args.watch_id)
    print(json.dumps(row, indent=2, sort_keys=True))
    return 0


def cmd_credential_create(args) -> int:
    """M22-F: provision a credential. Prints the plaintext token ONCE — it is not recoverable afterward."""
    from . import access
    role = access.ROLE_OPERATOR if args.operator else access.ROLE_CUSTOMER
    if role == access.ROLE_CUSTOMER and not args.customer:
        print(json.dumps({"error": "--customer is required for a customer credential"}))
        return 1
    metadata, token = access.create_credential(
        _state_store(), customer_id=args.customer or "", actor_label=args.actor or "",
        role=role, note=args.note or "")
    print(json.dumps(metadata, indent=2, sort_keys=True))
    print("\n  CREDENTIAL SECRET (shown once — store it securely; it cannot be recovered):")
    print(f"    {token}\n")
    return 0


def cmd_credential_list(args) -> int:
    from . import access
    print(json.dumps(access.list_credentials(_state_store(), customer_id=args.customer),
                     indent=2, sort_keys=True))
    return 0


def cmd_credential_revoke(args) -> int:
    from . import access
    row = access.revoke_credential(_state_store(), args.credential_id, note=args.note or "")
    print(json.dumps(row, indent=2, sort_keys=True))
    return 0


def cmd_search(args) -> int:
    """M22-D: resolve a query against the Pyrnova estate deterministically (no runtime LLM).

    Builds the point-in-time investigation estate from the configured global intelligence streams
    (falling back to the tracked demo state on a fresh checkout, mirroring the server) and prints the
    resolution (EXACT / PROBABLE / AMBIGUOUS / UNRESOLVED) with the resolved canonical objects."""
    from .config import load_config
    from .investigation import build_estate, search
    from .state import StateStore

    cfg = load_config()
    store = StateStore(cfg.state_dir)
    demo_state = Path(args.demo_dir) / "state"
    mc_store = store
    if not (Path(cfg.state_dir) / "threats.jsonl").exists() and (demo_state / "threats.jsonl").exists():
        mc_store = StateStore(demo_state)

    def _read(s, name):
        try:
            return list(s.read(name))
        except Exception:  # noqa: BLE001
            return []

    latest = {}
    for name, s in (("threats", mc_store), ("propagated_threats", mc_store),
                    ("opportunities", store), ("relationships", store)):
        rows = {}
        for r in _read(s, name):
            rid = r.get("id")
            if rid:
                rows[str(rid)] = r
        latest[name] = list(rows.values()) if name != "relationships" else _read(s, name)

    estate = build_estate(threats=latest["threats"], propagated_threats=latest["propagated_threats"],
                          opportunities=latest["opportunities"], relationships=latest["relationships"],
                          as_of=args.as_of)
    print(json.dumps(search(estate, args.query, limit=args.limit), indent=2, sort_keys=True))
    return 0


def cmd_domains_list(args) -> int:
    from .domains import all_domains
    rows = []
    for d in all_domains():
        rows.append({
            "code": d.code, "name": d.name, "validated": d.validated,
            "build_authority": d.build_authority,
            "operational": bool(d.validated and d.build_authority),
            "sources": {s.id: s.activation.value for s in d.sources},
            "dlt_calibrated": d.dlt_calibration is not None,
        })
    print(json.dumps(rows, indent=2, sort_keys=True))
    return 0


def cmd_domains_show(args) -> int:
    from .domains import get_domain
    d = get_domain(args.code)
    print(json.dumps({
        "code": d.code, "name": d.name, "validated": d.validated,
        "build_authority": d.build_authority,
        "operational": bool(d.validated and d.build_authority),
        "lifecycle": list(d.lifecycle), "routes": d.routes,
        "access_classes": list(d.access_classes),
        "industrial_position_classes": list(d.industrial_position_classes),
        "important_miss": list(d.important_miss),
        "evidence_languages": list(d.evidence_languages),
        "sources": [{"id": s.id, "name": s.name, "activation": s.activation.value,
                     "ingestible": s.ingestible, "role": s.role, "note": s.note} for s in d.sources],
        "dlt_calibration": (None if d.dlt_calibration is None else {
            "median_dlt_to_market_days": d.dlt_calibration.median_dlt_to_market_days,
            "p25_days": d.dlt_calibration.p25_days, "corpus_size": d.dlt_calibration.corpus_size,
            "qualifying_cases": d.dlt_calibration.qualifying_cases,
            "source_reference": d.dlt_calibration.source_reference}),
        "notes": d.notes,
    }, indent=2, sort_keys=False))
    return 0


def cmd_backup_create(args) -> int:
    from . import backup as _bk
    cfg = load_config()
    src = _git_head_commit(args.source_root)
    manifest = _bk.create_backup(
        Path(args.source_root), Path(args.dest), source_commit=src,
        state_dir=cfg.state_dir, archive_dir=cfg.archive_dir)
    print(json.dumps({
        "status": manifest.status,
        "files": len(manifest.files),
        "state_dir": str(cfg.state_dir),
        "archive_dir": str(cfg.archive_dir),
        "dest": str(Path(args.dest).resolve()),
        "manifest_sha256": manifest.manifest_sha256,
        "source_commit": manifest.source_commit,
    }, indent=2, sort_keys=True))
    return 0 if manifest.status == "complete" else 1


def cmd_backup_verify(args) -> int:
    from . import backup as _bk
    result = _bk.verify_backup(Path(args.backup_dir))
    print(json.dumps({"ok": result.ok, "checked": result.checked,
                      "problems": result.problems}, indent=2, sort_keys=True))
    return 0 if result.ok else 1


def cmd_backup_restore(args) -> int:
    from . import backup as _bk
    result = _bk.restore_backup(Path(args.backup_dir), Path(args.target),
                                verify=not args.no_verify)
    print(json.dumps({
        "target_root": result.target_root,
        "restored_files": result.restored_files,
        "verify_ok": result.verify.ok,
        "note": "run reconcile_display before any customer display (restore != display authorisation)",
    }, indent=2, sort_keys=True))
    return 0


def _git_head_commit(root: str) -> str:
    import subprocess
    try:
        out = subprocess.run(["git", "-C", root, "rev-parse", "HEAD"],
                             capture_output=True, text=True, timeout=5)
        return out.stdout.strip() if out.returncode == 0 else ""
    except Exception:
        return ""


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="pyrnova", description="Pyrnova Capture Radar kernel")
    sub = p.add_subparsers(dest="cmd", required=True)

    srch = sub.add_parser("search",
                          help="deterministically resolve a query against the Pyrnova estate (M22-D)")
    srch.add_argument("query")
    srch.add_argument("--as-of", default=None, dest="as_of")
    srch.add_argument("--limit", type=int, default=25)
    srch.add_argument("--demo-dir", default="examples/material_changes_demo")
    srch.set_defaults(func=cmd_search)

    # --- M22-F: seed-free customer onboarding + credential management -----------------------------
    cust_p = sub.add_parser("customer", help="onboard / inspect persisted customers (M22-F)")
    cust_sub = cust_p.add_subparsers(dest="subcmd", required=True)
    cc = cust_sub.add_parser("create", help="create a customer without editing any seed script")
    cc.add_argument("--id", required=True, help="stable customer slug")
    cc.add_argument("--name", required=True)
    cc.add_argument("--entity-ref", action="append", dest="entity_ref", help="canonical ref the customer IS")
    cc.add_argument("--capability", action="append", dest="capability")
    cc.add_argument("--agency", action="append", dest="agency")
    cc.add_argument("--sector", action="append", dest="sector")
    cc.add_argument("--geography", action="append", dest="geography")
    cc.set_defaults(func=cmd_customer_create)
    csh = cust_sub.add_parser("show", help="show a customer profile + active watchlist")
    csh.add_argument("id")
    csh.add_argument("--as-of", default=None, dest="as_of")
    csh.set_defaults(func=cmd_customer_show)
    cls_ = cust_sub.add_parser("list", help="list persisted customers")
    cls_.set_defaults(func=cmd_customer_list)

    watch_p = sub.add_parser("watch", help="configure customer watchlists (M22-F, reuses M22-B/D)")
    watch_sub = watch_p.add_subparsers(dest="subcmd", required=True)
    wa = watch_sub.add_parser("add", help="add a watch (optionally deterministically resolved)")
    wa.add_argument("customer")
    wa.add_argument("ref", help="canonical ref/id, or a free-text query when --resolve is used")
    wa.add_argument("--type", default=None, choices=("ENTITY", "PROGRAM", "CONTRACT", "AGENCY"))
    wa.add_argument("--label", default=None)
    wa.add_argument("--resolve", action="store_true",
                    help="resolve the ref via deterministic M22-D search before adding")
    wa.add_argument("--accept-probable", action="store_true", dest="accept_probable",
                    help="with --resolve, accept a single PROBABLE match (explicit confirmation)")
    wa.add_argument("--allow-unresolved", action="store_true", dest="allow_unresolved",
                    help="with --resolve, record an UNRESOLVED target literally (requires --type)")
    wa.add_argument("--demo-dir", default="examples/material_changes_demo")
    wa.set_defaults(func=cmd_watch_add)
    wl = watch_sub.add_parser("list", help="list a customer's active watches")
    wl.add_argument("customer")
    wl.add_argument("--as-of", default=None, dest="as_of")
    wl.set_defaults(func=cmd_watch_list)
    wr = watch_sub.add_parser("retire", help="retire a watch (append-only closure; preserves history)")
    wr.add_argument("customer")
    wr.add_argument("watch_id")
    wr.set_defaults(func=cmd_watch_retire)

    cred_p = sub.add_parser("credential", help="provision / list / revoke access credentials (M22-F)")
    cred_sub = cred_p.add_subparsers(dest="subcmd", required=True)
    cr_c = cred_sub.add_parser("create", help="provision a credential (prints the secret token once)")
    cr_c.add_argument("--customer", default=None, help="tenant for a customer credential")
    cr_c.add_argument("--actor", default=None, help="optional human/actor label")
    cr_c.add_argument("--operator", action="store_true", help="provision an internal operator credential")
    cr_c.add_argument("--note", default=None)
    cr_c.set_defaults(func=cmd_credential_create)
    cr_l = cred_sub.add_parser("list", help="list credential metadata (never secrets)")
    cr_l.add_argument("--customer", default=None)
    cr_l.set_defaults(func=cmd_credential_list)
    cr_r = cred_sub.add_parser("revoke", help="revoke a credential (append-only; fails auth immediately)")
    cr_r.add_argument("credential_id")
    cr_r.add_argument("--note", default=None)
    cr_r.set_defaults(func=cmd_credential_revoke)

    seedc = sub.add_parser("seed-customers",
                           help="seed the demo customers into persisted customer state (M22-B)")
    seedc.add_argument("--demo-dir", default="examples/material_changes_demo")
    seedc.set_defaults(func=cmd_seed_customers)

    fo = sub.add_parser("fanout",
                        help="materialize customer-scoped Material Changes from global intelligence (M22-C)")
    fo.add_argument("--customers", default=None, help="comma-separated customer ids (default: all persisted)")
    fo.add_argument("--as-of", default=None, help="ISO timestamp for point-in-time fan-out (default now)")
    fo.set_defaults(func=cmd_fanout)

    cr = sub.add_parser("capture-radar", help="run the Capture Radar pipeline")
    cr.add_argument("--profile", required=True, help="path to a capability profile JSON")
    src = cr.add_mutually_exclusive_group()
    src.add_argument("--live", action="store_true", help="fetch live public data (default)")
    src.add_argument("--fixtures", action="store_true", help="run offline from bundled fixtures")
    cr.add_argument("--as-of", default=None, help="YYYY-MM-DD (default today)")
    cr.add_argument("--window-days", type=int, default=540, help="recompete forward window")
    cr.add_argument("--threshold", type=float, default=0.3, help="relevance threshold for STRIKE")
    cr.add_argument("--min-amount", type=float, default=0.0, help="minimum award amount for recompete")
    cr.add_argument("--reviewer", default=None, help="legacy label only; use adjudicate for a human decision")
    cr.add_argument("--sam-records", default=None, help="append a saved SAM opportunities JSON observation")
    cr.set_defaults(func=cmd_capture_radar)

    sb = sub.add_parser("scoreboard", help="print accumulated scoreboard totals")
    sb.set_defaults(func=cmd_scoreboard)

    adj = sub.add_parser("adjudicate", help="persist a named ACCEPT/WATCH/REJECT decision")
    adj.add_argument("opportunity_id")
    adj.add_argument("--decision", required=True, choices=("ACCEPT", "WATCH", "REJECT"))
    adj.add_argument("--reviewer", required=True)
    adj.add_argument("--reason", default="")
    adj.set_defaults(func=cmd_adjudicate)

    replay = sub.add_parser("replay", help="run a deterministic point-in-time replay case")
    replay.add_argument("--case", required=True)
    replay.add_argument("--output", default=None)
    replay.add_argument("--scoring-version", default="scoring_v1")
    replay.add_argument("--inspect-excluded", action="store_true")
    replay.set_defaults(func=cmd_replay)

    metrics = sub.add_parser("metrics", help="print evaluation metrics from durable state")
    metrics.add_argument("--scoring-version", default=None)
    metrics.set_defaults(func=cmd_metrics)

    corpus = sub.add_parser("replay-corpus", help="run the canonical replay challenge corpus")
    corpus.add_argument("--corpus", default="examples/replay/corpus_v1.json")
    corpus.add_argument("--mechanism", default=None)
    corpus.add_argument("--scoring-version", default="scoring_v1")
    corpus.set_defaults(func=cmd_replay_corpus)

    compare = sub.add_parser("compare-scoring", help="compare two scoring versions on the full corpus")
    compare.add_argument("--corpus", default="examples/replay/corpus_v1.json")
    compare.add_argument("--mechanism", default=None)
    compare.add_argument("--baseline", default="scoring_v1")
    compare.add_argument("--challenger", default="scoring_v2_candidate")
    compare.set_defaults(func=cmd_compare_scoring)

    chain = sub.add_parser("chain-resolve", help="resolve the cross-source capital chain for one case")
    chain.add_argument("--case", required=True)
    chain.add_argument("--scoring-version", default="scoring_v1")
    chain.set_defaults(func=cmd_chain_resolve)

    chain_corpus = sub.add_parser("chain-corpus", help="resolve cross-source chains across a corpus")
    chain_corpus.add_argument("--corpus", default="examples/replay/corpus_m5.json")
    chain_corpus.add_argument("--scoring-version", default="scoring_v1")
    chain_corpus.add_argument("--verbose", action="store_true", help="include per-case chain detail")
    chain_corpus.set_defaults(func=cmd_chain_corpus)

    threshold = sub.add_parser("inferred-threshold", help="evaluate inferred-join acceptance threshold behavior")
    threshold.add_argument("--corpus", default="examples/replay/corpus_m6.json")
    threshold.set_defaults(func=cmd_inferred_threshold)

    jr = sub.add_parser("join-review", help="human review queue for uncertain (deferred) inferred joins")
    jr.add_argument("action", choices=("list", "decide"))
    jr.add_argument("--relationship-id", default=None)
    jr.add_argument("--decision", default=None, choices=("ACCEPT_JOIN", "REJECT_JOIN", "WATCH"))
    jr.add_argument("--reviewer", default=None)
    jr.add_argument("--reason", default="")
    jr.add_argument("--corpus", default=None, help="optionally resolve a corpus first to enqueue its deferred joins")
    jr.set_defaults(func=cmd_join_review)

    cons = sub.add_parser("consequences", help="derive capital catalysts + commercial consequences for one case")
    cons.add_argument("--case", required=True)
    cons.add_argument("--scoring-version", default="scoring_v1")
    cons.add_argument("--persist", action="store_true", help="persist catalysts/consequences to state")
    cons.set_defaults(func=cmd_consequences)

    cons_corpus = sub.add_parser("consequence-corpus", help="derive catalysts/consequences across a corpus")
    cons_corpus.add_argument("--corpus", default="examples/replay/corpus_m7.json")
    cons_corpus.add_argument("--scoring-version", default="scoring_v1")
    cons_corpus.add_argument("--verbose", action="store_true", help="include per-case catalyst/consequence detail")
    cons_corpus.add_argument("--persist", action="store_true")
    cons_corpus.set_defaults(func=cmd_consequence_corpus)

    prof = sub.add_parser("profile", help="build a real company capability profile as of a historical date")
    prof.add_argument("--company", required=True)
    prof.add_argument("--evidence", required=True, help="archived USAspending evidence JSON path")
    prof.add_argument("--as-of", default=None, help="ISO cutoff; omit for all-time")
    prof.add_argument("--geography", default=None)
    prof.set_defaults(func=cmd_profile)

    fit = sub.add_parser("fit", help="evaluate company capability fit for one case")
    fit.add_argument("--case", required=True)
    fit.add_argument("--persist", action="store_true")
    fit.set_defaults(func=cmd_fit)

    fit_corpus = sub.add_parser("fit-corpus", help="evaluate capability fit across a corpus")
    fit_corpus.add_argument("--corpus", default="examples/replay/corpus_m8.json")
    fit_corpus.add_argument("--verbose", action="store_true")
    fit_corpus.add_argument("--persist", action="store_true")
    fit_corpus.set_defaults(func=cmd_fit_corpus)

    contribution = sub.add_parser("source-contribution", help="measure source lift by deterministic replay ablation")
    contribution.add_argument("--corpus", default="examples/replay/corpus_m4.json")
    contribution.add_argument("--source", default=None)
    contribution.add_argument("--scoring-version", default="scoring_v1")
    contribution.set_defaults(func=cmd_source_contribution)

    # --- National-domain visibility (international operability / Phase 7/14) -----------------------
    dm = sub.add_parser("domains", help="inspect registered national government-intelligence domains")
    dm_sub = dm.add_subparsers(dest="subcmd", required=True)
    dm_l = dm_sub.add_parser("list", help="list national domains + activation posture")
    dm_l.set_defaults(func=cmd_domains_list)
    dm_s = dm_sub.add_parser("show", help="show one national domain's declared truth + sources")
    dm_s.add_argument("code", help="national code (US, AU, UK/GB, CA, NZ)")
    dm_s.set_defaults(func=cmd_domains_show)

    # --- Operator backup / restore control plane (Phase 7) ----------------------------------------
    # An operator must be able to back up and restore durable state without writing Python. These
    # honour PYRNOVA_STATE_DIR / PYRNOVA_ARCHIVE_DIR (via load_config), so they capture the *real*
    # live state even when it lives outside the release working directory (production layout).
    bk = sub.add_parser("backup", help="operator backup / restore of durable state (Phase 7/8)")
    bk_sub = bk.add_subparsers(dest="subcmd", required=True)
    bk_c = bk_sub.add_parser("create", help="create a verified backup of durable state into --dest")
    bk_c.add_argument("--dest", required=True, help="empty destination directory for the backup")
    bk_c.add_argument("--source-root", default=".", help="repo root (for db/schema.sql only)")
    bk_c.set_defaults(func=cmd_backup_create)
    bk_v = bk_sub.add_parser("verify", help="independently verify a backup's integrity")
    bk_v.add_argument("backup_dir")
    bk_v.set_defaults(func=cmd_backup_verify)
    bk_r = bk_sub.add_parser("restore", help="restore a backup into a clean, isolated --target")
    bk_r.add_argument("backup_dir")
    bk_r.add_argument("--target", required=True, help="clean/empty isolated target root")
    bk_r.add_argument("--no-verify", action="store_true", help="skip pre-restore integrity verification")
    bk_r.set_defaults(func=cmd_backup_restore)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
