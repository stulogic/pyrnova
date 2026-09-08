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

    def _collect(**kw):
        for _raw, results in client.search_awards(
            action_date_start=start, action_date_end=end, max_pages=3, limit=100, **kw
        ):
            for r in results:
                key = r.get("generated_internal_id") or r.get("Award ID")
                if key and key not in seen:
                    seen.add(key)
                    award_rows.append(r)

    # Pass 1 (anchor): the target company's own awards — incumbency + their upcoming recompetes.
    for name in profile.search_names:
        _collect(recipient_search=[name])
    # Pass 2 (market): recompete landscape in the target's NAICS they could compete for.
    if naics:
        _collect(naics_codes=naics)
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


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="pyrnova", description="Pyrnova Capture Radar kernel")
    sub = p.add_subparsers(dest="cmd", required=True)

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

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
