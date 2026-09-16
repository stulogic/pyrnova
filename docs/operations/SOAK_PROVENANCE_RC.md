# Immutable soak harness + SHA provenance (B4.10–11)

The Live Operations soak harness (`pyrnova/live_ops_acceptance.py`) is accepted and NOT redesigned.
B4.10–11 closes two release-readiness gaps on top of it: the documented restart rule was not
machine-enforced across cycles, and soak evidence had no single independently-recomputable integrity
chain. Nothing here starts a soak, changes intelligence semantics, source rights, or scoring.

## Immutability (machine-enforced)

| Requirement | Status | Evidence |
|---|---|---|
| Start pins the exact commit | IMPLEMENTED + TESTED | `SoakHarness.start` writes `manifest.commit = current HEAD`; `test_b4_soak_provenance.py::test_manifest_pins_commit_and_provenance_chain_verifies`. |
| Every cycle must run at the pinned commit | IMPLEMENTED + TESTED | `run_cycle` fails closed on `HEAD != manifest.commit` and records an `invalidates_soak` intervention; `::test_run_cycle_fails_closed_on_commit_drift`. |
| No cycle on a dirty tracked tree | IMPLEMENTED + TESTED | same guard rejects uncommitted tracked changes during an active soak; `::test_run_cycle_fails_closed_on_dirty_tracked_tree`. |

The restart rule ("any acceptance-critical code change restarts the seven-calendar-day / five-business-day
window") is now enforced by the harness, not only documented: drift cannot silently accrue evidence under
changed code.

## SHA provenance (independent, offline, fail-closed)

`pyrnova/soak_provenance.py` reads only the evidence the run already writes (`manifest.json`,
`cycles.jsonl`, `events.jsonl`) plus the append-only archive, and derives one reproducible
`chain_sha256` over the ordered per-cycle leaves. It owns no runtime.

| Guarantee | Status | Evidence |
|---|---|---|
| Every soak cycle ran at the pinned commit | IMPLEMENTED + TESTED | forged cycle commit detected; `::test_provenance_detects_forged_cycle_commit`. |
| Every referenced artifact re-hashes to its recorded SHA | IMPLEMENTED + TESTED | in-place tampering of archived bytes detected; `::test_provenance_detects_tampered_artifact_and_stale_chain`. |
| Stored provenance still matches the live evidence | IMPLEMENTED + TESTED | recomputed chain vs. stored `provenance.json` mismatch reported; same test. |
| No invalidating intervention recorded | IMPLEMENTED + TESTED | `::test_run_cycle_fails_closed_on_commit_drift` (drift → intervention → provenance fails closed). |
| Binds the pinned commit to an immutable staged release | IMPLEMENTED + TESTED | optional `released_shas` check ties the soak to the B4.6 release contract; `::test_provenance_binds_pinned_commit_to_staged_release`. |

Re-derivation over untouched evidence reproduces the exact `chain_sha256`; any edit to a cycle, its
commit, or an archived artifact changes it. `serve` keeps `provenance.json` current after each cycle, and
`python -m pyrnova.live_ops_acceptance provenance --plan <plan> --repo <repo>` verifies a run read-only
(exit 0 pass / 2 fail).

## Scope / non-goals

This is evidence integrity and immutability enforcement only. It does not itself run the 72-hour soak
(explicit owner action, still gated) and does not weaken any source-rights posture.
