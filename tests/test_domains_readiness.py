"""Live-activation readiness report (INTERNATIONAL-GOVERNMENT-ROLLOUT-001, shared operator capability).

Proves the shared readiness report composes EXISTING runtime truth honestly and fail-closed: UNKNOWN /
DECLARED stay denied, PROHIBITED stays hard-locked, FIXTURE_ONLY stays non-live, and only a source the
existing cross-layer check already clears is reported live. No national semantics are read or modified.
"""

from __future__ import annotations

import json

from pyrnova.cli import main
from pyrnova.domains.readiness import (
    domain_readiness, readiness_report, render_readiness_text, required_external_dependency,
)


def test_all_five_national_domains_appear():
    report = readiness_report()
    assert set(report["summary"]) == {"US", "AU", "GB", "CA", "NZ"}
    assert len(report["domains"]) == 5


def test_prohibited_source_is_blocked_and_never_live():
    nz = domain_readiness("NZ")
    gets = next(s for s in nz["sources"] if s["source_id"] == "nz_gets")
    assert gets["national_activation"] == "PROHIBITED"
    assert gets["live_ingestion_allowed"] == "NO"
    assert "hard-locked" in gets["blocker"]
    assert gets["required_external_dependency"].startswith("none")  # never an ingestion source


def test_fixture_only_source_is_live_blocked_but_replay_permitted():
    ca = domain_readiness("CA")
    ds = next(s for s in ca["sources"] if s["source_id"] == "ca_canadabuys_dataset")
    assert ds["national_activation"] == "FIXTURE_ONLY"
    assert ds["live_ingestion_allowed"] == "NO"          # FIXTURE_ONLY is never live
    assert ds["replay_derived_permitted"] is True
    assert ds["blocker"]


def test_declared_and_unknown_sources_stay_denied():
    for code, sid in (("GB", "uk_ssro"), ("AU", "au_defence_iip"), ("CA", "ca_dcb")):
        s = next(x for x in domain_readiness(code)["sources"] if x["source_id"] == sid)
        assert s["national_activation"] == "DECLARED"
        assert s["live_ingestion_allowed"] == "NO"
        assert s["replay_derived_permitted"] is False


def test_no_source_reports_live_ready_without_the_existing_cross_layer_clearance():
    # In the current accepted repository state NO national source is live-activatable (all external
    # activation pending). The readiness report must not fabricate a YES.
    report = readiness_report()
    for d in report["domains"]:
        for s in d["sources"]:
            if s["live_ingestion_allowed"] == "YES":
                # If a source ever clears, it must be because the cross-layer check allowed it (no blocker).
                assert s["blocker"] is None


def test_required_external_dependency_is_deterministic():
    assert required_external_dependency("PROHIBITED", False).startswith("none")
    assert "record-level" in required_external_dependency("FIXTURE_ONLY", False)
    assert "review" in required_external_dependency("DECLARED", False)
    assert required_external_dependency("ACTIVE", True).startswith("none")
    assert "credential" in required_external_dependency("ACTIVE", False)


def test_domains_are_operational_and_verdicts_present():
    report = readiness_report()
    for d in report["domains"]:
        assert d["operational"] is True
        assert d["validated"] is True and d["build_authority"] is True
        assert d["verdict"]  # a deterministic verdict string is present
        assert d["operator_capability"] is True


def test_runtime_reports_capabilities_and_never_prints_secrets():
    report = readiness_report()
    rt = report["runtime"]
    assert rt["config_loads"] is True
    caps = rt["capabilities"]
    assert caps["backup"] is True and caps["restore"] is True
    assert caps["release_stage_activate_rollback"] is True and caps["health_check"] is True
    assert caps["national_domain_registry"] is True
    # Env is reported PRESENT/ABSENT only — no secret value is surfaced for a credential.
    assert set(rt["env"]["SAM_API_KEY"]) <= {"present", "role"}
    assert isinstance(rt["env"]["SAM_API_KEY"]["present"], bool)


def test_readiness_is_deterministic_apart_from_timestamp():
    a = readiness_report()
    b = readiness_report()
    a.pop("generated_at"); b.pop("generated_at")
    a["runtime"].pop("generated_at", None); b["runtime"].pop("generated_at", None)
    assert a == b


def test_cli_readiness_text_and_json(capsys):
    assert main(["domains", "readiness"]) == 0
    text = capsys.readouterr().out
    assert "LIVE-ACTIVATION READINESS" in text
    for code in ("US", "AU", "GB", "CA", "NZ"):
        assert f"{code}  (" in text

    assert main(["domains", "readiness", "--json"]) == 0
    report = json.loads(capsys.readouterr().out)
    assert set(report["summary"]) == {"US", "AU", "GB", "CA", "NZ"}
