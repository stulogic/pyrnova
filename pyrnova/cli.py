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


def _fixture_rows() -> tuple[list[dict], list[dict]]:
    awards = json.loads((FIXTURES / "usaspending_awards.json").read_text())["results"]
    notices = json.loads((FIXTURES / "sam_opportunities.json").read_text())["opportunitiesData"]
    return awards, notices


def _live_rows(cfg, profile: CapabilityProfile, as_of: date, window_days: int):
    from .sources.usaspending import USAspendingClient

    award_rows: list[dict] = []
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
                _raw, rows = sam.search(
                    posted_from=posted_from, posted_to=posted_to, ptype=ptype,
                    naics=(naics[0] if naics else None), limit=100,
                )
                notice_rows.extend(rows)
            except Exception as exc:  # pragma: no cover - network dependent
                print(f"[warn] SAM {ptype} fetch failed: {exc}", file=sys.stderr)
    else:
        print("[info] SAM_API_KEY not set — running recompete-only (USAspending). "
              "Set SAM_API_KEY to include pre-solicitation intelligence.", file=sys.stderr)
    return award_rows, notice_rows


def cmd_capture_radar(args) -> int:
    cfg = load_config()
    profile = _load_profile(args.profile)
    as_of = date.fromisoformat(args.as_of) if args.as_of else date.today()
    archive = build_archive(cfg)
    store = StateStore(cfg.state_dir)

    if args.fixtures:
        award_rows, notice_rows = _fixture_rows()
    else:
        award_rows, notice_rows = _live_rows(cfg, profile, as_of, args.window_days)

    report = run(
        profile=profile,
        award_rows=award_rows,
        notice_rows=notice_rows,
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
    print(f"awards / notices: {len(award_rows)} / {len(notice_rows)}")
    print(f"candidates      : {report.stats['candidates']}")
    print(f"STRIKEs         : {report.stats['strikes']} "
          f"(recompete {report.stats['recompete']}, presol {report.stats['presolicitation']})")
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
    cr.add_argument("--reviewer", default=None, help="human reviewer name (upgrades recommend→accept)")
    cr.set_defaults(func=cmd_capture_radar)

    sb = sub.add_parser("scoreboard", help="print accumulated scoreboard totals")
    sb.set_defaults(func=cmd_scoreboard)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
