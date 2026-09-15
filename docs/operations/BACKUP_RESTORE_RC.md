# Backup / restore — release-candidate readiness (B4.8)

The backup + isolated-restore implementation (`pyrnova/backup.py`) is already accepted and is NOT
redesigned here. This records the release-readiness closure only.

## Verified for the release candidate

- **Isolated restore still passes after the B4.4 durability changes** — `test_backup_restore.py` green;
  restored JSONL is read back through the hardened `StateStore` (torn-tail-safe, fail-closed on corruption).
- **Release state paths are captured correctly** — the deploy layout (`ops/deploy/pyrnova-web.service.template`,
  `PYRNOVA_STATE_DIR=/srv/pyrnova/var/state`) matches the backup contract:
  `create_backup(source_root=/srv/pyrnova, ...)` captures `var/state/*.jsonl` + `var/archive/**` +
  `db/schema.sql`. (Fixed a mismatch introduced in the B4.6 draft where the service wrote to
  `/srv/pyrnova/state` while backup reads `var/state`.)
- **Backup ↔ deployable release SHA linkage** — the manifest records `source_commit`; a restore identifies
  the release SHA the state was captured under. Code rollback and data recovery stay distinct (B4.6):
  restoring state is a deliberate, separate operation from rolling back code.
- **Backups coordinate safely with active writes** — `create_backup` reads read-only with a torn-read
  guard and the manifest sha is computed over the bytes actually stored, so a backup taken during active
  appends is always self-consistent (`test_b4_backup_release.py`). The B4.4 `StateStore.snapshot` (shared
  lock, atomic temp+replace) is available for callers that want a lock-coordinated copy.
- **Rights compliance preserved** — restore reconciles restored state against current source-rights
  enforcement before any customer display (existing accepted behavior); backups do not resurrect prohibited
  display evidence, and derived/regenerable artifacts are recorded-as-excluded, never copied.

## Remaining EXTERNAL dependency

- **Off-host destination is NOT YET VERIFIED.** A real off-host/object-store destination (e.g. the `s3`
  extra / a remote target) requires infrastructure + credentials not available in this environment. The
  local backup/restore contract is complete and tested; the off-host copy is an explicit deployment
  dependency, not manufactured here.
