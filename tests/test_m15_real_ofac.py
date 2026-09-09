"""M15 — guarded real-data linkage check.

Runs the M15 sanctions-exposure linkage against the REAL archived OFAC SDN list (19,365 designations,
proven archive-operational in M14). The archive lives under the git-ignored ``var/m14_archive/`` (raw
bytes are never committed — archive-once/replay-many), so this test SKIPS cleanly in CI / a fresh clone.
It exists to prove the same deterministic-identifier linkage code that the corpus exercises against the
committed illustrative fixture also runs on the real designation set — and that a real designation with
NO authoritative identifier link never becomes an authoritative sanctions hit.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from pyrnova import threat
from pyrnova.sources import ofac

_ARCHIVE = sorted(Path("var/m14_archive/sanctions_ofac").glob("sdn_*.csv"))


@pytest.mark.skipif(not _ARCHIVE, reason="real OFAC archive absent (git-ignored); replay-from-archive only")
def test_real_ofac_linkage_is_deterministic_and_safe():
    designations = ofac.parse_ofac_csv(_ARCHIVE[0].read_bytes(), list_name="sdn")
    assert len(designations) > 10000  # the real bulk list

    real = designations[0]  # a genuine designation from the archive
    # 1) A record that explicitly resolves to a real ent_num => CONFIRMED, deterministic_identifier.
    confirmed_records = [{
        "source_ref": "reg:probe", "available_at": "2024-01-01", "relation": "SUPPLIER",
        "counterparty_name": real["sdn_name"], "counterparty_ofac_ent_num": real["ent_num"],
    }]
    exposures, weak = threat.sanctions_exposures("co_probe", "Probe", confirmed_records, designations)
    assert len(exposures) == 1
    assert exposures[0].link_class == "CONFIRMED"
    assert exposures[0].join_method == "deterministic_identifier"

    # 2) A benign company sharing only a token with SOME real designation is a weak candidate, never a
    #    threat — the whole point of evidence-safe sanctions linkage.
    weak_records = [{
        "source_ref": "reg:benign", "available_at": "2024-01-01", "relation": "CUSTOMER",
        "counterparty_name": "Anytown County Water District",
    }]
    exps2, weak2 = threat.sanctions_exposures("co_benign", "Benign", weak_records, designations)
    threats, rejections = threat.assess_threats("co_benign", "Benign", exps2, [], weak_candidates=weak2)
    assert threats == []  # a name resemblance against 19k designations never authoritative
