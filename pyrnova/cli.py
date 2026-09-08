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
from datetime import date
from pathlib import Path

from . import scoreboard
from .archive import build_archive
from .acquisition import fetch_live_rows, fixture_rows
from .brief import render_capture_radar_report, render_signal_brief
from .config import load_config
from .match import CapabilityProfile
from .pipeline import run
from .state import StateStore

FIXTURES = Path(__file__).resolve().parent.parent / "tests" / "fixtures"


def _load_profile(path: str) -> CapabilityProfile:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return CapabilityProfile.from_dict(data)


def cmd_capture_radar(args) -> int:
    cfg = load_config()
    profile = _load_profile(args.profile)
    as_of = date.fromisoformat(args.as_of) if args.as_of else date.today()
    archive = build_archive(cfg)
    store = StateStore(cfg.state_dir)

    if args.fixtures:
        award_rows, notice_rows = fixture_rows(FIXTURES)
    else:
        award_rows, notice_rows, statuses = fetch_live_rows(
            cfg, profile, as_of, sam_lookback_days=args.lookback_days
        )
        for status in statuses:
            suffix = f" — {status.detail}" if status.detail else ""
            print(f"source {status.source}: {status.status} ({status.records} records){suffix}")

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
    cr.add_argument("--lookback-days", type=int, default=30, help="SAM posting lookback window")
    cr.add_argument("--threshold", type=float, default=0.3, help="relevance threshold for STRIKE")
    cr.add_argument("--min-amount", type=float, default=0.0, help="minimum award amount for recompete")
    cr.add_argument("--reviewer", default=None, help="human reviewer name (upgrades recommend→accept)")
    cr.set_defaults(func=cmd_capture_radar)

    sb = sub.add_parser("scoreboard", help="print accumulated scoreboard totals")
    sb.set_defaults(func=cmd_scoreboard)

    console = sub.add_parser("console", help="launch the local Operator Console")
    console.add_argument("--host", default="127.0.0.1")
    console.add_argument("--port", type=int, default=8765)
    console.set_defaults(func=lambda args: _serve_console(args.host, args.port))

    args = p.parse_args(argv)
    return args.func(args)


def _serve_console(host: str, port: int) -> int:
    from .console import serve

    serve(host=host, port=port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
