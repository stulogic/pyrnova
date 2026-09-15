# Pyrnova — release / deploy / rollback runbook (B4.6)

Docker-free, single-node release mechanism. Code is served from an immutable, SHA-stamped release
directory selected by an atomically-swapped symlink; durable state and secrets live outside the release
payload and are never rolled back with code.

## Topology

```
Cloudflare edge/tunnel  ->  single production VM  ->  Pyrnova web/product (127.0.0.1:8765)
                                                   ->  Live Ops + watcher/alerts
                                                   ->  durable state (/srv/pyrnova/state)
                                                   ->  private evidence/backups
```

## Layout

```
/srv/pyrnova/releases/<sha>     immutable release artifact (exact git SHA; carries RELEASE.json)
/srv/pyrnova/current -> releases/<sha>   active release (atomic symlink swap)
/srv/pyrnova/state              DURABLE STATE — outside releases, never rolled back with code
/srv/pyrnova/evidence           private evidence
/srv/pyrnova/backups            local backup staging (off-host copy is a separate step)
/srv/pyrnova/venv               runtime venv (pip install -r requirements.lock.txt)
/etc/pyrnova/pyrnova.env        secrets/config — OUTSIDE the repo and release payload
```

Config/secrets are supplied via `EnvironmentFile=/etc/pyrnova/pyrnova.env` (systemd) and never committed.

## Deploy a new release

```sh
# 1. Stage an immutable artifact from a clean checkout at the release SHA (records SHA + lock hash).
ops/deploy/deploy.sh stage /path/to/checkout
#    -> prints the RELEASE.json manifest, including "sha".

# 2. Activate it: atomic symlink swap, restart services, health-verify (fails visibly on non-200).
ops/deploy/deploy.sh activate <sha>
```

Activation is fail-closed: a missing or unhealthy release is refused and `current` is left unchanged
(no silent partial release). Health is verified via the public `GET /healthz` probe, which returns the
active release SHA.

## Roll back (code only)

```sh
ops/deploy/deploy.sh rollback     # repoint current -> previously-activated release, restart, health-verify
```

Rollback moves **code** to the previous release. It does **NOT** touch `/srv/pyrnova/state` — code
rollback and data recovery are distinct operations. To recover DATA, use the backup/restore procedure
(`docs/operations/BACKUP_RESTORE_EVIDENCE.md`); restoring state is a deliberate, separate action.

## Inspect

```sh
ops/deploy/deploy.sh current      # active release SHA
ops/deploy/deploy.sh history      # activation/rollback audit log (/srv/pyrnova/activations.jsonl)
curl -fsS http://127.0.0.1:8765/healthz
```

## Failure modes (all visible, never silent)

- Staging refuses to overwrite an existing SHA (immutability).
- Staging publishes the artifact atomically (`.staging` dir + `os.replace`) — no half-copied release dir.
- Activation/rollback fail closed on a missing or unhealthy target; `current` is untouched.
- `deploy.sh` exits non-zero if the post-restart health check does not go green within the timeout.

## Underlying mechanism

`ops/deploy/deploy.sh` wraps `python -m pyrnova.release` (`pyrnova/release.py`): `stage_release`,
`activate`, `rollback`, `current`, `history`. Systemd units: `ops/deploy/pyrnova-web.service.template`
(+ the existing Live Ops unit). `WorkingDirectory=/srv/pyrnova/current` resolves the active release on each
(re)start, so a symlink swap + restart deterministically activates new code.
