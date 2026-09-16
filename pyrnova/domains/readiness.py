"""Live-activation readiness report — one shared operator view over EXISTING runtime state.

SHARE MECHANISM. KEEP NATIONAL TRUTH NATIONAL. This does NOT invent readiness and does NOT change any
national semantics or source-rights state. It COMPOSES what the repository already knows:

* the national domain registry (:mod:`pyrnova.domains`) — operational / validated / build-authority state;
* the cross-layer source status (:func:`pyrnova.domains.operator.domain_source_status`) — national
  activation posture × source-rights registry, live-activatable, and the exact blocker when not live;
* the runtime configuration (:mod:`pyrnova.config`) — required env / state / delivery / archive settings,
  reported as PRESENT/ABSENT only (never the secret values themselves);
* the presence of the shared deployment/runtime capabilities (backup/restore, release, health).

Fail-closed truth is preserved verbatim: UNKNOWN/DECLARED stays denied, PROHIBITED stays hard-locked, and
FIXTURE_ONLY stays non-live. A source is reported live-capable ONLY when the existing cross-layer check
already says so. Public accessibility is never read as authorization.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from . import all_domains, get_domain
from .base import SourceActivation
from .operator import domain_source_status

# National code -> lawful replay estate directory (the customer-product proof estate), if one exists.
_REPLAY_ESTATE = {
    "AU": "examples/au_replay",
    "NZ": "examples/nz_replay",
    "GB": "examples/uk_replay",
    "CA": "examples/ca_replay",
    # US exercises the shared customer product through the accepted bundle proofs, not a national replay dir.
}


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def required_external_dependency(activation: str, live_allowed: bool) -> str:
    """The exact external dependency that gates LIVE production ingestion for a source. Never faked."""
    if activation == SourceActivation.PROHIBITED.value:
        return "none — hard-locked; this source must NEVER be ingested"
    if live_allowed:
        return "none — rights-approved and live-transport permitted"
    if activation == SourceActivation.ACTIVE.value:
        # ACTIVE at the national layer but the registry denies live transport: the gate is a reviewed
        # endpoint/credential authorization (e.g. API key / allowed path), not a national-semantics change.
        return "live-transport / credential authorization (reviewed endpoint + API key where required)"
    if activation == SourceActivation.FIXTURE_ONLY.value:
        return "record-level / dataset source-rights approval before live activation (replay-derived only today)"
    return "source-rights review + approval (UNKNOWN => DENY)"


def domain_readiness(code: str, *, repo_root: Optional[Path] = None) -> dict:
    """Compose one national domain's live-activation readiness from existing runtime truth."""
    domain = get_domain(code)
    status = domain_source_status(domain.code)
    root = repo_root or Path.cwd()

    estate_rel = _REPLAY_ESTATE.get(domain.code)
    estate_present = bool(estate_rel and (root / estate_rel / "build_customer_proof.py").exists())

    sources = []
    blockers: list[str] = []
    for s in status["sources"]:
        live_allowed = bool(s["live_activatable"])
        activation = s["national_activation"]
        registry = s.get("registry_rights", {}) or {}
        dep = required_external_dependency(activation, live_allowed)
        blocker = None if live_allowed else s.get("blocked_live_activation")
        if blocker:
            blockers.append(f"{s['id']}: {blocker}")
        sources.append({
            "source_id": s["id"],
            "source_family": s["name"],
            "national_activation": activation,
            "registry_rights_state": registry.get("state") if registry.get("registered") else "UNREGISTERED",
            "live_ingestion_allowed": "YES" if live_allowed else "NO",
            "blocker": blocker,
            "replay_derived_permitted": bool(s["replay_derived_permitted"]),
            "required_external_dependency": dep,
        })

    operational = bool(status["operational"])
    any_live = any(s["live_ingestion_allowed"] == "YES" for s in sources)
    all_active = bool(sources) and all(
        s["national_activation"] == SourceActivation.ACTIVE.value for s in sources)
    if not operational:
        verdict = "NOT OPERATIONAL"
    elif any_live:
        verdict = "LIVE-CAPABLE (subject to runtime dependencies)"
    elif all_active:
        # National acquisition is validated and every source is nationally ACTIVE; only external activation
        # (credential / reviewed live transport) remains.
        verdict = "READY EXCEPT EXTERNAL ACTIVATION"
    else:
        verdict = "PRODUCT READY / LIVE DATA BLOCKED"

    return {
        "code": domain.code,
        "name": domain.name,
        "operational": operational,
        "validated": bool(domain.validated),
        "build_authority": bool(domain.build_authority),
        "dlt_calibrated": domain.dlt_calibration is not None,
        "customer_product_vertical": "operational" if operational else "not_operational",
        "replay_estate_present": estate_present,
        "customer_provisioning_capability": bool(operational and (estate_present or domain.code == "US")),
        "operator_capability": True,  # domains show/sources/lens/readiness + operator console (shared)
        "sources": sources,
        "external_blockers": sorted(set(blockers)),
        "verdict": verdict,
    }


def runtime_readiness(*, repo_root: Optional[Path] = None) -> dict:
    """Shared deployment/runtime readiness — config validation, required env (PRESENT/ABSENT only), and the
    presence of the backup/restore, release and health capabilities. Never prints secret values."""
    root = repo_root or Path.cwd()
    result: dict = {"config_loads": False}
    try:
        from ..config import load_config, load_alert_config
        cfg = load_config()
        result["config_loads"] = True
        result["state_dir"] = str(cfg.state_dir)
        result["out_dir"] = str(cfg.out_dir)
        result["archive_backend"] = cfg.archive_backend
        result["env"] = {
            "SAM_API_KEY": {"present": bool(cfg.sam_api_key), "role": "US SAM.gov live acquisition"},
            "PYRNOVA_DATABASE_URL": {"present": bool(cfg.database_url),
                                     "role": "durable database (optional; file state used when absent)"},
            "PYRNOVA_STATE_DIR": {"present": True, "role": "durable state path", "value": str(cfg.state_dir)},
        }
        if cfg.uses_s3:
            result["env"]["S3"] = {"present": bool(cfg.s3_bucket and cfg.s3_access_key_id),
                                   "role": "S3 archive backend"}
        try:
            alert = load_alert_config()
            result["delivery_smtp_configured"] = bool(getattr(alert, "delivery_configured", False))
        except Exception as exc:  # noqa: BLE001
            result["delivery_smtp_configured"] = False
            result["delivery_smtp_note"] = f"alert config unavailable: {exc}"
    except Exception as exc:  # noqa: BLE001
        result["config_error"] = str(exc)

    # Capability presence (import-only, no side effects). These are the shared deployment/runtime seams.
    def _cap(module: str, names: tuple[str, ...]) -> bool:
        try:
            mod = __import__(f"pyrnova.{module}", fromlist=list(names))
            return all(hasattr(mod, n) for n in names)
        except Exception:  # noqa: BLE001
            return False

    result["capabilities"] = {
        "backup": _cap("backup", ("create_backup", "verify_backup")),
        "restore": _cap("backup", ("restore_backup",)),
        "release_stage_activate_rollback": _cap("release", ("stage_release", "activate", "rollback")),
        "health_check": _cap("release", ("default_health_check",)),
        "national_domain_registry": len(all_domains()) > 0,
    }
    return result


def readiness_report(*, repo_root: Optional[Path] = None) -> dict:
    """The full shared live-activation readiness report across all five national domains + runtime."""
    domains = [domain_readiness(d.code, repo_root=repo_root) for d in all_domains()]
    return {
        "generated_at": _utcnow(),
        "runtime": runtime_readiness(repo_root=repo_root),
        "domains": domains,
        "summary": {d["code"]: d["verdict"] for d in domains},
    }


def render_readiness_text(report: dict) -> str:
    """Operator-facing plain-text rendering that makes the final state obvious."""
    lines: list[str] = []
    lines.append("PYRNOVA INTERNATIONAL — LIVE-ACTIVATION READINESS")
    lines.append(f"generated_at: {report.get('generated_at')}")
    lines.append("")
    rt = report.get("runtime", {})
    lines.append("RUNTIME / DEPLOYMENT")
    lines.append(f"  config loads: {rt.get('config_loads')}   archive backend: {rt.get('archive_backend')}")
    lines.append(f"  state dir: {rt.get('state_dir')}")
    for name, meta in (rt.get("env") or {}).items():
        lines.append(f"  env {name}: {'PRESENT' if meta.get('present') else 'ABSENT'} — {meta.get('role')}")
    lines.append(f"  delivery SMTP configured: {rt.get('delivery_smtp_configured')}")
    caps = rt.get("capabilities", {})
    lines.append("  capabilities: " + ", ".join(f"{k}={'YES' if v else 'NO'}" for k, v in caps.items()))
    lines.append("")
    for d in report.get("domains", []):
        lines.append(f"{d['code']}  ({d['name']})  —  {d['verdict']}")
        lines.append(f"  operational={d['operational']} validated={d['validated']} "
                     f"build_authority={d['build_authority']} dlt_calibrated={d['dlt_calibrated']}")
        lines.append(f"  customer-product vertical: {d['customer_product_vertical']} "
                     f"(replay estate present: {d['replay_estate_present']})")
        lines.append(f"  provisioning: {d['customer_provisioning_capability']}  operator: {d['operator_capability']}")
        lines.append("  sources:")
        for s in d["sources"]:
            lines.append(f"    - {s['source_id']} [{s['source_family']}]")
            lines.append(f"        national_activation={s['national_activation']} "
                         f"registry_rights={s['registry_rights_state']} "
                         f"live_ingestion_allowed={s['live_ingestion_allowed']}")
            if s["blocker"]:
                lines.append(f"        BLOCKER: {s['blocker']}")
            lines.append(f"        required external dependency: {s['required_external_dependency']}")
        lines.append("")
    return "\n".join(lines) + "\n"


__all__ = [
    "readiness_report", "domain_readiness", "runtime_readiness", "render_readiness_text",
    "required_external_dependency",
]
